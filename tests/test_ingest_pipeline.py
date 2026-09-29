"""官方正文入库管道的安全测试。

核心性质（必须成立，否则会把残缺正文写进法库并虚假升格）：
  正文不完整时，ingest_official_docs 不得写入 laws/，也不得把
  verification_status 提升为 verified_official。

这些用例会真的构造 docx 并调用入库逻辑，因此是管道唯一的防线。
"""
import shutil
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.ingest_official_docs import (
    extract_docx_paragraphs,
    split_articles,
    ingest_one,
)
from scripts import search_all

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


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


class DocxParsingTests(unittest.TestCase):
    def test_extracts_paragraphs_in_order(self):
        with TemporaryDirectory() as td:
            p = make_docx(Path(td) / "a.docx", ["第一条 内容甲", "第二条 内容乙"])
            got = extract_docx_paragraphs(p)
            self.assertEqual(["第一条 内容甲", "第二条 内容乙"], got)

    def test_split_articles_keeps_body_with_its_number(self):
        paras = [
            "第一章 总则",
            "第一条 甲条规定。",
            "甲条延续内容。",
            "第二条 乙条规定。",
        ]
        arts = split_articles(paras)
        self.assertIn("第一条", arts)
        self.assertIn("第二条", arts)
        self.assertIn("甲条规定。", " ".join(arts["第一条"]))
        self.assertNotIn("第一章", arts)

    def test_chapter_headings_are_not_articles(self):
        arts = split_articles(["第一章 总则", "第二章 合同"])
        self.assertEqual({}, arts)


class IngestSafetyTests(unittest.TestCase):
    """残缺正文绝不能被写入或升格。"""

    def _law_copy(self, td, title="中华人民共和国测试法"):
        src = search_all.ROOT / "laws" / "labor_contract_law.md"
        dst = Path(td) / "test_law.md"
        text = src.read_text(encoding="utf-8")
        text = text.replace("title: 中华人民共和国劳动合同法", "title: " + title, 1)
        dst.write_text(text, encoding="utf-8")
        return dst

    def test_incomplete_doc_is_refused_and_file_untouched(self):
        with TemporaryDirectory() as td:
            law = self._law_copy(td)
            before = law.read_text(encoding="utf-8")
            docx = make_docx(Path(td) / "test_law.docx",
                             ["第一条 只有一条，远少于官方结构。"])
            structure = {law_title(law): {"第一条", "第二条", "第三条"}}
            res = ingest_one(law, docx, structure, apply=False)
            self.assertFalse(res["complete"], "残缺文档被误判为完整")
            self.assertEqual(2, res["missing_count"], "应识别出缺失条数")
            self.assertEqual(before, law.read_text(encoding="utf-8"),
                             "预演模式改动了法文件")

    def test_apply_with_incomplete_doc_leaves_verification_status(self):
        with TemporaryDirectory() as td:
            law = self._law_copy(td)
            docx = make_docx(Path(td) / "test_law.docx", ["第一条 仅一条。"])
            structure = {law_title(law): {"第一条", "第二条"}}
            res = ingest_one(law, docx, structure, apply=True)
            self.assertFalse(res["complete"])
            self.assertFalse(res["applied"])
            text = law.read_text(encoding="utf-8")
            self.assertIn("verification_status: needs_recheck", text)
            self.assertIn("正文待补", text, "占位符被错误替换")

    def test_empty_article_blocks_promotion(self):
        with TemporaryDirectory() as td:
            law = self._law_copy(td)
            docx = make_docx(Path(td) / "test_law.docx",
                             ["第一条 甲。", "第二条"])
            structure = {law_title(law): {"第一条", "第二条"}}
            res = ingest_one(law, docx, structure, apply=False)
            self.assertFalse(res["complete"], "存在空条仍被判为完整")


def law_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("title:"):
            return line.split(":", 1)[1].strip()
    return ""


if __name__ == "__main__":
    unittest.main()
