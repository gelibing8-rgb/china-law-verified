# china-law-verified

Verified Chinese laws from official government sources, structured for human and AI-agent retrieval.

## 项目说明

本仓库收录中国法律法规的官方原文，仅使用经核验的官方发布来源。仓库采用**两层结构**：

- **VERIFIED（官方核验层）**：`laws/*.md`，元数据与结构树均经 `flk.npc.gov.cn`（国家法律法规数据库）官方 API 核验。当前仅收录 3 部法律用于流程验收。
- **CANDIDATE（本地候选层）**：本仓库**不**包含 CANDIDATE 文本；仅在 `scripts/search_all.py` 里以只读方式访问位于 `~/workspace/legal-sources/just-laws` 的本地候选库 `ImCa0/just-laws`（MIT）。候选层仅供"定位相关条文"，**不构成最终法律依据**。

## 中国网站合规铁律

本项目（含所有脚本、`search_all.py`、`verify.py`、`update.py`、`_generate_laws.py` 及使用本项目的任何 agent / 工作流）必须严格遵守：

1. **不得绕过**任何形式的验证码、登录、滑块、Cookie / Token 校验；
2. **不得绕过**任何限频（rate limit）、反爬、访问控制、防滥用、风控策略；
3. **不得调用**未经公开授权的内部接口、内网地址（`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`127.0.0.0/8` 等）、未公开 API；
4. **不得采取**任何规避手段，包括伪造 User-Agent、伪造 IP、分布式抓取、登录态劫持、Cookie 重放等；
5. **遇到任何访问限制**（HTTP 4xx/5xx、风控提示、TLS 握手失败被服务端 alert 拒绝、captcha、限速等），**立即停止自动化访问**，不得重试或换路径绕过；
6. **政府站点访问策略**：本项目允许的官方来源仅限 `sources.yaml` 中 `allowed_domains` 列出的站点；其他站点一律不主动抓取；不允许任何批量访问、轮询、或并发请求官方站点。

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
├── laws/                # VERIFIED 层（已官方核验）
│   ├── README.md         # needs_recheck 原因 + 补齐步骤
│   ├── civil_code.md
│   ├── company_law_2024.md
│   └── labor_contract_law.md
├── metadata/
│   └── index.jsonl      # VERIFIED 元数据
└── scripts/
    ├── search.py        # 单层（VERIFIED）全文检索
    ├── search_all.py    # V2.1 双层检索（精确 → AND 拆解）
    ├── verify.py        # 校验元数据 / 域名 / SHA256
    ├── update.py        # 增量更新占位
    └── _generate_laws.py # 生成器（V1 一次性脚本）
```

**CANDIDATE 候选层不在本仓库内**。运行 `search_all.py` 之前需要在 `~/workspace/legal-sources/just-laws` 下只读 clone `ImCa0/just-laws`（MIT，详见 `scripts/search_all.py` 中 `CANDIDATE_ROOT` 路径）。

## 单部法律格式

每份 `laws/*.md` 文件 YAML frontmatter 必填字段（V2.1）：

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

> **已废弃字段**（逐步废弃，禁止因为字段含义不清而自行推断）：
> - `effective_date` —— 仅保留向后兼容，**等同** `current_version_effective_date`
> - `version_date` —— 仅保留向后兼容，**等同** `current_version_date`
>
> 这两个字段在 V2.1 之后会被逐步移除；新代码必须使用新字段。

正文部分：

- 只保存官方原文，不包含 AI 生成、注释、出版社导读
- `verification_status = verified_official` 仅在实际读取官方原文并确认一致时使用
- `verification_status = needs_recheck` 用于当前无法确认全文 / 现行版本的法律

## 检索

### 单层检索（仅 VERIFIED）

```bash
python3 scripts/search.py "减资"
```

### 双层检索（V2.1，精确 → AND 拆解）

```bash
python3 scripts/search_all.py \
  --query "公司减资如何通知债权人" \
  --keywords "减资" "通知债权人" "债权人"
```

参数：
- `--query`：用户原始自然语言问题（用于整句精确检索）
- `--keywords`：2~4 个候选检索词（**由调用方拆词**；`search_all.py` 不调用 LLM）

执行顺序：
1. **阶段 1**：用 `--query` 整句精确检索
2. **阶段 2**（仅阶段 1 完全 0 命中时）：每个 `--keyword` 单独检索
3. **阶段 3**（仅阶段 1 完全 0 命中时）：`--keywords` 的 AND 交集（同一文件必须出现全部关键词，列出每条命中行）

输出始终区分：
- `VERIFIED` = `laws/`（已官方核验）
- `CANDIDATE` = `just-laws`（MIT，开源候选，仅供定位）

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

## 限制与下一步

- V1/V2.1 仅导入 3 部法律用于流程验证
- VERIFIED 层正文未补齐（受 flk 内网 WPS/OFD viewer 物理阻塞；本项目**不**采用规避措施）
- 不内置向量数据库 / 不内置 LLM 检索 / 不内置 RAG
- 任何 AI Agent 在引用本仓库时，应同时引用 `official_url` 中给出的官方原文链接

## 许可证

- 本项目自编脚本、结构化元数据、`README` 等自有内容采用 MIT License，详见 [LICENSE](./LICENSE)。
- 本仓库**不收录**任何法律法规正文（VERIFIED 层正文为 `（正文待补）` 占位）；待人工在 flk.npc.gov.cn 浏览器界面补齐后方可标 `verified_official`。