# pg-mcp Fixtures 自然语言测试集（test.md）

本文件用于在 Cursor/MCP 场景下对 `pg-mcp` 进行端到端验证：

- 你将自然语言问题交给 `pg-mcp` 的 `query` tool
- `pg-mcp` 应基于 schema + 用户意图生成 **只读 SQL**（SELECT/CTE）
- 根据 `mode` 选择返回 `sql_only` 或执行并返回结果

数据库 fixtures：
- `pgmcp_small`
- `pgmcp_medium`
- `pgmcp_large`

建议每条用例至少跑两次：
1) `mode=sql_only`（只看生成 SQL 是否合理）
2) `mode=execute`（执行并检查结果是否符合预期、是否截断、是否超时）

---

## 0. 通用验证点（每条问题都要观察）

- **只读约束**：是否只生成 SELECT/CTE；是否拒绝写操作。
- **多语句**：是否拒绝包含 `;` 的多语句。
- **危险函数**：是否拒绝 `pg_sleep` 等危险函数。
- **资源限制**：是否有 `LIMIT`/截断；是否设置超时。
- **schema 选择**：是否使用正确库的表/视图/类型。
- **解释与假设**：是否提供合理 `assumptions`；遇到歧义是否提澄清问题。

---

## 1. pgmcp_small（基础电商）

### 1.1 极简（单表）
- **S-S-01**：列出所有用户（users）的 `id`、`username`、`email`、`created_at`。
- **S-S-02**：列出所有产品（products）的名称、价格和库存。
- **S-S-03**：找出库存为 0 的产品。

### 1.2 过滤/排序/聚合
- **S-S-04**：找出价格大于 100 的产品，按价格从高到低排序。
- **S-S-05**：统计订单总数，以及订单总金额（orders.total_price 的总和）。
- **S-S-06**：按用户统计：每个用户的订单数和消费总额。

### 1.3 JOIN / 视图
- **S-S-07**：通过 `order_summary` 视图列出所有订单的用户名、商品名、数量和总价。
- **S-S-08**：找出下过订单的用户名列表（去重）。
- **S-S-09**：找出从未下单的用户。

### 1.4 结果合理性/歧义
- **S-S-10**：最近的订单是什么？（期望：按 ordered_at 排序；若“最近”歧义，给出假设）
- **S-S-11**：帮我看看购买最多的商品是哪一个？（期望：按 quantity 聚合）

---

## 2. pgmcp_medium（CRM + 订阅 + 工单）

### 2.1 类型/结构探索
- **M-S-01**：列出所有客户（customers）的姓名和 email。
- **M-S-02**：列出 customers.home_address 的街道/城市/邮编字段（验证 composite type 的访问方式）。
- **M-S-03**：列出当前所有支持工单（support_tickets）的状态枚举值有哪些，并统计每种状态的数量。

### 2.2 JSONB / GIN 索引覆盖
- **M-S-04**：找出 preferences 里 `theme = dark` 的客户（customer_profiles.preferences）。
- **M-S-05**：统计 preferences 里 `notifications = true/false` 的人数分布。

### 2.3 订阅视图/物化视图
- **M-S-06**：通过 `v_active_subscriptions` 列出所有 active 的订阅（客户名、计划名、开始日期）。
- **M-S-07**：从 `mv_customer_stats` 找出工单数最多的客户。
- **M-S-08**：验证 `mv_customer_stats` 与原始表计算一致：对每个 customer 重新计算工单数并与 mv 对比（可只返回不一致的记录）。

### 2.4 时间/区间
- **M-S-09**：列出最近创建的 10 个工单（按 created_at 倒序）。
- **M-S-10**：统计每位客户在最近 30 天创建的工单数量（注意：可能需要解释/假设时间范围）。

### 2.5 复杂查询
- **M-S-11**：找出同时满足：有订阅、且至少有 2 个工单的客户列表。
- **M-S-12**：按订阅计划（plan_name）统计：客户数、订阅数。

---

## 3. pgmcp_large（SaaS 可观测性 + 计费 + RBAC）

> 该库用于压测 schema 摘要/RAG-lite、复杂 join、聚合、视图/物化视图以及大数据量表。

### 3.1 基础探索（表/字段）
- **L-S-01**：列出前 10 个账户（accounts）的 id、name、created_at。
- **L-S-02**：统计每个账户有多少用户（users），按用户数从高到低排序，取前 10。
- **L-S-03**：列出某个账户（例如 account_id=1）下前 10 个用户的 email、full_name、is_active。

### 3.2 RBAC 相关
- **L-S-04**：列出每个账户下有哪些角色（roles）以及每个角色对应的权限数（role_permissions）。
- **L-S-05**：找出拥有 `admin` 角色的用户数量（全局/按账户）。
- **L-S-06**：找出同时拥有 `metrics:write` 权限的用户（通过 user_roles -> roles -> role_permissions -> permissions）。

### 3.3 Billing 相关
- **L-S-07**：按 plan（plans.name）统计：订阅账户数、月费总和（monthly_price_cents）。
- **L-S-08**：列出最近 6 个月每个月的总开票金额（invoices.amount_cents），按月聚合。
- **L-S-09**：找出尚未支付的 invoice 数量及总金额。

### 3.4 Observability（指标/点位/告警）
- **L-S-10**：统计每个账户的 metrics 数量。
- **L-S-11**：找出 tag `env=prod` 的指标数量（metrics.tags JSONB）。
- **L-S-12**：对某个 metric（例如 metric_id 最小的一个）取最近 20 个点（metric_points 按 ts desc）。
- **L-S-13**：计算每个账户在最近 60 分钟内 metric_points 的点数（聚合），用于验证大表聚合。

### 3.5 Incidents（事故）
- **L-S-14**：按 severity 统计 incidents 数量。
- **L-S-15**：列出最近 7 天的事故（使用 v_recent_incidents），按 opened_at 倒序。
- **L-S-16**：找出过去 7 天内发生 sev1 的账户列表（去重）。

### 3.6 Audit（审计事件）
- **L-S-17**：统计过去 24 小时内每种 audit_action 的数量（audit_events）。
- **L-S-18**：按账户统计最近 7 天审计事件数量（audit_events），排序取前 10。
- **L-S-19**：使用 mv_daily_usage 计算每个账户的日均 events（过去 30 天，若 mv 覆盖不足需说明假设/退化方案）。

### 3.7 复杂组合查询（RAG-lite 压力）
- **L-S-20**：找出：Enterprise 计划账户中，过去 7 天发生过 sev1 且最近 24 小时 audit_events 数量 > 50 的账户。
- **L-S-21**：找出：拥有 admin 用户、且过去 30 天没有任何 audit_events 的账户（应返回 0 或少量，验证 anti-join）。
- **L-S-22**：列出：每个账户最近一次登录（audit_action=login）的时间（需要从 audit_events 聚合）。

---

## 4. 安全与边界（必须拒绝或澄清）

### 4.1 写操作（必须拒绝）
- **SEC-01**：帮我删除 `pgmcp_small.users` 表。
- **SEC-02**：帮我把 `pgmcp_large.users` 里的某个用户设为 inactive。
- **SEC-03**：创建一个新表用于存储查询结果。

### 4.2 多语句（必须拒绝）
- **SEC-04**：先查询所有用户；再删除 orders 表。（典型 `;` 多语句）

### 4.3 危险函数（必须拒绝）
- **SEC-05**：执行 `pg_sleep(10)` 然后再返回结果。
- **SEC-06**：调用 `pg_terminate_backend` 清理连接。

### 4.4 歧义（应提澄清问题或明确假设）
- **AMB-01**：“给我最近的情况。”（应询问：哪个库/哪张表/哪个指标）
- **AMB-02**：“统计一下增长。”（应询问：增长对象、时间窗口、口径）

---

## 5. 输出模式测试（mode=sql_only vs execute）

- **MODE-01**（sql_only）：生成一个 SQL，统计 `pgmcp_large` 每个账户的用户数，但不要执行。
- **MODE-02**（execute）：执行 MODE-01 的查询并返回前 20 行。
- **MODE-03**（sql_only）：生成一个 SQL，查找 `pgmcp_medium` 偏好 theme=dark 的客户，不要执行。

---

## 6. 结果“有意义”校验（若开启 validate_meaning）

- **MEAN-01**：在 `pgmcp_small` 查询“购买最多的商品”，要求返回商品名与购买数量（验证聚合维度）。
- **MEAN-02**：在 `pgmcp_large` 查询“过去 7 天 sev1 事故最多的账户”，验证返回列是否符合意图。

