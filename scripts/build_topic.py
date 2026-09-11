#!/usr/bin/env python3
"""V4 本地法律专题生成器。

只读取三个已存在的本地候选 clone 和本仓库 laws 元数据；不联网、不运行候选库脚本、
不复制候选正文。关系只依据标题/元数据明确关联，正文偶然出现主法名称不建立 core/direct 关系。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT.parent
TOPICS = ROOT / "legal-topics"
SOURCES = {
    "just-laws": WORKSPACE / "legal-sources" / "just-laws",
    "lawtext-laws": WORKSPACE / "legal-sources" / "laws",
    "china-data-laws": WORKSPACE / "legal-sources" / "china-data-laws",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_commit(path: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    out: dict[str, str] = {}
    for line in text[3:end].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            value = value.strip().strip("'\"")
            if value and not value.startswith("["):
                out[key.strip()] = value
    return out


def title_of(path: Path) -> tuple[str | None, dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, {}
    fm = parse_frontmatter(text[:12000])
    if fm.get("title"):
        return fm["title"].strip(), fm
    for line in text[:12000].splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip(), fm
    return None, fm


def rel(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def document_type(path: Path) -> str:
    parts = set(path.parts)
    if "司法解释" in parts:
        return "司法解释"
    if "部门规章" in parts:
        return "部门规章"
    if "行政法规" in parts:
        return "行政法规"
    if "规范性文件" in parts:
        return "规范性文件"
    return "法律"


def explicit_status(fm: dict[str, str]) -> str:
    status = fm.get("status", "")
    if any(x in status for x in ("废止", "失效")):
        return "repealed"
    if any(x in status for x in ("替代", "修订")):
        return "replaced"
    if any(x in status for x in ("有效", "现行")):
        return "effective"
    return "pending_verification"


def doc_id(source: str, path: str) -> str:
    digest = hashlib.sha1(f"{source}:{path}".encode()).hexdigest()[:12].upper()
    return f"LOCAL-{digest}"


def candidate_record(source: str, path: Path, title: str, primary: str, fm: dict[str, str], is_primary: bool = False) -> dict:
    root = SOURCES[source]
    rp = rel(path, root)
    explicit = title == primary or primary in title
    status = explicit_status(fm)
    record = {
        "document_id": doc_id(source, rp),
        "title": title,
        "document_type": document_type(path),
        "document_number": fm.get("document_number"),
        "issuing_authority": fm.get("author") or fm.get("issuing_authority"),
        "promulgation_date": fm.get("publication_date") or fm.get("date"),
        "effective_date": fm.get("effective_date"),
        "legal_status": status if status != "pending_verification" else "pending_verification",
        "relation_strength": "core" if is_primary else "direct",
        "verification_status": "CANDIDATE",
        "source_url": None,
        "candidate_sources": [{
            "source": source,
            "local_root": str(root),
            "relative_path": rp,
            "source_commit": git_commit(root),
            "verification_status": "CANDIDATE",
            "match_method": "title_exact" if title == primary else "title_contains_primary_law",
        }],
        "notes": "由本地候选库标题/元数据明确关联；未复制正文，未提升为 VERIFIED。",
    }
    if fm.get("urls"):
        record["source_url"] = fm["urls"].split(",")[0].strip()
    return record


def official_primary(primary: str) -> dict | None:
    index = ROOT / "metadata" / "index.jsonl"
    if not index.exists():
        return None
    for line in index.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("title") == primary:
            name = d.get("path", "").removeprefix("laws/")
            return {
                "document_id": f"OFFICIAL-{Path(name).stem}",
                "title": primary,
                "document_type": d.get("document_type", "法律"),
                "issuing_authority": d.get("issuing_authority"),
                "promulgation_date": d.get("promulgation_date"),
                "effective_date": d.get("effective_date"),
                "legal_status": "effective" if d.get("status") == "现行" else "pending_verification",
                "relation_strength": "core",
                "verification_status": "OFFICIAL_META",
                "local_path": d.get("path"),
                "official_url": d.get("official_url"),
                "candidate_sources": [],
                "notes": "本仓库现有官方元数据层；正文是否逐字核验由源文件 frontmatter 决定。",
            }
    return None


def scan_candidates(primary: str) -> tuple[list[dict], list[str]]:
    docs: list[dict] = []
    gaps: list[str] = []
    exact: list[tuple[str, Path, str, dict]] = []
    related: list[tuple[str, Path, str, dict]] = []
    for source, root in SOURCES.items():
        if not root.exists():
            gaps.append(f"候选源不存在: {source}")
            continue
        for path in root.rglob("*.md"):
            title, fm = title_of(path)
            if not title:
                continue
            if title == primary:
                exact.append((source, path, title, fm))
            elif primary in title:
                related.append((source, path, title, fm))

    official = official_primary(primary)
    if official:
        # 官方元数据层与本地候选全文定位可以并存；不复制候选正文。
        seen_sources = set()
        for source, path, title, fm in exact:
            if source in seen_sources:
                continue
            seen_sources.add(source)
            rp = rel(path, SOURCES[source])
            official.setdefault("candidate_sources", []).append({
                "source": source,
                "local_root": str(SOURCES[source]),
                "relative_path": rp,
                "source_commit": git_commit(SOURCES[source]),
                "verification_status": "CANDIDATE",
                "match_method": "title_exact",
            })
        docs.append(official)
    elif exact:
        source, path, title, fm = sorted(exact, key=lambda x: (list(SOURCES).index(x[0]), str(x[1])))[0]
        docs.append(candidate_record(source, path, title, primary, fm, is_primary=True))
    else:
        gaps.append("主法律未在本地官方元数据或候选库中唯一找到")

    seen: set[tuple[str, str]] = set()
    for source, path, title, fm in sorted(related, key=lambda x: (x[0], str(x[1]))):
        key = (source, rel(path, SOURCES[source]))
        if key in seen:
            continue
        seen.add(key)
        docs.append(candidate_record(source, path, title, primary, fm))
    if not related:
        gaps.append("未发现标题明确包含主法律名称的配套行政法规、部门规章、司法解释或规范性文件")
    return docs, gaps


def build(primary: str, topic_id: str) -> Path:
    out_dir = TOPICS / topic_id
    out_dir.mkdir(parents=True, exist_ok=True)
    if topic_id == "company-law" and (out_dir / "manifest.json").exists():
        # 公司法为冻结参考模板；只补通用 V4 版本字段，不重建其人工校正内容。
        data = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        data.setdefault("topic", {})["schema_version"] = "V4"
        data["topic"]["topic_status"] = "frozen_reference_template"
        data.setdefault("update_state", {})["last_generated_at"] = now()
        (out_dir / "manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return out_dir

    docs, gaps = scan_candidates(primary)
    data = {
        "topic": {
            "id": topic_id,
            "title": f"{primary}专题",
            "primary_law": primary,
            "primary_document_id": docs[0]["document_id"] if docs else None,
            "schema_version": "V4",
            "topic_status": "generated_local_candidate",
            "generated_at": now(),
            "data_sources": [f"{k}: local read-only clone" for k in SOURCES],
        },
        "documents": docs,
        "documents_related": [],
        "case_collections": [],
        "cases": [],
        "cases_related": [],
        "statistics": {},
        "verification": {"generated_by": "scripts/build_topic.py", "no_government_network": True},
        "known_gaps": gaps + ["案例层未自动归类；需后续提供唯一可靠案例身份与本地材料。"],
        "update_state": {"generated_at": now(), "candidate_commits": {k: git_commit(v) for k, v in SOURCES.items()}},
    }
    from collections import Counter
    data["statistics"] = {
        "documents_total": len(docs),
        "documents_by_type": dict(Counter(x.get("document_type") for x in docs)),
        "documents_by_verification_status": dict(Counter(x.get("verification_status") for x in docs)),
        "documents_by_legal_status": dict(Counter(x.get("legal_status") for x in docs)),
        "documents_by_relation_strength": dict(Counter(x.get("relation_strength") for x in docs)),
        "cases_total": 0,
    }
    (out_dir / "manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "README.md").write_text(
        f"# {primary}专题\n\n由 V4 本地生成器创建。仅收录本地元数据和候选文件定位，不复制候选正文；`CANDIDATE` 不得作为最终法律依据。\n\n已知缺口：\n" +
        "\n".join(f"- {x}" for x in data["known_gaps"]) + "\n", encoding="utf-8")
    return out_dir


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--primary-law", required=True)
    p.add_argument("--topic-id", required=True)
    args = p.parse_args()
    out = build(args.primary_law, args.topic_id)
    print(f"[OK] {out / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
