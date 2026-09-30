#!/bin/sh
# 每日 08:00（Asia/Shanghai）法律库例行任务。
#
# 1) 官方现行版本核验：向 flk.npc.gov.cn 的 flfgDetails 逐条核对
#    laws/ 的公布日期、施行日期与时效性，发现漂移即以非零码退出。
#    该接口为官方页面自身调用的公开 GET 接口，无鉴权、无验证码。
# 2) 把复核时间落盘（verification_status 不会被提升，正文仍未补齐）。
# 3) 候选层可用性审计：官方正文不可得时，说明今天有哪些文本可用、
#    版本是否与官方现行一致。信任上限固定为 CANDIDATE。
# 4) 变化发现雷达（agent-driven，仅枚举查询，不自行联网）。
#
# 明确不做：不触碰 captchaImage 与 download/* 等被官方禁用的接口，
# 不下载正文文档（permission.download=0），不绕过任何访问控制，
# 不把候选层正文复制进 laws/。
set -eu

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "[1/4] 官方现行版本核验"
if python3 scripts/fetch_official_metadata.py; then
  echo "      无版本漂移"
else
  echo "      !! 检出版本漂移，详见 metadata/official-freshness.json"
  fetch_rc=0
fi

echo "[2/4] 记录官方复核时间"
python3 scripts/record_official_verification.py --apply

echo "[3/4] 正文覆盖与候选层可用性"
python3 scripts/body_coverage_report.py
python3 scripts/candidate_usability_audit.py

echo "[4/4] 变化发现雷达"
python3 scripts/discover_changes.py

exit ${fetch_rc:-0}
