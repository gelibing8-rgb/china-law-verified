# 正文投放目录

如通过获准渠道取得可与官方页面核对的 .docx，可放在这里；不要绕过页面下载限制。
文件名须与 laws/<name>.md 同名，例如：

  company_law_2024.docx
  civil_code.docx
  labor_contract_law.docx

然后执行：
  python3 scripts/ingest_official_docs.py          # 预演
  python3 scripts/ingest_official_docs.py --apply  # 写入待复核正文

脚本要求按法律标题精确匹配官方 flfgDetails 结构快照，并检查条号集合、空条、重复条号及法库占位行；无匹配快照或结构不完整即拒绝写入。`--apply` 会同步正文哈希，但不会记录人工核验时间或提升验证层级。
结构匹配不证明文件来源真实性，也不证明正文逐字等同官方原文。即使 `--apply` 成功，`verification_status` 仍保持 `needs_recheck`；必须由人工核对官方页面来源和正文后，才能按 `laws/README.md` 流程升级。

本目录内容不入库（见 .gitignore），避免把官方文档提交到公开仓库。
