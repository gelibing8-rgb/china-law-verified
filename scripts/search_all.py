#!/usr/bin/env python3
"""china-law-verified V3.1 三层语义检索 + 专题检索.

层级定义（V2.2）：
  VERIFIED       = laws/*.md 中 verification_status=verified_official 的文件
                   元数据 + 全文均已与官方原文逐字核验
  OFFICIAL_META  = laws/*.md 中 verification_status=needs_recheck 的文件
                   元数据 + 结构树已通过官方 API 核验；正文未经官方原文逐字核验，
                   不可作为最终法律依据引用
  CANDIDATE      = ~/workspace/legal-sources/just-laws (ImCa0/just-laws, MIT)
                   开源候选，仅供"定位相关条文"，**不能**作为最终法律依据

专题检索（V3.1）：
  --topic company-law  读 legal-topics/<topic>/manifest.yaml；
  限定 laws/ 检索范围为主题内 relation_strength∈[core,direct] 且存在 local_path 的文档。
  CANDIDATE 检索保持全量命中，由主题的 manifest 限定后续处理。
  --include-related 把 historical_version / relation_strength=related 的条目也纳入检索范围。

执行顺序：
  阶段 1：--query 整句精确检索
  阶段 2（仅阶段 1 完全 0 命中时）：每个 --keyword 单独检索
  阶段 3（仅阶段 1 完全 0 命中时）：--keywords 的 AND 交集

LLM / Agent 职责分工（V2.2）：
  - Agent / LLM 可以将自然语言问题转换为 2~4 个检索关键词
  - 法律正文检索**必须**由本脚本使用 rg / Python re 完成
  - LLM **禁止**生成、补写、修改或冒充法律原文；命中行的"原文"必须是源文件原样
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterator

try:
    import yaml  # V3.1 专题过滤使用；标准库 yaml 在 Python 3.10+；环境使用 PyYAML
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT.parent

LAWS_DIR = ROOT / "laws"
INDEX_FILE = ROOT / "metadata" / "index.jsonl"
CANDIDATE_ROOT = WORKSPACE / "legal-sources" / "just-laws"

LAYER_VERIFIED = "VERIFIED"
LAYER_OFFICIAL_META = "OFFICIAL_META"
LAYER_CANDIDATE = "CANDIDATE"


# ------------------------- 元数据 -------------------------

def load_index() -> dict[str, dict]:
    """key = laws/xxx.md 相对路径"""
    if not INDEX_FILE.exists():
        return {}
    out: dict[str, dict] = {}
    with INDEX_FILE.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("path"):
                out[rec["path"]] = rec
    return out


def law_verification_status(md_path: Path) -> str:
    """读 laws/<file>.md frontmatter 的 verification_status.
    缺省视为 needs_recheck（保守）。
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return "needs_recheck"
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return "needs_recheck"
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if k.strip() == "verification_status":
            val = v.split("#", 1)[0].strip()
            return val or "needs_recheck"
    return "needs_recheck"


def layer_for_law(rel_path: str) -> str:
    """V2.2: 按每个 law 文件自己的 verification_status 决定层标签."""
    md = LAWS_DIR / Path(rel_path).name
    status = law_verification_status(md)
    if status == "verified_official":
        return LAYER_VERIFIED
    return LAYER_OFFICIAL_META


def title_from_md(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^#\s+(.+?)\s*$", line)
            if m:
                return m.group(1).strip()
    except OSError:
        pass
    return path.stem


def category_of(path: Path) -> str:
    parts = path.parts
    if "constitution" in parts:
        return "constitution"
    try:
        i = parts.index("docs")
        return parts[i + 1]
    except (ValueError, IndexError):
        return "?"


# ------------------------- 检索后端 -------------------------

def iter_rg(root: Path, pattern: str) -> Iterator[tuple[str, int, str]]:
    if shutil.which("rg") is None:
        return None  # type: ignore[return-value]
    cmd = ["rg", "--no-heading", "--line-number", "--color=never",
           "--", pattern, str(root)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"rg failed: {proc.stderr}")
    for raw in proc.stdout.splitlines():
        m = re.match(r"^(.+?):(\d+):(.*)$", raw)
        if not m:
            continue
        path_str = m.group(1)
        try:
            rel = str(Path(path_str).resolve().relative_to(root))
        except ValueError:
            rel = path_str
        yield rel, int(m.group(2)), m.group(3)
    return


def iter_python(root: Path, pattern: str, suffix: str = ".md") -> Iterator[tuple[str, int, str]]:
    rx = re.compile(pattern)
    for p in sorted(root.rglob(f"*{suffix}")):
        try:
            with p.open("r", encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    if rx.search(line):
                        try:
                            rel = str(p.resolve().relative_to(root))
                        except ValueError:
                            rel = str(p)
                        yield rel, lineno, line.rstrip("\n")
        except UnicodeDecodeError:
            continue


def search_one(root: Path, pattern: str) -> tuple[str, list[tuple[str, int, str]], float]:
    """返回 (backend, hits, dt)."""
    t0 = time.perf_counter()
    backend = "rg" if shutil.which("rg") else "python"
    it = iter_rg(root, pattern) or iter_python(root, pattern)
    hits = list(it)
    dt = time.perf_counter() - t0
    return backend, hits, dt


# ------------------------- 渲染 -------------------------

def fmt_law_hit(rel_path: str, lineno: int, snippet: str, idx: dict, layer: str) -> list[str]:
    """VERIFIED / OFFICIAL_META 共用渲染：来自 laws/*.md."""
    rec = idx.get(rel_path, {})
    title = rec.get("title", Path(rel_path).stem)
    url = rec.get("official_url", "(无)")
    vdate = rec.get("current_version_date") or rec.get("version_date", "(无)")
    status = rec.get("verification_status", "needs_recheck")
    ctx = snippet.strip()[:200]
    return [
        f"  标题: {title}",
        f"  层: {layer}  verification: {status}",
        f"  版本日期: {vdate}",
        f"  路径: {rel_path}:{lineno}",
        f"  官方来源: {url}",
        f"  原文: {ctx}",
    ]


def fmt_candidate_hit(rel_path: str, lineno: int, snippet: str, _idx=None) -> list[str]:
    full = CANDIDATE_ROOT / rel_path
    title = title_from_md(full)
    cat = category_of(full)
    ctx = snippet.strip()[:200]
    return [
        f"  标题: {title}",
        f"  层: CANDIDATE",
        f"  类别: {cat}",
        f"  路径: {rel_path}:{lineno}",
        f"  原文: {ctx}",
    ]


def print_section(backend: str, dt: float, hits: list[tuple[str, int, str]],
                  root: Path, fmt_hit, idx) -> int:
    """返回本节命中行数. fmt_hit 决定 VERIFIED/OFFICIAL_META/CANDIDATE 渲染."""
    if not hits:
        print(f"  └─ (无命中)  backend: {backend}  耗时 {dt*1000:.1f} ms")
        return 0
    print(f"  └─ {len(hits)} 行  backend: {backend}  耗时 {dt*1000:.1f} ms")
    grouped: dict[str, list[tuple[int, str]]] = {}
    for rel, ln, content in hits:
        grouped.setdefault(rel, []).append((ln, content))
    total = 0
    for rel, hs in sorted(grouped.items()):
        # 计算每条命中所在文件的层标签
        if fmt_hit is fmt_candidate_hit:
            layer_label = LAYER_CANDIDATE
        else:
            layer_label = layer_for_law(rel)
        # 仅取标题行（fmt_law_hit 需要 layer 参数，title 情况下也补上）
        if fmt_hit is fmt_candidate_hit:
            title_line = fmt_hit(rel, 0, "", idx)[0]
        else:
            title_line = fmt_hit(rel, 0, "", idx, layer_label)[0]
        print(f"  · {title_line}  ({rel})  [{layer_label}]")
        for ln, snippet in hs[:20]:
            total += 1
            if fmt_hit is fmt_candidate_hit:
                lines = fmt_hit(rel, ln, snippet, idx)
            else:
                lines = fmt_hit(rel, ln, snippet, idx, layer_label)
            for line in lines:
                print("    " + line)
        if len(hs) > 20:
            print(f"    ... 省略 {len(hs) - 20} 行")
    return total


# ------------------------- AND 交集 -------------------------

def and_intersect(layer_root: Path, keywords: list[str]) -> dict[str, set[int]]:
    """返回 {rel_path: {行号, ...}}，文件必须包含所有关键词."""
    per_kw: list[dict[str, set[int]]] = []
    for kw in keywords:
        _, hits, _ = search_one(layer_root, re.escape(kw))
        d: dict[str, set[int]] = {}
        for rel, ln, _ in hits:
            d.setdefault(rel, set()).add(ln)
        per_kw.append(d)
    if not per_kw:
        return {}
    common = set(per_kw[0].keys())
    for d in per_kw[1:]:
        common &= set(d.keys())
    return {p: set().union(*(d[p] for d in per_kw)) for p in common}


# ------------------------- 专题过滤（V3.1） -------------------------

# 默认纳入：legal_status 仅 effective / pending_verification
TOPIC_DEFAULT_LEGAL_STATUS = {"effective", "pending_verification"}
# 默认纳入：relation_strength 仅 core / direct
TOPIC_DEFAULT_RELATION_STRENGTH = {"core", "direct"}


def _normalize_title(t: str) -> str:
    """去'中华人民共和国'前缀做 CANDIDATE 标题匹配."""
    return re.sub(r"^中华人民共和国\s*", "", (t or "").strip())


def _build_candidate_title_index() -> dict[str, set[str]]:
    """扫描 CANDIDATE_ROOT 下所有 README.md，取第一行 `# 标题` 建索引.
    返回 {normalized_title: {rel_path, ...}}.
    """
    idx: dict[str, set[str]] = {}
    if not CANDIDATE_ROOT.exists():
        return idx
    for p in CANDIDATE_ROOT.rglob("README.md"):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        first = text.splitlines()[0] if text else ""
        m = re.match(r"^#\s+(.+?)\s*$", first)
        if not m:
            continue
        norm = _normalize_title(m.group(1))
        if not norm:
            continue
        try:
            rel = str(p.resolve().relative_to(CANDIDATE_ROOT))
        except ValueError:
            rel = str(p)
        idx.setdefault(norm, set()).add(rel)
    return idx


def load_topic_manifest(topic_id: str, include_related: bool = False):
    """V3.1 专题加载：读 legal-topics/<topic_id>/manifest.yaml.

    返回 (topic_meta, scope, unresolved)：
      topic_meta    dict — 专题元数据
      scope         dict — {'laws_paths': set(相对 laws/), 'candidate_paths': set(相对 CANDIDATE/)}
      unresolved     list — [(doc_id, title, reason), ...]  本轮无法可靠映射的 manifest 条目

    过滤规则（默认）：
      legal_status      ∈ {effective, pending_verification}
      relation_strength ∈ {core, direct}
    排除：repealed / replaced / historical / draft
    """
    if not topic_id:
        return None, None, []
    if yaml is None:
        print("[ERR] 需要 PyYAML（pip install --user pyyaml）才能启用 --topic", file=sys.stderr)
        return None, None, []

    manifest_path = ROOT / "legal-topics" / topic_id / "manifest.yaml"
    if not manifest_path.exists():
        print(f"[ERR] manifest 不存在: {manifest_path}", file=sys.stderr)
        return None, None, []

    try:
        with manifest_path.open("r", encoding="utf-8") as fh:
            manifest = yaml.safe_load(fh)
    except yaml.YAMLError as e:
        print(f"[ERR] manifest YAML 解析失败: {e}", file=sys.stderr)
        return None, None, []

    topic_meta = manifest.get("topic", {}) or {}
    allowed_status = TOPIC_DEFAULT_LEGAL_STATUS if not include_related else (
        TOPIC_DEFAULT_LEGAL_STATUS | {"repealed", "replaced", "historical", "draft", "not_applicable"}
    )
    allowed_strength = TOPIC_DEFAULT_RELATION_STRENGTH if not include_related else (
        TOPIC_DEFAULT_RELATION_STRENGTH | {"related"}
    )

    docs: list[dict] = list(manifest.get("documents", []) or [])
    if include_related:
        docs = docs + list(manifest.get("documents_related", []) or [])

    laws_paths: set[str] = set()
    candidate_paths: set[str] = set()
    unresolved: list[tuple[str, str, str]] = []

    # CANDIDATE 标题索引：启动一次
    cand_index = _build_candidate_title_index()

    for doc in docs:
        status = doc.get("legal_status", "")
        strength = doc.get("relation_strength", "")
        title = doc.get("title", "")
        doc_id = doc.get("document_id", "?")

        if status not in allowed_status:
            continue
        if strength not in allowed_strength:
            continue

        lp = doc.get("local_path")
        if lp:
            if lp.startswith("laws/"):
                laws_paths.add(lp[len("laws/"):])
            elif lp.startswith("docs/") or lp.startswith("constitution/"):
                candidate_paths.add(lp)
            else:
                unresolved.append((doc_id, title, "local_path 不在已知层（laws/ 或 CANDIDATE/）"))
            continue

        # local_path=null：用 title 尝试匹配 CANDIDATE
        norm = _normalize_title(title)
        matches = cand_index.get(norm, set())
        if len(matches) == 1:
            candidate_paths.update(matches)
        elif len(matches) > 1:
            unresolved.append((doc_id, title, f"title 匹配多个 CANDIDATE 文件: {sorted(matches)}"))
        else:
            unresolved.append((doc_id, title, "title 在 CANDIDATE 中未匹配"))

    scope = {"laws_paths": laws_paths, "candidate_paths": candidate_paths}
    return topic_meta, scope, unresolved


def filter_hits_by_scope(hits, allowed_paths):
    """过滤 hits.

    allowed_paths = None  → 不过滤（专题未启用）
    allowed_paths = set() → 严格限定为空集 → 返回 0 命中（专题已启用但无文件可映射）
    allowed_paths = {p1, p2, ...} → 只保留这些文件中的命中
    """
    if allowed_paths is None:
        return list(hits)
    return [(rel, ln, content) for rel, ln, content in hits if rel in allowed_paths]


# ------------------------- 主流程 -------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description="china-law-verified V3.1 三层语义检索 + 专题过滤"
    )
    p.add_argument("--query", help="用户原始自然语言问题（用于整句精确检索）")
    p.add_argument("--keywords", nargs="+", help="2~4 个候选检索词（调用方已拆好）")
    p.add_argument("--limit", type=int, default=20, help="每个文件最多返回命中行数")
    p.add_argument("--candidate-only", action="store_true", help="只搜 CANDIDATE")
    p.add_argument("--laws-only", action="store_true",
                   help="只搜 VERIFIED + OFFICIAL_META（即 laws/）")
    p.add_argument("--topic", help="专题过滤：传 topic id 如 company-law，"
                                  "读 legal-topics/<id>/manifest.yaml 限定检索范围")
    p.add_argument("--include-related", action="store_true",
                   help="专题模式下额外纳入 historical_version / relation_strength=related 的条目")
    args = p.parse_args()

    if not args.query and not args.keywords:
        print("[ERR] 必须提供 --query 或 --keywords", file=sys.stderr)
        return 2
    if args.keywords and not (2 <= len(args.keywords) <= 4):
        print(f"[WARN] --keywords 建议 2~4 个，实际 {len(args.keywords)} 个", file=sys.stderr)

    query = (args.query or "").strip()
    keywords = [k.strip() for k in (args.keywords or []) if k.strip()]

    # V3.1 专题加载（--topic）
    topic_meta, topic_scope, topic_unresolved = (None, None, [])
    if args.topic:
        topic_meta, topic_scope, topic_unresolved = load_topic_manifest(
            args.topic, include_related=args.include_related
        )
        if topic_meta is None:
            return 2

    print("# china-law-verified V2.2 检索")
    if args.topic and topic_meta:
        print(f"Topic: {args.topic}")
        print(f"Topic title: {topic_meta.get('title', '')}")
        if topic_scope:
            print(f"Topic scope: laws_paths={len(topic_scope['laws_paths'])} files, "
                  f"candidate_paths={len(topic_scope['candidate_paths'])} files")
        if args.include_related:
            print("# (--include-related 已启用)")
    print(f"# query={query!r}")
    print(f"# keywords={keywords!r}\n")

    # 局部 search 包装：启用专题时按层过滤 hits
    def _s(root: Path, pattern: str):
        backend, hits, dt = search_one(root, pattern)
        if topic_scope is not None:
            if root == LAWS_DIR:
                hits = filter_hits_by_scope(hits, topic_scope["laws_paths"])
            elif root == CANDIDATE_ROOT:
                hits = filter_hits_by_scope(hits, topic_scope["candidate_paths"])
            else:
                # sub-path search（如 LAWS_DIR/xxx.md）不过滤：路径已由调用点限定
                pass
        return backend, hits, dt

    grand_total = 0
    t_total = time.perf_counter()
    idx = load_index()

    # laws/ 这一组（VERIFIED + OFFICIAL_META，按文件 frontmatter 区分）
    if not args.candidate_only and LAWS_DIR.exists():
        print(f"## laws/  (VERIFIED / OFFICIAL_META — 由每个文件 frontmatter 决定)")
        fmt_hit = fmt_law_hit
        total1 = 0
        if query:
            print(f"\n[阶段 1] 原句精确: {query!r}")
            backend, hits, dt = _s(LAWS_DIR, re.escape(query))
            total1 = print_section(backend, dt, hits, LAWS_DIR, fmt_hit, idx)
            grand_total += total1
        # 阶段 2/3：只要提供 keywords 就要跑（阶段 1 为 0 或未运行都跑）
        if keywords and total1 == 0:
            print(f"\n[阶段 2] 关键词单独检索（阶段 1 未命中后）")
            for kw in keywords:
                print(f"\n  keyword: {kw!r}")
                backend, hits, dt = _s(LAWS_DIR, re.escape(kw))
                grand_total += print_section(backend, dt, hits, LAWS_DIR, fmt_hit, idx)
            print(f"\n[阶段 3] 关键词 AND 交集")
            inter = and_intersect(LAWS_DIR, keywords)
            if topic_scope is not None:
                inter = {p: v for p, v in inter.items() if p in topic_scope["laws_paths"]}
            if not inter:
                print(f"  └─ (无文件同时包含全部 {len(keywords)} 个关键词)")
            else:
                print(f"  └─ {len(inter)} 个文件同时包含全部 {len(keywords)} 个关键词")
                for rel in sorted(inter):
                    layer = layer_for_law(rel)
                    rec = idx.get(rel, {})
                    title = rec.get("title", Path(rel).stem)
                    print(f"  · {title}  ({rel})  [{layer}]")
                    for kw in keywords:
                        backend, hits, dt = _s(LAWS_DIR / Path(rel).name, re.escape(kw))
                        for ln, snippet in hits[:args.limit]:
                            for line in fmt_hit(rel, ln, snippet, idx, layer):
                                print("    [kw=" + kw + "] " + line)
                        grand_total += len(hits)

    # CANDIDATE 层
    if not args.laws_only and CANDIDATE_ROOT.exists():
        print(f"\n## CANDIDATE  (ImCa0/just-laws, MIT — 仅供定位，不可作最终法律依据)")
        fmt_hit = fmt_candidate_hit
        total1 = 0
        if query:
            print(f"\n[阶段 1] 原句精确: {query!r}")
            backend, hits, dt = _s(CANDIDATE_ROOT, re.escape(query))
            total1 = print_section(backend, dt, hits, CANDIDATE_ROOT, fmt_hit, {})
            grand_total += total1
        if keywords and total1 == 0:
            print(f"\n[阶段 2] 关键词单独检索（阶段 1 未命中后）")
            for kw in keywords:
                print(f"\n  keyword: {kw!r}")
                backend, hits, dt = _s(CANDIDATE_ROOT, re.escape(kw))
                grand_total += print_section(backend, dt, hits, CANDIDATE_ROOT, fmt_hit, {})
            print(f"\n[阶段 3] 关键词 AND 交集")
            inter = and_intersect(CANDIDATE_ROOT, keywords)
            if topic_scope is not None:
                inter = {p: v for p, v in inter.items() if p in topic_scope["candidate_paths"]}
            if not inter:
                print(f"  └─ (无文件同时包含全部 {len(keywords)} 个关键词)")
            else:
                print(f"  └─ {len(inter)} 个文件同时包含全部 {len(keywords)} 个关键词")
                for rel in sorted(inter):
                    full = CANDIDATE_ROOT / rel
                    print(f"  · {title_from_md(full)}  ({rel})  [CANDIDATE]")
                    for kw in keywords:
                        backend, hits, dt = _s(CANDIDATE_ROOT / rel, re.escape(kw))
                        for ln, snippet in hits[:args.limit]:
                            for line in fmt_candidate_hit(rel, ln, snippet):
                                print("    [kw=" + kw + "] " + line)
                        grand_total += len(hits)

    dt_total = time.perf_counter() - t_total
    print(f"\n# 合计命中行数: {grand_total}  总耗时: {dt_total*1000:.1f} ms")

    # V3.1 专题 UNRESOLVED 报告
    if args.topic:
        if topic_unresolved:
            print(f"\n# TOPIC_UNRESOLVED: {len(topic_unresolved)} 个 manifest 条目未能可靠映射到本地文件")
            for did, title, reason in topic_unresolved:
                print(f"  - {did}  title={title!r}  reason: {reason}")
        else:
            print(f"\n# TOPIC_UNRESOLVED: (无)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())