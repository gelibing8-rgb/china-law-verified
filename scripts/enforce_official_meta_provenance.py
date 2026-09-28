"""恢复 V5.0.2 语义修正：缺官方来源的条目不得标 OFFICIAL_META。

规则（来自 V5.0.2，rebase 时一度丢失）：
  verification_status = OFFICIAL_META 要求 official_source_url 非空。
  不允许仅靠候选源交叉印证就升 OFFICIAL_META。
  CANDIDATE 与 FRESH 可共存：freshness 只代表本地候选版本未过期，
  不代表官方核验，因此不因降级而清空 freshness_status。
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILES = [
    "metadata/p0-core-documents.json",
    "metadata/current-version-registry.json",
    "metadata/legal-universe.json",
]


def walk(node, visit):
    if isinstance(node, dict):
        visit(node)
        for v in node.values():
            walk(v, visit)
    elif isinstance(node, list):
        for v in node:
            walk(v, visit)


def main() -> int:
    if "--apply" not in sys.argv:
        print("dry-run: 加 --apply 实际写入")
    apply = "--apply" in sys.argv
    total = 0
    for rel in FILES:
        f = ROOT / rel
        if not f.exists():
            print("skip", rel)
            continue
        raw = f.read_text(encoding="utf-8")
        data = json.loads(raw)
        demoted = []

        def visit(node, _rel=rel, _acc=demoted):
            if node.get("verification_status") == "OFFICIAL_META" and not node.get(
                "official_source_url"
            ):
                node["verification_status"] = "CANDIDATE"
                _acc.append(node.get("title") or node.get("canonical_document_id"))

        walk(data, visit)
        if demoted:
            total += len(demoted)
            print(rel, "-> demoted", len(demoted), ":", demoted[:6])
            if apply:
                f.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2) + chr(10),
                    encoding="utf-8",
                )
    print("total demoted:", total, "| applied:", apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
