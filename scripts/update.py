#!/usr/bin/env python3
"""china-law-verified 增量更新占位脚本 (V1).

V1 仅:
  1. 读取 metadata/index.jsonl
  2. 输出 verification_status = needs_recheck 的清单
  3. 暴露 update_law(keyword, url) 占位接口 (当前不实际下载)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META_FILE = ROOT / "metadata" / "index.jsonl"


def load_records() -> list[dict]:
    if not META_FILE.exists():
        return []
    out: list[dict] = []
    with META_FILE.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def list_pending(records: list[dict]) -> list[dict]:
    return [r for r in records if r.get("verification_status") == "needs_recheck"]


def update_law(keyword: str, official_url: str) -> dict:
    """占位接口：在 V1 不实际下载，仅返回计划。

    后续接入时使用统一的官方来源抓取器（带重试和失败回退），
    并将新版本写入 laws/<id>.md，同时更新 metadata/index.jsonl。
    """
    return {
        "status": "planned",
        "keyword": keyword,
        "official_url": official_url,
        "scheduled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "V1 不自动下载；需人工在官方站点确认后由 verify.py 重新校验。",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="china-law-verified 增量更新 (V1 占位)")
    parser.add_argument(
        "--plan-update",
        action="store_true",
        help="输出 needs_recheck 清单以及预留接口示例",
    )
    args = parser.parse_args()

    records = load_records()
    pending = list_pending(records)
    print(f"已登记法律: {len(records)} 部")
    print(f"待重新核验 (needs_recheck): {len(pending)} 部")

    if pending:
        print("\n待核验清单:")
        for r in pending:
            print(
                f"  - {r.get('title', '(无标题)')}  "
                f"版本日期 {r.get('version_date', '?')}  "
                f"路径 {r.get('path', '?')}"
            )

    if args.plan_update:
        plan = update_law("示例：民法典", "https://www.npc.gov.cn/...")
        print("\n[接口示例] update_law 返回:")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())