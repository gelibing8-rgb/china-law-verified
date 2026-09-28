#!/bin/sh
set -eu

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$PROJECT_DIR"

python3 scripts/update_candidates.py
python3 scripts/validate_topics.py

if git diff --quiet -- legal-topics metadata scripts; then
  exit 0
fi

git add legal-topics metadata scripts
git commit -m "chore: update local legal candidate indexes"

# 对外发布属高风险动作：无人值守定时任务不得自动 push。
# 需要推送时显式执行：LAW_UPDATE_PUSH=1 scripts/weekly_update.sh
if [ "${LAW_UPDATE_PUSH:-0}" = "1" ]; then
  git push origin main
else
  echo "[skip] 未设置 LAW_UPDATE_PUSH=1，跳过 git push（本地已提交）"
fi
