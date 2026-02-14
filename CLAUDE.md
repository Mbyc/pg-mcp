# CLAUDE.md（pg-mcp 工程规范）

本文件用于约束 `./w5/pg-mcp` 的实现质量：代码需符合 **Python best practice / idiomatic Python**，遵循 **SOLID/DRY**，具备高代码质量、高测试质量与良好性能。

## 1. 总体要求

- **唯一对外 MCP tool**：只提供 `query`（与 `0001/0002` 文档保持一致）。
- **只读强约束**：任何情况下不得执行写操作（DDL/DML/会话变更/危险函数等）。
- **默认安全配置**：必须有超时、行数限制、禁多语句、危险函数黑名单。
- **可追溯**：每个请求必须有结构化日志/审计字段（不泄露敏感信息）。

## 2. Python 代码风格与工程实践

- **目标版本**：Python 3.11+（如无明确约束，默认以 3.11 为基线）。
- **类型标注**：
  - 所有公共函数/方法必须写类型标注。
  - 关键数据结构使用 `pydantic` models 或 `dataclasses`（二选一，优先 pydantic 用于 I/O）。
- **异常处理**：
  - 定义项目内的领域异常（如 `SqlValidationError`, `SchemaNotLoadedError`）。
  - 不允许吞异常；对外返回需脱敏、对内日志需可诊断。
- **异步规范**：
  - 所有 DB 与网络调用（OpenAI）必须 async。
  - 禁止在事件循环中执行阻塞 I/O。

## 3. 架构与设计原则（SOLID/DRY）

- **单一职责（SRP）**：
  - `QueryService` 只负责 orchestrate，不直接拼 SQL、不直接写 catalog 查询。
  - `SchemaIntrospector` 只负责 schema 抽取。
  - `SqlSafetyGate` 只负责 SQL 解析与安全校验。
  - `Executor` 只负责执行与结果整形（含 statement_timeout/limit 等）。
  - `OpenAIClient` 只负责模型调用与结构化输出解析。

- **依赖倒置（DIP）**：
  - 业务逻辑依赖抽象协议（Protocol），便于 mock：
    - `LLMClientProtocol`
    - `DatabaseExecutorProtocol`
    - `SchemaProviderProtocol`

- **DRY**：
  - 统一的 SQL 校验入口；禁止在多个地方散落字符串检查。
  - 统一的配置读取与默认值 clamp（例如 `max_rows`）。

## 4. 性能要求

- **连接池**：使用 `asyncpg` pool；建议按数据库延迟初始化。
- **Schema cache**：
  - 启动加载 + 后台异步刷新。
  - 大 schema 必须做摘要/相关性检索，避免把全量 schema 直接塞进 prompt。
- **查询执行**：
  - 默认 `statement_timeout`。
  - 默认限制返回行数。
  - 避免无谓的全表扫描；优先 EXPLAIN 做可执行性验证。

## 5. 安全要求（必须）

- **SQL 只读白名单**：只允许 `SELECT` 与 `WITH ... SELECT`。
- **禁止多语句**：解析为多个 statement 直接拒绝。
- **危险函数黑名单**：至少包含 `pg_sleep`, `pg_terminate_backend`, `pg_cancel_backend`，并支持配置扩展。
- **敏感信息保护**：
  - 日志与返回中不得出现密码/完整 DSN。
  - 结果集必须截断。
- **最小权限账户**：文档与示例配置应默认只读账号。

## 6. 测试质量要求

- **测试框架**：建议 `pytest` + `pytest-asyncio`。
- **覆盖重点**（至少）：
  - `SqlSafetyGate`：
    - 允许 SELECT/CTE
    - 拒绝 DDL/DML/COPY/CALL/DO/SET
    - 拒绝多语句
    - 拒绝危险函数（含大小写/引号/schema-qualified 形式）
  - `Schema`：
    - 过滤系统 schema 生效
    - allowlist/blocklist 生效
  - `LLM`：
    - 结构化输出解析失败可重试/可报错
    - 澄清问题路径（`clarifying_questions` 非空）
  - `Executor`：
    - statement_timeout 被设置
    - max_rows 截断生效
  - `QueryService`：端到端 orchestrate（使用 mock LLM + mock DB）。

- **测试分层**：
  - 单元测试：纯逻辑/AST 校验/解析。
  - 集成测试（可选但建议）：连接本地 Postgres fixtures，验证 schema 抽取与只读执行。

## 7. 代码组织建议（与设计文档对齐）

建议保持清晰边界：

- `pg_mcp/server.py`：FastMCP server + tool 注册
- `pg_mcp/models/`：pydantic 请求/响应模型
- `pg_mcp/config.py`：pydantic settings
- `pg_mcp/db/`：pool、schema 抽取、schema cache
- `pg_mcp/sql/`：SQLGlot 安全校验
- `pg_mcp/llm/`：OpenAI client、prompt、意义校验
- `pg_mcp/services/`：QueryService orchestrator

## 8. PR/提交要求

- 每个 PR 必须满足：
  - 通过全部测试
  - 无明显类型错误
  - 不引入未使用依赖
  - 关键路径（SQL 校验、执行限制）有对应测试

## 9. 禁止事项

- 禁止添加除 `query` 外的 MCP tool。
- 禁止执行任何写 SQL。
- 禁止在日志/返回中输出敏感连接信息。
- 禁止把 OpenAI Key 写入代码或提交到仓库。
