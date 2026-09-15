#!/usr/bin/env python3
"""V4.1 独立"法律重大变化发现任务"。

本脚本**不**直接调用 web_search；web_search 由 agent 通过工具发起。脚本职责：

- `--emit-queries`：按 Topic × 变化类型生成结构化查询，输出 JSONL；
- `--ingest FILE`：从 stdin/文件读取 web_search 结果（JSONL），按官方域白名单
  去重、落盘到 metadata/change-candidates.jsonl；
- `--first-run`：仅校验脚本自身（state 文件、查询枚举），不调用 web_search；
  agent 必须另发起 1 个 web_search 验证接口，并将结果写入 `/tmp/v41-probe.jsonl`
  后用 `--ingest` 入库。

10 种变化：
1. 新法律公布或施行
2. 现行法律修改、修订、废止
3. 新行政法规
4. 与现有 Topic 直接相关的重要部门规章
5. 新司法解释
6. 司法解释修改或废止
7. 最高人民法院指导性案例发布
8. 指导性案例"不再参照"
9. 人民法院案例库重大规则性更新
10. 当前12个 Topic 直接相关的重要规范性文件变化
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "metadata" / "change-candidates.jsonl"
SCHEDULE_LOCK = ROOT / "metadata" / "discover-changes-state.json"

OFFICIAL_DOMAINS = [
    "npc.gov.cn",
    "gov.cn",
    "court.gov.cn",
    "moj.gov.cn",
    "samr.gov.cn",
    "ndrc.gov.cn",
    "mof.gov.cn",
    "mee.gov.cn",
    "mem.gov.cn",
    "mohurd.gov.cn",
]

TOPICS = [
    "civil-code",
    "company-law",
    "labor-contract-law",
    "tendering-bidding-law",
    "government-procurement-law",
    "land-administration-law",
    "urban-rural-planning-law",
    "construction-law",
    "work-safety-law",
    "environmental-protection-law",
    "administrative-penalty-law",
    "civil-procedure-law",
]

PRIMARY_LAW = {
    "civil-code": "中华人民共和国民法典",
    "company-law": "中华人民共和国公司法",
    "labor-contract-law": "中华人民共和国劳动合同法",
    "tendering-bidding-law": "中华人民共和国招标投标法",
    "government-procurement-law": "中华人民共和国政府采购法",
    "land-administration-law": "中华人民共和国土地管理法",
    "urban-rural-planning-law": "中华人民共和国城乡规划法",
    "construction-law": "中华人民共和国建筑法",
    "work-safety-law": "中华人民共和国安全生产法",
    "environmental-protection-law": "中华人民共和国环境保护法",
    "administrative-penalty-law": "中华人民共和国行政处罚法",
    "civil-procedure-law": "中华人民共和国民事诉讼法",
}

CHANGE_TYPES = [
    "new_law",
    "law_amendment",
    "law_repeal",
    "new_administrative_regulation",
    "new_department_rule",
    "new_judicial_interpretation",
    "judicial_interpretation_amendment",
    "judicial_interpretation_repeal",
    "guiding_case_release",
    "guiding_case_no_longer_reference",
    "court_database_rule_update",
    "normative_document_change",
]

CHANGE_TYPE_QUERIES = {
    "new_law":                          ["{law} 公布", "{law} 施行"],
    "law_amendment":                    ["{law} 修订", "{law} 修改"],
    "law_repeal":                       ["{law} 废止"],
    "new_administrative_regulation":    ["{law} 实施条例", "{law} 条例"],
    "new_department_rule":              ["{law} 办法", "{law} 部门规章"],
    "new_judicial_interpretation":      ["{law} 司法解释", "最高法 {law}"],
    "judicial_interpretation_amendment": ["{law} 司法解释 修改"],
    "judicial_interpretation_repeal":   ["{law} 司法解释 废止"],
    "guiding_case_release":             ["{law} 指导性案例", "最高法 指导性案例"],
    "guiding_case_no_longer_reference": ["指导性案例 不再参照", "最高法 不再参照"],
    "court_database_rule_update":       ["人民法院案例库 {law}", "案例库 规则参考"],
    "normative_document_change":        ["{law} 规范性文件", "市场监管总局 {law}"],
}

# 需主动通知的变化类型
NOTIFY_TYPES = {
    "new_law",
    "law_amendment",
    "law_repeal",
    "new_judicial_interpretation",
    "judicial_interpretation_repeal",
    "guiding_case_release",
    "guiding_case_no_longer_reference",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def doc_id(*parts: str) -> str:
    return "CHG-" + hashlib.sha1("|".join(parts).encode()).hexdigest()[:12].upper()


def extract_domain(url: str) -> str:
    m = re.search(r"https?://([^/]+)", url or "")
    return m.group(1) if m else ""


def is_official(url: str) -> bool:
    d = extract_domain(url)
    return any(d == dom or d.endswith("." + dom) for dom in OFFICIAL_DOMAINS)


def topic_for(title: str, url: str) -> list[str]:
    text = f"{title} {url}"
    out = []
    for tid, primary in PRIMARY_LAW.items():
        short = primary.replace("中华人民共和国", "")
        if short and short in text:
            out.append(tid)
    return out or ["(unknown)"]


def classify_change(title: str, snippet: str) -> str:
    text = f"{title} {snippet}"
    if any(k in text for k in ["不再参照", "不再指导", "废止参照"]):
        return "guiding_case_no_longer_reference"
    if any(k in text for k in ["指导性案例", "指导案例发布"]):
        return "guiding_case_release"
    if "司法解释" in text and "废止" in text:
        return "judicial_interpretation_repeal"
    if "司法解释" in text:
        return "new_judicial_interpretation"
    if any(k in text for k in ["修订", "修正", "修改"]):
        return "law_amendment"
    if any(k in text for k in ["条例"]):
        return "new_administrative_regulation"
    return "normative_document_change"


def load_seen_urls() -> set[str]:
    urls: set[str] = set()
    if STATE.exists():
        for line in STATE.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("source_url"):
                urls.add(rec["source_url"])
    return urls


def emit_queries(limit_topics: list[str] | None = None, limit_change_types: list[str] | None = None) -> None:
    topics = limit_topics or TOPICS
    for topic in topics:
        law = PRIMARY_LAW[topic]
        for ct in CHANGE_TYPES:
            if limit_change_types and ct not in limit_change_types:
                continue
            for q in CHANGE_TYPE_QUERIES.get(ct, []):
                rec = {
                    "topic": topic,
                    "primary_law": law,
                    "change_type": ct,
                    "query": q.format(law=law),
                    "domain_filter": OFFICIAL_DOMAINS,
                }
                print(json.dumps(rec, ensure_ascii=False))


def ingest_records(records: list[dict]) -> tuple[int, int]:
    seen = load_seen_urls()
    new_count = 0
    notify_count = 0
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with STATE.open("a", encoding="utf-8") as fh:
        for r in records:
            url = (r.get("url") or "").strip()
            if not url or url in seen or not is_official(url):
                continue
            title = (r.get("title") or "").strip()
            snippet = r.get("snippet") or ""
            classified = classify_change(title, snippet)
            rec = {
                "change_id": doc_id(classified, url),
                "title": title,
                "change_type": classified,
                "issuing_authority": "官方未逐项提取；按官方域名归属",
                "publication_date": None,
                "possible_effective_date": None,
                "related_topics": topic_for(title, url),
                "discovery_source": "MiniMax Search (agent)",
                "source_url": url,
                "discovered_at": now(),
                "verification_status": "UNVERIFIED",
                "snippet": (snippet[:300] + "…") if len(snippet) > 300 else snippet,
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            seen.add(url)
            new_count += 1
            if classified in NOTIFY_TYPES:
                notify_count += 1
    return new_count, notify_count


def write_lock(discovered: int, notify: int) -> None:
    SCHEDULE_LOCK.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_LOCK.write_text(
        json.dumps(
            {
                "last_run_at": now(),
                "task": "china-law-discover-changes-daily",
                "last_run_discovered": discovered,
                "last_run_important": notify,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="V4.1 法律重大变化发现任务（agent-driven）")
    p.add_argument("--dry-run", action="store_true", help="仅枚举查询，不写文件、不调用 web_search。")
    p.add_argument("--first-run", action="store_true",
                   help="校验脚本基础结构；不调用 web_search。agent 须另发起 1 个 web_search 验证接口。")
    p.add_argument("--emit-queries", action="store_true",
                   help="输出 JSONL 查询列表（每行一条），由 agent 调用 web_search。")
    p.add_argument("--topic", help="限定 emit-queries 的 Topic（逗号分隔）。")
    p.add_argument("--change-type", help="限定 emit-queries 的变化类型（逗号分隔）。")
    p.add_argument("--ingest", metavar="FILE", help="从 JSONL 读取 web_search 结果，去重落盘。")
    p.add_argument("--ingest-only-notify", action="store_true",
                   help="仅输出 NOTIFY_TYPES 中的 change_candidate。")
    args = p.parse_args()

    if args.dry_run:
        emit_queries()
        return 0

    if args.first_run:
        print("[FIRST-RUN] 校验脚本基础结构；不调用 web_search。")
        print(f"  候选源官方域白名单: {OFFICIAL_DOMAINS}")
        print(f"  Topic 数: {len(TOPICS)}")
        print(f"  变化类型数: {len(CHANGE_TYPES)}")
        print(f"  state 文件: {STATE}")
        write_lock(0, 0)
        print("[OK] state 初始化完成。下一步：agent 调用 web_search 1 次，验证接口。")
        return 0

    if args.emit_queries:
        topics = [t.strip() for t in (args.topic or "").split(",") if t.strip()] or None
        cts = [t.strip() for t in (args.change_type or "").split(",") if t.strip()] or None
        emit_queries(topics, cts)
        return 0

    if args.ingest:
        path = Path(args.ingest)
        if not path.exists():
            print(f"[ERR] 入库文件不存在: {path}", file=__import__("sys").stderr)
            return 2
        records = read_jsonl(path)
        new, notify = ingest_records(records)
        write_lock(new, notify)
        print(f"[ingest] 读取 {len(records)} 条；新增 change_candidate {new} 个；需通知 {notify} 个。")
        if args.ingest_only_notify and notify:
            print("\n--- 需要用户知晓的变化 ---")
            with STATE.open("r", encoding="utf-8") as fh:
                tail = list(fh.readlines())[-notify:]
            for line in tail:
                rec = json.loads(line)
                print(f"  · {rec['change_type']}  {rec['title']}")
                print(f"    source: {rec['source_url']}")
                print(f"    topics: {rec['related_topics']}")
        elif notify == 0:
            print("[silent] 未发现需用户知晓的重大变化。")
        return 0

    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())