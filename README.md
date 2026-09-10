# china-law-verified

Verified Chinese laws from official government sources, structured for human and AI-agent retrieval.

## 项目说明

本仓库收录中国法律法规的官方原文，仅使用经核验的官方发布来源，
用于：

- 人工快速查阅
- AI Agent / 自动化工具的本地全文检索
- 作为后续扩展的基础数据层

V1 仅收录 3 部法律用于验收：**中华人民共和国民法典**、**中华人民共和国公司法（2024 年 7 月 1 日施行版）**、**中华人民共和国劳动合同法（现行版）**。

## 数据来源（白名单）

仅收录下列官方站点发布的原文：

| 站点 | 域名 |
| --- | --- |
| 国家法律法规数据库 | `flk.npc.gov.cn` |
| 中国人大网 | `npc.gov.cn` |
| 中国政府网 | `gov.cn` |
| 最高人民法院 | `court.gov.cn` |
| 司法部 | `moj.gov.cn` |
| 其他经确认的中央国家机关官方站点 | （按官方域名白名单逐条登记） |

`scripts/verify.py` 中的 `ALLOWED_DOMAINS` 是上述来源的程序化落地。

**禁止来源**

- 商业法律数据库（北大法宝、威科先行、无讼等）
- 微信公众号、知乎、百度百科
- 出版社、付费内容、第三方注释版

## 目录

```
china-law-verified/
├── README.md
├── LICENSE
├── sources.yaml             # 官方来源白名单（机器可读）
├── laws/                    # 每部法律一个 Markdown 文件
├── metadata/
│   └── index.jsonl          # 每行一部法律的元数据 + SHA256
└── scripts/
    ├── search.py            # 全文检索（基于 rg，无 rg 时回退 Python）
    ├── verify.py            # 校验元数据 / 来源域名 / SHA256 / 重复
    └── update.py            # 输出待重新核验清单（增量更新预留）
```

## 单部法律的格式

每份 `laws/*.md` 文件头包含：

```yaml
---
title: 中华人民共和国××法
document_type: 法律
issuing_authority: 全国人民代表大会 / 全国人大常委会
promulgation_date: YYYY-MM-DD
effective_date: YYYY-MM-DD
status: 现行 / 已废止 / 已被修正
version_date: YYYY-MM-DD
official_url: https://...
retrieved_at: YYYY-MM-DDTHH:MM:SSZ
verification_status: verified_official | needs_recheck
content_sha256: <hex>
---
```

- 正文以下只保存官方法律原文，不得包含 AI 生成、注释、出版社导读。
- `verification_status = verified_official` 仅在实际读取官方来源并确认内容一致时使用。
- `verification_status = needs_recheck` 用于当前无法确认现行版本或来源失效的法律。

## 检索示例

```bash
python3 scripts/search.py "减资"
python3 scripts/search.py "解除劳动合同"
```

输出包含：法律名称、命中上下文（含行号）、文件路径、官方来源 URL、版本日期。

## 校验

```bash
python3 scripts/verify.py
```

逐项检查：

- 必填元数据完整
- `official_url` 域名属于 `ALLOWED_DOMAINS`
- 正文非空
- `content_sha256` 与正文一致
- 没有重复法律 / 重复版本

## 更新机制（V1 占位）

`scripts/update.py` 第一版仅：

- 读取 `metadata/index.jsonl`
- 列出 `verification_status = needs_recheck` 的记录
- 预留增量更新接口（`update_law(keyword, url)`），不在 V1 启用自动爬取

## 许可证

- 本项目自编脚本、结构化元数据、`README` 等自有内容采用 MIT License，详见 [LICENSE](./LICENSE)。
- 本仓库收录的法律法规原文来源于中国官方公开文件；该等文本本身不构成项目自身的著作权主张，使用请遵循相应官方发布机构的规定。

## 限制与下一步

- V1 只导入 3 部法律，仅用于验证流程；任何大规模扩充都应分阶段进行。
- 当前不内置向量数据库、不内置 LLM 检索。
- 任何 AI Agent 在引用本仓库时，应同时引用 `official_url` 中给出的官方原文链接。