# V4 Topic Schema

所有专题统一使用 `manifest.json`，包括 `topic`、法规清单、案例清单、统计、校验、缺口和更新状态。

## 状态边界

- `verification_status` 表示数据可信等级，不表示法律效力。
- `legal_status` 只用于法规文件。
- `reference_status` 只用于案例，不使用 `legal_status`。
- `VERIFIED` 仅在已逐字核验官方全文时使用；候选库全文统一为 `CANDIDATE`。
- 默认检索只纳入 `relation_strength=core|direct`；`related`、`pending_relation` 不进入默认专题检索。

V4 生成器只读取本地候选库和现有 `laws/` 元数据，不访问政府/法院网站，不运行候选库自带爬虫，不复制候选正文。
