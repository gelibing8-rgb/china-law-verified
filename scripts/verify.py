#!/usr/bin/env python3
"""china-law-verified 校验脚本 (V1).

校验项:
  1. laws/*.md frontmatter 必填字段齐全
  2. official_url 域名属于 sources.yaml 的 allowed_domains
  3. 正文非空
  4. content_sha256 与正文一致
  5. metadata/index.jsonl 与磁盘文件一致
  6. 没有重复法律 / 重复 (issuing_authority, title, version_date) 组合
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
LAWS_DIR = ROOT / "laws"
META_FILE = ROOT / "metadata" / "index.jsonl"
SOURCES_YAML = ROOT / "sources.yaml"

REQUIRED_FIELDS = (
    "title",
    "document_type",
    "issuing_authority",
    "promulgation_date",
    "effective_date",
    "status",
    "version_date",
    "official_url",
    "retrieved_at",
    "verification_status",
    "content_sha256",
)

ALLOWED_STATUS = {"现行", "已被修正", "已废止", "已失效"}
VERIFICATION_STATUS = {"verified_official", "needs_recheck"}

# 最小白名单；当 sources.yaml 不存在时使用，保证 verify 不依赖 yaml 解析。
DEFAULT_ALLOWED_DOMAINS = {
    "flk.npc.gov.cn",
    "npc.gov.cn",
    "gov.cn",
    "court.gov.cn",
    "chinacourt.gov.cn",
    "moj.gov.cn",
    "spp.gov.cn",
    "audit.gov.cn",
}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def load_allowed_domains() -> set[str]:
    if not SOURCES_YAML.exists():
        return set(DEFAULT_ALLOWED_DOMAINS)
    text = SOURCES_YAML.read_text(encoding="utf-8")
    domains: set[str] = set()
    in_block = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not in_block:
            if line.strip() == "allowed_domains:":
                in_block = True
            continue
        if not line.startswith("  - "):
            # 列表结束
            if line.strip() and not line.startswith("  "):
                in_block = False
            continue
        # 取注释前的域名
        entry = line[4:].strip()
        entry = entry.split("#", 1)[0].strip()
        if entry:
            domains.add(entry)
    return domains or set(DEFAULT_ALLOWED_DOMAINS)


def parse_frontmatter(md_path: Path) -> tuple[dict, str, list[str]]:
    """返回 (meta, body, errors)。"""
    errors: list[str] = []
    try:
        text = md_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return {}, "", [f"无法以 UTF-8 读取: {exc}"]
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, "", ["缺少 --- ... --- frontmatter"]
    meta_raw, body = m.group(1), m.group(2)
    meta: dict[str, str] = {}
    for raw_line in meta_raw.splitlines():
        if ":" not in raw_line:
            errors.append(f"frontmatter 行无法解析: {raw_line!r}")
            continue
        key, _, value = raw_line.partition(":")
        meta[key.strip()] = value.strip()
    body = body.lstrip("\n")
    return meta, body, errors


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    allowed_domains = load_allowed_domains()
    files = sorted(p for p in LAWS_DIR.glob("*.md") if p.name.lower() != "readme.md")
    if not files:
        print("[FAIL] laws/ 目录下没有任何法律文件")
        return 1

    all_errors: list[str] = []
    seen_keys: set[tuple[str, str, str]] = set()
    disk_records: list[dict] = []
    # Ignore non-law files inside laws/ (e.g. README.md)
    excluded = set()

    for md in files:
        rel = md.relative_to(ROOT).as_posix()
        meta, body, errs = parse_frontmatter(md)
        if errs:
            all_errors.extend(f"[{rel}] " + e for e in errs)
        # 必填字段
        for field in REQUIRED_FIELDS:
            if not meta.get(field):
                all_errors.append(f"[{rel}] 缺少必填字段: {field}")
        # 正文非空
        if not body.strip():
            all_errors.append(f"[{rel}] 正文为空")
        # 域名
        url = meta.get("official_url", "")
        if url:
            host = urlparse(url).hostname or ""
            if host not in allowed_domains:
                all_errors.append(
                    f"[{rel}] official_url 域名 {host!r} 不在白名单 {sorted(allowed_domains)}"
                )
        # SHA256
        declared_sha = meta.get("content_sha256", "")
        if declared_sha and body:
            actual = sha256_of(body)
            if declared_sha.lower() != actual.lower():
                all_errors.append(
                    f"[{rel}] content_sha256 不一致: 声明 {declared_sha[:12]}..., 实际 {actual[:12]}..."
                )
        # verification_status 取值
        vs = meta.get("verification_status", "")
        if vs and vs not in VERIFICATION_STATUS:
            all_errors.append(
                f"[{rel}] verification_status 取值非法: {vs!r}, 允许 {VERIFICATION_STATUS}"
            )
        # status 取值（允许为空表示未填写，但提示）
        status = meta.get("status", "")
        if status and status not in ALLOWED_STATUS:
            all_errors.append(
                f"[{rel}] status 取值不在推荐列表: {status!r}, 建议 {ALLOWED_STATUS}"
            )
        # 重复检测
        key = (meta.get("title", ""), meta.get("issuing_authority", ""), meta.get("version_date", ""))
        if key != ("", "", "") and key in seen_keys:
            all_errors.append(f"[{rel}] 与已有记录重复: {key}")
        seen_keys.add(key)

        disk_records.append(
            {
                "path": rel,
                "title": meta.get("title", ""),
                "version_date": meta.get("version_date", ""),
                "official_url": url,
                "verification_status": vs,
            }
        )

    # index.jsonl 一致性
    on_disk_paths = {r["path"] for r in disk_records}
    if META_FILE.exists():
        index_records: list[dict] = []
        with META_FILE.open("r", encoding="utf-8") as fh:
            for ln, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    all_errors.append(f"[index.jsonl:{ln}] JSON 解析失败: {exc}")
                    continue
                index_records.append(rec)
        index_paths = {r.get("path", "") for r in index_records}
        for missing in on_disk_paths - index_paths:
            all_errors.append(f"[index.jsonl] 缺少文件记录: {missing}")
        for extra in index_paths - on_disk_paths:
            all_errors.append(f"[index.jsonl] 文件不存在: {extra}")
    else:
        all_errors.append("metadata/index.jsonl 不存在")

    print(f"扫描 laws/*.md: {len(files)} 个文件")
    print(f"白名单域名: {sorted(allowed_domains)}")
    if all_errors:
        print("\n[FAIL] 发现问题:")
        for e in all_errors:
            print("  - " + e)
        return 1
    print("\n[OK] 全部校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())