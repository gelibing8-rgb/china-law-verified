# 公司法专题（V3.3A）

> 这是 `china-law-verified` 项目"法律专题知识包"模式的样板（V3.1 清理版）。
> 围绕 **中华人民共和国公司法（2023 修订 / 2024-07-01 施行）** 现行版本展开。

## 1. 核心现行法律体系

> 默认展示 `relation_strength = core | direct`；`related` 见 §4。

### 主法律

| 文件 | 标题 | 施行日期 | legal_status | verification_status |
| --- | --- | --- | --- | --- |
| `laws/company_law_2024.md` | 中华人民共和国公司法（2023 修订） | 2024-07-01 | **effective** | **OFFICIAL_META** |

正文为 `（正文待补）` 占位；元数据 + 结构树已通过 `flk.npc.gov.cn` 公开 API 核验。

### 行政法规

| 标题 | 发布/施行 | legal_status | verification_status |
| --- | --- | --- | --- |
| 国务院关于实施《中华人民共和国公司法》注册资本登记管理制度的规定 | 2024-07-01 / 2024-07-01 | **effective** | CANDIDATE |
| 中华人民共和国市场主体登记管理条例 | 2021-07-27 / 2022-03-01 | **effective** | CANDIDATE |
| 企业名称登记管理规定 | 2020-12-28 / 2021-03-01 | **effective** | CANDIDATE |

### 部门规章

| 文号 | 标题 | 施行日期 | legal_status | verification_status | 候选全文 |
| --- | --- | --- | --- | --- | --- |
| 国家市场监督管理总局令第52号 | 中华人民共和国市场主体登记管理条例实施细则 | 2022-03-01 | **effective** | **CANDIDATE** | `china-data-laws/部门规章/市场监督管理总局/市场主体登记管理条例实施细则(2022-03-01).md` |

该条目的法律效力依据已确认元数据登记为 `effective`；正文仍来自本地候选库，`verification_status` 保持 `CANDIDATE`。

| 国家市场监督管理总局令第95号 | 公司登记管理实施办法 | 2025-02-10 | **effective** | **CANDIDATE** | 无可靠本地全文 |

《公司登记管理实施办法》按已确认元数据登记；本地候选库未找到唯一可靠全文，未做模糊关联。

### 重要规范性文件

| 文号 | 标题 | 施行日期 | legal_status | verification_status | 候选全文 |
| --- | --- | --- | --- | --- | --- |
| 国市监注发〔2026〕5号 | 市场监管总局关于印发经营主体登记文书规范和提交材料规范（2026年版）的通知 | 2026-05-01 | **effective** | **CANDIDATE** | 无可靠本地全文 |
| 国市监注发〔2026〕5号（文件组） | 经营主体登记文书规范（2026年版） | 2026-05-01 | **effective** | **CANDIDATE** | 无可靠本地全文 |
| 国市监注发〔2026〕5号（文件组） | 经营主体登记提交材料规范（2026年版） | 2026-05-01 | **effective** | **CANDIDATE** | 无可靠本地全文 |

上述 2026 年版文件直接落实公司法关于股东出资期限、股东失权、弥补亏损减资等登记要求。2022 版《市场主体登记文书规范》和《市场主体登记提交材料规范》已标记 `replaced`，由 2026 年版替代，不进入当前默认检索范围。

### 现行司法解释

| document_number | 标题 | 发布 / 施行 | legal_status | 备注 |
| --- | --- | --- | --- | --- |
| 法释〔2024〕7号 | 公司法时间效力的若干规定 | 2024-06-29 / 2024-07-01 | **effective** | 第四条被 法释〔2024〕15号批复实质否定 |
| 法释〔2024〕15号 | 公司法第八十八条第一款不溯及适用的批复 | 2024-12-24 / 2024-12-24 | **effective** | 应对 2024 备案审查公民建议 |
| 法释〔2020〕18号 | 公司法若干问题的规定（二）2020 修正 | 2020-12-29 / 2021-01-01 | **effective** | 与新法无冲突内容继续适用 |
| 法释〔2020〕18号 | 公司法若干问题的规定（三）2020 修正 | 2020-12-29 / 2021-01-01 | **effective** | 第十三条第三款被 2023 公司法第九十九条吸收 |
| 法释〔2020〕18号 | 公司法若干问题的规定（四）2020 修正 | 2020-12-29 / 2021-01-01 | **effective** | |
| 法释〔2020〕18号 | 公司法若干问题的规定（五）2020 修正 | 2020-12-29 / 2021-01-01 | **effective** | |
| 法释〔2014〕2号 | 公司法若干问题的规定（一）2014 修正 | 2014-02-20 / 2014-03-01 | **effective** | 条文援引旧法序号应改写为新法序号 |

## 2. 权威案例层（V3.3B）

案例与法规效力状态完全分开。案例使用 `reference_status`（`active` / `no_longer_reference` / `historical` / `pending_verification`），不使用 `legal_status`。

本轮登记三起种子案例：指导性案例 215、人民法院案例库编号 `2023-08-2-084-028`、指导性案例 9。由于本地候选库未找到三起案例的唯一可靠全文或当前参照状态材料，均保持 `verification_status=CANDIDATE`、`reference_status=pending_verification`；不得据此直接作为最终案例依据。

状态记录见 `case-reference-status.json`。`official_holding` 仅保存已登记的官方明确裁判要旨；本轮种子案例未填充官方要旨，分析性说明统一使用 `analysis_note.content_type=ai_summary`。

`search_all.py --topic company-law` 默认在法律检索后展示匹配案例元数据，案例按指导性案例、人民法院案例库、公报案例、典型案例排序，并显示案例编号、参照状态、可信等级和候选来源。

> **官方核验依据**：最高人民法院民二庭负责人就公司法时间效力的规定答记者问（2024-07-01）。
> 原话："五部旧公司法司法解释尚未被废除，……五部旧公司法司法解释条文与公司法规定原理一致、不存在冲突时，五部旧公司法司法解释可以继续适用。……五部旧公司法司法解释条文与公司法规定内容不一致、存在冲突时，应当适用公司法。"
> 来源：<https://www.court.gov.cn/zixun/xiangqing/438551.html>

## 3. 权威案例

### 指导性案例

> **暂无。** 最高人民法院指导性案例需通过 `court.gov.cn` 公告逐年核对；本环境 `court.gov.cn` TLS 握手被服务端 alert 拒绝；按合规铁律，不批量访问、不绕过。

**当前专题库未收录已核验权威案例**。

### 人民法院案例库案例

> **暂无。** 人民法院案例库（rmfyalk.court.gov.cn）需登录查询；本项目不绕过登录控制；V3.1 仅占位、不批量访问。

**当前专题库未收录已核验权威案例**。

### 公报案例

> **暂无。** 公报案例需逐年核对《最高人民法院公报》目录；本环境不绕过访问控制；V3.1 仅占位。

**当前专题库未收录已核验权威案例**。

### 最高法典型案例（已收录 8 件）

来源：见 `cases[]` 中 `official_source_url`，均为最高法对外发布的典型案例。
所有 case_number / decision_date 字段在原始公开稿中以化名披露的，已标 `null` 并在 `notes` 中说明；不补全、不冒充。

| case_id | 案件 | 关系强度 | verification_status | 备注 |
| --- | --- | --- | --- | --- |
| CASE-EVADE-001 | 陈某与乙公司、丙公司等买卖合同纠纷案 | direct | CANDIDATE | 关联公司人格否认 / 横向'刺穿公司面纱' |
| CASE-EVADE-002 | 某建材公司诉庄某某、某矿业公司等股东损害公司债权人利益纠纷案 | direct | CANDIDATE | 股东零对价转让股权 + 延长出资期限 |
| CASE-EVADE-003 | 丙公司诉乙公司、崔某、李某追加被执行人执行异议之诉案 | direct | CANDIDATE | 出资款 2 日内转出 → 出资不实 |
| CASE-EQ-001 | 某投资公司诉某集团公司执行异议之诉案 | direct | CANDIDATE | 最高法提审；股东有限责任保护 |
| CASE-EQ-002 | 某资产管理公司河南分公司诉某商贸公司金融不良债权追偿纠纷案 | direct | CANDIDATE | 改制企业债务承担 |
| CASE-CC-001 | 某海峡公司强制清算案（存续式和解） | direct | CANDIDATE | 化解股东僵局 |
| CASE-CC-002 | 某股权收购僵局案（1.5 亿元） | direct | CANDIDATE | 实质解纷 |
| CASE-PROP-001 | 谢某等三人虚报注册资本、私分国有资产、行贿、职务侵占再审部分改判无罪案 | direct | CANDIDATE | 公司法资本制度调整后不再承担刑责 |

**案件批次来源（case_collections）**：见 `manifest.yaml` 中 `case_collections` 段。

## 4. 历史沿革

### 历次公司法版本

| document_id | 标题 | 施行日期 | legal_status |
| --- | --- | --- | --- |
| CL-1993-ORIGINAL | 公司法（1993 通过） | 1994-07-01 | **repealed** |
| CL-2013-CORRECTION | 公司法（2013 修正版） | 2014-03-01 | **replaced** |
| CL-2018-CORRECTION | 公司法（2018 修正版） | 2018-10-26 | **replaced** |
| CL-PRIMARY-2024 | 公司法（2023 修订） | 2024-07-01 | **effective** |

### 已废止 / 被替代司法解释

| document_id | 标题 | legal_status |
| --- | --- | --- |
| JI-1-2006-EXPIRED | 公司法若干问题的规定（一）2006 版 | **replaced** |
| JI-2-2014-EXPIRED | 公司法若干问题的规定（二）2014 版 | **replaced** |
| JI-3-2014-EXPIRED | 公司法若干问题的规定（三）2014 版 | **replaced** |
| JI-4-2017-EXPIRED | 公司法若干问题的规定（四）2017 版 | **replaced** |
| JI-5-2019-EXPIRED | 公司法若干问题的规定（五）2019 版 | **replaced** |

### 重要修订节点

- **2023-12-29** 全国人大常委会通过《公司法（2023 修订）》，自 **2024-07-01** 起施行；新增 49 条；强化股东出资责任、引入"公司法人人格否认"细化规则。
- **2024-07-01** 同步施行《国务院关于实施〈中华人民共和国公司法〉注册资本登记管理制度的规定》。
- **2024-12-24** 最高法公布 法释〔2024〕15号，明确 公司法第八十八条第一款仅适用于 2024-07-01 之后发生的股权转让。
- **2024 年备案审查** 全国人大常委会法工委对 时间效力规定 第四条溯及适用第八十八条第一款提出审查建议；最高法随后出台批复实质否定该溯及适用。

## 5. 关联但非核心文件（`relation_strength = related`）

仅按需展示，不参与默认法律结论推荐：

- 2018 / 2013 / 1993 公司法旧版（CL-*）
- 已被取代的 2006 / 2014 / 2017 / 2019 司法解释版（JI-*-EXPIRED）

## 数据可信等级、法律效力与案例参照状态是三个维度

| 维度 | 字段 | 取值 |
| --- | --- | --- |
| 数据可信 | `verification_status` | `VERIFIED` / `OFFICIAL_META` / `CANDIDATE` / `UNVERIFIED` |
| 法律效力 | `legal_status` | `effective` / `repealed` / `replaced` / `historical` / `draft` / `pending_verification` / `not_applicable` |
| 案例参照状态 | `reference_status` | `active` / `no_longer_reference` / `historical` / `pending_verification` |

禁止：
- 用 `CANDIDATE` 表示"失效"
- 用 `VERIFIED` 表示"现行有效"

## 数据来源与合规铁律

- `flk.npc.gov.cn`（国家法律法规数据库）公开 API —— 元数据
- `just-laws`（ImCa0/just-laws, MIT）—— 本地只读 CANDIDATE
- `china-data/laws`（commit `1ca7a3518d115c8dd3b752849ebdfa09878fa1b0`，无明确 LICENSE）—— 本地只读 CANDIDATE；不复制其整理文件
- `web_search`（MiniMax Search）—— 仅取 `source_url` + 案件标题 / 官方裁判要旨
- `court.gov.cn` / `npc.gov.cn` / `gov.cn` / `moj.gov.cn` —— **本环境 TLS 握手被服务端 alert 拒绝**；不绕过、不批量、不重试
- 不复制 `just-laws` 正文到本仓库
- 不让 LLM 生成法律正文 / 裁判原文 / 案号 / 裁判要旨

## 使用方式

```bash
# 只搜本专题（默认 core+direct）
python3 ../../scripts/search_all.py \
  --topic company-law \
  --query "股东抽逃出资承担什么责任" \
  --keywords "抽逃出资" "股东" "责任"

# 包含历史 + 关联
python3 ../../scripts/search_all.py \
  --topic company-law --include-related \
  --query "公司法 2018 修正 注册资本" \
  --keywords "2018修正" "注册资本"
```

`--topic` 模式仅在专题 `manifest.yaml` 存在且含 `topic.id` 字段时生效。

## manifest 可复用性

`build_manifest.py` 可直接复制到 `legal-topics/<other-topic>/build_manifest.py`；
`topic` / `documents` / `documents_related` / `case_collections` / `cases` / `cases_related` /
`statistics` / `verification` / `known_gaps` 结构已通用。

## 已知真实缺口（V3.3A.1）

1. 部门规章 / 规范性文件：现有条目均保持 `CANDIDATE`；《公司登记管理实施办法》和 2026 年版登记文书/提交材料规范暂无可靠本地全文映射
2. 指导性案例 / 公报案例 / 案例库入库案例：官方源 TLS 阻断或需登录，未绕过
3. 典型案例的案号 / 裁决日期：最高法公开稿以化名披露，原文未给出
4. primary_law 公司法正文：仍为 `（正文待补）` 占位，需人工在 flk.npc.gov.cn 浏览器复制
5. 已盘点案例 8 件全部 `verification_status=CANDIDATE`，未经 flk.npc.gov.cn 元数据级核验
