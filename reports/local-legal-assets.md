# 本地法律资产清单 (V5)

_生成时间：2026-09-15T00:16:29Z_

## 候选源

| 候选源 | Git commit | 文件数 | 磁盘占用 |
| --- | --- | ---: | ---: |
| just-laws | `56770b043bf19686fec43403bd24e8e290275794` | 377 | 9.0 MB |
| lawtext-laws | `8ae72a51090e8216d44f0a563990794896fa30f8` | 2501 | 38.5 MB |
| china-data-laws | `1ca7a3518d115c8dd3b752849ebdfa09878fa1b0` | 3112 | 47.8 MB |

- 候选源总文件数：**5990**
- 候选源总磁盘占用：**95.4 MB**
- 本仓库 `laws/` 收录：4 个官方元数据文件，286914 bytes

## 当前覆盖
- 主法律（OFFICIAL_META）：3 部
- 候选正文（just-laws / lawtext-laws / china-data-laws）：按 bbbs / 文号 / 标题+机关+日期去重后建立 canonical_document_id。

## 候选正文原则
- 候选源只读，不复制整个仓库到 china-law-verified GitHub；
- 本地正文用于发现、定位、版本变化检测、缺失补充，不冒充官方最终依据；
- 正式合同 / 律师意见 / 诉讼仲裁 / 重大交易仍以官方现行有效性核验结果作为最终依据。

## 缺口
- 见 `metadata/business-legal-gaps.json`。
- P0 主法律正文需人工在 flk.npc.gov.cn 浏览器补齐。
