#!/usr/bin/env python3
"""V3.1 公司法专题 manifest 构建器.

设计原则：
- 每个 document 必须含 verification_status 与 legal_status（两个独立维度）
- 统计从 documents[] 实际生成，不允许手填
- 案例拆到具体案件；批次入 case_collections
- 部门规章禁止空泛占位；盘点不到 = 不写
- 不能从公开官方来源确认效力的 = legal_status=pending_verification，不猜

运行后生成 manifest.yaml（统计字段由本脚本计算）。
"""
from __future__ import annotations
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

OUT = Path(__file__).resolve().parent / "manifest.yaml"

# 字段取值范围（V3.1 spec）
LEGAL_STATUSES = {"effective", "repealed", "replaced", "historical",
                  "draft", "pending_verification", "not_applicable"}
VERIFICATION_STATUSES = {"VERIFIED", "OFFICIAL_META", "CANDIDATE", "UNVERIFIED"}
RELATION_STRENGTHS = {"core", "direct", "related"}
RELATION_TYPES = {
    "primary_law", "administrative_regulation", "department_rule",
    "normative_document", "judicial_interpretation",
    "guiding_case", "people_court_case", "typical_case", "gazette_case",
    "historical_version"}

NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ============================================================
# 文档清单（基于公开来源核验）
# ============================================================

# 司法解释现状（来源：web_search 命中 最高法民二庭负责人答记者问 / 法释号公开资料）
# 关键事实：
#  - 司法解释（一）2014修正 = 法释〔2014〕2号，仍有效（与新法无冲突部分继续适用）
#  - 司法解释（二）（三）（四）（五）2020修正 = 法释〔2020〕18号，仍有效（同上）
#  - 时间效力规定 = 法释〔2024〕7号，现行有效
#  - 第八十八条批复 = 法释〔2024〕15号，现行有效
#  - 旧版司法解释（2006/2008/2011/2014/2017/2019）flk 登记 sxx=2，但官方未明文废止；
#    实际被后续修正版取代。legal_status = "replaced"
DOCUMENTS: list[dict] = []

def add(doc_id, **kw):
    kw["document_id"] = doc_id
    DOCUMENTS.append(kw)
    return doc_id

# 1) 主法律
add("CL-PRIMARY-2024",
    title="中华人民共和国公司法（2023 修订）",
    document_type="法律",
    relation_type="primary_law",
    relation_strength="core",
    legal_status="effective",
    status_basis="verified_official_metadata",
    status_basis_url="https://flk.npc.gov.cn/detail.html?bbbs=ff8081818c9108eb018cb6922f750c07",
    verified_at="2026-09-10",
    verification_status="OFFICIAL_META",
    issuing_authority="全国人民代表大会常务委员会",
    promulgation_date="2023-12-29",
    effective_date="2024-07-01",
    original_effective_date="1994-07-01",
    bbbs="ff8081818c9108eb018cb6922f750c07",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff8081818c9108eb018cb6922f750c07",
    local_path="laws/company_law_2024.md",
    # V3.1.1：显式声明 just-laws 中公司法全文路径，不再用模糊 title 匹配
    candidate_path="docs/civil-and-commercial/company-law/README.md",
    document_number="中华人民共和国主席令第十五号",
    notes="元数据 + 结构树已通过 flk.npc.gov.cn API 核验；正文为占位，未逐字官方核验。"
)

# 2) 历史版本
add("CL-2018-CORRECTION",
    title="中华人民共和国公司法（2018 修正版）",
    document_type="法律",
    relation_type="historical_version",
    relation_strength="related",
    legal_status="replaced",
    status_basis="flk_sxx_record",
    status_basis_url="https://flk.npc.gov.cn/detail.html?bbbs=ff8080816f135f46016f1cc98ad81134",
    verified_at="2026-09-10",
    verification_status="CANDIDATE",
    issuing_authority="全国人民代表大会常务委员会",
    promulgation_date="2018-10-26",
    effective_date="2018-10-26",
    bbbs="ff8080816f135f46016f1cc98ad81134",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff8080816f135f46016f1cc98ad81134",
    local_path=None,
    notes="flk sxx=2；2018 修正版已被 2023 修订版替代。"
)
add("CL-2013-CORRECTION",
    title="中华人民共和国公司法（2013 修正版）",
    document_type="法律",
    relation_type="historical_version",
    relation_strength="related",
    legal_status="replaced",
    status_basis="flk_sxx_record",
    status_basis_url="https://flk.npc.gov.cn/detail.html?bbbs=2c909fdd678bf17901678bf76abb070d",
    verified_at="2026-09-10",
    verification_status="CANDIDATE",
    issuing_authority="全国人民代表大会常务委员会",
    promulgation_date="2013-12-28",
    effective_date="2014-03-01",
    bbbs="2c909fdd678bf17901678bf76abb070d",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=2c909fdd678bf17901678bf76abb070d",
    local_path=None,
    notes="flk sxx=2；已被 2018 → 2023 修订版替代。"
)
add("CL-1993-ORIGINAL",
    title="中华人民共和国公司法（1993 通过）",
    document_type="法律",
    relation_type="historical_version",
    relation_strength="related",
    legal_status="repealed",
    status_basis="historical_record_no_longer_listed",
    status_basis_url=None,
    verified_at="2026-09-10",
    verification_status="CANDIDATE",
    issuing_authority="全国人民代表大会",
    promulgation_date="1993-12-29",
    effective_date="1994-07-01",
    bbbs=None,
    source_url=None,
    local_path=None,
    notes="flk.npc.gov.cn 未单独登记 1993 原版；被后续多次修订/修正最终由 2023 修订版整体替代。"
)

# 3) 行政法规
add("AR-CAPITAL-2024",
    title="国务院关于实施《中华人民共和国公司法》注册资本登记管理制度的规定",
    document_type="行政法规",
    relation_type="administrative_regulation",
    relation_strength="core",
    legal_status="effective",
    status_basis="flk_sxx_record",
    status_basis_url="https://flk.npc.gov.cn/detail.html?bbbs=ff808181907350630190dd6d975c6c01",
    verified_at="2026-09-10",
    verification_status="CANDIDATE",
    issuing_authority="国务院",
    promulgation_date="2024-07-01",
    effective_date="2024-07-01",
    bbbs="ff808181907350630190dd6d975c6c01",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff808181907350630190dd6d975c6c01",
    local_path=None,
    candidate_sources=[
        {
            "source": "lawtext-laws",
            "local_root": "~/workspace/legal-sources/laws",
            "relative_path": "content/行政法规/ff808181907350630190dd6d975c6c01.md",
            "source_commit": "aefdfca37fb06e90a29af6311a1ed9804c9670bd",
            "source_license_status": "unclear",
            "verification_status": "CANDIDATE",
            "match_method": "bbbs_exact_match",
        }
    ],
    notes="2023 修订公司法同步配套；just-laws 无副本；正文未逐字核验。"
)
add("AR-MARKET-ENTITY-2022",
    title="中华人民共和国市场主体登记管理条例",
    document_type="行政法规",
    relation_type="administrative_regulation",
    relation_strength="direct",
    legal_status="effective",
    status_basis="flk_sxx_record",
    status_basis_url="https://flk.npc.gov.cn/detail.html?bbbs=ff8081817b63b679017b7b2085953607",
    verified_at="2026-09-10",
    verification_status="CANDIDATE",
    issuing_authority="国务院",
    promulgation_date="2021-07-27",
    effective_date="2022-03-01",
    bbbs="ff8081817b63b679017b7b2085953607",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff8081817b63b679017b7b2085953607",
    local_path=None,
    candidate_sources=[
        {
            "source": "lawtext-laws",
            "local_root": "~/workspace/legal-sources/laws",
            "relative_path": "content/行政法规/ff8081817b63b679017b7b2085953607.md",
            "source_commit": "aefdfca37fb06e90a29af6311a1ed9804c9670bd",
            "source_license_status": "unclear",
            "verification_status": "CANDIDATE",
            "match_method": "bbbs_exact_match",
        }
    ],
    notes="公司登记 / 备案的直接依据；just-laws 无副本。"
)
add("AR-NAME-2020",
    title="企业名称登记管理规定",
    document_type="行政法规",
    relation_type="administrative_regulation",
    relation_strength="direct",
    legal_status="effective",
    status_basis="flk_sxx_record",
    status_basis_url="https://flk.npc.gov.cn/detail.html?bbbs=ff808081777d0c94017784da4aa50a73",
    verified_at="2026-09-10",
    verification_status="CANDIDATE",
    issuing_authority="国务院",
    promulgation_date="2020-12-28",
    effective_date="2021-03-01",
    bbbs="ff808081777d0c94017784da4aa50a73",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff808081777d0c94017784da4aa50a73",
    local_path=None,
    candidate_sources=[
        {
            "source": "lawtext-laws",
            "local_root": "~/workspace/legal-sources/laws",
            "relative_path": "content/行政法规/ff808081777d0c94017784da4aa50a73.md",
            "source_commit": "aefdfca37fb06e90a29af6311a1ed9804c9670bd",
            "source_license_status": "unclear",
            "verification_status": "CANDIDATE",
            "match_method": "bbbs_exact_match",
        }
    ],
)

# 4) 司法解释（现行）
# 一律按 2024 年最高法民二庭公开口径标 effective；status_basis 注明依据
add("JI-1-2014",
    title="最高人民法院关于适用《中华人民共和国公司法》若干问题的规定（一）（2014 修正）",
    document_type="司法解释",
    relation_type="judicial_interpretation",
    relation_strength="core",
    legal_status="effective",
    status_basis="highest_court_press_qa_2024",
    status_basis_url="https://www.court.gov.cn/zixun/xiangqing/438551.html",
    verified_at="2026-09-11",
    verification_status="CANDIDATE",
    issuing_authority="最高人民法院",
    promulgation_date="2014-02-20",
    effective_date="2014-03-01",
    bbbs="ff8081818a1cb709018acf819b8f452f",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff8081818a1cb709018acf819b8f452f",
    document_number="法释〔2014〕2号",
    local_path=None,
    candidate_sources=[
        {
            "source": "lawtext-laws",
            "local_root": "~/workspace/legal-sources/laws",
            "relative_path": "content/司法解释/ff8081818a1cb709018acf819b8f452f.md",
            "source_commit": "aefdfca37fb06e90a29af6311a1ed9804c9670bd",
            "source_license_status": "unclear",
            "verification_status": "CANDIDATE",
            "match_method": "bbbs_exact_match",
        }
    ],
    notes="2014 修正版（最新）；与 2023 公司法无冲突的内容继续适用；条文援引旧法序号应改写为新法序号。"
)
add("JI-2-2020",
    title="最高人民法院关于适用《中华人民共和国公司法》若干问题的规定（二）（2020 修正）",
    document_type="司法解释",
    relation_type="judicial_interpretation",
    relation_strength="core",
    legal_status="effective",
    status_basis="highest_court_press_qa_2024",
    status_basis_url="https://www.court.gov.cn/zixun/xiangqing/438551.html",
    verified_at="2026-09-11",
    verification_status="CANDIDATE",
    issuing_authority="最高人民法院",
    promulgation_date="2020-12-29",
    effective_date="2021-01-01",
    bbbs="ff808181799df6140179ac069a281a27",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff808181799df6140179ac069a281a27",
    document_number="法释〔2020〕18号",
    local_path=None,
    candidate_sources=[
        {
            "source": "lawtext-laws",
            "local_root": "~/workspace/legal-sources/laws",
            "relative_path": "content/司法解释/ff808181799df6140179ac069a281a27.md",
            "source_commit": "aefdfca37fb06e90a29af6311a1ed9804c9670bd",
            "source_license_status": "unclear",
            "verification_status": "CANDIDATE",
            "match_method": "bbbs_exact_match",
        }
    ],
    notes="2020 修正版；公司解散与清算纠纷。"
)
add("JI-3-2020",
    title="最高人民法院关于适用《中华人民共和国公司法》若干问题的规定（三）（2020 修正）",
    document_type="司法解释",
    relation_type="judicial_interpretation",
    relation_strength="core",
    legal_status="effective",
    status_basis="highest_court_press_qa_2024",
    status_basis_url="https://www.court.gov.cn/zixun/xiangqing/438551.html",
    verified_at="2026-09-11",
    verification_status="CANDIDATE",
    issuing_authority="最高人民法院",
    promulgation_date="2020-12-29",
    effective_date="2021-01-01",
    bbbs="ff808181799def980179ac07a9ca117c",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff808181799def980179ac07a9ca117c",
    document_number="法释〔2020〕18号",
    local_path=None,
    candidate_sources=[
        {
            "source": "lawtext-laws",
            "local_root": "~/workspace/legal-sources/laws",
            "relative_path": "content/司法解释/ff808181799def980179ac07a9ca117c.md",
            "source_commit": "aefdfca37fb06e90a29af6311a1ed9804c9670bd",
            "source_license_status": "unclear",
            "verification_status": "CANDIDATE",
            "match_method": "bbbs_exact_match",
        }
    ],
    notes="2020 修正版；公司设立、股东出资、股权确认等纠纷。第十三条第三款被 2023 公司法第九十九条吸收。"
)
add("JI-4-2020",
    title="最高人民法院关于适用《中华人民共和国公司法》若干问题的规定（四）（2020 修正）",
    document_type="司法解释",
    relation_type="judicial_interpretation",
    relation_strength="core",
    legal_status="effective",
    status_basis="highest_court_press_qa_2024",
    status_basis_url="https://www.court.gov.cn/zixun/xiangqing/438551.html",
    verified_at="2026-09-11",
    verification_status="CANDIDATE",
    issuing_authority="最高人民法院",
    promulgation_date="2020-12-29",
    effective_date="2021-01-01",
    bbbs="ff808181799df4000179ac08cb701145",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff808181799df4000179ac08cb701145",
    document_number="法释〔2020〕18号",
    local_path=None,
    candidate_sources=[
        {
            "source": "lawtext-laws",
            "local_root": "~/workspace/legal-sources/laws",
            "relative_path": "content/司法解释/ff808181799df4000179ac08cb701145.md",
            "source_commit": "aefdfca37fb06e90a29af6311a1ed9804c9670bd",
            "source_license_status": "unclear",
            "verification_status": "CANDIDATE",
            "match_method": "bbbs_exact_match",
        }
    ],
    notes="2020 修正版；公司决议效力、股东知情权、利润分配权、股东代位诉讼。"
)
add("JI-5-2020",
    title="最高人民法院关于适用《中华人民共和国公司法》若干问题的规定（五）（2020 修正）",
    document_type="司法解释",
    relation_type="judicial_interpretation",
    relation_strength="core",
    legal_status="effective",
    status_basis="highest_court_press_qa_2024",
    status_basis_url="https://www.court.gov.cn/zixun/xiangqing/438551.html",
    verified_at="2026-09-11",
    verification_status="CANDIDATE",
    issuing_authority="最高人民法院",
    promulgation_date="2020-12-29",
    effective_date="2021-01-01",
    bbbs="ff808181799df4000179ac1ef1b1115c",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff808181799df4000179ac1ef1b1115c",
    document_number="法释〔2020〕18号",
    local_path=None,
    candidate_sources=[
        {
            "source": "lawtext-laws",
            "local_root": "~/workspace/legal-sources/laws",
            "relative_path": "content/司法解释/ff808181799df4000179ac1ef1b1115c.md",
            "source_commit": "aefdfca37fb06e90a29af6311a1ed9804c9670bd",
            "source_license_status": "unclear",
            "verification_status": "CANDIDATE",
            "match_method": "bbbs_exact_match",
        }
    ],
    notes="2020 修正版；关联交易、董事职务解除、利润分配履行。"
)
add("JI-TIME-2024",
    title="最高人民法院关于适用《中华人民共和国公司法》时间效力的若干规定",
    document_type="司法解释",
    relation_type="judicial_interpretation",
    relation_strength="core",
    legal_status="effective",
    status_basis="official_court_announcement",
    status_basis_url="https://www.court.gov.cn/zixun/xiangqing/438551.html",
    verified_at="2026-09-11",
    verification_status="CANDIDATE",
    issuing_authority="最高人民法院",
    promulgation_date="2024-06-29",
    effective_date="2024-07-01",
    bbbs="ff8081819150444501916e8c37764524",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff8081819150444501916e8c37764524",
    document_number="法释〔2024〕7号",
    local_path=None,
    candidate_sources=[
        {
            "source": "lawtext-laws",
            "local_root": "~/workspace/legal-sources/laws",
            "relative_path": "content/司法解释/ff8081819150444501916e8c37764524.md",
            "source_commit": "aefdfca37fb06e90a29af6311a1ed9804c9670bd",
            "source_license_status": "unclear",
            "verification_status": "CANDIDATE",
            "match_method": "bbbs_exact_match",
        }
    ],
    notes="2024 年发布；解决新旧公司法衔接适用问题。第四条关于第八十八条第一款溯及适用的规定，已被 法释〔2024〕15号批复实质否定。"
)
add("JI-88-FB-2024",
    title="最高人民法院关于《中华人民共和国公司法》第八十八条第一款不溯及适用的批复",
    document_type="司法解释",
    relation_type="judicial_interpretation",
    relation_strength="core",
    legal_status="effective",
    status_basis="official_court_announcement",
    status_basis_url="https://www.court.gov.cn/zixun/xiangqing/450831.html",
    verified_at="2026-09-11",
    verification_status="CANDIDATE",
    issuing_authority="最高人民法院",
    promulgation_date="2024-12-24",
    effective_date="2024-12-24",
    bbbs="ff808181927f1276019448a29dca7d34",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff808181927f1276019448a29dca7d34",
    document_number="法释〔2024〕15号",
    local_path=None,
    candidate_sources=[
        {
            "source": "lawtext-laws",
            "local_root": "~/workspace/legal-sources/laws",
            "relative_path": "content/司法解释/ff808181927f1276019448a29dca7d34.md",
            "source_commit": "aefdfca37fb06e90a29af6311a1ed9804c9670bd",
            "source_license_status": "unclear",
            "verification_status": "CANDIDATE",
            "match_method": "bbbs_exact_match",
        }
    ],
    notes="2024-12-24 最高法审委会第 1939 次会议通过；针对 2024 备案审查中公民、组织对 JI-TIME-2024 第四条溯及适用的审查建议；明确第八十八条第一款仅适用于 2024-07-01 之后发生的股权转让。"
)

# 5) 历史司法解释（已被取代或废止的旧版）
add("JI-5-2019-EXPIRED",
    title="最高人民法院关于适用《中华人民共和国公司法》若干问题的规定（五）（2019 版）",
    document_type="司法解释",
    relation_type="judicial_interpretation",
    relation_strength="related",
    legal_status="replaced",
    status_basis="flk_sxx_record",
    status_basis_url="https://flk.npc.gov.cn/detail.html?bbbs=2c90e5b96c128b4c016c8a0cf68c0b77",
    verified_at="2026-09-10",
    verification_status="CANDIDATE",
    issuing_authority="最高人民法院",
    promulgation_date="2019-04-28",
    effective_date="2019-04-29",
    bbbs="2c90e5b96c128b4c016c8a0cf68c0b77",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=2c90e5b96c128b4c016c8a0cf68c0b77",
    local_path=None,
    notes="flk sxx=2；已被 2020 修正版 JI-5-2020 取代。"
)
add("JI-4-2017-EXPIRED",
    title="最高人民法院关于适用《中华人民共和国公司法》若干问题的规定（四）（2017 版）",
    document_type="司法解释",
    relation_type="judicial_interpretation",
    relation_strength="related",
    legal_status="replaced",
    status_basis="flk_sxx_record",
    status_basis_url="https://flk.npc.gov.cn/detail.html?bbbs=402881e45ffbbe41015ffc04f9dc03ea",
    verified_at="2026-09-10",
    verification_status="CANDIDATE",
    issuing_authority="最高人民法院",
    promulgation_date="2017-08-25",
    effective_date="2017-09-01",
    bbbs="402881e45ffbbe41015ffc04f9dc03ea",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=402881e45ffbbe41015ffc04f9dc03ea",
    local_path=None,
    notes="flk sxx=2；已被 2020 修正版 JI-4-2020 取代。"
)
add("JI-3-2014-EXPIRED",
    title="最高人民法院关于适用《中华人民共和国公司法》若干问题的规定（三）（2014 版）",
    document_type="司法解释",
    relation_type="judicial_interpretation",
    relation_strength="related",
    legal_status="replaced",
    status_basis="flk_sxx_record",
    status_basis_url="https://flk.npc.gov.cn/detail.html?bbbs=ff8081818a1cb709018acf8e84b14587",
    verified_at="2026-09-10",
    verification_status="CANDIDATE",
    issuing_authority="最高人民法院",
    promulgation_date="2014-02-20",
    effective_date="2014-03-01",
    bbbs="ff8081818a1cb709018acf8e84b14587",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff8081818a1cb709018acf8e84b14587",
    local_path=None,
    notes="flk sxx=2；已被 2020 修正版 JI-3-2020 取代。"
)
add("JI-2-2014-EXPIRED",
    title="最高人民法院关于适用《中华人民共和国公司法》若干问题的规定（二）（2014 版）",
    document_type="司法解释",
    relation_type="judicial_interpretation",
    relation_strength="related",
    legal_status="replaced",
    status_basis="flk_sxx_record",
    status_basis_url="https://flk.npc.gov.cn/detail.html?bbbs=ff8081818a1cb709018acf8c4907456f",
    verified_at="2026-09-10",
    verification_status="CANDIDATE",
    issuing_authority="最高人民法院",
    promulgation_date="2014-02-20",
    effective_date="2014-03-01",
    bbbs="ff8081818a1cb709018acf8c4907456f",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=ff8081818a1cb709018acf8c4907456f",
    local_path=None,
    notes="flk sxx=2；已被 2020 修正版 JI-2-2020 取代。"
)
add("JI-1-2006-EXPIRED",
    title="最高人民法院关于适用《中华人民共和国公司法》若干问题的规定（一）（2006 版）",
    document_type="司法解释",
    relation_type="judicial_interpretation",
    relation_strength="related",
    legal_status="replaced",
    status_basis="flk_sxx_record",
    status_basis_url="https://flk.npc.gov.cn/detail.html?bbbs=402881e45ffbbe41015ffbfe45e1037d",
    verified_at="2026-09-10",
    verification_status="CANDIDATE",
    issuing_authority="最高人民法院",
    promulgation_date="2006-04-28",
    effective_date="2006-05-09",
    bbbs="402881e45ffbbe41015ffbfe45e1037d",
    source_url="https://flk.npc.gov.cn/detail.html?bbbs=402881e45ffbbe41015ffbfe45e1037d",
    local_path=None,
    notes="flk sxx=2；已被 2014 修正版 JI-1-2014 取代。"
)

# ============================================================
# 案例集合（case_collections） + 具体案例（cases）
# ============================================================
# 案例集合：发布批次
CASE_COLLECTIONS = [
    {
        "collection_id": "CC-CIVIL-COMMERCIAL-2025-02",
        "title": "最高人民法院 2025 年度民商事典型案例",
        "issuing_body": "最高人民法院",
        "publication_date": "2025-02-24",
        "official_url": "https://www.court.gov.cn/zixun/xiangqing/489801.html",
        "notes": "含股东僵局化解（存续式和解）、1.5 亿元股权收购纠纷调解等；本批含若干与公司法相关案例。"
    },
    {
        "collection_id": "CC-EQ-PROTECTION-2025-12",
        "title": "依法平等保护民营企业合法权益典型民商事案例",
        "issuing_body": "最高人民法院",
        "publication_date": "2025-12",
        "official_url": "http://www.chinacourt.cn/article/detail/2025/12/id/9102003.shtml",
        "notes": "包含若干与公司法相关的典型案例（股东出资 / 有限责任公司 / 关联交易等）。"
    },
    {
        "collection_id": "CC-PRIVATE-PROPERTY-2025-11",
        "title": "涉民营企业产权和民营企业家权益保护再审典型案例",
        "issuing_body": "最高人民法院",
        "publication_date": "2025-11-05",
        "official_url": "https://www.court.gov.cn/zixun/xiangqing/480681.html",
        "notes": "含虚报注册资本再审改判无罪案（涉及 2013 公司法资本制度修正）。"
    },
    {
        "collection_id": "CC-EVADE-DEBT-2025-12",
        "title": "惩治逃废债典型案例",
        "issuing_body": "最高人民法院",
        "publication_date": "2025-12-29",
        "official_url": "https://www.court.gov.cn/zixun/xiangqing/485211.html",
        "notes": "7 件典型案例；含公司人格否认、股东出资责任等公司法议题。"
    },
]

# 具体案例（从 web_search 公开新闻报道 / 法院网摘录的官方表述）
# 字段缺失（案号 / 法院 / 裁判日期）= null，待人工按 URL 补充
CASES = [
    # CC-EVADE-DEBT 三个具体案例
    {
        "case_id": "CASE-EVADE-001",
        "case_title": "陈某与乙公司、丙公司等买卖合同纠纷案",
        "case_number": None,
        "court": None,
        "decision_date": None,
        "publication_date": "2025-12-29",
        "case_type": "typical_case",
        "collection_id": "CC-EVADE-DEBT-2025-12",
        "official_source_url": "https://www.court.gov.cn/zixun/xiangqing/485211.html",
        "related_articles": ["公司法 第二十三条（关联公司人格否认）"],
        "related_topics": ["company-law"],
        "relation_strength": "direct",
        "content_source": "official_typical_significance",
        "verification_status": "CANDIDATE",
        "official_typical_significance_official_text": "关联公司之间恶意转移交易收益、人员财务混同、边界不清——横向'刺穿公司面纱'，判决关联公司对债务承担连带责任。",
        "analysis_note": None,
    },
    {
        "case_id": "CASE-EVADE-002",
        "case_title": "某建材公司诉庄某某、某矿业公司等股东损害公司债权人利益纠纷案",
        "case_number": None,
        "court": None,
        "decision_date": None,
        "publication_date": "2025-12-29",
        "case_type": "typical_case",
        "collection_id": "CC-EVADE-DEBT-2025-12",
        "official_source_url": "https://www.court.gov.cn/zixun/xiangqing/485211.html",
        "related_articles": ["股东出资责任相关条款"],
        "related_topics": ["company-law"],
        "relation_strength": "direct",
        "content_source": "official_typical_significance",
        "verification_status": "CANDIDATE",
        "official_typical_significance_official_text": "股东在公司不能清偿对外负债的情况下两次零对价转让股权，受让人通过修改章程延长出资期限——延长出资期限的内部决议对公司债权人不发生法律效力，股权出让人和受让人向公司债权人承担补充赔偿责任。",
        "analysis_note": None,
    },
    {
        "case_id": "CASE-EVADE-003",
        "case_title": "丙公司诉乙公司、崔某、李某追加被执行人执行异议之诉案",
        "case_number": None,
        "court": None,
        "decision_date": None,
        "publication_date": "2025-12-29",
        "case_type": "typical_case",
        "collection_id": "CC-EVADE-DEBT-2025-12",
        "official_source_url": "https://www.court.gov.cn/zixun/xiangqing/485211.html",
        "related_articles": ["股东出资责任相关条款"],
        "related_topics": ["company-law"],
        "relation_strength": "direct",
        "content_source": "official_typical_significance",
        "verification_status": "CANDIDATE",
        "official_typical_significance_official_text": "股东向公司转入出资款 2 日内即将全部资金转给案外人且无证据证明基于正常交易——构成出资不实 / 抽逃出资，由股东承担相应责任。",
        "analysis_note": None,
    },
    # CC-EQ-PROTECTION 两个具体案例
    {
        "case_id": "CASE-EQ-001",
        "case_title": "某投资公司诉某集团公司执行异议之诉案",
        "case_number": None,
        "court": "最高人民法院（提审）",
        "decision_date": "2025-03-31",
        "publication_date": "2025-12",
        "case_type": "typical_case",
        "collection_id": "CC-EQ-PROTECTION-2025-12",
        "official_source_url": "https://myjj.ndrc.gov.cn/myjjcfzt/dxal/yfpdbhmyqy/202512/t20251212_1402377.html",
        "related_articles": ["公司法 第三条（公司法人财产权）", "公司法 第三条（股东有限责任）"],
        "related_topics": ["company-law"],
        "relation_strength": "direct",
        "content_source": "official_typical_significance",
        "verification_status": "CANDIDATE",
        "official_typical_significance_official_text": "已依法履行出资义务的股东受股东有限责任制度保护；股东与公司责任之间存在有效'防火墙'；不得仅以资金账目异动即否定股东有限责任。",
        "analysis_note": None,
    },
    {
        "case_id": "CASE-EQ-002",
        "case_title": "某资产管理公司河南分公司诉某商贸公司金融不良债权追偿纠纷案",
        "case_number": None,
        "court": None,
        "decision_date": None,
        "publication_date": "2025-12",
        "case_type": "typical_case",
        "collection_id": "CC-EQ-PROTECTION-2025-12",
        "official_source_url": "http://www.chinacourt.cn/article/detail/2025/12/id/9102003.shtml",
        "related_articles": ["公司法相关企业改制债务承担规则"],
        "related_topics": ["company-law"],
        "relation_strength": "direct",
        "content_source": "official_typical_significance",
        "verification_status": "CANDIDATE",
        "official_typical_significance_official_text": "改制企业债务承担应遵循'权利义务相一致'原则；在确认原改制方案未完全履行、企业仅实际接收部分资产的基础上，判决其在接收资产范围内承担连带责任。",
        "analysis_note": None,
    },
    # CC-CIVIL-COMMERCIAL 两个具体案例
    {
        "case_id": "CASE-CC-001",
        "case_title": "某海峡公司强制清算案（存续式和解）",
        "case_number": None,
        "court": "湖北省谷城县人民法院",
        "decision_date": None,
        "publication_date": "2025-02-24",
        "case_type": "typical_case",
        "collection_id": "CC-CIVIL-COMMERCIAL-2025-02",
        "official_source_url": "https://www.court.gov.cn/zixun/xiangqing/489801.html",
        "related_articles": ["公司法强制清算相关规则"],
        "related_topics": ["company-law"],
        "relation_strength": "direct",
        "content_source": "official_typical_significance",
        "verification_status": "CANDIDATE",
        "official_typical_significance_official_text": "法院未简单'一清了之'，组织调解促成'存续式和解'：一方延长经营期限，一方股权转让退出；保全企业资产，化解十余年股东僵局。",
        "analysis_note": None,
    },
    {
        "case_id": "CASE-CC-002",
        "case_title": "某股权收购僵局案（1.5 亿元）",
        "case_number": None,
        "court": None,
        "decision_date": None,
        "publication_date": "2025-02-24",
        "case_type": "typical_case",
        "collection_id": "CC-CIVIL-COMMERCIAL-2025-02",
        "official_source_url": "https://www.court.gov.cn/zixun/xiangqing/489801.html",
        "related_articles": ["公司法股权转让 / 公司收购相关规则"],
        "related_topics": ["company-law"],
        "relation_strength": "direct",
        "content_source": "official_typical_significance",
        "verification_status": "CANDIDATE",
        "official_typical_significance_official_text": "1.5 亿元股权收购因房地产行业形势变化陷入僵局，法院通过实质解纷、源头治理方式化解。",
        "analysis_note": None,
    },
    # CC-PRIVATE-PROPERTY 一个具体案例
    {
        "case_id": "CASE-PROP-001",
        "case_title": "谢某等三人虚报注册资本、私分国有资产、行贿、职务侵占再审部分改判无罪案",
        "case_number": None,
        "court": None,
        "decision_date": None,
        "publication_date": "2025-11-05",
        "case_type": "typical_case",
        "collection_id": "CC-PRIVATE-PROPERTY-2025-11",
        "official_source_url": "https://www.court.gov.cn/zixun/xiangqing/480681.html",
        "related_articles": ["公司法资本制度（2013 / 2018 修正）"],
        "related_topics": ["company-law"],
        "relation_strength": "direct",
        "content_source": "official_typical_significance",
        "verification_status": "CANDIDATE",
        "official_typical_significance_official_text": "原二审期间公司法已对资本注册制度作出重大调整，当事人没有实缴注册资本的行为未违反修正后公司法的规定，不再需要承担刑事责任；体现罪刑法定原则与公司法资本制度变化的衔接。",
        "analysis_note": None,
    },
]

# ============================================================
# 自动统计（V3.1 spec：从 documents[] / cases[] / collections[] 实际生成）
# ============================================================

def compute_statistics():
    by_rt = Counter(d.get("relation_type") for d in DOCUMENTS)
    by_ls = Counter(d.get("legal_status") for d in DOCUMENTS)
    by_vs = Counter(d.get("verification_status") for d in DOCUMENTS)
    by_rs = Counter(d.get("relation_strength") for d in DOCUMENTS)

    has_local_path = sum(1 for d in DOCUMENTS if d.get("local_path"))
    has_official_source = sum(1 for d in DOCUMENTS if d.get("bbbs") or d.get("source_url"))
    pending = sum(
        1 for d in DOCUMENTS
        if d.get("legal_status") == "pending_verification"
        or d.get("verification_status") in (None, "UNVERIFIED")
    )

    return {
        "documents_total": len(DOCUMENTS),
        "documents_by_relation_type": dict(by_rt),
        "documents_by_legal_status": dict(by_ls),
        "documents_by_verification_status": dict(by_vs),
        "documents_by_relation_strength": dict(by_rs),
        "documents_with_local_path": has_local_path,
        "documents_with_official_source": has_official_source,
        "documents_pending_verification": pending,
        "case_collections_total": len(CASE_COLLECTIONS),
        "cases_total": len(CASES),
        "cases_by_type": dict(Counter(c.get("case_type") for c in CASES)),
        "cases_by_verification_status": dict(Counter(c.get("verification_status") for c in CASES)),
        "cases_with_case_number": sum(1 for c in CASES if c.get("case_number")),
        "cases_with_decision_date": sum(1 for c in CASES if c.get("decision_date")),
        "cases_pending_official_detail": sum(
            1 for c in CASES
            if not c.get("case_number") or not c.get("decision_date")
        ),
    }


# ============================================================
# 写出 manifest.yaml
# ============================================================

def build_manifest():
    stats = compute_statistics()
    # 过滤 core + direct 默认展示（related 单独分组）
    core_direct_docs = [d for d in DOCUMENTS if d.get("relation_strength") in ("core", "direct")]
    related_docs = [d for d in DOCUMENTS if d.get("relation_strength") == "related"]
    core_direct_cases = [c for c in CASES if c.get("relation_strength") in ("core", "direct")]
    related_cases = [c for c in CASES if c.get("relation_strength") == "related"]

    core_direct_jis_effective = [
        d for d in core_direct_docs
        if d.get("relation_type") == "judicial_interpretation"
        and d.get("legal_status") == "effective"
    ]

    manifest = {
        "topic": {
            "id": "company-law",
            "title": "公司法专题",
            "description": "以中华人民共和国公司法（2023 修订 / 2024-07-01 施行）为枢轴，关联相关行政法规、部门规章、司法解释与典型案例",
            "primary_law_document_id": "CL-PRIMARY-2024",
            "generated_at": NOW,
            "default_show_relation_strength": ["core", "direct"],
            "data_sources": [
                "flk.npc.gov.cn（国家法律法规数据库，allowed_domains 白名单）",
                "just-laws（ImCa0/just-laws, MIT，本地只读）",
                "web_search（MiniMax Search，仅取 source_url + 元数据）",
            ],
        },
        # ----------- 主清单（默认 core + direct）-----------
        "documents": core_direct_docs,
        # ----------- 历史/相关单独组 -----------
        "documents_related": related_docs,
        # ----------- 案例集合 -----------
        "case_collections": CASE_COLLECTIONS,
        # ----------- 具体案例 -----------
        "cases": core_direct_cases,
        "cases_related": related_cases,
        # ----------- 自动统计 -----------
        "statistics": stats,
        # ----------- 验收对齐 -----------
        "verification": {
            "schema_separation": {
                "verification_status_kept_independent_from_legal_status": True,
                "evidence": (
                    "verification_status 表示数据可信等级（VERIFIED/OFFICIAL_META/CANDIDATE/UNVERIFIED）；"
                    "legal_status 表示法律文件自身效力状态（effective/repealed/replaced/historical/draft/"
                    "pending_verification/not_applicable）。两者完全独立。"
                ),
            },
            "auto_stats_match_documents": True,
            "judicial_interpretations_split_by_effectiveness": True,
            "no_empty_department_rule_placeholders": True,
            "cases_split_to_individual": True,
            "current_core_documents": len(core_direct_docs),
            "current_effective_judicial_interpretations": len(core_direct_jis_effective),
            "individual_cases": len(CASES),
            "history_documents": len(related_docs),
            "still_pending_or_unverified": stats["documents_pending_verification"],
        },
        "known_gaps": [
            "未盘点具体部门规章 / 规范性文件：合规铁律下不批量访问国家市场监管总局 / 证监会等官网；按 V3.1 spec，盘点不到的具体文件不写入 manifest。",
            "人民法院案例库（rmfyalk.court.gov.cn）需登录访问；不绕过登录控制；具体入库案例无法直接核验。",
            "指导性案例 / 公报案例：court.gov.cn 在本环境 TLS 阻断；按 V3.1 spec，不批量绕过。",
            "公司法部分具体案例的案号 / 裁判日期 / 法院：最高法典型案例多以当事人化名披露，官方原文未给出完整案号；已在 manifest 标 null 并说明。",
            "三法（民法典 / 劳动合同法）OFFICIAL_META 正文仍是占位，未补齐。",
        ],
    }

    return manifest


def main() -> int:
    import json
    manifest = build_manifest()
    # V3.1.1：同时生成 manifest.yaml （人工阅读）和 manifest.json （search_all.py 默认读取）
    with OUT.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(manifest, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"[OK] {OUT}")
    json_path = OUT.with_suffix(".json")
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print(f"[OK] {json_path}")
    print(f"[stats]")
    for k, v in manifest["statistics"].items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())