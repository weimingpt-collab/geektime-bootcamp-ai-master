# Implementation Plan: 数据库查询工具

**Branch**: `001-db-query-tool` | **Date**: 2025-11-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-db-query-tool/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

构建一个数据库查询工具，允许用户添加PostgreSQL数据库连接，查看数据库元数据，执行SQL查询（仅SELECT），并通过自然语言生成SQL。系统使用FastAPI后端和React+Refine前端，数据存储在本地SQLite数据库中，支持查询结果导出。

技术方案：

- 后端：Python 3.12+ with FastAPI, sqlglot for SQL parsing, OpenAI SDK for NL2SQL
- 前端：React 18 with TypeScript, Refine 5, Ant Design, Monaco Editor for SQL editing
- 存储：SQLite (本地) for connections/metadata, PostgreSQL (remote) for querying
- 安全：sqlglot验证SQL，仅允许SELECT，自动添加LIMIT 1000

**数据导出（Story 4）重新设计**（2026-08-07 更新，详见 [research.md](./research.md#query-result-export-story-4-redesign)）：

- **混合策略**：小结果集（≤ 10000 行）走前端 `Blob` 即时下载；大结果集走新增的后端流式导出 endpoint `GET /api/v1/dbs/{name}/query/export`
- **后端流式导出**：FastAPI `StreamingResponse` + cursor 流式 fetch，避免 OOM；支持 CSV（UTF-8 BOM）和 JSON Array 两种格式
- **安全护栏**：仅 SELECT、`limit` 参数硬上限 100000、60 秒超时、CSV 公式注入防护
- **前端 UX**：现有 `EXPORT CSV/JSON` 按钮保留（小结果），新增 `EXPORT ALL` 触发后端流式下载（大结果，带确认弹窗）

## Technical Context

**Language/Version**:

- Backend: Python 3.12+
- Frontend: TypeScript 5.0+ (React 19+)

**Primary Dependencies**:

- Backend: FastAPI 0.104+, Pydantic v2, sqlglot, OpenAI SDK, asyncpg (PostgreSQL driver), SQLAlchemy/SQLModel (SQLite ORM)
- Frontend: React 19, Refine 5, Ant Design 5, Monaco Editor, Tailwind CSS 4, Vite

**Storage**:

- Local: SQLite (~/.db_query/db_query.db) for database connections and metadata cache
- Remote: PostgreSQL (user-provided) for query execution

**Testing**:

- Backend: pytest, pytest-asyncio, httpx (for FastAPI testing)
- Frontend: Vitest, React Testing Library

**Target Platform**:

- Backend: Cross-platform (Linux/macOS/Windows), runs as local web server
- Frontend: Modern browsers (Chrome, Firefox, Safari, Edge)

**Project Type**: Web application (frontend + backend)

**Performance Goals**:

- Metadata fetch: <5 seconds for typical database (100 tables)
- Query execution: <3 seconds for simple SELECT with <1000 rows
- Natural language to SQL: <10 seconds (LLM API call)
- UI responsiveness: <100ms for user interactions

**Constraints**:

- No authentication required (local tool)
- SQL safety: Only SELECT statements allowed
- Result set limit: Auto-apply LIMIT 1000 if not specified
- Local storage: All connections stored in ~/.db_query/
- CORS: Backend must allow all origins for local development

**Scale/Scope**:

- Support: 5-10 concurrent database connections
- Metadata cache: Up to 1000 tables per database
- Query history: Store last 50 queries
- Result display: Handle up to 10,000 rows in UI (with pagination)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ I. Ergonomic Python with Strict Typing

- **Compliance**: All backend code will use Python 3.12+ with full type annotations
- **Implementation**: Use `typing` module, type hints on all functions/methods/classes
- **Validation**: mypy type checking in CI/CD

### ✅ II. Pydantic for Data Models

- **Compliance**: All API models and configuration use Pydantic BaseModel
- **Implementation**:
  - Request/Response models: Pydantic BaseModel
  - Database models: SQLModel (Pydantic + SQLAlchemy)
  - Config: Pydantic Settings
- **Validation**: Automatic via Pydantic validators

### ✅ III. camelCase JSON API Convention

- **Compliance**: All API responses use camelCase field names
- **Implementation**: Configure Pydantic `alias_generator=to_camel` globally
- **Validation**: API contract tests verify camelCase format

### ✅ IV. TypeScript with Strict Type Safety

- **Compliance**: All frontend code uses TypeScript with `strict: true`
- **Implementation**:
  - tsconfig.json with strict mode enabled
  - Define interfaces for all API responses
  - No `any` types without justification
- **Validation**: TypeScript compiler in strict mode

### ✅ V. No Authentication Required

- **Compliance**: No user authentication or authorization
- **Implementation**: All endpoints publicly accessible, connections stored locally
- **Note**: Production deployment should use network-level access control

### ✅ VI. SQL Safety and Query Validation

- **Compliance**: Strict SQL validation using sqlglot
- **Implementation**:
  - Parse SQL with sqlglot before execution
  - Block all non-SELECT statements
  - Auto-add LIMIT 1000 if missing
  - Return detailed parse errors
- **Validation**: Comprehensive test suite for SQL validation logic

### ✅ VII. Test-Driven Development (Recommended)

- **Compliance**: Key features have test coverage
- **Implementation**:
  - SQL validation: Unit tests (>95% coverage)
  - API endpoints: Integration tests
  - Data models: Serialization tests
  - Frontend: Component tests for critical flows
- **Validation**: pytest coverage >80% for backend critical paths

### Constitution Compliance Summary

✅ **All principles satisfied** - No violations or justifications required.

## Project Structure

### Documentation (this feature)

```text
specs/001-db-query-tool/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── api-v1.yaml      # OpenAPI specification
├── checklists/
│   └── requirements.md  # Already created
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
w2/db_query/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entry
│   │   ├── config.py            # Pydantic Settings configuration
│   │   ├── models/              # Pydantic models & SQLModel entities
│   │   │   ├── __init__.py
│   │   │   ├── database.py      # DatabaseConnection entity
│   │   │   ├── metadata.py      # DatabaseMetadata entity
│   │   │   ├── query.py         # QueryHistory entity
│   │   │   └── schemas.py       # Request/Response Pydantic models
│   │   ├── services/            # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── db_connection.py # Database connection management
│   │   │   ├── metadata.py      # Metadata extraction service
│   │   │   ├── query.py         # Query execution service
│   │   │   ├── sql_validator.py # SQL parsing & validation (sqlglot)
│   │   │   ├── export.py        # CSV/JSON streaming export service (US4 redesign)
│   │   │   └── nl2sql.py        # Natural language to SQL (OpenAI)
│   │   ├── api/                 # FastAPI routers
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── databases.py # /api/v1/dbs endpoints
│   │   │   │   └── queries.py   # /api/v1/dbs/{name}/query + /query/export endpoints
│   │   ├── database.py          # SQLite database setup
│   │   └── dependencies.py      # FastAPI dependencies
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py          # pytest fixtures
│   │   ├── unit/
│   │   │   ├── test_sql_validator.py
│   │   │   ├── test_metadata.py
│   │   │   └── test_models.py
│   │   ├── integration/
│   │   │   ├── test_api_databases.py
│   │   │   └── test_api_queries.py
│   │   └── contract/
│   │       └── test_api_contracts.py
│   ├── pyproject.toml           # uv dependencies & project config
│   ├── README.md
│   └── .python-version          # Python 3.12
│
└── frontend/
    ├── src/
    │   ├── App.tsx              # Main application component
    │   ├── main.tsx             # Vite entry point
    │   ├── types/               # TypeScript type definitions
    │   │   ├── database.ts      # Database connection types
    │   │   ├── metadata.ts      # Metadata types
    │   │   ├── query.ts         # Query & result types
    │   │   └── api.ts           # API response types
    │   ├── services/            # API client & data providers
    │   │   ├── api.ts           # Axios instance & interceptors
    │   │   └── dataProvider.ts  # Refine data provider
    │   ├── pages/               # Refine resource pages
    │   │   ├── databases/
    │   │   │   ├── list.tsx     # Database list view
    │   │   │   ├── create.tsx   # Add new database
    │   │   │   ├── show.tsx     # Database metadata view
    │   │   │   └── edit.tsx     # Edit database connection
    │   │   └── queries/
    │   │       └── execute.tsx  # Query execution page
    │   ├── components/          # Reusable React components
    │   │   ├── SqlEditor.tsx    # Monaco-based SQL editor
    │   │   ├── ResultTable.tsx  # Query result display
    │   │   ├── MetadataTree.tsx # Database schema tree
    │   │   └── NaturalLanguageInput.tsx
    │   ├── hooks/               # Custom React hooks
    │   │   ├── useQueryExecution.ts
    │   │   └── useMetadata.ts
    │   └── styles/
    │       └── index.css        # Tailwind imports
    ├── public/
    ├── package.json
    ├── tsconfig.json            # Strict TypeScript config
    ├── vite.config.ts
    ├── tailwind.config.js
    └── README.md
```

**Structure Decision**: Web application structure (Option 2) selected because this is a full-stack application with distinct frontend (React SPA) and backend (FastAPI REST API) components. The backend serves as a REST API server, and the frontend is a standalone SPA that communicates via HTTP. This separation enables independent development, testing, and potential future deployment strategies.

The project is located at `w2/db_query/` to align with the course week structure.

## Story 4 (Export) Implementation Plan

> 本段为 2026-08-07 重新设计的导出方案，替代原 tasks.md 中 T070-T077 的纯前端实现路径。其他 Story 的实现方案不变。

### Architecture: Hybrid Frontend + Backend Streaming

```
用户点击导出按钮
    │
    ├─ 当前结果行数 ≤ EXPORT_THRESHOLD (10000)
    │     └─ 前端 Blob 下载（即时，零网络往返）
    │           - handleExportCSV / handleExportJSON（重构为 async）
    │           - UTF-8 BOM + RFC 4180 引用规则
    │
    └─ 当前结果行数 > 阈值 或 用户点 "EXPORT ALL"
          └─ Modal.confirm 确认
                └─ 构造 GET /api/v1/dbs/{name}/query/export?sql=...&format=csv&limit=...
                      └─ 浏览器原生下载（StreamingResponse 直存盘）
```

### Backend Components

**1. `app/services/export.py`** (新增)
- `stream_csv(adapter, sql, max_rows) -> AsyncGenerator[bytes, None]`
- `stream_json(adapter, sql, max_rows) -> AsyncGenerator[bytes, None]`
- `sanitize_csv_field(value) -> str`: RFC 4180 引用 + CSV 公式注入防护（`=`/`+`/`-`/`@` 开头字段加 `'` 前缀）
- 依赖 adapter 新增 `stream_query(sql, batch_size, max_rows)` 方法（cursor 流式 fetch，不复用 `execute_query` 的 fetchall）

**2. `app/api/v1/queries.py`** (扩展)
- 新增 `GET /{name}/query/export`
- Query params: `sql` (required), `format` (csv|json), `limit` (default 100000, max 100000), `delimiter` (default ,)
- 用 `StreamingResponse(media_type=..., headers={Content-Disposition: ...})`
- SQL 校验：复用 `validate_and_transform_sql`，**不自动加 LIMIT 1000**，改用 sqlglot AST 改写注入 `LIMIT {limit}`
- 错误：非 SELECT → 400；limit 超上限 → 400；超时 → 504

**3. Adapter 扩展** (`app/adapters/base.py` + `mysql.py` + `postgresql.py`)
- `DatabaseAdapter` 新增抽象方法 `stream_query(sql, batch_size, max_rows) -> AsyncGenerator[List[dict], None]`
- PostgreSQL: `asyncpg` 的 `conn.cursor()` + `async for`
- MySQL: `aiomysql.SSCursor`（服务端游标，避免全量加载）

### Frontend Components

**`frontend/src/pages/Home.tsx`** (重构现有 + 新增)
- `EXPORT_THRESHOLD = 10000` 常量
- `handleExportCSV` / `handleExportJSON`：重构为 async，小结果走 Blob（保留现有逻辑）
- `handleExportAll(format)`：新增
  - 弹 `Modal.confirm`（行数提示）
  - 构造后端 URL（`encodeURIComponent(sql)`）
  - 用隐藏 `<a href={url} download={filename}>` 触发下载
- UI：现有两按钮 + 新增 `EXPORT ALL` 下拉（CSV/JSON）

### Security & Performance Gates

| Gate | 阈值 | 失败行为 |
|------|------|---------|
| SQL 类型 | 仅 SELECT | 400 |
| 行数上限 | 100000 | 400 |
| 超时 | 60s | 504 |
| CSV 注入 | 字段以 `=+-@` 开头 | 加 `'` 前缀 |
| UTF-8 BOM | CSV 必须 | 写入 `\ufeff` 头 |
| 内存 | 后端每 chunk ≤ 1000 行 | cursor 流式 |

### Constitution Re-check (Post-Design)

- ✅ **I. Python 严格类型**：`export.py` 全部 type hints，`AsyncGenerator[bytes, None]`
- ✅ **II. Pydantic**：endpoint 的 query params 用 Pydantic 模型或 FastAPI `Query` 注解
- ✅ **III. camelCase JSON**：JSON 导出字段名保持 camelCase（与查询结果一致）
- ✅ **IV. TypeScript strict**：前端 `handleExportAll` 有完整类型签名
- ✅ **VI. SQL 安全**：复用 sqlglot 校验，不因导出路径放宽

无宪法违规，无需 Complexity Tracking 条目。

## Complexity Tracking

No constitution violations. All principles are satisfied with standard patterns and technologies.



