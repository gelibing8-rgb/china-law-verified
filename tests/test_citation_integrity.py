"""V5.0.4 回归测试：锁住引用完整性、来源合规与元数据语义。

每个用例对应一个已修复的真实缺陷，防止静默退化：

1. load_index 键名失配            -> IndexKeyTests
2. 标题冒充法条原文                -> VerifiedQuoteIntegrityTests
3. laws/README.md 假命中           -> ReadmeExclusionTests
4. 域名白名单越界                  -> WhitelistComplianceTests
5. 无人值守自动 push                -> PushGateTests
6. OFFICIAL_META 缺官方来源        -> OfficialMetaProvenanceTests
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import search_all
from scripts.search_all import classify_law_line, fmt_law_hit, load_index
from scripts import discover_changes


class LawLineClassificationTests(unittest.TestCase):
    """命中行必须能被判定为「可引用正文」或「非正文」。"""

    def test_markdown_heading_is_not_body(self):
        for line in (
            "## 第四章 有限责任公司的股权转让",
            "### 第二节 股东会",
            "# 中华人民共和国公司法",
        ):
            kind, _ = classify_law_line(line)
            self.assertEqual("heading", kind, line)

    def test_frontmatter_is_not_body(self):
        for line in (
            "title: 中华人民共和国公司法",
            "verification_status: needs_recheck",
            "official_url: https://flk.npc.gov.cn/detail.html?bbbs=x",
        ):
            kind, _ = classify_law_line(line)
            self.assertEqual("frontmatter", kind, line)

    def test_placeholder_is_not_body(self):
        line = "（正文待补：来自 flk.npc.gov.cn 的 WPS/OFD 文档无法在公网下载。条目 ID：x）"
        kind, _ = classify_law_line(line)
        self.assertEqual("placeholder", kind)

    def test_real_article_text_is_body(self):
        kind, art = classify_law_line("第八十四条 股东可以向其他股东转让股权。")
        self.assertEqual("text", kind)
        self.assertEqual("第八十四条", art)

    def test_arabic_numeral_article_is_body(self):
        kind, art = classify_law_line("第84条 依照本法规定。")
        self.assertEqual("text", kind)
        self.assertEqual("第84条", art)

    def test_empty_line(self):
        self.assertEqual("empty", classify_law_line("   ")[0])


class VerifiedQuoteIntegrityTests(unittest.TestCase):
    """核心红线：非正文命中绝不能以「原文」字段呈现。"""

    IDX = {
        "company_law_2024.md": {
            "title": "中华人民共和国公司法",
            "official_url": "https://flk.npc.gov.cn/detail.html?bbbs=ff80",
            "current_version_date": "2023-12-29",
            "verification_status": "needs_recheck",
        }
    }

    def test_nonbody_never_rendered_as_verified_quote(self):
        for line in (
            "## 第四章 有限责任公司的股权转让",
            "title: 中华人民共和国公司法",
            "（正文待补：WPS/OFD 无法下载。条目 ID：x）",
        ):
            out = chr(10).join(
                fmt_law_hit("company_law_2024.md", 10, line, self.IDX, "OFFICIAL_META")
            )
            self.assertNotIn("原文:", out, "非正文行被当成可引用原文: " + line)
            self.assertIn("非正文", out)
            self.assertIn("不得作为法条原文引用", out)

    def test_body_text_still_rendered_as_quote(self):
        line = "第八十四条 股东可以向其他股东转让股权。"
        out = chr(10).join(
            fmt_law_hit("company_law_2024.md", 10, line, self.IDX, "OFFICIAL_META")
        )
        self.assertIn("原文: " + line, out)
        self.assertNotIn("非正文", out)

    def test_metadata_resolves_by_bare_filename(self):
        """索引键是 laws/xxx.md，检索传 xxx.md —— 必须仍能取到元数据。"""
        src = self.IDX["company_law_2024.md"]
        idx = {"laws/company_law_2024.md": src}
        out = chr(10).join(
            fmt_law_hit("company_law_2024.md", 290, "## 第四章", idx, "OFFICIAL_META")
        )
        self.assertIn("标题: 中华人民共和国公司法", out)
        self.assertIn("版本日期: 2023-12-29", out)
        self.assertIn("https://flk.npc.gov.cn/", out)
        self.assertNotIn("官方来源: (无)", out)


class IndexKeyTests(unittest.TestCase):
    def test_index_registers_both_key_forms(self):
        idx = load_index()
        if not idx:
            self.skipTest("metadata/index.jsonl 不存在")
        for rel in (
            "laws/civil_code.md",
            "laws/company_law_2024.md",
            "laws/labor_contract_law.md",
        ):
            stem = Path(rel).name
            self.assertIn(rel, idx, "缺少仓库根键 " + rel)
            self.assertIn(stem, idx, "缺少 LAWS_DIR 基准键 " + stem)
            self.assertEqual(idx[rel]["title"], idx[stem]["title"])


class ReadmeExclusionTests(unittest.TestCase):
    """README 是说明文档，被当法条命中会污染结果并被误当原文引用。"""

    def test_readme_excluded_from_both_backends(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text("劳动合同法 速查表", encoding="utf-8")
            (root / "x_law.md").write_text("劳动合同法 正文", encoding="utf-8")
            for backend in (search_all.iter_rg, search_all.iter_python):
                rels = {rel for rel, _, _ in backend(root, "劳动合同法")}
                self.assertNotIn("README.md", rels, backend.__name__ + " 未排除 README")
                self.assertIn("x_law.md", rels, backend.__name__ + " 误伤正常法条文件")


class WhitelistComplianceTests(unittest.TestCase):
    """自动化不得主动访问 sources.yaml 白名单之外的政府站点。"""

    def _allowed(self):
        allowed = set()
        in_block = False
        for raw in (search_all.ROOT / "sources.yaml").read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].rstrip()
            if line.startswith("allowed_domains:"):
                in_block = True
                continue
            if in_block:
                if line.strip().startswith("-"):
                    allowed.add(line.strip()[1:].strip())
                elif line.strip():
                    break
        return allowed

    def test_official_domains_within_whitelist(self):
        allowed = self._allowed()
        self.assertTrue(allowed, "未能从 sources.yaml 解析 allowed_domains")
        extra = set(discover_changes.OFFICIAL_DOMAINS) - allowed
        self.assertFalse(extra, "越界域名: " + str(sorted(extra)))

    def test_flk_domain_present(self):
        self.assertIn("flk.npc.gov.cn", discover_changes.OFFICIAL_DOMAINS)


class PushGateTests(unittest.TestCase):
    """无人值守定时任务不得自动 push。"""

    def test_weekly_update_does_not_push_unconditionally(self):
        text = (search_all.ROOT / "scripts" / "weekly_update.sh").read_text(encoding="utf-8")
        self.assertIn("LAW_UPDATE_PUSH", text)
        self.assertIn("跳过 git push", text)


class OfficialMetaProvenanceTests(unittest.TestCase):
    """V5.0.2 语义：OFFICIAL_META 必须有 official_source_url，否则应为 CANDIDATE。

    该修正曾在 rebase 到 origin/main 时丢失（远端独立演进 metadata 时未包含
    它），导致 16 条无官方来源的条目被标成 OFFICIAL_META。
    """

    METADATA = (
        "metadata/p0-core-documents.json",
        "metadata/current-version-registry.json",
        "metadata/legal-universe.json",
    )

    def _collect(self, node, out):
        if isinstance(node, dict):
            if node.get("verification_status") == "OFFICIAL_META":
                out.append(node)
            for v in node.values():
                self._collect(v, out)
        elif isinstance(node, list):
            for v in node:
                self._collect(v, out)

    def test_official_meta_requires_official_source_url(self):
        checked = 0
        for rel in self.METADATA:
            f = search_all.ROOT / rel
            if not f.exists():
                continue
            entries = []
            self._collect(json.loads(f.read_text(encoding="utf-8")), entries)
            for e in entries:
                checked += 1
                label = e.get("title") or e.get("canonical_document_id")
                self.assertTrue(
                    e.get("official_source_url"),
                    rel + ": OFFICIAL_META 缺 official_source_url (" + str(label) + ")",
                )
        # 不因当前为 0 条而 skip：不变式必须始终成立，将来若有人把
        # 无官方来源的条目重新标成 OFFICIAL_META，本用例会立即失败。
        self.assertGreaterEqual(checked, 0)


if __name__ == "__main__":
    unittest.main()
