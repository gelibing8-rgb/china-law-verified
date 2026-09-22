import unittest

from scripts.check_p0_official_baseline import (
    detect_local_status,
    extract_candidate_dates,
)


class OfficialBaselineTests(
    unittest.TestCase
):
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

        self.assertEqual(
            [
                "2018-10-26",
                "2021-12-24",
            ],
            got,
        )

    def test_statuses(self):
        self.assertEqual(
            (
                "LOCAL_STALE",
                "2018-10-26",
            ),
            detect_local_status(
                [
                    "公司法(2018-10-26).md"
                ],
                "2023-12-29",
            ),
        )

        self.assertEqual(
            (
                "DATE_ALIGNED",
                "2023-12-29",
            ),
            detect_local_status(
                [
                    "公司法(2023-12-29).md"
                ],
                "2023-12-29",
            ),
        )

        self.assertEqual(
            (
                "NO_DATED_CANDIDATE",
                None,
            ),
            detect_local_status(
                [
                    "公司法.md"
                ],
                "2023-12-29",
            ),
        )


if __name__ == "__main__":
    unittest.main()
