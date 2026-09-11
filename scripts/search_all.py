#!/usr/bin/env python3
"""china-law-verified V2.1 统一检索：精确 → AND 拆解.

输入：
    --query     用户原始自然语言问题（用于精确整句检索）
    --keywords  2~4 个候选检索词（由调用方拆词；本脚本不做 LLM 拆词）
    --candidate-only / --verified-only   只搜某一层

执行顺序（每次查询都在 VERIFIED 与 CANDIDATE 两层各跑一遍）：
  阶段 1：--query 整句精确检索
  阶段 2（仅在阶段 1 完全 0 命中时）：每个 --keyword 单独检索
  阶段 3（仅在阶段 1 完全 0 命中时）：--keywords 的 AND 交集
          （同一文件必须出现全部关键词，列出每条命中行）

输出始终区分：
  VERIFIED   = china-law-verified/laws/  (已官方核验)
  CANDIDATE  = just-laws ImCa0/just-laws (MIT，开源候选，仅供定位)

不调用 LLM；正文查找只用 rg / Python re。
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

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT.parent

VERIFIED_DIR = ROOT / "laws"
VERIFIED_INDEX = ROOT / "metadata" / "index.jsonl"

CANDIDATE_ROOT = WORKSPACE / "legal-sources" / "just-laws"

LAYER_VERIFIED = "VERIFIED"
LAYER_CANDIDATE = "CANDIDATE"


# ------------------------- I/O 辅助 -------------------------

def load_verified_index() -> dict[str, dict]:
    if not VERIFIED_INDEX.exists():
        return {}
    out: dict[str, dict] = {}
    with VERIFIED_INDEX.open("r", encoding="utf-8") as fh:
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


def search_one(layer_name: str, root: Path, pattern: str) -> tuple[str, list[tuple[str, int, str]], float]:
    """返回 (backend, hits, dt)。"""
    t0 = time.perf_counter()
    backend = "rg" if shutil.which("rg") else "python"
    it = iter_rg(root, pattern) or iter_python(root, pattern)
    hits = list(it)
    dt = time.perf_counter() - t0
    return backend, hits, dt


# ------------------------- 渲染 -------------------------

def fmt_verified_hit(rel_path: str, lineno: int, snippet: str, idx: dict) -> list[str]:
    rec = idx.get(rel_path, {})
    title = rec.get("title", Path(rel_path).stem)
    url = rec.get("official_url", "(无)")
    vdate = rec.get("current_version_date") or rec.get("version_date", "(无)")
    status = rec.get("verification_status", "needs_recheck")
    ctx = snippet.strip()[:200]
    return [
        f"  标题: {title}",
        f"  版本日期: {vdate}  verification: {status}",
        f"  路径: {rel_path}:{lineno}",
        f"  官方来源: {url}",
        f"  上下文: {ctx}",
    ]


def fmt_candidate_hit(rel_path: str, lineno: int, snippet: str, _idx=None) -> list[str]:
    full = CANDIDATE_ROOT / rel_path
    title = title_from_md(full)
    cat = category_of(full)
    ctx = snippet.strip()[:200]
    return [
        f"  标题: {title}",
        f"  类别: {cat}",
        f"  路径: {rel_path}:{lineno}",
        f"  原文: {ctx}",
    ]


def print_layer_section(layer_name: str, backend: str, dt: float,
                        hits: list[tuple[str, int, str]], root: Path,
                        fmt_hit, idx) -> int:
    if not hits:
        print(f"  └─ (无命中)  backend: {backend}  耗时 {dt*1000:.1f} ms")
        return 0
    print(f"  └─ {len(hits)} 行  backend: {backend}  耗时 {dt*1000:.1f} ms")
    grouped: dict[str, list[tuple[int, str]]] = {}
    for rel, ln, content in hits:
        grouped.setdefault(rel, []).append((ln, content))
    total = 0
    for rel, hs in sorted(grouped.items()):
        title_path = fmt_hit(rel, 0, "", idx)[0]
        print(f"  · {title_path}  ({rel})")
        for ln, snippet in hs[:20]:
            total += 1
            for line in fmt_hit(rel, ln, snippet, idx):
                print("    " + line)
        if len(hs) > 20:
            print(f"    ... 省略 {len(hs) - 20} 行")
    return total


# ------------------------- AND 交集 -------------------------

def and_intersect(layer_root: Path, keywords: list[str]) -> dict[str, set[int]]:
    """返回 {rel_path: {行号, ...}}，文件必须包含所有关键词；行号是任何关键词出现的行集合。"""
    per_kw: list[dict[str, set[int]]] = []
    for kw in keywords:
        _, hits, _ = search_one("", layer_root, re.escape(kw))
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


# ------------------------- 主流程 -------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description="china-law-verified V2.1 统一检索：原句精确 → AND 拆解"
    )
    p.add_argument("--query", help="用户原始自然语言问题（用于整句精确检索）")
    p.add_argument("--keywords", nargs="+", help="2~4 个候选检索词（调用方已拆好）")
    p.add_argument("--limit", type=int, default=20, help="每个文件最多返回命中行数")
    p.add_argument("--verified-only", action="store_true")
    p.add_argument("--candidate-only", action="store_true")
    args = p.parse_args()

    if not args.query and not args.keywords:
        print("[ERR] 必须提供 --query 或 --keywords", file=sys.stderr)
        return 2
    if args.keywords and not (2 <= len(args.keywords) <= 4):
        print(f"[WARN] --keywords 建议 2~4 个，实际 {len(args.keywords)} 个", file=sys.stderr)

    query = (args.query or "").strip()
    keywords = [k.strip() for k in (args.keywords or []) if k.strip()]

    print(f"# 检索: query={query!r}  keywords={keywords!r}\n")

    grand_total = 0
    t_total = time.perf_counter()

    layers = []
    if not args.candidate_only:
        layers.append((LAYER_VERIFIED, VERIFIED_DIR))
    if not args.verified_only:
        layers.append((LAYER_CANDIDATE, CANDIDATE_ROOT))

    for layer_name, root in layers:
        print(f"## {layer_name}  ({root})")
        idx = load_verified_index() if layer_name == LAYER_VERIFIED else {}
        fmt_hit = fmt_verified_hit if layer_name == LAYER_VERIFIED else fmt_candidate_hit

        # 阶段 1：原句精确
        if query:
            print(f"\n[阶段 1] 原句精确: {query!r}")
            backend, hits, dt = search_one(layer_name, root, re.escape(query))
            total = print_layer_section(layer_name, backend, dt, hits, root, fmt_hit, idx)
            grand_total += total
            if total == 0 and keywords:
                # 阶段 2：每个关键词单独
                print(f"\n[阶段 2] 关键词单独检索（0 命中后）")
                for kw in keywords:
                    print(f"\n  keyword: {kw!r}")
                    backend, hits, dt = search_one(layer_name, root, re.escape(kw))
                    grand_total += print_layer_section(layer_name, backend, dt, hits, root, fmt_hit, idx)
                # 阶段 3：AND 交集
                print(f"\n[阶段 3] 关键词 AND 交集")
                inter = and_intersect(root, keywords)
                if not inter:
                    print(f"  └─ (无文件同时包含全部 {len(keywords)} 个关键词)")
                else:
                    print(f"  └─ {len(inter)} 个文件同时包含全部 {len(keywords)} 个关键词")
                    for rel in sorted(inter):
                        title_path = fmt_hit(rel, 0, "", idx)[0]
                        print(f"  · {title_path}  ({rel})")
                        # 显示每个关键词在该文件的命中行
                        for kw in keywords:
                            backend, hits, dt = search_one(layer_name, root / rel, re.escape(kw))
                            for ln, snippet in hits[:args.limit]:
                                for line in fmt_hit(rel, ln, snippet, idx):
                                    print("    [kw=" + kw + "] " + line)
                            grand_total += len(hits)

    dt_total = time.perf_counter() - t_total
    print(f"\n# 合计命中行数: {grand_total}  总耗时: {dt_total*1000:.1f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())