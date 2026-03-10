# pg-mcp

基于 FastMCP + Asyncpg 的 PostgreSQL MCP 服务：将自然语言查询转为安全的只读 SQL，并可执行返回结果。

## 功能特性

- 多数据库连接与 Schema 缓存
- LLM 生成 SQL（只读校验）
- 结果执行与可选语义校验
- 一次自动修复（执行失败时）

## 环境准备

- Python 3.10+
- PostgreSQL
- OpenAI 兼容 API（默认 `gpt-5-mini`）

## 配置

设置环境变量（示例）：

```bash
export OPENAI_API_KEY=your_key
export OPENAI_BASE_URL=https://api.openai.com/v1
export PG_MCP_DATABASES='[{"name":"pgmcp_small","dsn":"postgresql://postgres:zycx@localhost:5432/pgmcp_small"}]'
export PG_MCP_DEFAULT_DATABASE=pgmcp_small
```

更多配置项见 `pg_mcp/config.py`。

## 运行

```bash
uvx --refresh --from . pg-mcp
```

## MCP 工具

- `health`：健康检查与配置摘要
- `query`：自然语言查询（支持 `sql_only` / `execute`）

## 目录结构

```
pg_mcp/
  db/
  llm/
  models/
  services/
  sql/
```

## License

MIT
