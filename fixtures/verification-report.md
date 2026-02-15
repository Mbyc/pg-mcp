# pg-mcp Fixtures 数据库验证报告

- **日期**: 2026-02-14
- **验证方式**: Docker Compose 启动 `postgres:16`，在 `pgmcp-postgres` 容器内通过 `psql` 执行 `./w5/pg-mcp/fixtures/verify.sql`
- **数据库**:
  - `pgmcp_small`
  - `pgmcp_medium`
  - `pgmcp_large`

## 1. 环境与执行命令

- **启动 Postgres**:
  - `docker compose up -d db`
- **初始化导入**:
  - `docker compose up init`
- **验证脚本**:
  - `docker compose exec db psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f /fixtures/verify.sql`

## 2. 验证结果摘要

### 2.1 pgmcp_small

- **表数量（public, BASE TABLE）**: 3
- **视图数量（public）**: 1
- **数据行数**:
  - `users`: 2
  - `products`: 2
  - `orders`: 2
  - `order_summary`(view): 2

### 2.2 pgmcp_medium

- **表数量（public, BASE TABLE）**: 4
- **视图数量（public）**: 1
- **物化视图数量（public）**: 1
- **类型存在性**:
  - `email_address`（domain）: 存在 (count=1)
  - `ticket_status`（enum）: 存在 (count=1)
  - `address_type`（composite）: 存在 (count=1)
- **数据行数**:
  - `customers`: 2
  - `subscriptions`: 2
  - `support_tickets`: 3
  - `v_active_subscriptions`(view): 2
  - `mv_customer_stats`(mview): 2

### 2.3 pgmcp_large

- **表数量（public, BASE TABLE）**: 17
- **视图数量（public）**: 1
- **物化视图数量（public）**: 1
- **类型存在性**:
  - `nonempty_text`（domain）: 存在 (count=1)
  - `incident_severity`（enum）: 存在 (count=1)
  - `audit_action`（enum）: 存在 (count=1)
- **数据量检查（关键表）**:
  - `accounts`: 20
  - `users`: 1000
  - `metrics`: 200
  - `metric_points`: 20000
  - `audit_events`: 5000
  - `incidents`: 150
  - `v_recent_incidents`(view): 150
  - `mv_daily_usage`(mview): 20

## 3. 修复记录

- **docker-compose init 脚本变量替换问题**:
  - 原因：Compose 会对 `$name` 做环境变量插值，导致空字符串。
  - 修复：在 `docker-compose.yml` 中使用 `$$name` 传递给容器 shell。

- **large/setup.sql 类型错误**:
  - 错误：`CURRENT_DATE - (a.id % 90)` 触发 `date - bigint` 不支持。
  - 修复：改为 `CURRENT_DATE - ((a.id % 90)::int)`。

## 4. 结论

- **结论**: 三套数据库已成功创建并导入，关键 schema 元素（table/view/mview/domain/enum/composite）与数据量均符合 fixtures 设计目标，可用于后续自然语言查询与 pg-mcp 端到端测试。
