# 个人业务法律全景图 (V5)

_生成时间：2026-09-15T00:52:47Z_

51 个一级业务领域 × P0/P1/P2 分级 × canonical 关联

## 字段说明
- `domain_code` / `domain_name`：一级业务领域
- `related_topics`：当前领域直接关联的现有 Topic
- `linked_canonical_count`：当前领域已识别到的 canonical 规范数
- `priority`：P0（高频高风险）/ P1（常用非核心高频）/ P2（低频）
- `local_text_count`：本地候选源中具备正文的副本数

## 业务领域清单

| 编号 | 名称 | 优先级 | 关联 Topic | 关联 canonical | 本地正文副本 |
| --- | --- | --- | --- | ---: | ---: |
| 01 | 民商事基础 | P0 | civil-code | 1254 | 1269 |
| 02 | 公司治理 | P0 | company-law | 25 | 26 |
| 03 | 合同与担保 | P0 | civil-code, company-law | 1260 | 1276 |
| 04 | 劳动人事 | P0 | labor-contract-law | 16 | 17 |
| 05 | 招标投标 | P0 | tendering-bidding-law | 7 | 8 |
| 06 | 政府采购 | P0 | government-procurement-law | 4 | 5 |
| 07 | 工程建设 | P0 | construction-law | 146 | 148 |
| 08 | EPC / EPCO / 工程总承包 | P0 | tendering-bidding-law, construction-law, civil-code | 1391 | 1409 |
| 09 | 房地产与工业地产 | P0 | civil-code, land-administration-law, urban-rural-planning-law | 1320 | 1340 |
| 10 | 土地管理 | P0 | land-administration-law | 67 | 71 |
| 11 | 城乡规划 | P0 | urban-rural-planning-law | 22 | 23 |
| 12 | 产业园区开发运营 | P1 | land-administration-law, urban-rural-planning-law, company-law | 114 | 120 |
| 13 | 招商引资 | P1 | company-law, civil-code, land-administration-law | 1304 | 1324 |
| 14 | 国有资产与国有企业 | P0 | company-law, civil-code | 1260 | 1276 |
| 15 | 政府平台公司 | P0 | company-law | 25 | 26 |
| 16 | 投资并购 | P0 | company-law, civil-code | 1260 | 1276 |
| 17 | 私募基金 | P1 | company-law, civil-code | 1260 | 1276 |
| 18 | 政府投资基金 / 引导基金 | P1 | company-law | 25 | 26 |
| 19 | 企业融资与金融 | P1 | company-law, civil-code | 1260 | 1276 |
| 20 | 税务财政 | P1 | civil-code | 1254 | 1269 |
| 21 | 企业登记与市场监管 | P1 | company-law | 25 | 26 |
| 22 | 安全生产 | P0 | work-safety-law | 258 | 273 |
| 23 | 消防 | P1 | work-safety-law | 258 | 273 |
| 24 | 环境保护 | P0 | environmental-protection-law | 49 | 53 |
| 25 | 节能与双碳 | P1 | environmental-protection-law | 49 | 53 |
| 26 | 分布式光伏 | P1 | environmental-protection-law | 49 | 53 |
| 27 | 储能 | P1 | environmental-protection-law | 49 | 53 |
| 28 | 电力与综合能源 | P1 | environmental-protection-law | 49 | 53 |
| 29 | 行政许可 | P0 | administrative-penalty-law, civil-procedure-law | 183 | 186 |
| 30 | 行政处罚 | P1 | administrative-penalty-law | 19 | 20 |
| 31 | 行政复议 | P1 | administrative-penalty-law, civil-procedure-law | 183 | 186 |
| 32 | 行政诉讼 | P1 | administrative-penalty-law, civil-procedure-law | 183 | 186 |
| 33 | 民事诉讼 | P0 | civil-procedure-law | 167 | 169 |
| 34 | 仲裁 | P1 | civil-procedure-law | 167 | 169 |
| 35 | 强制执行 | P1 | civil-procedure-law | 167 | 169 |
| 36 | 企业破产 | P0 | company-law, civil-procedure-law | 192 | 195 |
| 37 | 知识产权 | P1 | civil-code | 1254 | 1269 |
| 38 | 数据安全 | P1 | civil-code | 1254 | 1269 |
| 39 | 网络安全 | P1 | civil-code | 1254 | 1269 |
| 40 | 个人信息保护 | P1 | civil-code | 1254 | 1269 |
| 41 | 人工智能相关合规 | P1 | civil-code | 1254 | 1269 |
| 42 | 反不正当竞争 | P1 | civil-code | 1254 | 1269 |
| 43 | 反垄断 | P1 | civil-code | 1254 | 1269 |
| 44 | 广告与宣传 | P1 | civil-code, administrative-penalty-law | 1270 | 1286 |
| 45 | 企业信用 | P1 | administrative-penalty-law | 19 | 20 |
| 46 | 产业扶持资金 | P1 | civil-code, company-law | 1260 | 1276 |
| 47 | 政府补贴与专项资金 | P1 | civil-code, company-law | 1260 | 1276 |
| 48 | 商协会 / 社会组织 | P1 | civil-code | 1254 | 1269 |
| 49 | 拍卖业务 | P1 | civil-code, administrative-penalty-law | 1270 | 1286 |
| 50 | 律师业务相关程序规范 | P1 | civil-procedure-law, administrative-penalty-law | 183 | 186 |
| 51 | 与产业园区经营直接相关的其他必要专题 | P1 | land-administration-law, company-law | 92 | 97 |

## 怎么用
- OpenClaw 收到自然语言问题后，先在 `metadata/business-legal-map.json` 找到相关一级领域；
- 取其 `related_topics` 调 `search_all.py --topics a,b,c` 聚合；
- 缺一级的 canonical 视为真实缺口，按 `business-legal-gaps.json` 处理。
