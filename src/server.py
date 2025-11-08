"""FastAPI MCP Server entry point"""
import logging
import json
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse, StreamingResponse
from contextlib import asynccontextmanager

from .config import config

# Configure logging
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    logger.info("Starting Python Odoo MCP Server")
    logger.info(f"Pool TTL: {config.CONNECTION_POOL_TTL_MINUTES} minutes")
    yield
    logger.info("Shutting down Python Odoo MCP Server")

# Create FastAPI app
app = FastAPI(
    title="Python Odoo MCP Server",
    description="Multi-tenant Odoo XML-RPC MCP with scope-based access control",
    version="1.0.0",
    lifespan=lifespan
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
        "status": "running"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }

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
                    "model": {"type": "string", "description": "Odoo model name (e.g., res.partner)"},
                    "domain": {"type": "array", "description": "Search domain filter", "default": []},
                    "limit": {"type": "integer", "description": "Max records to return", "default": 100},
                    "offset": {"type": "integer", "description": "Records to skip", "default": 0}
                },
                "required": ["model"]
            }
        },
        {
            "name": "read",
            "description": "Read records from a model",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "ids": {"type": "array", "description": "Record IDs to read"},
                    "fields": {"type": "array", "description": "Fields to return", "default": []}
                },
                "required": ["model", "ids"]
            }
        },
        {
            "name": "search_read",
            "description": "Search and read records in one call",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "domain": {"type": "array", "description": "Search domain filter", "default": []},
                    "fields": {"type": "array", "description": "Fields to return", "default": []},
                    "limit": {"type": "integer", "description": "Max records to return", "default": 100},
                    "offset": {"type": "integer", "description": "Records to skip", "default": 0}
                },
                "required": ["model"]
            }
        },
        {
            "name": "search_count",
            "description": "Count records matching domain",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "domain": {"type": "array", "description": "Search domain filter", "default": []}
                },
                "required": ["model"]
            }
        },
        {
            "name": "fields_get",
            "description": "Get field definitions for a model",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "fields": {"type": "array", "description": "Specific fields to describe", "default": []}
                },
                "required": ["model"]
            }
        },
        {
            "name": "default_get",
            "description": "Get default values for model fields",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "fields": {"type": "array", "description": "Fields to get defaults for", "default": []}
                },
                "required": ["model"]
            }
        },
        {
            "name": "create",
            "description": "Create a new record in a model",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "values": {"type": "object", "description": "Field values for new record"}
                },
                "required": ["model", "values"]
            }
        },
        {
            "name": "write",
            "description": "Update existing records in a model",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "ids": {"type": "array", "description": "Record IDs to update"},
                    "values": {"type": "object", "description": "Field values to set"}
                },
                "required": ["model", "ids", "values"]
            }
        },
        {
            "name": "unlink",
            "description": "Delete records from a model",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Odoo model name"},
                    "ids": {"type": "array", "description": "Record IDs to delete"}
                },
                "required": ["model", "ids"]
            }
        }
    ]

    return {"tools": tools}

@app.post("/tools/call")
async def call_tool(
    request: dict,
    x_auth_credentials: str = Header(None)
):
    """MCP: Call a tool with multi-tenant authentication

    Expects header:
    X-Auth-Credentials: base64(JSON with url, db, username, password, scope)
    """

    # TODO: Implement auth, scope validation, and tool execution
    # This will be wired up in Phase 6 after all components are ready

    return {
        "error": "Tool execution not yet implemented",
        "status": "ready_for_phase_6"
    }

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

if __name__ == "__main__":
    import uvicorn

    # Validate configuration on startup
    config.validate()

    logger.info(f"Starting server on {config.HOST}:{config.PORT}")

    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower()
    )
