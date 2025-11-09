# Python Odoo MCP Server

Multi-tenant Odoo XML-RPC MCP server with scope-based access control, connection pooling, and HTTP Stream transport.

**Repository:** https://github.com/christopher-igweze/python-odoo-mcp

## Quick Start

### Local Development

```bash
# Clone and install
git clone https://github.com/christopher-igweze/python-odoo-mcp.git
cd python-odoo-mcp
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run server
python -m src.server
# Server starts on http://localhost:3000
```

### Docker

```bash
# Build and run
docker-compose up --build

# Server starts on http://localhost:3000
```

## Usage with n8n

### 1. Generate API Key

First, POST your Odoo credentials to `/auth/generate` to get an encrypted API key:

```bash
curl -X POST http://localhost:3000/auth/generate \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://company.odoo.com",
    "database": "company_db",
    "username": "api_user",
    "password": "secret123",
    "scope": "res.partner:RWD,sale.order:RW,product.product:R,*:R"
  }'

# Response:
# {
#   "api_key": "gAAAAABl...",
#   "expires": null,
#   "user": "api_user"
# }
```

In n8n, you can store this `api_key` in a variable for later use.

### 2. Create HTTP Request Node

In n8n, use an HTTP Request node with:

- **Method:** POST
- **URL:** `http://localhost:3000/tools/call` (or your Coolify URL)
- **Headers:**
  - `X-API-Key: {{ $variables.api_key }}`  (use your stored API key)
- **Body:**
  ```json
  {
    "name": "search",
    "arguments": {
      "model": "res.partner",
      "limit": 10
    }
  }
  ```

### 3. Available Tools

All tools work on any Odoo model. Permission enforced by scope.

**Read Operations** (require `R` permission):
- `search` - Search records with domain
- `read` - Read specific records
- `search_read` - Combined search + read
- `search_count` - Count matching records
- `fields_get` - Get model schema
- `default_get` - Get default values

**Write Operations** (require `W` permission):
- `create` - Create new record
- `write` - Update records

**Delete Operations** (require `D` permission):
- `unlink` - Delete records

## Scope Format

Control permissions with a scope string:

```
# Full access to res.partner
res.partner:RWD

# Can search/read/write sales orders, no delete
sale.order:RW

# Read-only access
product.product:R

# Multiple models
res.partner:RWD,sale.order:RW,account.invoice:R

# Wildcard: read-only to all models
*:R

# Mixed: specific full access + wildcard read-only
res.partner:RWD,sale.order:RWD,*:R
```

Permissions:
- `R` = Read (search, read, search_read, search_count, fields_get, default_get)
- `W` = Write (create, write)
- `D` = Delete (unlink)

## Architecture

```
┌─ n8n ─────────────────────────────────┐
│ HTTP Request with X-Auth-Credentials  │
└────────────┬────────────────────────────┘
             │ (base64 JSON with credentials + scope)
             ▼
┌─ Python Odoo MCP ─────────────────────┐
│ ┌──────────────────────────────────┐  │
│ │ Authentication & Scope Validator │  │
│ └──────────┬───────────────────────┘  │
│            │                           │
│ ┌──────────▼───────────────────────┐  │
│ │ Connection Pool (Scope-Aware)    │  │
│ │ Caches connections per user+scope│  │
│ └──────────┬───────────────────────┘  │
│            │                           │
│ ┌──────────▼───────────────────────┐  │
│ │ Odoo Client                      │  │
│ │ - Validates scope before every op│  │
│ │ - Uses pooled connections        │  │
│ └──────────┬───────────────────────┘  │
│            │                           │
│ ┌──────────▼───────────────────────┐  │
│ │ Tools (search, read, write, etc) │  │
│ │ Execute on Odoo via XML-RPC     │  │
│ └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
             │
             ▼ (XML-RPC)
         Odoo Instance
```

## Environment Variables

```bash
# Encryption key for API key generation (auto-generated if not set)
# Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your_base64_fernet_key_here

# Connection pool TTL (default: 60 minutes)
CONNECTION_POOL_TTL_MINUTES=60

# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Server host and port (defaults for Docker)
HOST=0.0.0.0
PORT=3000
```

## Deployment

### Coolify Setup

1. Push repo to GitHub
2. In Coolify, create new service → Docker
3. Point to repository
4. Set environment variables (if needed)
5. Deploy
6. Get public URL from Coolify
7. Use in n8n: `https://your-mcp-xxx.coolify.io/tools/call`

## Testing

### Unit and Integration Tests

The project includes comprehensive unit and integration tests using pytest:

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_encryption.py -v

# Run tests matching pattern
pytest -k "scope_validator" -v

# Run with markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m slow         # Slow/e2e tests
```

### Test Structure

```
tests/
├── unit/                           # Unit tests (no external dependencies)
│   ├── test_config.py             # Config management & encryption key validation
│   ├── test_encryption.py         # Credential encryption/decryption
│   └── test_scope_validator.py    # Scope parsing and permission checking
├── integration/                    # Integration tests (with app instance)
│   ├── test_auth_endpoints.py     # /auth/generate and /auth/validate
│   ├── test_health.py             # Health check endpoints
│   └── test_tools_endpoints.py    # /tools/list and /tools/call
└── conftest.py                    # Shared pytest fixtures
```

### Health Check

```bash
curl http://localhost:3000/health
```

### List Tools

```bash
curl -X POST http://localhost:3000/tools/list
```

### Test with Script

```bash
./test_server.sh
```

### Test in n8n

Import `test_n8n.json` workflow for examples.

### Coverage Goals

Current coverage: 46% (61 tests passing)
- **High coverage:** Authentication, encryption, scope validation (89%), connection pool management
- **Low coverage:** Tool implementations, Odoo client methods (require live Odoo instance)

To improve coverage:
1. Run tests against real Odoo instance (see Phase 8 in development history)
2. Mock Odoo responses in unit tests
3. Use testcontainers for Odoo in CI/CD

### Coverage Monitoring with Codecov

This project uses [Codecov](https://codecov.io/) for continuous coverage tracking and reporting.

**Coverage Tracking:**
- View detailed coverage dashboard: https://codecov.io/gh/christopher-igweze/python-odoo-mcp
- Coverage reports generated automatically on every push via GitHub Actions
- Pull requests show coverage impact (lines added/removed/changed)
- Coverage history graphs track improvements over time

**Current Status:**
- Overall coverage: 46% (target: 75%+)
- Authentication & encryption: 89% ✅
- Scope validation: 89% ✅
- Tools & Odoo client: 15-29% (improving with mocked tests)

**Understanding Coverage Reports:**
1. **Line Coverage** - Percentage of source code lines executed during tests
2. **Branch Coverage** - All code paths (if/else) tested
3. **Uncovered Lines** - Listed with file paths for targeting improvement
4. **Trending** - See if coverage increases or decreases with each commit

**Local Coverage Reports:**

Generate and view HTML coverage reports locally:

```bash
# Run tests with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# View in browser
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

**For Contributors:**

When implementing new features:
1. Write tests alongside implementation
2. Aim for 80%+ coverage on new code
3. Run `pytest` to see coverage before pushing
4. Codecov will comment on PRs showing impact
5. Target overall coverage of 75%+

## Features

✅ **Multi-tenant** - Different users, different Odoo instances, same server
✅ **Scope-based access control** - Fine-grained R/W/D permissions per model
✅ **Connection pooling** - Caches authenticated sessions, scope-aware
✅ **HTTP Stream MCP** - Works with n8n's official MCP node
✅ **Stateless** - Each request is self-contained
✅ **Error handling** - Clear permission errors, auth errors, connection errors
✅ **Thread-safe** - RLock for pool access
✅ **Async** - Full async/await support

## Error Handling

All errors return `{"error": "...", "status": "..."}`:

- `auth_failed` - Invalid credentials header
- `scope_invalid` - Invalid scope syntax
- `connection_failed` - Can't connect to Odoo
- `permission_denied` - Operation violates scope
- `tool_not_found` - Unknown tool name
- `odoo_error` - Odoo RPC error

## Development

Micro-commit workflow with glassbear format:

```bash
# Read the requirements
cat requirements.txt

# Make a change, test it
# Then commit
git commit -m "🔧 fix(scope): handle wildcard override"
git push origin main
```

See `.git/logs` for commit history.

## License

This project is open source.

## Support

Issues? Check:
1. Odoo URL and credentials are correct
2. User has permissions in Odoo (create API user in settings)
3. Scope syntax is valid (see examples above)
4. Server logs: `docker logs python-odoo-mcp`
