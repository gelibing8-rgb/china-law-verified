# V5.0.1 10 题 ROUTING + COVERAGE 拆开验收

_生成时间：2026-09-15_

## 验收口径（V5.0.1 新增）

- **ROUTING**：判断 Agent 是否正确找到相关 Topic；每题都跑 `--topics` 或 `--auto-topic` 实际检索本地数据库。
- **COVERAGE**：判断是否真的找到足够核心法律规范（主法律 + 行政法规 + 部门规章 + 司法解释 + 重要规范性文件 + 必要案例）。

## 10 题总览

| # | 题目 | 路由 Topic | 命中行数 | ROUTING | COVERAGE | 备注 |
| --- | --- | --- | ---: | --- | --- | --- |
| Q1 | 园区厂房租赁合同需要注意哪些法律问题？ | `company-law,civil-code,land-administration-law,work-safety-law` | 329 | ROUTING_PASS | COVERAGE_PASS | company-law 主法 + 民法典合同编 + 土地管理法 + 安全生产法齐备 |
| Q2 | EPC项目招标和工程总承包有哪些主要法律依据？ | `tendering-bidding-law,construction-law,civil-code` | 104 | ROUTING_PASS | COVERAGE_PASS | 招标投标法 + 建筑法 + 民法典合同编齐备 |
| Q3 | 工业用地招商后企业不按约投资怎么办？ | `land-administration-law,civil-code,company-law` | 3 | ROUTING_PASS | COVERAGE_PARTIAL | 缺闲置土地处置、项目履约监管专门文件（仅候选定位） |
| Q4 | 政府平台公司与民企合作投资产业园有哪些法律风险？ | `company-law,civil-code,land-administration-law` | 1 | ROUTING_PASS | COVERAGE_PARTIAL | 缺政府平台公司合规专门规定、企业投资合规指引（仅候选定位） |
| Q5 | 园区屋顶建设分布式光伏涉及哪些法规？ | `environmental-protection-law,construction-law,work-safety-law` | 92 | ROUTING_PASS | COVERAGE_PASS | 环境保护法 + 环境影响评价法 + 建筑法 + 安全生产法齐备 |
| Q6 | 员工严重违纪解除劳动合同怎么处理？ | `labor-contract-law` | 247 | ROUTING_PASS | COVERAGE_PASS | 劳动合同法 + 劳动法齐备 |
| Q7 | 企业股东未实缴出资怎么办？ | `company-law` | 316 | ROUTING_PASS | COVERAGE_PASS | 公司法齐备 |
| Q8 | 政府采购项目中标以后能不能变更合同？ | `government-procurement-law` | 113 | ROUTING_PASS | COVERAGE_PASS | 政府采购法 + 政府采购法实施条例齐备 |
| Q9 | 工业园区发生安全事故，可能涉及哪些责任？ | `work-safety-law,company-law,civil-code` | 388 | ROUTING_PASS | COVERAGE_PASS | 安全生产法 + 公司法 + 民法典侵权编齐备 |
| Q10 | 企业取得招商奖励或产业扶持资金有哪些合规风险？ | `civil-code,company-law,administrative-penalty-law` | 1 | ROUTING_PASS | COVERAGE_PARTIAL | 缺招商引资协议监管、产业扶持资金审计专门文件（仅候选定位） |

## 验收结果汇总

- **ROUTING 测试通过率：10 / 10 = 100%**（10 题均正确路由 Topic 且实际检索本地数据库）
- **COVERAGE 测试通过率：7 / 10 = 70%**
- **COVERAGE_PARTIAL 题目：3 个** —— Q3 工业用地违约 / Q4 政府平台公司合作 / Q10 招商奖励合规

## COVERAGE_PARTIAL 题目详情

### Q3 工业用地招商后企业不按约投资怎么办？
- 路由 Topic：`land-administration-law,civil-code,company-law`
- 命中行数：3
- **缺**：闲置土地处置办法、项目履约监管、地方政府土地节约集约利用等专门规定；目前仅获得主法律（土地管理法）和合同法原则条文，未获得实施细则级别规范。
- **处置**：V5.0.1 已在 `business-legal-gaps.json` 标记为 P0 缺口；等待人工在 flk.npc.gov.cn / ndrc.gov.cn 核验后写入候选源或 laws/。

### Q4 政府平台公司与民企合作投资产业园有哪些法律风险？
- 路由 Topic：`company-law,civil-code,land-administration-law`
- 命中行数：1
- **缺**：政府平台公司合规管理专门规定、国资委投资合规指引、产业基金管理办法等专门规范；目前仅命中公司法原则条文。
- **处置**：V5.0.1 已在 `business-legal-gaps.json` 标记为 P0 缺口；等待人工在 sasac.gov.cn / ndrc.gov.cn 核验。

### Q10 企业取得招商奖励或产业扶持资金有哪些合规风险？
- 路由 Topic：`civil-code,company-law,administrative-penalty-law`
- 命中行数：1
- **缺**：地方政府招商引资协议监管、产业扶持资金审计、财政补贴合规、财政违法行为处罚处分办法等专门规定。
- **处置**：V5.0.1 已在 `business-legal-gaps.json` 标记为 P0 缺口；等待人工在 mof.gov.cn / ndrc.gov.cn 核验。

## V5.0.0 vs V5.0.1 验收口径差别

- V5.0.0：报告 10/10 完全通过；
- V5.0.1：拆开 ROUTING 与 COVERAGE，诚实区分通过与部分通过。
- V5.0.0 Q3/Q4/Q10 命中数过少是诚实反映，不应掩盖为'通过'。
