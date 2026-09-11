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
git push origin main
