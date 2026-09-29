"""入库闸门测试：覆盖新增的 fail-closed 闸门。

结构检查通过不等于可以写入。以下性质必须成立，否则会把未经逐字核验的
正文写进法库，或覆盖已经 VERIFIED 的正文：

1. 已标 verified_official 的法律文件必须被拒绝（保护已核验正文）。
2. 法库缺少某条法条的占位行时必须拒绝（否则该条正文无处落盘）。
3. 法库缺少某条法条标题时必须拒绝。
4. 重复条号必须拒绝（目录页或拼接文档会伪装成完整正文）。
5. 没有官方结构快照时必须拒绝。
6. 结构通过时写入正文但保持 needs_recheck，并同步 content_sha256。
"""
import hashlib
import re
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.ingest_official_docs import ingest_one

NL = chr(10)
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PLACEHOLDER = "（正文待补：来自官方文档，待补齐）"
STRUCT = {"中华人民共和国测试法": {"第一条", "第二条"}}


def make_docx(path: Path, paragraphs) -> Path:
    ps = "".join(
        '<w:p><w:r><w:t xml:space="preserve">' + p + "</w:t></w:r></w:p>"
        for p in paragraphs
    )
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="' + W + '"><w:body>' + ps + "</w:body></w:document>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", doc)
    return path


def make_law(path: Path, *, status: str = "needs_recheck",
             articles=("第一条", "第二条"), with_placeholder: bool = True) -> Path:
    lines = [
        "---",
        "title: 中华人民共和国测试法",
        "document_type: 法律",
        "issuing_authority: 全国人民代表大会常务委员会",
        "promulgation_date: 2020-01-01",
        "original_effective_date: 2020-01-01",
        "current_version_date: 2020-01-01",
        "current_version_effective_date: 2020-01-01",
        "status: 现行",
        "official_url: https://flk.npc.gov.cn/detail.html?bbbs=zzz",
        "retrieved_at: 2026-09-29T00:00:00Z",
        "verification_status: " + status,
        "content_sha256: " + "0" * 64,
        "---",
        "# 中华人民共和国测试法",
        "",
    ]
    for a in articles:
        lines.append("#### " + a)
        lines.append(PLACEHOLDER if with_placeholder else "")
        lines.append("")
    path.write_text(NL.join(lines), encoding="utf-8")
    return path


class GateTests(unittest.TestCase):
    def test_verified_law_is_refused_and_not_overwritten(self):
        with TemporaryDirectory() as td:
            law = make_law(Path(td) / "t.md", status="verified_official")
            docx = make_docx(Path(td) / "t.docx", ["第一条 甲。", "第二条 乙。"])
            res = ingest_one(law, docx, STRUCT, apply=True)
            self.assertFalse(res["structurally_complete"], "已核验法律被允许覆盖")
            self.assertEqual("verified_official", res["existing_verification_status"])
            self.assertFalse(res["applied"])
            text = law.read_text(encoding="utf-8")
            self.assertIn("verification_status: verified_official", text)
            self.assertIn(PLACEHOLDER, text, "已核验正文被覆盖")

    def test_missing_placeholder_row_blocks_write(self):
        with TemporaryDirectory() as td:
            law = make_law(Path(td) / "t.md", with_placeholder=False)
            docx = make_docx(Path(td) / "t.docx", ["第一条 甲。", "第二条 乙。"])
            res = ingest_one(law, docx, STRUCT, apply=False)
            self.assertFalse(res["structurally_complete"])
            self.assertEqual(["第一条", "第二条"], res["missing_placeholders"])

    def test_missing_markdown_heading_blocks_write(self):
        with TemporaryDirectory() as td:
            law = make_law(Path(td) / "t.md", articles=("第一条",))
            docx = make_docx(Path(td) / "t.docx", ["第一条 甲。", "第二条 乙。"])
            res = ingest_one(law, docx, STRUCT, apply=False)
            self.assertFalse(res["structurally_complete"])
            self.assertEqual(["第二条"], res["missing_law_markdown_headings"])

    def test_duplicate_article_blocks_write(self):
        with TemporaryDirectory() as td:
            law = make_law(Path(td) / "t.md")
            docx = make_docx(Path(td) / "t.docx",
                             ["第一条 甲。", "第二条 乙。", "第一条 甲（目录重复）。"])
            res = ingest_one(law, docx, STRUCT, apply=True)
            self.assertFalse(res["structurally_complete"], "重复条号未被拦截")
            self.assertEqual(["第一条"], res["duplicate_articles"])
            self.assertFalse(res["applied"])

    def test_missing_official_structure_blocks_write(self):
        with TemporaryDirectory() as td:
            law = make_law(Path(td) / "t.md")
            docx = make_docx(Path(td) / "t.docx", ["第一条 甲。", "第二条 乙。"])
            res = ingest_one(law, docx, {}, apply=True)
            self.assertFalse(res["structurally_complete"])
            self.assertFalse(res["structure_available"])
            self.assertFalse(res["applied"], "无官方结构时仍写入")

    def test_structural_match_writes_body_without_promotion(self):
        with TemporaryDirectory() as td:
            law = make_law(Path(td) / "t.md")
            docx = make_docx(Path(td) / "t.docx",
                             ["第一条 甲条规定。", "第二条 乙条规定。"])
            res = ingest_one(law, docx, STRUCT, apply=True)
            self.assertTrue(res["structurally_complete"], res.get("reason"))
            self.assertTrue(res["applied"])

            text = law.read_text(encoding="utf-8")
            self.assertIn("verification_status: needs_recheck", text)
            self.assertNotIn("verified_official", text)
            self.assertIn("第一条 甲条规定。", text)
            self.assertIn("第二条 乙条规定。", text)
            self.assertNotIn(PLACEHOLDER, text)
            self.assertNotIn("body_verified_at", text, "误记人工核验时间")
            self.assertIn("body_ingested_at", text)

            m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
            self.assertIsNotNone(m, "写入后 frontmatter 结构损坏")
            declared = re.search(r"^content_sha256:\s*(\S+)", m.group(1), re.M).group(1)
            actual = hashlib.sha256(m.group(2).lstrip("\n").encode("utf-8")).hexdigest()
            self.assertEqual(declared, actual, "写入后 content_sha256 未同步")


if __name__ == "__main__":
    unittest.main()
