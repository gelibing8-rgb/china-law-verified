"""统计口径回归测试：候选层审计与正文覆盖率的可信度边界。

这两个脚本决定「今天有什么文本可用」的判断，一旦口径出错就会给出
误导性结论。2026-09-29 的候选层审计曾因两处统计口径错误给出错误结论：

  1. 民法典在候选层按编拆成多个文件，只取最大的一编会把 1260 条
     误报成 526 条。必须按条号并集统计。
  2. 关键词匹配把司法解释、实施条例也拉了进来，实施条例的旧日期
     会让劳动合同法被误判为过期版本。必须排除不同法律文书。

覆盖率报告同理：正文存在但未经人工逐字核验时，不得计入 VERIFIED。
"""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import candidate_usability_audit as audit
from scripts import body_coverage_report as coverage

NL = chr(10)
PLACEHOLDER = "（正文待补：待补齐）"


def write_law(path, status, articles, body_for=None):
    body_for = body_for or {}
    lines = [
        "---",
        "title: 中华人民共和国测试法",
        "verification_status: " + status,
        "content_sha256: " + "0" * 64,
        "---",
        "# 中华人民共和国测试法",
        "",
    ]
    for a in articles:
        lines.append("#### " + a)
        lines.append(body_for.get(a, PLACEHOLDER))
        lines.append("")
    path.write_text(NL.join(lines), encoding="utf-8")
    return path


class CandidateUnionTests(unittest.TestCase):
    """按编拆分的法律必须按条号并集统计，不能只取最大的一编。"""

    def _scan(self, root, keyword):
        old = dict(audit.CANDIDATE_ROOTS)
        audit.CANDIDATE_ROOTS = {"fake": Path(root)}
        try:
            return audit.scan_candidate([keyword])
        finally:
            audit.CANDIDATE_ROOTS = old

    def test_split_files_are_counted_as_union(self):
        with TemporaryDirectory() as td:
            d = Path(td) / "民法典"
            d.mkdir()
            (d / "合同编.md").write_text(
                NL.join(["第一条 甲。", "第二条 乙。", "第三条 丙。", ""]), encoding="utf-8")
            (d / "物权编.md").write_text(
                NL.join(["第四条 丁。", "第五条 戊。", ""]), encoding="utf-8")
            hits, union = self._scan(td, "民法典")
            self.assertEqual(2, len(hits), "应命中两个分编文件")
            self.assertEqual(5, len(union), "并集应为 5 条而非最大文件的 3 条")

    def test_largest_file_alone_would_undercount(self):
        with TemporaryDirectory() as td:
            d = Path(td) / "民法典"
            d.mkdir()
            (d / "a.md").write_text("第一条 甲。" + NL, encoding="utf-8")
            (d / "b.md").write_text(NL.join(["第二条 乙。", "第三条 丙。", ""]), encoding="utf-8")
            hits, union = self._scan(td, "民法典")
            biggest = max(h["articles"] for h in hits)
            self.assertEqual(3, len(union))
            self.assertEqual(2, biggest)
            self.assertGreater(len(union), biggest, "并集必须大于任一单文件")


class CandidateExclusionTests(unittest.TestCase):
    """司法解释、实施条例是不同法律文书，不能污染本法统计。"""

    def _scan(self, root, keyword="劳动合同法"):
        old = dict(audit.CANDIDATE_ROOTS)
        audit.CANDIDATE_ROOTS = {"fake": Path(root)}
        try:
            return audit.scan_candidate([keyword])
        finally:
            audit.CANDIDATE_ROOTS = old

    def test_implementing_regulation_excluded(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "社会法").mkdir()
            (root / "行政法规").mkdir()
            (root / "社会法" / "劳动合同法(2012-12-28).md").write_text(
                NL.join(["第一条 甲。", "第二条 乙。", ""]), encoding="utf-8")
            (root / "行政法规" / "劳动合同法实施条例(2008-09-18).md").write_text(
                "第三条 丙。" + NL, encoding="utf-8")
            hits, union = self._scan(root)
            rels = [h["relative_path"] for h in hits]
            self.assertEqual(1, len(hits), "实施条例未被排除: " + str(rels))
            self.assertEqual(2, len(union))

    def test_judicial_interpretation_excluded(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "司法解释").mkdir()
            (root / "民法商法").mkdir()
            (root / "民法商法" / "公司法(2018-10-26).md").write_text(
                "第一条 甲。" + NL, encoding="utf-8")
            (root / "司法解释" / "最高人民法院关于适用《公司法》若干问题的规定（三）.md").write_text(
                "第二条 乙。" + NL, encoding="utf-8")
            hits, union = self._scan(root, "公司法")
            rels = [h["relative_path"] for h in hits]
            self.assertEqual(1, len(hits), "司法解释未被排除: " + str(rels))
            self.assertEqual(1, len(union))


class VerdictTests(unittest.TestCase):
    """版本判定。"""

    def test_same_version_aligned(self):
        v = audit.verdict({"第一条", "第二条"}, {"第一条", "第二条"},
                          [{"version_date_in_name": "2012-12-28"}], "2012-12-28")
        self.assertEqual("ALIGNED_CANDIDATE", v)

    def test_older_candidate_is_stale(self):
        v = audit.verdict({"第一条"}, {"第一条"},
                          [{"version_date_in_name": "2018-10-26"}], "2023-12-29")
        self.assertEqual("STALE_VERSION", v)

    def test_short_candidate_is_incomplete(self):
        v = audit.verdict({"第一条", "第二条", "第三条"}, {"第一条"},
                          [{"version_date_in_name": "2023-12-29"}], "2023-12-29")
        self.assertEqual("INCOMPLETE", v)

    def test_no_candidate_text(self):
        v = audit.verdict({"第一条"}, set(), [], "2023-12-29")
        self.assertEqual("NO_CANDIDATE_TEXT", v)


class CoverageTrustTests(unittest.TestCase):
    """正文存在不等于已核验；未经人工核验不得计入 VERIFIED。"""

    def test_placeholder_counts_as_placeholder(self):
        with TemporaryDirectory() as td:
            p = write_law(Path(td) / "x.md", "needs_recheck", ("第一条", "第二条"))
            r = coverage.scan(p)
            self.assertEqual(2, r["articles"])
            self.assertEqual(0, r["with_verified_text"])
            self.assertEqual(2, r["placeholder"])

    def test_text_with_needs_recheck_is_not_verified(self):
        with TemporaryDirectory() as td:
            p = write_law(Path(td) / "x.md", "needs_recheck", ("第一条", "第二条"),
                         {"第一条": "第一条 甲条规定正文。"})
            r = coverage.scan(p)
            self.assertEqual(0, r["with_verified_text"], "needs_recheck 被误计为 VERIFIED")
            self.assertEqual(1, r["with_unverified_text"])

    def test_text_with_verified_official_counts(self):
        with TemporaryDirectory() as td:
            p = write_law(Path(td) / "x.md", "verified_official", ("第一条",),
                         {"第一条": "第一条 甲条规定正文。"})
            r = coverage.scan(p)
            self.assertEqual(1, r["with_verified_text"])
            self.assertEqual(0, r["with_unverified_text"])
            self.assertEqual(100.0, r["coverage_pct"])


if __name__ == "__main__":
    unittest.main()

