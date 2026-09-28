"""把官方元数据复核时间写入 laws/*.md frontmatter 与 metadata/index.jsonl。

重要：verification_status 保持 needs_recheck 不变。
本次核验只证明「元数据与官方一致、且仍为现行版本」，
不证明正文已逐字核验——正文仍因官方 permission.download=0 而缺失。
把 verification_status 升为 verified_official 属于造假。
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FRESH = ROOT / "metadata" / "official-freshness.json"
INDEX = ROOT / "metadata" / "index.jsonl"
FIELD = "official_metadata_verified_at"
GUARD = "needs_recheck"


def main() -> int:
    if not FRESH.exists():
        print(f"[FAIL] 缺少 {FRESH}，请先运行 scripts/fetch_official_metadata.py")
        return 2
    report = json.loads(FRESH.read_text(encoding="utf-8"))
    ts = report["generated_at"]
    ok = {i["path"] for i in report["items"]
          if i.get("status") == "OK" and not i.get("mismatches")}

    apply = "--apply" in sys.argv
    changed = 0
    for rel in sorted(ok):
        p = ROOT / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        m = re.match(r"^(---\s*\n)(.*?)(\n---\s*\n)", text, re.DOTALL)
        if not m:
            print(f"[skip] {rel}: 无 frontmatter")
            continue
        meta = m.group(2)
        # 防线：正文未补齐前，verification_status 不得被提升。
        if re.search(r"^verification_status:\s*\S+", meta, re.M):
            meta = re.sub(r"^(verification_status:)\s*\S+",
                          r"\1 " + GUARD, meta, count=1, flags=re.M)
        if re.search(rf"^{FIELD}:", meta, re.M):
            meta = re.sub(rf"^{FIELD}:.*$", f"{FIELD}: {ts}", meta, count=1, flags=re.M)
        else:
            meta = meta.rstrip() + chr(10) + f"{FIELD}: {ts}"
        new_text = m.group(1) + meta + m.group(3) + text[m.end():]
        if new_text != text:
            changed += 1
            print(f"  [update] {rel} {FIELD}={ts} (verification_status={GUARD})")
            if apply:
                p.write_text(new_text, encoding="utf-8")

    if apply:
        lines = INDEX.read_text(encoding="utf-8").splitlines()
        out, n = [], 0
        for ln in lines:
            if not ln.strip():
                out.append(ln)
                continue
            d = json.loads(ln)
            if d.get("path") in ok:
                d[FIELD] = ts
                d["verification_status"] = GUARD
                n += 1
            out.append(json.dumps(d, ensure_ascii=False))
        INDEX.write_text(chr(10).join(out) + chr(10), encoding="utf-8")
        print(f"index.jsonl 更新 {n} 行")

    print(f"待更新 {changed} 个文件 | applied: {apply}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
