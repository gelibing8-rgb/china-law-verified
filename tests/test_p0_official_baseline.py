import unittest

from scripts.check_p0_official_baseline import (
    classify_candidate_set,
    extract_candidate_dates,
)

class OfficialBaselineTests(unittest.TestCase):
    def test_extract_dates(self):
        got = [
            d.isoformat()
            for d in extract_candidate_dates(
                [
                    "公司法(2018-10-26).md",
                    "x/2021-12-24/a.md",
                    "x/no-date.md",
                ]
            )
        ]
        self.assertEqual(["2018-10-26", "2021-12-24"], got)

    def test_mixed_version_with_current_provenance(self):
        status, old_date = classify_candidate_set(
            [
                "just-laws::docs/civil-and-commercial/company-law/README.md",
                "china-data-laws::民法商法/公司法(2018-10-26).md",
            ],
            "2023-12-29",
            {"status": "CURRENT_CANDIDATE_PRESENT"},
        )
        self.assertEqual("MIXED_VERSION_CANDIDATES", status)
        self.assertEqual("2018-10-26", old_date)

    def test_current_candidate_without_old_dated_copy(self):
        self.assertEqual(
            ("CURRENT_CANDIDATE_PRESENT", None),
            classify_candidate_set(
                ["just-laws::docs/procedural/civil-procedure/README.md"],
                "2023-09-01",
                {"status": "CURRENT_CANDIDATE_PRESENT"},
            ),
        )

    def test_stale_only_without_current_provenance(self):
        self.assertEqual(
            ("LOCAL_STALE_ONLY", "2021-12-24"),
            classify_candidate_set(
                ["china-data-laws::诉讼与非诉讼程序法/民事诉讼法(2021-12-24).md"],
                "2023-09-01",
                None,
            ),
        )

if __name__ == "__main__":
    unittest.main()
