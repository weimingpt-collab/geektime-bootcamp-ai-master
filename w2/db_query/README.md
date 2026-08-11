# Database Query Tool

A web-based tool for managing PostgreSQL database connections, viewing metadata, and executing SQL queries with natural language support.

## Project Structure

```
w2/db_query/
├── backend/          # FastAPI backend (Python 3.12+)
├── frontend/         # React frontend (TypeScript, Refine 5)
├── fixtures/         # REST Client test files
│   ├── test.rest     # API test requests
│   └── README.md     # Testing guide
└── Makefile          # Development commands
```

## Quick Start

### Initial Setup

**macOS / Linux:**

```bash
# Install all dependencies
make install

# Setup database and environment
make setup
# Then edit backend/.env and add your OPENAI_API_KEY

# Start development servers
make dev
```

**Windows (PowerShell):**

The `Makefile` relies on GNU Make and Unix shell commands that are not
available on Windows by default. Use the provided `setup.ps1` script instead —
it mirrors the Makefile targets and auto-installs `uv` and Python 3.12 if
missing.

```powershell
# Initial setup: install deps + apply DB migrations (auto-installs uv/python)
.\setup.ps1

# Install dependencies only
.\setup.ps1 -Task install

# Start backend + frontend dev servers
.\setup.ps1 -Task dev

# See all available tasks
.\setup.ps1 -Task help
```

### Development Commands

```bash
# View all available commands
make help            # macOS/Linux
.\setup.ps1 -Task help   # Windows

# Start backend only
make dev-backend

# Start frontend only
make dev-frontend

# Run tests
make test

# Format code
make format

# Run linters
make lint
```

## API Testing

### Using REST Client (VSCode)

1. Install [REST Client extension](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)
2. Open `fixtures/test.rest`
3. Click "Send Request" above any HTTP request
4. View responses in VSCode panel

See `fixtures/README.md` for detailed testing guide.

### Using Makefile

```bash
# Check if backend is running
make health

# Open API documentation
make docs
```

## Phase 1 Status

✅ **Phase 1 Complete**: All setup and foundation tasks completed.

- Backend project structure initialized
- Frontend project structure initialized
- Core infrastructure (FastAPI, database, models) ready
- Data models defined with camelCase API convention
- Makefile with common development tasks
- REST Client test file for API testing

## Next Steps

Proceed to Phase 2 for core feature implementation (US1 + US2).
