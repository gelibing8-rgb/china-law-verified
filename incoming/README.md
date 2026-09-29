# 正文投放目录

把从 https://flk.npc.gov.cn 详情页手动下载的官方 .docx 放在这里，
文件名须与 laws/<name>.md 同名，例如：

  company_law_2024.docx
  civil_code.docx
  labor_contract_law.docx

然后执行：
  python3 scripts/ingest_official_docs.py          # 预演
  python3 scripts/ingest_official_docs.py --apply  # 正式入库

脚本会比对官方 flfgDetails 结构树的条号集合，
不完整则拒绝写入且不升格 verification_status。

本目录内容不入库（见 .gitignore），避免把官方文档提交到公开仓库。
