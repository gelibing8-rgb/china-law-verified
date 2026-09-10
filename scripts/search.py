#!/usr/bin/env python3
"""china-law-verified 全文检索 (V1).

优先调用 ripgrep (rg)；如系统无 rg，则用 Python 标准库做简单的行级全文匹配。
不调用任何 LLM。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent
LAWS_DIR = ROOT / "laws"
META_FILE = ROOT / "metadata" / "index.jsonl"
SOURCES_YAML = ROOT / "sources.yaml"


def load_index() -> dict[str, dict]:
    """key = 文件相对路径 (laws/xxx.md)。"""
    if not META_FILE.exists():
        return {}
    index: dict[str, dict] = {}
    with META_FILE.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("path"):
                index[rec["path"]] = rec
    return index


def iter_ripgrep(pattern: str) -> Iterator[tuple[str, int, str]]:
    if shutil.which("rg") is None:
        return None  # type: ignore[return-value]
    cmd = [
        "rg",
        "--no-heading",
        "--line-number",
        "--color=never",
        "--",
        pattern,
        str(LAWS_DIR),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode not in (0, 1):  # 1 = no match
        raise RuntimeError(f"rg failed: {proc.stderr}")
    for raw in proc.stdout.splitlines():
        # format: /abs/path/laws/xxx.md:lineno:content
        m = re.match(r"^(.+?):(\d+):(.*)$", raw)
        if not m:
            continue
        path_str = m.group(1)
        # Normalize to project-relative path so the index lookup hits
        try:
            rel = str(Path(path_str).resolve().relative_to(ROOT))
        except ValueError:
            rel = path_str
        yield rel, int(m.group(2)), m.group(3)
    return


def iter_python(pattern: str) -> Iterator[tuple[str, int, str]]:
    rx = re.compile(pattern)
    for path in sorted(LAWS_DIR.glob("*.md")):
        try:
            with path.open("r", encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    if rx.search(line):
                        yield str(path.relative_to(ROOT)), lineno, line.rstrip("\n")
        except UnicodeDecodeError:
            continue


def extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        m = re.match(r"^title:\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
    return fallback


def render_hit(rel_path: str, lineno: int, snippet: str, meta: dict | None) -> str:
    title = (meta or {}).get("title") or extract_title(
        (LAWS_DIR / Path(rel_path).name).read_text(encoding="utf-8"),
        Path(rel_path).stem,
    )
    url = (meta or {}).get("official_url", "(无)")
    version = (meta or {}).get("version_date", "(无)")
    context = snippet.strip()
    if len(context) > 200:
        context = context[:197] + "..."
    return (
        f"- 法律: {title}\n"
        f"  版本日期: {version}\n"
        f"  文件: {rel_path}:{lineno}\n"
        f"  官方来源: {url}\n"
        f"  上下文: {context}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="china-law-verified 全文检索")
    parser.add_argument("pattern", help="检索关键字（可使用 rg/正则语法）")
    parser.add_argument(
        "--limit", type=int, default=20, help="每个文件最多返回命中行数 (默认 20)"
    )
    args = parser.parse_args()

    if not LAWS_DIR.exists():
        print(f"[ERR] laws 目录不存在: {LAWS_DIR}", file=sys.stderr)
        return 2

    index = load_index()
    backend = "rg" if shutil.which("rg") else "python"
    iterator = iter_ripgrep(args.pattern) or iter_python(args.pattern)

    hits_by_file: dict[str, list[tuple[int, str]]] = {}
    for rel_path, lineno, content in iterator:
        hits_by_file.setdefault(rel_path, []).append((lineno, content))

    if not hits_by_file:
        print(f"(无命中) 关键字: {args.pattern!r}  backend: {backend}")
        return 0

    total_hits = 0
    for rel_path, hits in hits_by_file.items():
        meta = index.get(rel_path)
        title = (meta or {}).get("title", Path(rel_path).stem)
        print(f"\n## {title} ({rel_path})")
        for lineno, snippet in hits[: args.limit]:
            total_hits += 1
            print(render_hit(rel_path, lineno, snippet, meta))
        if len(hits) > args.limit:
            print(f"  ... 省略 {len(hits) - args.limit} 行")

    print(f"\n合计命中: {total_hits} 行  (backend: {backend})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())