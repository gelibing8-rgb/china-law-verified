"""按 verify.py 的同一口径重算 laws/*.md 的 content_sha256 并同步 index.jsonl。

口径必须与 verify.py 完全一致，否则改完仍然 FAIL。
复用 verify.parse_frontmatter / sha256_of，避免二次实现漂移。
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# 直接以脚本方式运行时 sys.path 只有 scripts/，需把仓库根加进去才能 import scripts.*
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify import LAWS_DIR, parse_frontmatter, sha256_of  # noqa: E402

INDEX = ROOT / "metadata" / "index.jsonl"
NL = chr(10)


def main() -> int:
    new_sha = {}
    for p in sorted(LAWS_DIR.glob("*.md")):
        if p.name.lower() == "readme.md":
            continue
        text = p.read_text(encoding="utf-8")
        meta, body, _errors = parse_frontmatter(p)
        h = sha256_of(body)
        new_sha["laws/" + p.name] = h
        old = meta.get("content_sha256", "")
        if old == h:
            continue
        new_meta = re.sub(
            r"^content_sha256:.*$", "content_sha256: " + h, text, count=1, flags=re.M
        )
        p.write_text(new_meta, encoding="utf-8")
        print("frontmatter " + p.name + ": " + old[:12] + " -> " + h[:12])

    lines = INDEX.read_text(encoding="utf-8").splitlines()
    out, changed = [], 0
    for ln in lines:
        if not ln.strip():
            out.append(ln)
            continue
        d = json.loads(ln)
        k = d.get("path")
        if k in new_sha and d.get("content_sha256") != new_sha[k]:
            d["content_sha256"] = new_sha[k]
            changed += 1
        out.append(json.dumps(d, ensure_ascii=False))
    INDEX.write_text(NL.join(out) + NL, encoding="utf-8")
    print("index.jsonl rows updated: " + str(changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
