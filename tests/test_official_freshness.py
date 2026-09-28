"""官方现行版本核验的回归测试。

锁住两条不变量：
1. laws/ 中不得存在「标为 VERIFIED 却无逐字正文」的条目
   —— 正文因官方 permission.download=0 仍缺失，verification_status
      只能是 needs_recheck，升格即为造假。
2. 官方元数据核验产物必须存在且三部法律均无版本漂移。
"""
import json
import unittest

from scripts import search_all

ROOT = search_all.ROOT


class VerificationStatusHonestyTests(unittest.TestCase):
    """正文未补齐前，不得把任何 law 标成 verified_official。"""

    def test_no_law_claims_verified_text_while_body_missing(self):
        laws = [p for p in (ROOT / "laws").glob("*.md")
                if p.name.lower() != "readme.md"]
        if not laws:
            self.skipTest("laws/ 为空")
        for p in laws:
            text = p.read_text(encoding="utf-8")
            head = text.split("---", 2)[1] if text.startswith("---") else ""
            status = ""
            for line in head.splitlines():
                if line.startswith("verification_status:"):
                    status = line.split(":", 1)[1].strip()
                    break
            placeholders = text.count("正文待补")
            if status == "verified_official":
                self.fail(
                    f"{p.name} 标为 verified_official 但含 {placeholders} 处正文待补占位符"
                )


class OfficialFreshnessReportTests(unittest.TestCase):
    """官方核验产物必须落盘且无漂移。"""

    REPORT = ROOT / "metadata" / "official-freshness.json"

    def test_report_exists_and_has_no_drift(self):
        if not self.REPORT.exists():
            self.skipTest("尚未运行 scripts/fetch_official_metadata.py")
        report = json.loads(self.REPORT.read_text(encoding="utf-8"))
        self.assertIn("items", report)
        self.assertEqual([], report.get("drift", []), "存在官方版本漂移")
        for item in report["items"]:
            if item.get("status") != "OK":
                continue
            self.assertEqual("CURRENT_MATCH", item.get("verdict"), item.get("path"))
            self.assertEqual(3, item["official"]["sxx"],
                             item.get("path") + " 官方时效性非现行有效")
            self.assertTrue(item.get("snapshot_sha256"), "缺少可复现的快照校验和")

    def test_body_note_records_why_text_is_absent(self):
        if not self.REPORT.exists():
            self.skipTest("尚未运行 scripts/fetch_official_metadata.py")
        report = json.loads(self.REPORT.read_text(encoding="utf-8"))
        note = report.get("body_text_note", "")
        self.assertIn("download", note)
        self.assertIn("内网", note)


class SnapshotIntegrityTests(unittest.TestCase):
    """快照文件必须与报告中记录的 sha256 一致。"""

    def test_snapshots_match_recorded_sha256(self):
        import hashlib

        report_path = ROOT / "metadata" / "official-freshness.json"
        if not report_path.exists():
            self.skipTest("尚未运行 scripts/fetch_official_metadata.py")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        checked = 0
        for item in report["items"]:
            if item.get("status") != "OK" or not item.get("snapshot"):
                continue
            p = ROOT / item["snapshot"]
            if not p.exists():
                self.fail("快照缺失: " + item["snapshot"])
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(item["snapshot_sha256"], digest, item["snapshot"])
            checked += 1
        if checked == 0:
            self.skipTest("无快照可校验")


if __name__ == "__main__":
    unittest.main()
