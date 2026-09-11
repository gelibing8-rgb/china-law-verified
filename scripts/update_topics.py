#!/usr/bin/env python3
"""只重建受影响专题；不访问政府/法院网站。"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPICS = ROOT / "legal-topics"
BUILDER = ROOT / "scripts" / "build_topic.py"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--topics", nargs="+", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    for topic_id in args.topics:
        path = TOPICS / topic_id / "manifest.json"
        if not path.exists():
            print(f"[SKIP] topic 不存在: {topic_id}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        primary = data.get("topic", {}).get("primary_law")
        if not primary:
            print(f"[SKIP] 缺少 primary_law: {topic_id}")
            continue
        if args.dry_run:
            print(f"[DRY-RUN] rebuild {topic_id}: {primary}")
            continue
        subprocess.run([sys.executable, str(BUILDER), "--primary-law", primary, "--topic-id", topic_id], check=True)
    if not args.dry_run:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_registry.py")], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
