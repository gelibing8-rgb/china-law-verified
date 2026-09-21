import unittest

from scripts import v501_p0


class V501P0RegressionTests(unittest.TestCase):
    def test_shared_law_preserves_many_to_many_domains(self):
        old = v501_p0.P0_CORE
        v501_p0.P0_CORE = [("01", ["共享法"]), ("03", ["共享法"])]
        try:
            universe = {
                "canonicals": {
                    "shared": {
                        "canonical_document_id": "CD-SHARED",
                        "title": "共享法",
                        "document_type": "law",
                        "candidate_sources": [{"local_text_available": True}],
                        "candidate_paths": ["candidate/shared.md"],
                        "version_status": "current",
                        "legal_status": "effective",
                        "freshness_status": "FRESH",
                        "verification_status": "CANDIDATE",
                        "official_source_url": None,
                        "official_last_verified_at": None,
                        "source_commits": {"fixture": "abc"},
                    }
                }
            }
            business_map = {
                "domains": [
                    {"domain_code": "01", "domain_name": "领域一", "priority": "P0"},
                    {"domain_code": "03", "domain_name": "领域三", "priority": "P0"},
                ]
            }
            out = v501_p0.build_p0_core_documents(universe, business_map)
            self.assertEqual(1, out["p0_core_total"])
            rec = out["p0_core_documents"][0]
            self.assertEqual(["01", "03"], rec["domain_codes"])
            self.assertEqual(["领域一", "领域三"], rec["business_domains"])
        finally:
            v501_p0.P0_CORE = old

    def test_confirmed_rate_uses_strict_predicate(self):
        p0 = {
            "p0_core_documents": [
                {"freshness_status": "FRESH", "legal_status": "effective", "version_status": "current"},
                {"freshness_status": "FRESH", "legal_status": "unknown", "version_status": "current"},
                {"freshness_status": "UNKNOWN", "legal_status": "effective", "version_status": "current"},
            ]
        }
        out = v501_p0.calc_p0_freshness(p0)
        self.assertEqual(2, out["FRESH"])
        self.assertEqual(1, out["current_effective_confirmed"])
        self.assertEqual(33.3, out["p0_current_effective_confirmed_rate"])

    def test_business_gap_builder_is_structured_and_idempotent(self):
        p0 = {
            "missing_from_local_sources": [
                {
                    "domain_code": "99",
                    "domain_name": "测试领域",
                    "missing_title": "测试主法",
                    "reason": "fixture missing",
                }
            ],
            "p0_core_documents": [
                {
                    "canonical_document_id": "CD-NO-TEXT",
                    "title": "无正文本法",
                    "business_domains": ["测试领域"],
                    "local_text_available": False,
                }
            ],
        }
        first, summary1 = v501_p0.build_business_gaps({"gaps": []}, p0)
        scenario_ids = {
            g.get("scenario_id")
            for g in first["gaps"]
            if g.get("missing_type") == "coverage_partial"
        }
        self.assertEqual({"Q3", "Q4", "Q10"}, scenario_ids)
        self.assertEqual(5, summary1["added"])

        second, summary2 = v501_p0.build_business_gaps(first, p0)
        self.assertEqual(0, summary2["added"])
        self.assertEqual(len(first["gaps"]), len(second["gaps"]))


if __name__ == "__main__":
    unittest.main()
