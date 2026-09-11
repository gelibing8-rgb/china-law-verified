#!/usr/bin/env python3
"""GitHub 候选库增量更新器。

只执行候选仓库 git pull、读取 git diff、重建受影响专题；绝不运行候选仓库自带脚本。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "metadata" / "update-state.json"
SOURCES = {
    "just-laws": ROOT.parent / "legal-sources" / "just-laws",
    "lawtext-laws": ROOT.parent / "legal-sources" / "laws",
    "china-data-laws": ROOT.parent / "legal-sources" / "china-data-laws",
}


def run(cmd: list[str], cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=str(cwd) if cwd else None, text=True).strip()


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def affected_topics(source: str, changed: list[str]) -> list[str]:
    out = set()
    for p in ROOT.joinpath("legal-topics").glob("*/manifest.json"):
        if p.parent.name == "_schema":
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for doc in list(d.get("documents", [])) + list(d.get("documents_related", [])):
            for cs in doc.get("candidate_sources", []) or []:
                if cs.get("source") == source and cs.get("relative_path") in changed:
                    out.add(p.parent.name)
    return sorted(out)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    state = {"updated_at": now(), "dry_run": args.dry_run, "sources": [], "affected_topics": []}
    for name, path in SOURCES.items():
        rec = {"source": name, "path": str(path), "old_commit": None, "new_commit": None, "changed_files": [], "status": "skipped"}
        if not path.exists():
            rec["status"] = "missing"
            state["sources"].append(rec)
            continue
        rec["old_commit"] = run(["git", "rev-parse", "HEAD"], path)
        if args.dry_run:
            rec["new_commit"] = rec["old_commit"]
            rec["status"] = "dry_run"
        else:
            dirty = run(["git", "status", "--porcelain"], path)
            if dirty:
                rec["status"] = "blocked_dirty_worktree"
                state["sources"].append(rec)
                continue
            subprocess.run(["git", "pull", "--ff-only"], cwd=str(path), check=True)
            rec["new_commit"] = run(["git", "rev-parse", "HEAD"], path)
            if rec["old_commit"] != rec["new_commit"]:
                rec["changed_files"] = run(["git", "diff", "--name-only", rec["old_commit"], rec["new_commit"]], path).splitlines()
            rec["status"] = "updated" if rec["changed_files"] else "unchanged"
        topics = affected_topics(name, rec["changed_files"])
        rec["affected_topics"] = topics
        state["affected_topics"] = sorted(set(state["affected_topics"]) | set(topics))
        state["sources"].append(rec)
    changed_or_issue = any(s.get("status") not in {"unchanged", "dry_run"} for s in state["sources"])
    if args.dry_run or changed_or_issue or state["affected_topics"]:
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False, indent=2))
    if not args.dry_run and state["affected_topics"]:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "update_topics.py"), "--topics", *state["affected_topics"]], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
