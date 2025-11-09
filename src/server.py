"""FastAPI MCP Server entry point"""

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from .auth.header_parser import AuthenticationError, parse_auth_header
from .auth.scope_validator import ScopeValidationError, ScopeValidator
from .auth_manager import APIKeyResponse, Credentials, encryption_manager
from .config import config
from .connection.manager import OdooConnectionError, OdooConnectionManager
from .connection.pool import ConnectionPool
from .odoo.client import OdooClient, OdooClientError
from .tools.tools import TOOLS_REGISTRY

# Configure logging
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Global instances
connection_pool: ConnectionPool = None
connection_manager: OdooConnectionManager = None


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    global connection_pool, connection_manager

    logger.info("Starting Python Odoo MCP Server")
    logger.info(f"Pool TTL: {config.CONNECTION_POOL_TTL_MINUTES} minutes")

    # Initialize connection pool
    connection_pool = ConnectionPool(ttl_minutes=config.CONNECTION_POOL_TTL_MINUTES)
    connection_manager = OdooConnectionManager(connection_pool)

    logger.info("✓ Connection pool and manager initialized")

    yield

    logger.info("Shutting down Python Odoo MCP Server")


# Create FastAPI app
app = FastAPI(
    title="Python Odoo MCP Server",
    description="Multi-tenant Odoo XML-RPC MCP with scope-based access control",
    version="1.0.0",
    lifespan=lifespan,
)

# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/")
async def root():
    """Server info endpoint"""
    return {
        "name": "Python Odoo MCP Server",
        "version": "1.0.0",
        "transport": "http_streamable",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    global connection_manager

    pool_stats = connection_manager.get_pool_stats() if connection_manager else {}

    return {"status": "healthy", "version": "1.0.0", "pool": pool_stats}


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================


@app.post("/auth/generate", response_model=APIKeyResponse)
async def generate_api_key(credentials: Credentials):
    """Generate encrypted API key from credentials

    This endpoint takes raw Odoo credentials and generates an encrypted
    API key that can be used for subsequent /tools/call requests.

    Args:
        credentials: Odoo credentials (url, database, username, password, scope)

    Returns:
        APIKeyResponse with encrypted api_key and credential info (no password)
    """
    try:
        # Encrypt the credentials
        api_key = encryption_manager.encrypt_credentials(credentials)

        # Get credential info without password
        cred_info = encryption_manager.get_credential_info(api_key)

        logger.info(f"✓ Generated API key for user: {credentials.username}")

        return APIKeyResponse(api_key=api_key, credentials=cred_info)

    except Exception as e:
        logger.error(f"Failed to generate API key: {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Failed to generate API key: {str(e)}"
        )


@app.post("/auth/validate")
async def validate_api_key(request: dict):
    """Validate an API key and return credential info

    Decrypts an API key to verify it's valid and returns the credential
    info (without password) for debugging purposes.

    Body:
        {"api_key": "encrypted_api_key"}

    Returns:
        Credential info dictionary (no password)
    """
    api_key = request.get("api_key")

    if not api_key:
        raise HTTPException(status_code=400, detail="Missing api_key in request body")

    try:
        cred_info = encryption_manager.get_credential_info(api_key)
        logger.info(f"✓ API key validated for user: {cred_info['username']}")

        return {"status": "valid", "credentials": cred_info}

    except ValueError as e:
        logger.warning(f"Invalid API key: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to validate API key: {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Failed to validate API key: {str(e)}"
        )


@app.post("/tools/list")
async def list_tools():
    """MCP: List available tools

    Returns all tools without filtering by scope.
    Scope enforcement happens at execution time in /tools/call
    """
    tools = [
        {
            "name": "search",
            "description": "Search for records in a model",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Odoo model name (e.g., res.partner)",
                    },
                    "domain": {
                        "type": "array",
                        "description": "Search domain filter",
                        "default": [],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max records to return",
                        "default": 100,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Records to skip",
                        "default": 0,
                    },
                },
                "required": ["model"],
            },
        },
        {
            "name": "read",
            "description": "Read records from a model",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "ids": {"type": "array", "description": "Record IDs to read"},
                    "fields": {
                        "type": "array",
                        "description": "Fields to return",
                        "default": [],
                    },
                },
                "required": ["model", "ids"],
            },
        },
        {
            "name": "search_read",
            "description": "Search and read records in one call",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "domain": {
                        "type": "array",
                        "description": "Search domain filter",
                        "default": [],
                    },
                    "fields": {
                        "type": "array",
                        "description": "Fields to return",
                        "default": [],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max records to return",
                        "default": 100,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Records to skip",
                        "default": 0,
                    },
                },
                "required": ["model"],
            },
        },
        {
            "name": "search_count",
            "description": "Count records matching domain",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "domain": {
                        "type": "array",
                        "description": "Search domain filter",
                        "default": [],
                    },
                },
                "required": ["model"],
            },
        },
        {
            "name": "fields_get",
            "description": "Get field definitions for a model",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "fields": {
                        "type": "array",
                        "description": "Specific fields to describe",
                        "default": [],
                    },
                },
                "required": ["model"],
            },
        },
        {
            "name": "default_get",
            "description": "Get default values for model fields",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "fields": {
                        "type": "array",
                        "description": "Fields to get defaults for",
                        "default": [],
                    },
                },
                "required": ["model"],
            },
        },
        {
            "name": "create",
            "description": "Create a new record in a model",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "values": {
                        "type": "object",
                        "description": "Field values for new record",
                    },
                },
                "required": ["model", "values"],
            },
        },
        {
            "name": "write",
            "description": "Update existing records in a model",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "ids": {"type": "array", "description": "Record IDs to update"},
                    "values": {"type": "object", "description": "Field values to set"},
                },
                "required": ["model", "ids", "values"],
            },
        },
        {
            "name": "unlink",
            "description": "Delete records from a model",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "ids": {"type": "array", "description": "Record IDs to delete"},
                },
                "required": ["model", "ids"],
            },
        },
    ]

    return {"tools": tools}


@app.post("/tools/call")
async def call_tool(request: dict, x_api_key: str = Header(None)):
    """MCP: Call a tool with encrypted API key authentication

    Expects:
    - Header: X-API-Key: <encrypted_api_key>
    - Body: {"name": "tool_name", "arguments": {...}}

    To get an X-API-Key:
    1. POST to /auth/generate with credentials
    2. Use the returned api_key in the X-API-Key header
    """
    global connection_manager

    # =========================================================================
    # 1. PARSE & VALIDATE CREDENTIALS FROM API KEY
    # =========================================================================

    if not x_api_key:
        logger.warning("Missing X-API-Key header")
        return {"error": "Missing X-API-Key header", "status": "auth_failed"}

    try:
        creds = encryption_manager.decrypt_credentials(x_api_key)
        logger.debug(f"Decrypted credentials for user: {creds['username']}")
    except ValueError as e:
        logger.warning(f"Auth error: {str(e)}")
        return {"error": str(e), "status": "auth_failed"}

    # =========================================================================
    # 2. PARSE & VALIDATE SCOPE
    # =========================================================================

    try:
        scope_validator = ScopeValidator(creds["scope"])
        logger.debug(f"Scope validated for user: {creds['username']}")
    except ScopeValidationError as e:
        logger.warning(f"Scope error: {str(e)}")
        return {"error": f"Invalid scope: {str(e)}", "status": "scope_invalid"}

    # =========================================================================
    # 3. GET ODOO CONNECTION (FROM POOL OR CREATE NEW)
    # =========================================================================

    try:
        uid, db, models_proxy = connection_manager.get_connection(
            creds["url"],
            creds["database"],
            creds["username"],
            creds["password"],
            creds["scope"],
        )
        logger.debug(f"Got connection for {creds['username']} (UID: {uid})")
    except OdooConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        return {"error": str(e), "status": "connection_failed"}

    # =========================================================================
    # 4. CREATE ODOO CLIENT WITH SCOPE VALIDATION
    # =========================================================================

    client = OdooClient(
        odoo_url=creds["url"],
        odoo_db=creds["database"],
        username=creds["username"],
        password=creds["password"],
        connection_manager=connection_manager,
        scope_validator=scope_validator,
    )

    # =========================================================================
    # 5. PARSE & EXECUTE TOOL
    # =========================================================================

    tool_name = request.get("name")
    arguments = request.get("arguments", {})

    if not tool_name:
        return {"error": "Missing 'name' in request", "status": "invalid_request"}

    if tool_name not in TOOLS_REGISTRY:
        return {
            "error": f"Tool '{tool_name}' not found. Available tools: {list(TOOLS_REGISTRY.keys())}",
            "status": "tool_not_found",
        }

    try:
        logger.debug(f"Executing tool '{tool_name}' for {creds['username']}")

        # Call the tool function
        tool_func = TOOLS_REGISTRY[tool_name]
        result = await tool_func(client, **arguments)

        logger.debug(f"Tool '{tool_name}' executed successfully")

        # Stream the result back
        def generate():
            yield json.dumps({"result": result}).encode() + b"\n"

        return StreamingResponse(generate(), media_type="application/json")

    except PermissionError as e:
        logger.warning(f"Permission denied for {creds['username']}: {str(e)}")
        return {"error": str(e), "status": "permission_denied"}
    except OdooClientError as e:
        logger.error(f"Odoo client error: {str(e)}")
        return {"error": str(e), "status": "odoo_error"}
    except Exception as e:
        logger.error(f"Unexpected error in tool execution: {str(e)}", exc_info=True)
        return {
            "error": f"Tool execution failed: {str(e)}",
            "status": "execution_error",
        }


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


if __name__ == "__main__":
    import uvicorn

    # Validate configuration on startup
    config.validate()

    logger.info(f"Starting server on {config.HOST}:{config.PORT}")

    uvicorn.run(
        app, host=config.HOST, port=config.PORT, log_level=config.LOG_LEVEL.lower()
    )
