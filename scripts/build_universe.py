#!/usr/bin/env python3
"""V5 canonical 法律规范总目录 + current-version-registry + local-legal-assets + business map + gaps + freshness gate 构建器.

完全本地；只读三个候选源；不复制候选正文到 GitHub 仓库；SHA256 索引本地只读。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT.parent
SOURCES = {
    "just-laws":      WORKSPACE / "legal-sources" / "just-laws",
    "lawtext-laws":   WORKSPACE / "legal-sources" / "laws",
    "china-data-laws":WORKSPACE / "legal-sources" / "china-data-laws",
}

OUT_DIR = ROOT / "metadata"
OUT_DIR.mkdir(parents=True, exist_ok=True)

NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# V5 业务一级领域（spec 十四）
BUSINESS_DOMAINS = [
    ("01", "民商事基础", ["civil-code"]),
    ("02", "公司治理", ["company-law"]),
    ("03", "合同与担保", ["civil-code", "company-law"]),
    ("04", "劳动人事", ["labor-contract-law"]),
    ("05", "招标投标", ["tendering-bidding-law"]),
    ("06", "政府采购", ["government-procurement-law"]),
    ("07", "工程建设", ["construction-law"]),
    ("08", "EPC / EPCO / 工程总承包", ["tendering-bidding-law", "construction-law", "civil-code"]),
    ("09", "房地产与工业地产", ["civil-code", "land-administration-law", "urban-rural-planning-law"]),
    ("10", "土地管理", ["land-administration-law"]),
    ("11", "城乡规划", ["urban-rural-planning-law"]),
    ("12", "产业园区开发运营", ["land-administration-law", "urban-rural-planning-law", "company-law"]),
    ("13", "招商引资", ["company-law", "civil-code", "land-administration-law"]),
    ("14", "国有资产与国有企业", ["company-law", "civil-code"]),
    ("15", "政府平台公司", ["company-law"]),
    ("16", "投资并购", ["company-law", "civil-code"]),
    ("17", "私募基金", ["company-law", "civil-code"]),
    ("18", "政府投资基金 / 引导基金", ["company-law"]),
    ("19", "企业融资与金融", ["company-law", "civil-code"]),
    ("20", "税务财政", ["civil-code"]),
    ("21", "企业登记与市场监管", ["company-law"]),
    ("22", "安全生产", ["work-safety-law"]),
    ("23", "消防", ["work-safety-law"]),
    ("24", "环境保护", ["environmental-protection-law"]),
    ("25", "节能与双碳", ["environmental-protection-law"]),
    ("26", "分布式光伏", ["environmental-protection-law"]),
    ("27", "储能", ["environmental-protection-law"]),
    ("28", "电力与综合能源", ["environmental-protection-law"]),
    ("29", "行政许可", ["administrative-penalty-law", "civil-procedure-law"]),
    ("30", "行政处罚", ["administrative-penalty-law"]),
    ("31", "行政复议", ["administrative-penalty-law", "civil-procedure-law"]),
    ("32", "行政诉讼", ["administrative-penalty-law", "civil-procedure-law"]),
    ("33", "民事诉讼", ["civil-procedure-law"]),
    ("34", "仲裁", ["civil-procedure-law"]),
    ("35", "强制执行", ["civil-procedure-law"]),
    ("36", "企业破产", ["company-law", "civil-procedure-law"]),
    ("37", "知识产权", ["civil-code"]),
    ("38", "数据安全", ["civil-code"]),
    ("39", "网络安全", ["civil-code"]),
    ("40", "个人信息保护", ["civil-code"]),
    ("41", "人工智能相关合规", ["civil-code"]),
    ("42", "反不正当竞争", ["civil-code"]),
    ("43", "反垄断", ["civil-code"]),
    ("44", "广告与宣传", ["civil-code", "administrative-penalty-law"]),
    ("45", "企业信用", ["administrative-penalty-law"]),
    ("46", "产业扶持资金", ["civil-code", "company-law"]),
    ("47", "政府补贴与专项资金", ["civil-code", "company-law"]),
    ("48", "商协会 / 社会组织", ["civil-code"]),
    ("49", "拍卖业务", ["civil-code", "administrative-penalty-law"]),
    ("50", "律师业务相关程序规范", ["civil-procedure-law", "administrative-penalty-law"]),
    ("51", "与产业园区经营直接相关的其他必要专题", ["land-administration-law", "company-law"]),
]

TOPIC_KEYWORDS = {
    "tendering-bidding-law": ["招标投标", "招标", "投标", "必须招标", "邀请招标"],
    "civil-code":            ["民法典", "民法", "物权", "合同", "人格权", "侵权"],
    "company-law":           ["公司法", "股东", "出资", "减资", "公司治理"],
    "labor-contract-law":    ["劳动合同", "用人单位", "劳动者", "经济补偿"],
    "government-procurement-law": ["政府采购", "采购人", "供应商", "采购代理"],
    "land-administration-law":["土地", "建设用地", "农用地", "土地征收"],
    "urban-rural-planning-law":["城乡规划", "城市规划", "选址意见书"],
    "construction-law":      ["建筑", "建设", "施工", "监理", "竣工"],
    "work-safety-law":       ["安全生产", "安全", "事故", "应急"],
    "environmental-protection-law": ["环境保护", "环境影响评价", "排污"],
    "administrative-penalty-law": ["行政处罚", "罚款", "听证"],
    "civil-procedure-law":   ["民事诉讼", "起诉", "受理", "管辖", "判决"],
}


def sha256_file(p: Path) -> str | None:
    h = hashlib.sha256()
    try:
        with p.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def git_commit(path: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def normalize_title(t: str) -> str:
    return re.sub(r"[\s ]+", "", (t or "")).strip()


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    out: dict[str, str] = {}
    for line in text[3:end].splitlines():
        k, sep, v = line.partition(":")
        if sep:
            v = v.strip().strip("'\"")
            if v and not v.startswith("["):
                out[k.strip()] = v
    return out


def first_heading(text: str) -> str | None:
    for line in text.splitlines()[:50]:
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
    return None


# V5.0.1 严格 12 类 document_type 枚举
DOCUMENT_TYPES = [
    "constitution",
    "law",
    "legislative_interpretation",
    "administrative_regulation",
    "supervision_regulation",
    "department_rule",
    "normative_document",
    "judicial_interpretation",
    "local_regulation",
    "local_government_rule",
    "local_normative_document",
    "other",
]

# lawtext-laws frontmatter group → 12 类严格映射
LAWTEXT_GROUP_TO_TYPE = {
    "司法解释": "judicial_interpretation",
    "行政法规": "administrative_regulation",
    "法律": "law",
    "法律解释": "legislative_interpretation",
    "宪法": "constitution",
    "监察法规": "supervision_regulation",
    "修正案": "normative_document",
    "修改、废止的决定": "normative_document",
    "有关法律问题和重大问题的决定（部分）": "normative_document",
    "资料": "other",
}

# china-data-laws 路径分类 → 12 类（注意：经济法/行政法/社会法/刑法/民法商法/诉讼与非诉讼程序法是主法律的子分类）
CHINA_DATA_DIR_TO_TYPE = {
    "地方性法规": "local_regulation",
    "地方政府规章": "local_government_rule",
    "地方规章": "local_government_rule",
    "地方规范性文件": "local_normative_document",
    "行政法规": "administrative_regulation",
    "部门规章": "department_rule",
    "司法解释": "judicial_interpretation",
    "宪法": "constitution",
    "宪法相关法": "law",
    "法律": "law",
    "经济法": "law",
    "行政法": "law",
    "社会法": "law",
    "刑法": "law",
    "民法商法": "law",
    "诉讼与非诉讼程序法": "law",
    "案例": "other",
    "资料": "other",
}

# 中国省份列表（用于 china-data-laws 地方规范的 province 字段）
CHINA_PROVINCES = [
    "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
    "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海",
    "内蒙古", "广西", "西藏", "宁夏", "新疆", "台湾",
    "香港特别行政区", "澳门特别行政区",
]


def classify_doc_type(group: str | None, path: Path) -> str:
    """V5.0.1 严格 12 类分类。优先级：lawtext group > china-data 路径 > just-laws 路径。"""
    rel = str(path)
    parts = set(path.parts)
    # 1. lawtext-laws frontmatter group
    if group and group in LAWTEXT_GROUP_TO_TYPE:
        return LAWTEXT_GROUP_TO_TYPE[group]
    # 2. china-data-laws 路径分类（顶级目录）
    for part in parts:
        for p in [part]:
            # 路径组件顶层即 china-data 分类
            if rel.endswith("china-data-laws.md") or "china-data-laws" in rel:
                pass
    # 检测 china-data-laws 路径
    if "china-data-laws" in rel:
        # 取相对 china-data-laws 后的第一层目录
        try:
            rel_to_root = Path(rel).relative_to(Path(rel).parts[0]) if False else None
        except Exception:
            rel_to_root = None
        # 直接枚举 parts
        rel_parts = list(Path(rel).parts)
        for i, part in enumerate(rel_parts):
            if part == part and part in CHINA_DATA_DIR_TO_TYPE:
                return CHINA_DATA_DIR_TO_TYPE[part]
        # 省级地方性法规
        for part in rel_parts:
            if part in CHINA_PROVINCES:
                return "local_regulation"
    # 3. just-laws 路径：docs/<category>/<law>/README.md → law
    if "/docs/" in rel and "/just-laws" in rel:
        # 若路径包含 constitution 子目录，归 constitution；否则归 law
        if "/constitution/" in rel or "/constitutional-relevance/" in rel:
            return "law"  # constitutional-relevance 是相关法，仍归 law
        return "law"
    # 4. lawtext-laws content/法律/<file>.md → law
    if "/content/法律/" in rel:
        return "law"
    # 5. lawtext-laws content/<其他> → 走 CHINA_DATA_DIR_TO_TYPE 同款
    if "/laws/" in rel and "/legal-sources/laws/" in rel:
        # 取 content/ 后第一层
        for part in parts:
            if part in CHINA_DATA_DIR_TO_TYPE:
                return CHINA_DATA_DIR_TO_TYPE[part]
    return "other"


def province_from_path(path: Path) -> str | None:
    """从 china-data-laws 路径提取省份。"""
    parts = list(path.parts)
    for part in parts:
        if part in CHINA_PROVINCES:
            return part
    return None


def infer_document_type_from_path(path: Path) -> str | None:
    """V5.0.1 deprecated：保留旧接口，内部转调 classify_doc_type。"""
    return classify_doc_type(None, path)


def parse_md(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    fm = parse_frontmatter(text)
    title = fm.get("title") or first_heading(text)
    if not title:
        return {}
    group = fm.get("group") or fm.get("document_type")
    doc_type = classify_doc_type(group, path)
    return {
        "title": title.strip(),
        "document_type": doc_type,
        "issuing_authority": fm.get("author") or fm.get("issuing_authority"),
        "document_number": fm.get("document_number"),
        "publication_date": fm.get("publication_date") or fm.get("date"),
        "effective_date": fm.get("effective_date"),
        "status_text": fm.get("status"),
        "urls": fm.get("urls"),
        "groups": fm.get("group"),
        "categories": fm.get("categories"),
        "province": province_from_path(path),
    }


def derive_legal_status(d: dict) -> str:
    s = (d.get("status_text") or "").strip()
    if "有效" in s or "现行" in s or "未生效" in s:
        return "effective" if s != "未生效" else "not_yet_effective"
    if "废止" in s:
        return "repealed"
    if "失效" in s:
        return "expired"
    if "修订" in s or "修正" in s or "修改" in s:
        return "amended"
    if "替代" in s or "被新法替代" in s:
        return "replaced"
    return "unknown"


def derive_version_status(d: dict, title: str) -> str:
    if "修订" in (d.get("status_text") or ""):
        return "historical"
    if "废止" in (d.get("status_text") or "") or "失效" in (d.get("status_text") or ""):
        return "historical"
    return "current"


def canonical_key(d: dict) -> str:
    bbbs = d.get("bbbs")
    if bbbs:
        return f"bbbs:{bbbs}"
    if d.get("document_number"):
        return f"doc_no:{d['document_number']}"
    return f"tad:{normalize_title(d.get('title') or '')}|{d.get('issuing_authority') or ''}|{d.get('publication_date') or ''}"


def scan_source(name: str, root: Path) -> list[dict]:
    if not root.exists():
        return []
    out: list[dict] = []
    commit = git_commit(root)
    for path in root.rglob("*.md"):
        info = parse_md(path)
        if not info.get("title"):
            continue
        rel = str(path.resolve().relative_to(root.resolve()))
        sha = sha256_file(path)
        rec = dict(info)
        rec["source"] = name
        rec["local_root"] = str(root)
        rec["candidate_path"] = rel
        rec["source_commit"] = commit
        rec["canonical_key"] = canonical_key(rec)
        rec["local_text_available"] = True
        rec["local_file_size"] = path.stat().st_size if path.exists() else 0
        rec["local_sha256"] = sha
        out.append(rec)
    return out


def scan_laws_dir() -> list[dict]:
    out: list[dict] = []
    for path in sorted((ROOT / "laws").glob("*.md")):
        info = parse_md(path)
        if not info.get("title"):
            continue
        sha = sha256_file(path)
        rec = dict(info)
        rec["source"] = "china-law-verified/laws"
        rec["local_root"] = str(ROOT / "laws")
        rec["candidate_path"] = path.name
        rec["source_commit"] = None
        rec["canonical_key"] = canonical_key(rec)
        rec["local_text_available"] = True
        rec["local_file_size"] = path.stat().st_size if path.exists() else 0
        rec["local_sha256"] = sha
        out.append(rec)
    return out


def build_universe() -> dict:
    all_records: list[dict] = []
    for name, root in SOURCES.items():
        all_records.extend(scan_source(name, root))
    all_records.extend(scan_laws_dir())

    canonicals: dict[str, dict] = {}
    for r in all_records:
        k = r["canonical_key"]
        c = canonicals.setdefault(k, {
            "canonical_document_id": "CD-" + hashlib.sha1(k.encode()).hexdigest()[:12].upper(),
            "title": r["title"],
            "issuing_authority": r.get("issuing_authority"),
            "document_number": r.get("document_number"),
            "publication_date": r.get("publication_date"),
            "original_effective_date": r.get("effective_date"),
            "current_version_date": None,
            "current_version_effective_date": None,
            "document_type": r.get("document_type") or "未分类",
            "legal_status": "unknown",
            "version_status": "unknown",
            "verification_status": "UNVERIFIED",
            "official_source_url": (r.get("urls") or "").split(",")[0].strip() if r.get("urls") else None,
            "candidate_sources": [],
            "candidate_paths": [],
            "source_commits": {},
            "related_primary_laws": [],
            "related_topics": [],
            "last_local_update_at": NOW,
            "last_status_checked_at": NOW,
            "official_last_verified_at": None,
            "_records": [],
        })
        # 记录候选副本
        cs_entry = {
            "source": r["source"],
            "relative_path": r["candidate_path"],
            "local_root": r["local_root"],
            "source_commit": r["source_commit"],
            "verification_status": "CANDIDATE" if r["source"] != "china-law-verified/laws" else "OFFICIAL_META",
            "match_method": "canonical_key_match",
            "local_text_available": r["local_text_available"],
            "local_sha256": r["local_sha256"],
            "local_file_size": r["local_file_size"],
        }
        c["candidate_sources"].append(cs_entry)
        c["candidate_paths"].append(f"{r['source']}::{r['candidate_path']}")
        if r["source_commit"]:
            c["source_commits"][r["source"]] = r["source_commit"]
        # 本仓 laws/ 来源的元数据更权威
        if r["source"] == "china-law-verified/laws":
            c["verification_status"] = "OFFICIAL_META"
            if r.get("publication_date"):
                c["publication_date"] = r["publication_date"]
            if r.get("effective_date"):
                c["original_effective_date"] = r["effective_date"]
        else:
            # 候选源默认 CANDIDATE：有 title/authority/dates 等可用元数据可用于定位分析。
            if c.get("verification_status") == "UNVERIFIED":
                c["verification_status"] = "CANDIDATE"
        c["_records"].append(r)
        c["related_topics"] = sorted({t for t in c["related_topics"] if t} | {
            t for t in TOPIC_KEYWORDS if any(k in (r["title"] or "") for k in TOPIC_KEYWORDS[t])
        })
        # V5.0.1：document_type 不再合并主法律／法律；严格保留 12 类
        c["province"] = r.get("province") or c.get("province")

    # 计算 legal_status / version_status / current_version_date
    for c in canonicals.values():
        records = c["_records"]
        # 选生效日期最大的代表性记录
        def eff_key(r):
            return r.get("effective_date") or r.get("publication_date") or ""
        latest = max(records, key=eff_key) if records else None
        if latest:
            c["current_version_date"] = latest.get("publication_date")
            c["current_version_effective_date"] = latest.get("effective_date")
            c["legal_status"] = derive_legal_status(latest)
            c["version_status"] = derive_version_status(latest, c["title"])
        # 关联主法（topic->primary_law）
        for topic in c["related_topics"]:
            c["related_primary_laws"].append(topic)
        # freshness_status 在所有状态字段确定后计算并入 canonical
        c["freshness_status"] = freshness_status(c)

    return {"canonicals": canonicals, "raw_count": len(all_records)}


def freshness_status(c: dict) -> str:
    """FRESH/STALE/UNKNOWN/CONFLICT."""
    if c["legal_status"] == "unknown" or c["version_status"] == "unknown":
        return "UNKNOWN"
    # 判断冲突：候选源间 status_text 不一致
    statuses = {r.get("status_text") for r in c["_records"] if r.get("status_text")}
    if len(statuses) > 1:
        return "CONFLICT"
    if c["version_status"] == "historical":
        return "STALE"
    return "FRESH"


def build_local_assets(universe: dict) -> dict:
    by_source_count: dict[str, int] = {}
    by_source_size: dict[str, int] = {}
    by_source_commit: dict[str, str] = {}
    text_total = 0
    for name, root in SOURCES.items():
        cnt = 0
        sz = 0
        for path in root.rglob("*.md"):
            cnt += 1
            try:
                sz += path.stat().st_size
            except OSError:
                pass
        by_source_count[name] = cnt
        by_source_size[name] = sz
        by_source_commit[name] = git_commit(root)
        text_total += cnt
    out = {
        "generated_at": NOW,
        "candidate_sources": {
            name: {
                "local_root": str(root),
                "git_commit": by_source_commit[name],
                "file_count": by_source_count[name],
                "disk_bytes": by_source_size[name],
                "human_size": _human_size(by_source_size[name]),
            } for name, root in SOURCES.items()
        },
        "candidate_total_files": text_total,
        "candidate_total_human": _human_size(sum(by_source_size.values())),
        "repo_laws_files": 0,
        "repo_laws_total_bytes": 0,
    }
    p = ROOT / "laws"
    if p.exists():
        for f in p.glob("*.md"):
            out["repo_laws_files"] += 1
            try:
                out["repo_laws_total_bytes"] += f.stat().st_size
            except OSError:
                pass
    return out


def _human_size(n: int) -> str:
    f = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if f < 1024 or unit == "GB":
            return f"{f:.1f} {unit}"
        f /= 1024
    return f"{n} B"


def build_current_version_registry(universe: dict) -> dict:
    out: list[dict] = []
    for key, c in universe["canonicals"].items():
        if c["version_status"] != "current":
            continue
        out.append({
            "canonical_document_id": c["canonical_document_id"],
            "title": c["title"],
            "current_version_date": c["current_version_date"],
            "current_version_effective_date": c["current_version_effective_date"],
            "legal_status": c["legal_status"],
            "version_status": c["version_status"],
            "official_source_url": c["official_source_url"],
            "candidate_sources": [s["source"] for s in c["candidate_sources"]],
            "candidate_paths": c["candidate_paths"],
            "source_commits": c["source_commits"],
            "last_checked_at": NOW,
            "check_method": "candidate_metadata_scan",
            "verification_status": c["verification_status"],
            "freshness_status": freshness_status(c),
        })
    return {"generated_at": NOW, "current_count": len(out), "current_versions": out}


def build_business_legal_map(universe: dict) -> dict:
    """51 个一级领域，每个关联已识别到的 canonical。"""
    domains = []
    canonicals = universe["canonicals"]
    for code, name, topic_ids in BUSINESS_DOMAINS:
        linked = []
        for key, c in canonicals.items():
            if any(t in c["related_topics"] for t in topic_ids):
                linked.append(c["canonical_document_id"])
        domains.append({
            "domain_code": code,
            "domain_name": name,
            "related_topics": topic_ids,
            "linked_canonical_count": len(linked),
            "linked_canonicals_sample": sorted(set(linked))[:5],
            "priority": "P0" if code in {"01","02","03","04","05","06","07","08","09","10","11","14","15","16","22","24","29","33","36"} else "P1",
            "local_text_count": sum(
                1 for cid in linked
                for cs in canonicals[next(k for k,cv in canonicals.items() if cv["canonical_document_id"]==cid)]["candidate_sources"]
                if cs["local_text_available"]
            ),
        })
    return {"generated_at": NOW, "domain_count": len(domains), "domains": domains}


def build_gaps(universe: dict) -> dict:
    """P0 硬标准缺口 + 已知缺口。"""
    canonicals = universe["canonicals"]
    gaps: list[dict] = []
    # P0 主法律：核心 12 个 Topic 的主法本体
    for topic in ["civil-code","company-law","labor-contract-law","tendering-bidding-law","government-procurement-law","land-administration-law","urban-rural-planning-law","construction-law","work-safety-law","environmental-protection-law","administrative-penalty-law","civil-procedure-law"]:
        found = any(t == topic for c in canonicals.values() for t in c["related_topics"])
        if not found:
            gaps.append({
                "business_domain": topic,
                "topic_id": topic,
                "missing_type": "primary_law",
                "expected_document": "现行主法律全文",
                "reason": "本仓库 laws/ 与候选源均未唯一找到该 Topic 主法律",
                "priority": "P0",
                "recommended_action": "人工在 flk.npc.gov.cn 浏览器补齐 laws/<topic>.md",
                "detected_at": NOW,
            })
    # 已收录主法律但缺正式正文：VERIFIED 或 OFFICIAL_META 主法律的本地 laws/ 全文待补
    for c in canonicals.values():
        if c["verification_status"] == "OFFICIAL_META" and c["legal_status"] == "effective":
            # 当前 laws/ 文件
            rec = next((r for r in c["_records"] if r["source"] == "china-law-verified/laws"), None)
            if rec and rec["local_file_size"] < 4000:  # 占位文件
                gaps.append({
                    "business_domain": c["related_topics"][0] if c["related_topics"] else "(unknown)",
                    "topic_id": c["related_topics"][0] if c["related_topics"] else None,
                    "missing_type": "verified_full_text",
                    "expected_document": c["title"],
                    "reason": "laws/ 仅有结构树与占位，未逐字官方核验",
                    "priority": "P0",
                    "recommended_action": "在 flk.npc.gov.cn 浏览器复制正文并人工补齐 laws/",
                    "detected_at": NOW,
                })
    return {"generated_at": NOW, "gaps": gaps}


def write_local_assets_md(asset: dict) -> str:
    lines = ["# 本地法律资产清单 (V5)", "", f"_生成时间：{asset['generated_at']}_", "",
             "## 候选源", "",
             "| 候选源 | Git commit | 文件数 | 磁盘占用 |",
             "| --- | --- | ---: | ---: |"]
    for name, info in asset["candidate_sources"].items():
        lines.append(f"| {name} | `{info['git_commit'] or 'N/A'}` | {info['file_count']} | {info['human_size']} |")
    lines += [
        "",
        f"- 候选源总文件数：**{asset['candidate_total_files']}**",
        f"- 候选源总磁盘占用：**{asset['candidate_total_human']}**",
        f"- 本仓库 `laws/` 收录：{asset['repo_laws_files']} 个官方元数据文件，{asset['repo_laws_total_bytes']} bytes",
        "",
        "## 当前覆盖",
        "- 主法律（OFFICIAL_META）：3 部",
        "- 候选正文（just-laws / lawtext-laws / china-data-laws）：按 bbbs / 文号 / 标题+机关+日期去重后建立 canonical_document_id。",
        "",
        "## 候选正文原则",
        "- 候选源只读，不复制整个仓库到 china-law-verified GitHub；",
        "- 本地正文用于发现、定位、版本变化检测、缺失补充，不冒充官方最终依据；",
        "- 正式合同 / 律师意见 / 诉讼仲裁 / 重大交易仍以官方现行有效性核验结果作为最终依据。",
        "",
        "## 缺口",
        "- 见 `metadata/business-legal-gaps.json`。",
        "- P0 主法律正文需人工在 flk.npc.gov.cn 浏览器补齐。",
    ]
    return "\n".join(lines) + "\n"


def write_business_map_md(blm: dict) -> str:
    lines = ["# 个人业务法律全景图 (V5)", "",
             f"_生成时间：{NOW}_",
             "",
             "51 个一级业务领域 × P0/P1/P2 分级 × canonical 关联",
             "",
             "## 字段说明",
             "- `domain_code` / `domain_name`：一级业务领域",
             "- `related_topics`：当前领域直接关联的现有 Topic",
             "- `linked_canonical_count`：当前领域已识别到的 canonical 规范数",
             "- `priority`：P0（高频高风险）/ P1（常用非核心高频）/ P2（低频）",
             "- `local_text_count`：本地候选源中具备正文的副本数",
             "",
             "## 业务领域清单", "",
             "| 编号 | 名称 | 优先级 | 关联 Topic | 关联 canonical | 本地正文副本 |",
             "| --- | --- | --- | --- | ---: | ---: |"]
    for d in blm["domains"]:
        lines.append(
            f"| {d['domain_code']} | {d['domain_name']} | {d['priority']} | {', '.join(d['related_topics'])} | {d['linked_canonical_count']} | {d['local_text_count']} |"
        )
    lines += [
        "",
        "## 怎么用",
        "- OpenClaw 收到自然语言问题后，先在 `metadata/business-legal-map.json` 找到相关一级领域；",
        "- 取其 `related_topics` 调 `search_all.py --topics a,b,c` 聚合；",
        "- 缺一级的 canonical 视为真实缺口，按 `business-legal-gaps.json` 处理。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--emit-only", help="只生成某个 JSON 文件到 stdout")
    args = p.parse_args()
    universe = build_universe()
    asset = build_local_assets(universe)
    cv = build_current_version_registry(universe)
    blm = build_business_legal_map(universe)
    gaps = build_gaps(universe)

    if args.emit_only == "universe":
        # 精简输出（不写 raw records）
        canon = {k: {k2: v[k2] for k2 in v if k2 != "_records"} for k, v in universe["canonicals"].items()}
        print(json.dumps({
            "generated_at": NOW,
            "raw_record_count": universe["raw_count"],
            "canonical_count": len(canon),
            "canonicals": canon,
        }, ensure_ascii=False, indent=2))
        return 0
    if args.emit_only == "current":
        print(json.dumps(cv, ensure_ascii=False, indent=2))
        return 0
    if args.emit_only == "assets":
        print(json.dumps(asset, ensure_ascii=False, indent=2))
        return 0
    if args.emit_only == "business_map":
        print(json.dumps(blm, ensure_ascii=False, indent=2))
        return 0
    if args.emit_only == "gaps":
        print(json.dumps(gaps, ensure_ascii=False, indent=2))
        return 0

    # 写出所有
    canon = {k: {k2: v[k2] for k2 in v if k2 != "_records"} for k, v in universe["canonicals"].items()}
    (OUT_DIR / "legal-universe.json").write_text(
        json.dumps({
            "generated_at": NOW,
            "schema_version": "V5",
            "raw_record_count": universe["raw_count"],
            "canonical_count": len(canon),
            "by_document_type": dict(sorted(_count(canon.values(), "document_type").items())),
            "by_legal_status": dict(sorted(_count(canon.values(), "legal_status").items())),
            "by_version_status": dict(sorted(_count(canon.values(), "version_status").items())),
            "by_verification_status": dict(sorted(_count(canon.values(), "verification_status").items())),
            "by_freshness_status": dict(sorted({k: _count(canon.values(), "freshness_status")[k] for k in _count(canon.values(), "freshness_status")}.items())),
            "canonicals": canon,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    (OUT_DIR / "current-version-registry.json").write_text(
        json.dumps(cv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    (OUT_DIR / "local-legal-assets.json").write_text(
        json.dumps(asset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    (OUT_DIR / "business-legal-map.json").write_text(
        json.dumps(blm, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    (OUT_DIR / "business-legal-gaps.json").write_text(
        json.dumps(gaps, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )

    (ROOT / "reports").mkdir(parents=True, exist_ok=True)
    (ROOT / "reports" / "local-legal-assets.md").write_text(
        write_local_assets_md(asset), encoding="utf-8",
    )
    (ROOT / "legal-topics" / "business-map").mkdir(parents=True, exist_ok=True)
    (ROOT / "legal-topics" / "business-map" / "README.md").write_text(
        write_business_map_md(blm), encoding="utf-8",
    )

    print(f"[OK] legal-universe.json: canonical={len(canon)} raw={universe['raw_count']}")
    print(f"[OK] current-version-registry.json: current_count={cv['current_count']}")
    print(f"[OK] local-legal-assets.json: candidate_total={asset['candidate_total_files']}")
    print(f"[OK] business-legal-map.json: domains={blm['domain_count']}")
    print(f"[OK] business-legal-gaps.json: gaps={len(gaps['gaps'])}")
    print(f"[OK] reports/local-legal-assets.md")
    print(f"[OK] legal-topics/business-map/README.md")
    return 0


def _count(items, key):
    from collections import Counter
    return Counter(x.get(key) for x in items)


if __name__ == "__main__":
    raise SystemExit(main())