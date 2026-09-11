# 公司法专题（V3 样板）

> 这是 `china-law-verified` 项目按"法律专题知识包"组织的第一份样板。
> 目标：把"单部法律全文"升级为"以专题为单位的法律知识包"。

本专题围绕 **中华人民共和国公司法（2023 修订 / 2024-07-01 施行）** 现行版本展开，关联其直接相关的：

- 行政法规 / 实施规定
- 公司登记、注册资本、股东、董监高、公司治理等相关的部门规章 / 规范性文件
- 现行有效的公司法司法解释
- 最高人民法院发布的指导性 / 典型 / 公报案例
- 公司法历次修订、修正、修改的版本沿革

## 目录

```
legal-topics/
└── company-law/
    ├── README.md       # 本文件
    └── manifest.yaml   # 专题清单（核心数据）
```

**本专题不复制任何法条正文 / 案例全文**。所有底层文件按"不重复存储"原则，
仅记录：

- 已在 `laws/` 收录的 → 指向 `laws/company_law_2024.md`
- 仅在 `just-laws`（CANDIDATE 候选层）有的 → 指向本地只读路径
- 仅官方源 / web 检索发现元数据的 → 留 `local_path: null`，待人工补齐

## 可信等级

每条记录的 `verification_status` 沿用 V2.2 三层语义：

| 层级 | 含义 |
| --- | --- |
| **VERIFIED** | 元数据 + 全文均已官方核验（当前本专题 0 条） |
| **OFFICIAL_META** | 元数据 + 结构树已通过 `flk.npc.gov.cn` 等官方 API 核验；正文未经官方逐字核验 |
| **CANDIDATE** | 来自 `just-laws`（ImCa0/just-laws, MIT）或 `web_search` 公开结果，仅供定位 |

**禁止**：仅因文件与公司法相关就自动提升可信等级。

## 数据来源

| 来源 | 用途 | 限制 |
| --- | --- | --- |
| `flk.npc.gov.cn`（国家法律法规数据库）官方 API | 主法律、司法解释、行政法规元数据 | 正文受内网 WPS/OFD viewer 阻塞，本项目不绕过 |
| `just-laws`（ImCa0/just-laws, MIT，本地只读） | CANDIDATE 正文本体的唯一来源 | 仅本地只读；不复制进本仓库；不冒充权威 |
| `web_search`（MiniMax Search） | 找典型 / 指导性 / 公报案例的 `source_url` 与发布机构 | 命中内容不直接采纳为法条正文 |
| `court.gov.cn` / `gov.cn` / `moj.gov.cn` / `npc.gov.cn` | **本次环境 TLS 握手被服务端 alert 拒绝**；无法直接访问 | 严禁任何规避措施 |

## 中国网站合规铁律（持续执行）

- 不绕过验证码 / 登录 / 滑块 / 限频 / 反爬 / 访问控制 / 风控
- 不调用未公开接口 / 内网接口
- 遇到访问限制立即停止，不尝试规避
- 不批量访问政府站点
- 仅在 `sources.yaml` 列出的白名单域名内主动访问政府站点
- 不复制 `just-laws` 候选层正文到本仓库
- 不新增 Agent、不新增 MCP 来绕过上述限制

## 如何扩展为其他专题

本 manifest.yaml 结构可直接复制到其他法律专题。复制步骤：

1. 在 `legal-topics/` 下创建新专题目录，例如 `labor-contract-law/`
2. 复制 `manifest.yaml` 作为模板
3. 按 `relation_type` 列表盘点该专题应该包含的关联文件
4. 逐条查询 `flk.npc.gov.cn` / `just-laws` / `web_search`，登记元数据
5. 实际正文与案例按"不重复存储"原则，**只填 `local_path` 或留空待补**
6. 写专题 README 说明覆盖范围与限制

## 待补清单

| 类型 | 缺失内容 | 补齐方法 |
| --- | --- | --- |
| primary_law 正文 | 公司法全文 | 浏览器打开 flk 详情页复制 → 写入 `laws/company_law_2024.md` |
| 行政法规 / 部门规章 全文 | 多部无 just-laws 副本 | flk 详情页复制 / 后续按需入 OFFICIAL_META |
| 司法解释 全文 | 6 部现行司法解释无 just-laws 副本 | flk 详情页复制 |
| 指导性案例 | court.gov.cn 被 TLS 阻断 | 通过 web_search 找 `source_url`，待人工按指引访问 |
| 部门规章 / 规范性文件 | flk.npc.gov.cn 未单独类目 | web_search 找国家市场监督管理总局 / 中国证监会等部门规章 |
| 历史版本 | 1993 / 1999 / 2004 / 2005 详细沿革 | 已在 manifest 列出 bbbs；正文按需补 |
