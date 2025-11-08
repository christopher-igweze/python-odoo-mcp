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

### 1. Set Up Odoo Credentials

In n8n, prepare your Odoo credentials as a JSON object:

```json
{
  "url": "https://company.odoo.com",
  "database": "company_db",
  "username": "api_user",
  "password": "secret123",
  "scope": "res.partner:RWD,sale.order:RW,product.product:R,*:R"
}
```

### 2. Create HTTP Request Node

In n8n, use an HTTP Request node with:

- **Method:** POST
- **URL:** `http://localhost:3000/tools/call` (or your Coolify URL)
- **Headers:**
  - `X-Auth-Credentials: {{ Buffer.from(JSON.stringify({...your_creds...})).toString('base64') }}`
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
