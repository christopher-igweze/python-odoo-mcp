# Python Odoo MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![codecov](https://codecov.io/gh/christopher-igweze/python-odoo-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/christopher-igweze/python-odoo-mcp)
[![Tests](https://github.com/christopher-igweze/python-odoo-mcp/workflows/Tests/badge.svg)](https://github.com/christopher-igweze/python-odoo-mcp/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

HTTP REST API for Odoo automation with encrypted API keys, multi-tenant scope isolation, and connection pooling. Built for n8n, webhooks, and custom integrations.

**Repository:** https://github.com/christopher-igweze/python-odoo-mcp

## Features

✅ **Multi-tenant** - Different users, different Odoo instances, same server

✅ **Scope-based access control** - Fine-grained R/W/D permissions per model

✅ **Encrypted API keys** - Fernet encryption for secure key storage

✅ **Connection pooling** - Caches authenticated sessions with TTL

✅ **n8n ready** - Drop-in HTTP integration for automation workflows

✅ **Complete CRUD** - Search, read, create, write, delete any Odoo model

✅ **Error handling** - Clear permission, auth, and connection errors

✅ **Async support** - Full async/await for high concurrency

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

**Request Flow:**

```
HTTP Request (X-API-Key header)
    ↓
Authentication & Scope Validation
    ↓
Connection Pool (scope-aware caching)
    ↓
Odoo Client (validates permissions, executes operations)
    ↓
Odoo Instance (XML-RPC)
```

**Key Components:**
- **HTTP Server** - FastAPI REST API on port 3000
- **Connection Pool** - Caches authenticated Odoo sessions with TTL and scope isolation
- **Scope Validator** - Enforces R/W/D permissions per model
- **Odoo Client** - XML-RPC wrapper with automatic connection pooling

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

## Testing & Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Running tests with pytest
- Test coverage information (75.37% achieved)
- Development workflow and micro-commits

## Error Handling

All errors return `{"error": "...", "status": "..."}`:

- `auth_failed` - Invalid credentials header
- `scope_invalid` - Invalid scope syntax
- `connection_failed` - Can't connect to Odoo
- `permission_denied` - Operation violates scope
- `tool_not_found` - Unknown tool name
- `odoo_error` - Odoo RPC error

## Note: REST API vs MCP Protocol

This project exposes **MCP-style tools via HTTP REST API**, which is different from the official MCP protocol:

- **This server:** REST API with HTTP endpoints (`/tools/list`, `/tools/call`)
- **Official MCP protocol:** Used by Claude Desktop, Cursor, and other AI assistants via stdio or websockets

For AI assistant integration, see the excellent [ivnvxd/mcp-server-odoo](https://github.com/ivnvxd/mcp-server-odoo) which uses true MCP protocol.

This REST API approach is ideal for **n8n, webhooks, and automation platforms** where HTTP is more practical.

## License

MIT License - see [LICENSE](LICENSE) for details.

This means you can freely use, modify, and distribute this software as long as you include the license notice.

## Support

Issues? Check:
1. Odoo URL and credentials are correct
2. User has permissions in Odoo (create API user in settings)
3. Scope syntax is valid (see examples above)
4. Server logs: `docker logs python-odoo-mcp`

## About

**Python Odoo MCP Server** is a production-ready REST API that bridges Odoo with automation platforms like n8n, Zapier, and custom integrations. Built with security and scalability in mind:

- **Encrypted by default** - API keys are Fernet-encrypted, never stored in plaintext
- **Multi-tenant ready** - Isolate data with scope-based access control
- **Connection pooling** - Efficient resource usage with TTL-based cache expiration
- **Enterprise-grade testing** - 142 tests covering critical paths, 75%+ code coverage
- **Developer-friendly** - Complete async/await support, clear error messages, detailed docs

Whether you're automating Odoo workflows in n8n, building a custom integration, or managing Odoo data programmatically, this server provides a reliable, secure HTTP API with fine-grained permission control.

### Use Cases

- **n8n automation** - Use Odoo as a data source or action in n8n workflows
- **Webhook integration** - Trigger Odoo operations from external systems
- **Custom applications** - Build apps that interact with Odoo without direct XML-RPC
- **API aggregation** - Combine Odoo with other APIs in automation platforms
- **Data synchronization** - Sync Odoo data with other business systems

### Technology Stack

- **Framework:** FastAPI (async Python web framework)
- **Protocol:** HTTP REST API with XML-RPC backend
- **Caching:** In-memory connection pooling with TTL expiration
- **Security:** Fernet encryption for API keys, scope-based access control
- **Testing:** pytest with 75%+ code coverage
- **Deployment:** Docker, Docker Compose, or traditional Python server

### Project Status

- **Version:** 0.1.0 (stable)
- **License:** MIT (open source, commercial-friendly)
- **Maintenance:** Active development
- **Compatibility:** Odoo 11.0+ with Python 3.9+

For more details, see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and [LICENSE](LICENSE) for licensing terms.
