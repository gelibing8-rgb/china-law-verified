# laws/ 目录说明

本目录收录中国法律法规 Markdown 文件。每份文件包含：

1. YAML frontmatter：标题、制定机关、发布/施行日期、版本日期、官方来源 URL、retrieved_at、`verification_status`、`content_sha256`
2. 官方结构树（编/章/条 标题）
3. 核验记录块

## V2.2 三层语义

V2.2 起，本目录中的每个 `*.md` 文件依据其 frontmatter 中 `verification_status` 的取值决定属于哪一层：

| verification_status | 层级 | 含义 |
| --- | --- | --- |
| `verified_official` | **VERIFIED** | 元数据 + 全文均已与官方原文逐字核验；可直接引用 |
| `needs_recheck` | **OFFICIAL_META** | 元数据 + 结构树已通过官方 API 核验；正文**未经**官方原文逐字核验；**不可**作为最终法律依据引用 |

`scripts/search_all.py` 在输出每条命中时会根据文件自身的 frontmatter 动态标注 `VERIFIED` 或 `OFFICIAL_META`。本目录当前所有 3 部法律均为 `needs_recheck`（OFFICIAL_META）。

## 当前 V1 / 2 收录

| 文件 | 标题 | 发布日期 | 当前版本日期 | 当前版本施行日期 | 原始施行日期 | 层级 |
| --- | --- | --- | --- | --- | --- | --- |
| `civil_code.md` | 中华人民共和国民法典 | 2020-05-28 | 2020-05-28 | 2021-01-01 | 2021-01-01 | OFFICIAL_META |
| `company_law_2024.md` | 中华人民共和国公司法 | 2023-12-29 | 2023-12-29 | 2024-07-01 | 1994-07-01 | OFFICIAL_META |
| `labor_contract_law.md` | 中华人民共和国劳动合同法 | 2012-12-28 | 2012-12-28 | 2013-07-01 | 2008-01-01 | OFFICIAL_META |

3 部法律的标题、制定机关、发布日期、当前版本施行日期、当前版本日期、`sxx=3 现行` 均通过 `flk.npc.gov.cn`（国家法律法规数据库）公开 API 核验一致。

## 为什么当前都是 OFFICIAL_META

按 V1 任务规则："只有实际读取官方来源并确认的内容才能标记 `verified_official`"。

**已通过官方来源（flk.npc.gov.cn API）核验：**

- 标题、制定机关（`zdjgName`）、发布日期（`gbrq`）、施行日期（`sxrq`）、当前版本日期（`current_version_date`）、原始施行日期（`original_effective_date`）、当前版本施行日期（`current_version_effective_date`）、现行有效性（`sxx=3`）、法律性质（`flxz=法律`）
- 完整结构树（编 / 章 / 条 标题，所有条目的 id）

**未核验：每条正文文本。**

正文文本不在 `flk.npc.gov.cn` 的服务端 API 返回中（仅返回结构树）。正文文本在 SPA 中通过嵌入的 WPS / OFD 文档查看器渲染，文档源（OFD / DOCX）存储于内网 OSS（路径形如 `prod/YYYYMMDD/<hash>.ofd`），文件下载接口返回的 preview URL 最终指向 `http://172.16.220.27:38080/...`，从公网无法直接下载。

本任务允许的其他官方源（`npc.gov.cn`、`gov.cn`、`moj.gov.cn`、`court.gov.cn`）在本次执行环境下 TLS 握手被服务端 alert 拒绝，未能拿到正文 HTML。

按"中国网站合规铁律"（见根目录 `README.md`），本项目**不**采取任何规避措施（包括伪造 User-Agent、伪造 IP、分布式抓取、登录态劫持等）。正文只能由人工在 flk.npc.gov.cn 浏览器界面复制补齐，才能从 OFFICIAL_META 升级为 VERIFIED。

## 从 OFFICIAL_META 升级为 VERIFIED 的步骤（人工操作）

针对每份 `*.md`：

1. 浏览器访问 `official_url`（或直接在 flk.npc.gov.cn 搜索标题）
2. 在 WPS / OFD 查看器中逐条复制正文
3. 在 Markdown 文件中找到对应 `#### 第X条` 后的 `（正文待补：...）` 占位行，替换为正文
4. 删除 `（正文待补：...）` 中的条目 ID
5. 重新计算正文 SHA256：

   ```bash
   python3 -c "import re,hashlib,sys; t=open(sys.argv[1]).read(); m=re.match(r'^---\\s*\\n.*?\\n---\\s*\\n(.*)$', t, re.DOTALL); print(hashlib.sha256(m.group(1).encode('utf-8')).hexdigest())" laws/civil_code.md
   ```

6. 把 SHA256 写回 frontmatter
8. 把 `verification_status: needs_recheck` 改为 `verification_status: verified_official`
9. 重新运行 `python3 scripts/verify.py` 与 `python3 scripts/search_all.py --keywords "关键词" "关键词2" ...` 验收

> 说明：人工补齐后的正文不得包含 AI 总结、推断、第三方注释；只允许复制 flk.npc.gov.cn 渲染的官方原文。

## V1 / 2 范围限制

- 仅收录 3 部法律用于流程验证。
- 不收录司法解释、实施条例、地方性法规。
- 不收录已废止或失效版本。
- 不收录出版商注释版。
- 不复制 `just-laws` 候选层文本到本目录（候选层只读引用，详见 `scripts/search_all.py`）。