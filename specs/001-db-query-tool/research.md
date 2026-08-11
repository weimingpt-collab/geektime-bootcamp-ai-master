# Research Document: 数据库查询工具

**Feature**: 001-db-query-tool
**Date**: 2025-11-16
**Phase**: 0 - Technology Research & Decisions

## Overview

本文档记录了数据库查询工具实现过程中的技术选型、最佳实践研究和设计决策。所有决策都基于项目宪法的原则和功能需求。

## Technology Stack Decisions

### Backend Framework: FastAPI

**Decision**: 使用 FastAPI 作为后端 Web 框架

**Rationale**:
- **自动化文档**: 自动生成 OpenAPI (Swagger) 文档，方便 API 测试和前端集成
- **Pydantic 集成**: 深度集成 Pydantic，自动进行请求/响应验证和序列化
- **性能优秀**: 基于 Starlette 和 Pydantic，性能接近 Node.js 和 Go
- **类型安全**: 完全支持 Python 类型提示，配合 mypy 实现编译时类型检查
- **异步支持**: 原生支持 async/await，适合 I/O 密集型操作（数据库查询）
- **成熟生态**: 丰富的中间件、依赖注入系统和测试工具

**Alternatives Considered**:
- **Flask**: 更简单但缺乏自动文档和类型验证，需要更多手动配置
- **Django**: 过于重量级，自带 ORM 和认证系统与需求不符
- **Starlette**: FastAPI 基于 Starlette，直接使用 FastAPI 获得更多开箱即用特性

### SQL Parser: sqlglot

**Decision**: 使用 sqlglot 进行 SQL 解析和验证

**Rationale**:
- **纯 Python 实现**: 无需额外系统依赖，易于安装和分发
- **多方言支持**: 支持 PostgreSQL、MySQL 等多种 SQL 方言
- **AST 解析**: 提供完整的抽象语法树，可以精确分析 SQL 语句结构
- **类型安全**: 可以识别 SELECT/INSERT/UPDATE/DELETE 等语句类型
- **SQL 转换**: 支持 SQL 重写（如自动添加 LIMIT 子句）
- **性能良好**: 对于单条查询解析速度 <10ms

**Alternatives Considered**:
- **sqlparse**: 功能较弱，只能做基本的格式化和 tokenization，无法深度分析语句类型
- **pglast (libpg_query)**: 使用 PostgreSQL 官方解析器，但依赖 C 库，安装复杂，且仅支持 PostgreSQL
- **手动正则表达式**: 不可靠，容易被绕过，维护困难

### PostgreSQL Driver: asyncpg

**Decision**: 使用 asyncpg 作为 PostgreSQL 数据库驱动

**Rationale**:
- **异步 I/O**: 原生支持 asyncio，与 FastAPI 异步模型完美配合
- **高性能**: 比 psycopg2/3 快 2-3 倍，使用 Cython 优化
- **类型转换**: 自动处理 PostgreSQL 类型到 Python 类型的转换
- **连接池**: 内置连接池管理，避免频繁建立连接
- **元数据查询**: 支持查询 PostgreSQL 系统表获取 schema 信息

**Alternatives Considered**:
- **psycopg3**: 支持同步和异步，但性能不如 asyncpg，且异步模式较新
- **SQLAlchemy**: ORM 层过重，不需要完整的 ORM 功能，只需执行原始 SQL

### Local Database: SQLite with SQLModel

**Decision**: 使用 SQLite + SQLModel 管理本地数据

**Rationale**:
- **零配置**: SQLite 无需安装和配置，文件即数据库
- **轻量级**: 适合存储少量元数据和连接信息
- **SQLModel 优势**:
  - 基于 Pydantic 和 SQLAlchemy，同时获得类型验证和 ORM 功能
  - 代码更简洁，一个类同时定义 Pydantic 模型和数据库表
  - 自动生成迁移（通过 Alembic）
- **本地存储**: ~/.db_query/db_query.db，用户数据不离开本地机器

**Alternatives Considered**:
- **纯 SQLAlchemy**: 需要分别定义 ORM 模型和 Pydantic 模型，代码冗余
- **JSON 文件**: 缺乏查询能力，数据完整性难以保证
- **Redis**: 过度设计，不需要缓存服务器

### LLM Integration: OpenAI SDK

**Decision**: 使用官方 OpenAI Python SDK 进行自然语言转 SQL

**Rationale**:
- **官方支持**: OpenAI 官方维护，API 稳定可靠
- **异步支持**: 支持 async/await，与 FastAPI 无缝集成
- **流式响应**: 支持 streaming，可以实时返回 LLM 生成的 SQL（未来功能）
- **简单易用**: API 设计清晰，文档完善
- **提示工程**: 可以灵活设计 system prompt 和 user prompt，注入元数据上下文

**Implementation Strategy**:
```python
# Prompt template structure
system_prompt = """
You are a SQL expert. Generate PostgreSQL SELECT queries based on natural language.

Database schema:
{metadata_json}

Rules:
- ONLY generate SELECT statements
- Include column names explicitly (no SELECT *)
- Add appropriate WHERE, ORDER BY, LIMIT clauses
- Return valid PostgreSQL syntax
"""

user_prompt = "User query: {natural_language_input}"
```

**Alternatives Considered**:
- **Langchain**: 过于重量级，包含大量不需要的功能（chains, agents）
- **本地 LLM (Ollama)**: 准确率不如 GPT-4，且需要用户安装额外软件
- **Fine-tuned model**: 成本高，数据准备复杂，OpenAI API 已足够准确

## Frontend Technology Decisions

### React Admin Framework: Refine

**Decision**: 使用 Refine 5 作为 React admin 框架

**Rationale**:
- **开箱即用**: 提供 CRUD 操作的完整脚手架，减少重复代码
- **Data Provider 模式**: 抽象数据层，易于切换后端或添加缓存
- **UI 框架无关**: 可以自由选择 UI 库（Ant Design, Material-UI, Chakra UI）
- **TypeScript 友好**: 完整的类型定义，提供良好的开发体验
- **路由集成**: 与 React Router 深度集成，自动生成 CRUD 路由
- **钩子系统**: 提供丰富的 hooks（useTable, useForm, useShow 等）处理常见场景

**Alternatives Considered**:
- **React Admin**: 功能类似但更固定，定制化难度更高
- **自行构建**: 需要从头实现 CRUD 逻辑、路由、状态管理等，开发时间长

### UI Library: Ant Design

**Decision**: 使用 Ant Design 5 作为 UI 组件库

**Rationale**:
- **Refine 集成**: Refine 对 Ant Design 有一流支持，提供预构建的 Refine-Ant Design 组件
- **企业级**: 组件质量高，适合数据密集型应用
- **Table 组件**: 强大的 Table 组件，支持排序、过滤、分页，完美适配查询结果展示
- **Form 组件**: 丰富的表单组件，适合数据库连接表单
- **中文友好**: 官方中文文档和社区支持

**Alternatives Considered**:
- **Material-UI**: 设计风格偏移动端，不如 Ant Design 适合数据展示
- **Chakra UI**: 组件较简单，缺少复杂的 Table 和 Form 场景支持

### Code Editor: Monaco Editor

**Decision**: 使用 Monaco Editor 作为 SQL 编辑器

**Rationale**:
- **VSCode 引擎**: 与 VSCode 使用相同的编辑器，功能强大
- **语法高亮**: 内置 SQL 语法高亮
- **智能提示**: 可以配置自定义的自动补全（表名、列名）
- **多光标**: 支持多光标编辑、查找替换等高级功能
- **主题支持**: 支持亮色/暗色主题
- **React 集成**: @monaco-editor/react 提供良好的 React 封装

**Alternatives Considered**:
- **CodeMirror**: 更轻量但功能较弱，定制化复杂度高
- **Ace Editor**: 较老旧，社区活跃度低
- **Textarea**: 无法满足语法高亮和自动补全需求

### Build Tool: Vite

**Decision**: 使用 Vite 作为构建工具

**Rationale**:
- **极速开发**: HMR (热模块替换) 速度极快，开发体验好
- **原生 ES Modules**: 利用浏览器原生 ESM，无需打包即可开发
- **TypeScript 支持**: 开箱即用的 TypeScript 支持
- **插件生态**: 丰富的插件系统，React 官方推荐
- **生产构建**: 使用 Rollup 进行优化的生产构建

**Alternatives Considered**:
- **Create React App**: 已过时，构建速度慢，配置不灵活
- **Webpack**: 配置复杂，开发体验不如 Vite

## Architecture Patterns

### Backend Architecture

**Pattern**: Layered Architecture (三层架构)

```
API Layer (FastAPI routers)
    ↓ 调用
Service Layer (Business logic)
    ↓ 调用
Data Layer (SQLModel, asyncpg)
```

**Layers**:

1. **API Layer** (`app/api/v1/`):
   - FastAPI 路由定义
   - 请求验证（Pydantic models）
   - 响应格式化
   - 错误处理

2. **Service Layer** (`app/services/`):
   - 业务逻辑
   - SQL 验证和转换
   - 元数据提取
   - LLM 调用
   - 事务管理

3. **Data Layer** (`app/models/` + `app/database.py`):
   - SQLModel 实体定义
   - 数据库连接管理
   - CRUD 操作

**Benefits**:
- 关注点分离
- 易于测试（可以 mock 任何层）
- 业务逻辑独立于框架

### SQL Validation Strategy

**Strategy**: Parse → Validate → Transform

**Flow**:
```python
1. Parse SQL using sqlglot
   ↓
2. Check statement type (must be SELECT)
   ↓
3. Extract components (FROM, WHERE, LIMIT)
   ↓
4. Transform: Add LIMIT if missing
   ↓
5. Generate modified SQL
   ↓
6. Execute against target database
```

**Security Checks**:
- ✅ Block INSERT/UPDATE/DELETE/DROP/ALTER/CREATE
- ✅ Block multi-statement (SQL injection via `;`)
- ✅ Block dangerous functions (pg_read_file, COPY)
- ✅ Enforce LIMIT clause
- ✅ Timeout mechanism (max 30s query time)

### Metadata Caching Strategy

**Strategy**: Database → Extract → Transform → Cache

**Flow**:
```python
1. Connect to PostgreSQL
   ↓
2. Query system tables:
   - pg_catalog.pg_tables
   - information_schema.columns
   - pg_constraint (for PKs/FKs)
   ↓
3. Transform to JSON structure
   ↓
4. Use LLM to generate summary (optional)
   ↓
5. Store in SQLite with timestamp
   ↓
6. Return cached data for subsequent requests
```

**Cache Invalidation**:
- Manual refresh button in UI
- Auto-refresh after 24 hours
- Invalidate on connection error (stale cache)

### Error Handling Strategy

**Pattern**: Exception Hierarchy

```python
# Custom exceptions
class DBQueryError(Exception):
    """Base exception"""
    pass

class ConnectionError(DBQueryError):
    """Database connection failed"""
    pass

class ValidationError(DBQueryError):
    """SQL validation failed"""
    pass

class QueryExecutionError(DBQueryError):
    """Query execution failed"""
    pass
```

**Error Response Format** (camelCase per constitution):
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Only SELECT statements are allowed",
    "details": {
      "statementType": "INSERT",
      "line": 1,
      "column": 0
    }
  }
}
```

## API Design

### RESTful Principles

**Resource-based URLs**:
- `/api/v1/dbs` - Database collection
- `/api/v1/dbs/{name}` - Single database
- `/api/v1/dbs/{name}/query` - Query execution (sub-resource)

**HTTP Methods Mapping**:
- `GET /api/v1/dbs` - List all databases
- `PUT /api/v1/dbs/{name}` - Create/Update database (idempotent)
- `GET /api/v1/dbs/{name}` - Get database metadata
- `DELETE /api/v1/dbs/{name}` - Delete database connection
- `POST /api/v1/dbs/{name}/query` - Execute SQL query
- `POST /api/v1/dbs/{name}/query/natural` - Natural language query

**Rationale for PUT vs POST**:
- 使用 `PUT /api/v1/dbs/{name}` 而不是 `POST /api/v1/dbs` 因为：
  - 客户端指定资源名称（数据库名）
  - 幂等性：多次 PUT 相同名称不会创建重复资源
  - 符合 REST 最佳实践

### CORS Configuration

**Decision**: Allow all origins

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Rationale**:
- 本地工具，前端和后端运行在不同端口
- 无认证需求，无安全风险
- 简化开发，无需配置特定 origins

## Testing Strategy

### Backend Testing Layers

1. **Unit Tests** (`tests/unit/`):
   - SQL validator logic
   - Metadata extraction
   - Pydantic model serialization
   - Coverage target: >90%

2. **Integration Tests** (`tests/integration/`):
   - API endpoints with test database
   - Database connection flow
   - Query execution flow
   - Coverage target: >80%

3. **Contract Tests** (`tests/contract/`):
   - API response format validation
   - camelCase field name verification
   - Error response structure

### Frontend Testing Strategy

1. **Component Tests**:
   - SqlEditor component
   - ResultTable component
   - MetadataTree component

2. **Integration Tests**:
   - Full query execution flow
   - Database connection form
   - Natural language input

3. **Type Safety**:
   - TypeScript compiler as first line of defense
   - Runtime validation for API responses

### Test Data

**Mock PostgreSQL Database**:
```sql
-- Test database schema
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    total DECIMAL(10, 2),
    status VARCHAR(20)
);
```

## Performance Optimizations

### Backend

1. **Connection Pooling**:
   - asyncpg connection pool (min=2, max=10)
   - SQLite connection pool (singleton)

2. **Metadata Caching**:
   - Cache in SQLite to avoid repeated system table queries
   - In-memory cache (LRU) for frequently accessed metadata

3. **Query Timeout**:
   - Set statement_timeout in PostgreSQL session
   - Prevent long-running queries from blocking

### Frontend

1. **Code Splitting**:
   - Lazy load Monaco Editor (large bundle)
   - Lazy load query result pages

2. **Virtual Scrolling**:
   - Use Ant Design Table's virtual scrolling for large result sets

3. **Debouncing**:
   - Debounce natural language input (500ms)
   - Debounce SQL editor autocomplete (300ms)

## Security Considerations

### SQL Injection Prevention

1. **sqlglot Parsing**: Reject malformed SQL
2. **Statement Type Check**: Only SELECT allowed
3. **Function Blacklist**: Block dangerous functions
4. **No Dynamic SQL**: Use parameterized queries for internal SQLite

### Data Privacy

1. **Local Storage**: All data stored in ~/.db_query/
2. **No Telemetry**: No data sent to external services except OpenAI API
3. **API Key Security**: OPENAI_API_KEY from environment variable, never logged

### Environment Configuration

**Environment Variables**:
```bash
OPENAI_API_KEY=sk-...           # OpenAI API key
DB_QUERY_DATA_DIR=~/.db_query  # Optional: custom data directory
LOG_LEVEL=INFO                  # Logging level
```

## Development Workflow

### Backend Setup

```bash
cd w2/db_query/backend

# Install uv if not installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -e ".[dev]"

# Run tests
pytest

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd w2/db_query/frontend

# Install dependencies
npm install  # or yarn install

# Run dev server
npm run dev  # defaults to port 5173

# Run tests
npm test

# Build for production
npm run build
```

## Deployment Considerations

虽然当前是开发工具，但考虑未来可能的部署需求：

### Local Tool Mode (Current)
- Backend: `uvicorn app.main:app --host 127.0.0.1 --port 8000`
- Frontend: `npm run preview` or serve `dist/` folder
- Access: http://localhost:5173

### Packaged Application (Future)
- 使用 PyInstaller 打包后端为独立可执行文件
- 使用 Electron 或 Tauri 打包前端
- 一键启动，无需安装 Python 或 Node.js

### Server Deployment (Future)
- Backend: Docker container with uvicorn
- Frontend: Static files served by Nginx
- Add authentication layer (OAuth2)
- PostgreSQL for user data instead of SQLite

## Risk Mitigation

### Risk: LLM API Failure
- **Mitigation**: Graceful degradation, show error message, fallback to manual SQL

### Risk: Large Result Sets
- **Mitigation**: Enforce LIMIT 1000, pagination, export to file option

### Risk: Database Connection Leaks
- **Mitigation**: Connection pool with timeout, connection health checks

### Risk: SQL Parser Bugs
- **Mitigation**: Comprehensive test suite, additional regex checks for critical patterns

## Documentation Requirements

### API Documentation
- ✅ Auto-generated OpenAPI docs via FastAPI (http://localhost:8000/docs)

### User Documentation
- README.md with setup instructions
- Quick start guide in quickstart.md

### Code Documentation
- ✅ Python: Docstrings for all public functions/classes
- ✅ TypeScript: JSDoc comments for complex logic
- ✅ Type annotations serve as inline documentation

## Conclusion

所有技术选型都基于以下原则：
- ✅ 符合项目宪法要求（类型安全、Pydantic、camelCase）
- ✅ 成熟稳定的技术栈
- ✅ 良好的开发体验
- ✅ 适合项目规模（中小型工具）
- ✅ 易于测试和维护

---

## Query Result Export (Story 4 Redesign)

> 本节为 `/speckit.plan` 针对 Story 4（查询结果导出）的重新设计研究，其他故事（US1/US2/US3）方案不变。

### Problem Statement

现有实现把导出完全放在前端（`frontend/src/pages/Home.tsx` 的 `handleExportCSV` / `handleExportJSON`），存在三个硬伤：

1. **只能导出已加载到浏览器内存的行**：当前查询接口受 `LIMIT 1000` 限制，前端拿到的 `queryResult.rows` 至多 1000 行。Spec Story 4 场景 3 要求"超大结果集（>10000 行）分批导出"，但前端根本拿不到超过 LIMIT 的数据，更别说 10000 行。
2. **大数据集阻塞 UI 线程**：现有 `exportToCSV` 用同步循环拼字符串，1 万行时主线程卡顿明显，违反 SC-009（5 秒内完成）和"不出现卡顿"的隐性要求。
3. **tasks.md 标记矛盾**：T070/T071 标记为 `[X]`（已完成）但 `backend/app/services/export.py` 文件不存在；T072/T073 标记为"前端代替"而跳过。后端能力实际为零。

### Decision: Hybrid Export (Frontend for small + Backend streaming for large)

**Decision**: 采用**前后端混合**策略：

| 场景 | 路径 | 触发条件 |
|------|------|---------|
| 小结果集（≤ 当前已加载行数） | 前端 `Blob` 下载 | 默认，无需额外请求 |
| 大结果集（> LIMIT 1000 或用户显式选择"导出全部") | 后端 `GET /api/v1/dbs/{name}/query/export` 流式响应 | 行数超阈值或用户确认 |

**Rationale**:
- 小数据集走前端：零网络往返、即时下载、实现简单。现有 `handleExportCSV`/`handleExportJSON` 保留但需重构为异步 + Web Worker 友好。
- 大数据集走后端：后端可重新执行 SQL（不强制 LIMIT），用 `StreamingResponse` 分块输出，避免 OOM。这是覆盖 Story 4 场景 3 的唯一可行方式。

**Alternatives considered**:
- **纯前端导出全部**：需要前端绕过 LIMIT 重新查询，本质上还是调后端，且把"是否拉取全量"决策推给前端，逻辑更混乱。
- **纯后端导出**：即使是 50 行的小结果也走后端，增加延迟（多一次 SQL 执行），UX 变差。
- **预生成 + 轮询下载**：异步任务模式（提交导出任务 → 轮询状态 → 下载）。对本地单用户工具是过度设计，放弃。

### Backend Export Endpoint Design

**Route**: `GET /api/v1/dbs/{name}/query/export`

**Query Parameters**:
- `sql` (string, required): 要导出的 SELECT 查询（必须通过 sqlglot 校验，仅 SELECT）
- `format` (enum: `csv` | `json`, required): 导出格式
- `limit` (int, optional, default: `100000`): 最大导出行数上限（安全护栏，默认 10 万）
- `delimiter` (string, optional, default: `,`): CSV 分隔符（仅 `format=csv`）

**Response**:
- `format=csv`: `text/csv; charset=utf-8`，带 `Content-Disposition: attachment; filename="{name}_{timestamp}.csv"`
- `format=json`: `application/json; charset=utf-8`，文件名后缀 `.json`
- **流式输出**：用 FastAPI `StreamingResponse` + async generator，每次 yield 一批行（约 1000 行/chunk），避免一次性把全部行加载进内存。

**SQL Safety**:
- 复用 `sql_validator.validate_and_transform_sql`，仅允许 SELECT
- **不自动追加 `LIMIT 1000`**（前端默认查询会加，但导出场景需要用户指定的 `limit` 参数），改用 `limit` 查询参数作为行数上限，通过 sqlglot 改写 AST 注入 `LIMIT {limit}`

**Streaming Implementation**:
```python
# 伪代码（实际实现见 tasks）
async def export_csv_generator(adapter, sql, max_rows):
    yield csv_header  # BOM + 列名
    async for batch in adapter.stream_query(sql, batch_size=1000, max_rows=max_rows):
        yield rows_to_csv(batch)
```

### Frontend Export UX Design

**触发点**：结果区现有的 `EXPORT CSV` / `EXPORT JSON` 按钮保持，但行为分叉：

1. **当前结果行数 ≤ 阈值（默认 10000）**：
   - 直接前端 `Blob` 下载（现有逻辑，重构为 async）
2. **当前结果行数 > 阈值 或 用户选"导出全部"**：
   - 弹 `Modal.confirm`：提示"将导出最多 N 行，可能耗时较长"
   - 用户确认后，构造 `GET .../query/export?sql=...&format=...&limit=...` URL
   - 用隐藏 `<a download>` 或 `window.location` 触发浏览器原生下载（流式响应浏览器会直接存盘，不占内存）

**新增 UI 元素**：在现有两个导出按钮旁加一个 `EXPORT ALL (CSV)` 按钮（或下拉菜单项），明确表示"绕过 1000 行限制导出全部"。

### Large Result Set Guardrails

- **前端阈值**：`queryResult.rowCount > 10000` 时弹确认框（现有 `handleExportCSV` 已有此逻辑，保留）
- **后端硬上限**：`limit` 参数最大 100000，超过则 400 错误
- **超时**：后端流式导出单次最长 60 秒（与 `ConnectionConfig.command_timeout` 对齐），超时则中断并返回 504
- **内存**：后端用 cursor 流式 fetch（`asyncpg` 的 `fetch` 或 `aiomysql` 的 `SSCursor`），不一次性 `fetchall`

### CSV Format Details

- **UTF-8 with BOM** (`\ufeff` 前缀)：确保 Excel 正确识别中文（Spec SC-006 要求处理多字节字符）
- **引用规则**：字段含 `,` `"` `\n` 时用 `"..."` 包裹，内部 `"` 转义为 `""`（RFC 4180）
- **null 值**：输出为空字符串（CSV 无 null 概念）
- **datetime**：ISO 8601 格式

### JSON Format Details

- **格式**：JSON Array of objects（`[{...}, {...}]`），非 NDJSON
- **编码**：UTF-8，无 BOM
- **null 值**：输出为 JSON `null`
- **datetime**：ISO 8601 字符串

### Testing Strategy

**Backend**:
- 单元测试：CSV/JSON 序列化函数（含特殊字符、null、datetime、emoji）
- 集成测试：`/query/export` endpoint，小结果 + 大结果（mock adapter 的 stream）
- 安全测试：非 SELECT 被拒、`limit` 超上限被拒、超时中断

**Frontend**:
- 组件测试：小结果走前端 Blob、大结果触发确认 + 后端下载
- E2E（手动）：导出 1000 行 CSV，Excel 打开验证 BOM 和中文

### Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| 后端流式导出 OOM | cursor 流式 fetch + 小 chunk yield |
| 恶意大 LIMIT 拖垮 DB | 硬上限 100000 + 60 秒超时 |
| CSV 注入（字段以 `=` `+` `-` `@` 开头会被 Excel 当公式） | CSV 单元格前缀 `'` 或用 `"` 包裹（RFC 4180 已覆盖大部分，额外加公式注入防护） |
| 浏览器下载中断 | 后端设 `Content-Length`（可行时）或 `Transfer-Encoding: chunked` |


无需进一步研究，可以直接进入 Phase 1 设计阶段。
