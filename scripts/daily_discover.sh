#!/bin/sh
# V4.1 每日 08:00（Asia/Shanghai）雷达调度入口。
# 推荐由外部 cron / launchd / OpenClaw 调度器以 --dry-run 预演后调用。
set -eu
PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$PROJECT_DIR"

python3 scripts/discover_changes.py