# china-law-verified

Verified Chinese laws from official government sources, structured for human and AI-agent retrieval.

## 项目规模（V5.0.0）

`legal-universe.json` 按 bbbs / 文号 / 标题+机关+日期 去重后：

- **主法律**：833
- **行政法规**：1433
- **部门规章**：29
- **规范性文件**：425（修改、废止的决定 / 修正案 / 法律解释 / 未分类补推）
- **司法解释**：1235
- **地方规范**：1681（地方性法规 1670 + 宪法 8 + 监察法规 3）
- **去重后法律规范总数**：5637
- **现行版本**：5362
- **案例**（公司法专题）：
  - 指导性案例：3
  - 人民法院案例库案例：1
  - 其他权威案例：7
- **完整 Topic**：12
- **轻量 Topic**：0
- **业务一级领域**：51（P0 = 19，P1 = 32，P2 = 0）

可信等级分布：

- **VERIFIED**：0
- **OFFICIAL_META**：4（3 个 laws/ 主法律 + 1 个独立元数据）
- **CANDIDATE**：5633
- **UNVERIFIED**：0

Freshness Gate 分布：

- **FRESH**：1920
- **STALE**：275
- **UNKNOWN**：3441
- **CONFLICT**：1

## 正式用途说明

正式合同 / 法律意见 / 诉讼 / 仲裁 / 重大投资 / 重大交易等场景仍以官方现行有效性核验结果为最终依据；本库 `CANDIDATE` 不得直接作为最终法律依据。

## 项目说明

本仓库收录中国法律法规的官方核验层元数据及本地候选全文定位，采用 **V4 Topic Schema**；候选正文不复制入库，不能替代官方依据。

| 层级 | 含义 | 路径 |
| --- | --- | --- |
| **VERIFIED** | 元数据 + 全文均已与官方原文逐字核验；可直接引用 | `laws/*.md` 中 `verification_status=verified_official` 的文件 |
| **OFFICIAL_META** | 元数据 + 结构树已通过官方 API 核验；正文未经官方原文逐字核验；**不可**作为最终法律依据引用 | `laws/*.md` 中 `verification_status=needs_recheck` 的文件 |
| **CANDIDATE** | 开源候选，仅供"定位相关条文"，**不能**作为最终法律依据 | `~/workspace/legal-sources/just-laws`（本仓库**不**收录 CANDIDATE 文本） |

`scripts/search_all.py` 在输出每条命中时根据文件自身的 frontmatter 动态标注 `VERIFIED` / `OFFICIAL_META` / `CANDIDATE`，不会把所有 `laws/*.md` 一律标为 VERIFIED。

## 中国网站合规铁律

本项目（含所有脚本、`search_all.py`、`verify.py`、`update.py`、`_generate_laws.py` 及使用本项目的任何 agent / 工作流）**必须**严格遵守：

1. **不得绕过**任何形式的验证码、登录、滑块、Cookie / Token 校验；
2. **不得绕过**任何限频（rate limit）、反爬、访问控制、防滥用、风控策略；
3. **不得调用**未经公开授权的内部接口、内网地址（`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`127.0.0.0/8` 等）、未公开 API；
4. **不得采取**任何规避手段，包括伪造 User-Agent、伪造 IP、分布式抓取、登录态劫持、Cookie 重放等；
5. **遇到任何访问限制**（HTTP 4xx/5xx、风控提示、TLS 握手失败被服务端 alert 拒绝、captcha、限速等），**立即停止自动化访问**，不得重试或换路径绕过；
6. **政府站点访问策略**：本项目允许的官方来源仅限 `sources.yaml` 中 `allowed_domains` 列出的站点；其他站点一律不主动抓取；不允许任何批量访问、轮询、或并发请求官方站点。

## Agent / LLM 职责分工（V2.2）

- **Agent / LLM 可以**：将用户的自然语言问题转换为 2~4 个检索关键词，作为 `--keywords` 参数传给 `scripts/search_all.py`
- **法律正文检索必须**：`scripts/search_all.py` 仅使用 `rg` 或 Python `re` 在已落盘的本地 Markdown 文件中检索；**禁止**把正文查找交给 LLM
- **LLM 禁止**：生成、补写、修改或冒充任何法律原文；命中行展示的"原文"**必须**是源文件按行原样截取
- **Agent 调用方式**（示意）：

  ```bash
  python3 scripts/search_all.py \
    --query "公司减资如何通知债权人" \
    --keywords "减资" "通知债权人" "债权人"
  ```

## 数据来源白名单

| 站点 | 域名 |
| --- | --- |
| 国家法律法规数据库 | `flk.npc.gov.cn` |
| 中国人大网 | `npc.gov.cn` |
| 中国政府网 | `gov.cn` |
| 最高人民法院 | `court.gov.cn` / `chinacourt.gov.cn` |
| 司法部 | `moj.gov.cn` |
| 最高人民检察院 | `spp.gov.cn` |
| 审计署 | `audit.gov.cn` |

具体来源登记见 `sources.yaml` 中 `used_sources`。`scripts/verify.py` 会逐项核验 `official_url` 域名是否在白名单内。

**禁止来源**：商业法律数据库（北大法宝、威科先行、无讼等）、微信公众号、知乎、百度百科、出版社付费内容、第三方注释版。

## 目录

```
china-law-verified/
├── README.md            # 本文件
├── LICENSE              # MIT（仅覆盖自有代码 / 元数据）
├── sources.yaml         # 官方来源白名单 + 实际来源登记
├── laws/                # VERIFIED / OFFICIAL_META 层（按各文件 frontmatter 分层）
│   ├── README.md         # needs_recheck 原因 + 升级为 VERIFIED 的步骤
│   ├── civil_code.md
│   ├── company_law_2024.md
│   └── labor_contract_law.md
├── legal-topics/          # V4 专题、Schema、topics registry、311 部法律 catalog
│   ├── _schema/
│   ├── topics.json
│   ├── catalog.json
│   └── company-law/       # 冻结的公司法参考专题
├── metadata/
│   └── index.jsonl      # laws/*.md 元数据
└── scripts/
    ├── search.py        # 单层（laws/）全文检索
    ├── search_all.py    # V2.2 三层语义检索：laws/ + CANDIDATE
    ├── verify.py        # 校验元数据 / 域名 / SHA256
    ├── update.py        # 旧版兼容入口
    ├── build_topic.py   # V4 本地专题生成器
    ├── build_registry.py # topics/catalog 生成器
    ├── update_candidates.py # GitHub 候选库增量更新
    ├── update_topics.py # 受影响专题重建
    ├── validate_topics.py # V4 QA
    ├── weekly_update.sh # 自动任务执行入口
    └── _generate_laws.py # 生成器（V1 一次性脚本）
```

**CANDIDATE 候选层不在本仓库内**。运行 `search_all.py` 之前需要准备 `~/workspace/legal-sources/just-laws`、`laws`、`china-data-laws` 三个本地只读 clone；许可证和来源风险按各专题 manifest 记录。

## 单部法律格式

每份 `laws/*.md` 文件 YAML frontmatter 必填字段（V2.1 起）：

```yaml
---
title: 中华人民共和国××法
document_type: 法律
issuing_authority: 全国人民代表大会 / 全国人大常委会
promulgation_date: YYYY-MM-DD            # 当前版本通过/公布日期
original_effective_date: YYYY-MM-DD      # 原法律首次施行日期
current_version_date: YYYY-MM-DD         # 当前修正/修订版本通过日期
current_version_effective_date: YYYY-MM-DD # 当前版本实际施行日期
status: 现行 / 已废止 / 已被修正 / 已失效
official_url: https://...
retrieved_at: YYYY-MM-DDTHH:MM:SSZ
verification_status: verified_official | needs_recheck
content_sha256: <hex>
---
```

> **字段说明**：
> - `promulgation_date` = 当前版本通过 / 公布日期（来自 `flk.npc.gov.cn` gbrq 字段）
> - `original_effective_date` = 原法律首次施行日期（用于区分初次立法 vs 修正史）
> - `current_version_date` = 当前修正 / 修订版本通过日期
> - `current_version_effective_date` = 当前版本实际施行日期
> - `verification_status`：
>   - `verified_official` → 本文件属于 VERIFIED 层
>   - `needs_recheck` → 本文件属于 OFFICIAL_META 层（不可作最终法律依据）

> **已废弃字段**（逐步废弃，禁止因为字段含义不清而自行推断）：
> - `effective_date` —— 仅保留向后兼容，**等同** `current_version_effective_date`
> - `version_date` —— 仅保留向后兼容，**等同** `current_version_date`

正文部分：

- 只保存官方原文，不包含 AI 生成、注释、出版社导读
- `verification_status = verified_official` 仅在实际读取官方原文并确认一致时使用
- `verification_status = needs_recheck` 用于当前无法确认全文 / 现行版本的法律

## 检索

### 单层检索（仅 laws/）

```bash
python3 scripts/search.py "减资"
```

### 三层检索（V2.2，精确 → AND 拆解）

```bash
python3 scripts/search_all.py \
  --query "公司减资如何通知债权人" \
  --keywords "减资" "通知债权人" "债权人"
```

参数：
- `--query`：用户原始自然语言问题（用于整句精确检索）
- `--keywords`：2~4 个候选检索词（**由调用方拆词**；`search_all.py` 不调用 LLM）
- `--laws-only`：只搜 laws/（VERIFIED + OFFICIAL_META）
- `--candidate-only`：只搜 CANDIDATE

执行顺序：
1. **阶段 1**：用 `--query` 整句精确检索
2. **阶段 2**（仅阶段 1 完全 0 命中时）：每个 `--keyword` 单独检索
3. **阶段 3**（仅阶段 1 完全 0 命中时）：`--keywords` 的 AND 交集（同一文件必须出现全部关键词，列出每条命中行）

输出始终区分三层，每条命中带层标签：
- `[VERIFIED]` = 元数据 + 全文已官方核验
- `[OFFICIAL_META]` = 元数据 + 结构树已核验，正文未核验
- `[CANDIDATE]` = 开源候选，不可作最终法律依据

## 校验

```bash
python3 scripts/verify.py
```

逐项检查：
- 必填元数据完整（含新日期字段）
- `official_url` 域名属于白名单
- 正文非空
- `content_sha256` 与正文一致
- 没有重复法律 / 重复 (title, issuing_authority, current_version_date) 组合
- `metadata/index.jsonl` 与磁盘文件一致

## 候选层（CANDIDATE）说明

| 项 | 内容 |
| --- | --- |
| 仓库 | https://github.com/ImCa0/just-laws |
| 本地路径 | `~/workspace/legal-sources/just-laws`（**不在本仓库内**） |
| LICENSE | MIT（Copyright 2022 ImCaO） |
| 自述 | 311 部现行有效法律、覆盖至 2026-06；最近 commit 2026-08-29 |
| 法律责任 | MIT 明文"AS IS"，作者不承担任何责任 |

**使用约束**：
- CANDIDATE 内容仅供"定位相关条文"，**不能直接作为最终法律依据**
- 任何对外引用必须回到 `flk.npc.gov.cn` 等官方源对照原文
- 本项目**不**把 `just-laws` 的全文复制进 `china-law-verified/laws/`；如需把某条 CANDIDATE 提级为 VERIFIED，必须在 `flk.npc.gov.cn` 详情页核对全文与官方 URL，并按 `laws/README.md` 步骤补齐 frontmatter

## 限制与状态

- V1 / V2.1 / V2.2 仅导入 3 部法律用于流程验证
- 当前 3 部法律均为 `OFFICIAL_META`（受 flk 内网 WPS/OFD viewer 物理阻塞；本项目**不**采用规避措施）
- 不内置向量数据库 / 不内置 LLM 检索 / 不内置 RAG
- 任何 AI Agent 在引用本仓库时，应同时引用 `official_url` 中给出的官方原文链接
- **项目进入稳定使用状态**，不再继续扩充数据源

## 许可证

- 本项目自编脚本、结构化元数据、`README` 等自有内容采用 MIT License，详见 [LICENSE](./LICENSE)。
- 本仓库**不收录**任何法律法规正文（VERIFIED 层正文为 `（正文待补）` 占位，OFFICIAL_META 层正文未补齐）；待人工在 flk.npc.gov.cn 浏览器界面补齐后方可标 `verified_official`。
