# laws/ 目录说明

本目录收录中国法律法规 Markdown 文件。每份文件包含：

1. YAML frontmatter：标题、制定机关、发布/施行日期、版本日期、官方来源 URL、retrieved_at、`verification_status`、`content_sha256`
2. 官方结构树（编/章/条 标题）
3. 核验记录块

## 当前 V1 收录

| 文件 | 标题 | 发布日期 | 施行日期 | 当前版本 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `civil_code.md` | 中华人民共和国民法典 | 2020-05-28 | 2021-01-01 | 2020-05-28 | needs_recheck |
| `company_law_2024.md` | 中华人民共和国公司法 | 2023-12-29 | 2024-07-01 | 2023-12-29 | needs_recheck |
| `labor_contract_law.md` | 中华人民共和国劳动合同法 | 2007-06-29 | 2008-01-01 | 2012-12-28 | needs_recheck |

3 部法律的标题、制定机关、发布日期、施行日期、当前版本日期、`sxx=3 现行` 均通过 `flk.npc.gov.cn`（国家法律法规数据库）公开 API 核验一致。

## 为什么 `verification_status = needs_recheck`

按 V1 任务规则："只有实际读取官方来源并确认的内容才能标记 `verified_official`"。

**已通过官方来源（flk.npc.gov.cn API）核验：**

- 标题、制定机关（`zdjgName`）、发布日期（`gbrq`）、施行日期（`sxrq`）、现行有效性（`sxx=3`）、法律性质（`flxz=法律`）
- 完整结构树（编 / 章 / 条 标题，所有条目的 id）

**未核验：每条正文文本。**

正文文本不在 `flk.npc.gov.cn` 的服务端 API 返回中（仅返回结构树）。正文文本在 SPA 中通过嵌入的 WPS / OFD 文档查看器渲染，文档源（OFD / DOCX）存储于内网 OSS（路径形如 `prod/YYYYMMDD/<hash>.ofd`），文件下载接口 `https://flk.npc.gov.cn/law-search/amazonFile/...` 返回的 preview URL 最终指向 `http://172.16.220.27:38080/...`，从公网无法直接下载。

本任务允许的其他官方源（`npc.gov.cn`、`gov.cn`、`moj.gov.cn`、`court.gov.cn`）在本次执行环境下 TLS 握手被服务端拒绝（`SSL alert number 40`，即服务端主动中断 TLS 协商），未能拿到正文 HTML。

因此，**正文文本必须由人工在 flk.npc.gov.cn 浏览器界面复制补齐**，才能转为 `verified_official`。

## 补齐步骤（人工操作）

针对每份 `*.md`：

1. 浏览器访问 `official_url`（或直接在 flk.npc.gov.cn 搜索标题）
3. 在 WPS / OFD 查看器中逐条复制正文
4. 在 Markdown 文件中找到对应 `#### 第X条` 后的 `（正文待补：...）` 占位行，替换为正文
5. 删除 `（正文待补：...）` 中的条目 ID
6. 重新计算正文 SHA256：

   ```bash
   python3 -c "import re,hashlib,sys; t=open(sys.argv[1]).read(); m=re.match(r'^---\\s*\\n.*?\\n---\\s*\\n(.*)$', t, re.DOTALL); print(hashlib.sha256(m.group(1).encode('utf-8')).hexdigest())" laws/civil_code.md
   ```

7. 把 SHA256 写回 frontmatter
8. 把 `verification_status: needs_recheck` 改为 `verification_status: verified_official`
9. 重新运行 `python3 scripts/verify.py` 与 `python3 scripts/search.py "关键词"` 验收

> 说明：人工补齐后的正文不得包含 AI 总结、推断或第三方注释；只允许复制 flk.npc.gov.cn 渲染的官方原文。

## V1 范围限制

- 仅收录 3 部法律用于流程验证。
- 不收录司法解释、实施条例、地方性法规。
- 不收录已废止或失效版本。
- 不收录出版商注释版。