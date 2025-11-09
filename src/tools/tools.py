"""All MCP tools for Odoo operations"""

import logging
from typing import Any, Dict, List, Optional

from ..odoo.client import OdooClient

logger = logging.getLogger(__name__)

# ============================================================================
# READ OPERATIONS (Require R permission)
# ============================================================================


async def search(
    client: OdooClient,
    model: str,
    domain: Optional[List] = None,
    limit: int = 100,
    offset: int = 0,
    **kwargs,
) -> Dict[str, Any]:
    """
    Search for records in a model.

    Args:
        client: OdooClient instance
        model: Odoo model name (e.g., "res.partner")
        domain: Search domain filter
        limit: Maximum records to return
        offset: Number of records to skip

    Returns:
        Dict with 'ids' list of matching record IDs
    """
    try:
        domain = domain or []
        ids = await client.search(model, domain, limit=limit, offset=offset)
        return {"ids": ids, "count": len(ids), "model": model}
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Search failed for {model}: {str(e)}")
        return {"error": f"Search failed: {str(e)}"}


async def read(
    client: OdooClient,
    model: str,
    ids: List[int],
    fields: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Read specific records from a model.

    Args:
        client: OdooClient instance
        model: Odoo model name
        ids: List of record IDs to read
        fields: List of fields to return

    Returns:
        Dict with 'records' list containing record data
    """
    try:
        fields = fields or []
        records = await client.read(model, ids, fields=fields)
        return {"records": records, "count": len(records), "model": model}
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Read failed for {model}: {str(e)}")
        return {"error": f"Read failed: {str(e)}"}


async def search_read(
    client: OdooClient,
    model: str,
    domain: Optional[List] = None,
    fields: Optional[List[str]] = None,
    limit: int = 100,
    offset: int = 0,
    **kwargs,
) -> Dict[str, Any]:
    """
    Search and read records in one call.

    Args:
        client: OdooClient instance
        model: Odoo model name
        domain: Search domain filter
        fields: Fields to return
        limit: Maximum records to return
        offset: Number of records to skip

    Returns:
        Dict with 'records' list containing search results
    """
    try:
        domain = domain or []
        fields = fields or []
        records = await client.search_read(
            model, domain=domain, fields=fields, limit=limit, offset=offset
        )
        return {"records": records, "count": len(records), "model": model}
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Search read failed for {model}: {str(e)}")
        return {"error": f"Search read failed: {str(e)}"}


async def search_count(
    client: OdooClient, model: str, domain: Optional[List] = None, **kwargs
) -> Dict[str, Any]:
    """
    Count records matching domain in a model.

    Args:
        client: OdooClient instance
        model: Odoo model name
        domain: Search domain filter

    Returns:
        Dict with 'count' of matching records
    """
    try:
        domain = domain or []
        count = await client.search_count(model, domain=domain)
        return {"count": count, "model": model}
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Search count failed for {model}: {str(e)}")
        return {"error": f"Search count failed: {str(e)}"}


async def fields_get(
    client: OdooClient, model: str, fields: Optional[List[str]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Get field definitions for a model.

    Args:
        client: OdooClient instance
        model: Odoo model name
        fields: Specific fields to describe (empty = all fields)

    Returns:
        Dict with 'fields' containing field metadata
    """
    try:
        fields = fields or []
        field_defs = await client.fields_get(model, fields=fields)
        return {"fields": field_defs, "count": len(field_defs), "model": model}
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Fields get failed for {model}: {str(e)}")
        return {"error": f"Fields get failed: {str(e)}"}


async def default_get(
    client: OdooClient, model: str, fields: Optional[List[str]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Get default values for model fields.

    Args:
        client: OdooClient instance
        model: Odoo model name
        fields: Fields to get defaults for

    Returns:
        Dict with 'defaults' containing default values
    """
    try:
        fields = fields or []
        defaults = await client.default_get(model, fields=fields)
        return {"defaults": defaults, "model": model}
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Default get failed for {model}: {str(e)}")
        return {"error": f"Default get failed: {str(e)}"}


# ============================================================================
# WRITE OPERATIONS (Require W permission)
# ============================================================================


async def create(
    client: OdooClient, model: str, values: Dict[str, Any], **kwargs
) -> Dict[str, Any]:
    """
    Create a new record in a model.

    Args:
        client: OdooClient instance
        model: Odoo model name
        values: Field values for new record

    Returns:
        Dict with 'id' of created record
    """
    try:
        record_id = await client.create(model, values)
        return {"id": record_id, "model": model, "status": "created"}
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Create failed for {model}: {str(e)}")
        return {"error": f"Create failed: {str(e)}"}


async def write(
    client: OdooClient, model: str, ids: List[int], values: Dict[str, Any], **kwargs
) -> Dict[str, Any]:
    """
    Update existing records in a model.

    Args:
        client: OdooClient instance
        model: Odoo model name
        ids: Record IDs to update
        values: Field values to set

    Returns:
        Dict with 'success' status and count of updated records
    """
    try:
        result = await client.write(model, ids, values)
        return {
            "success": result,
            "count": len(ids),
            "model": model,
            "status": "updated",
        }
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Write failed for {model}: {str(e)}")
        return {"error": f"Write failed: {str(e)}"}


# ============================================================================
# DELETE OPERATIONS (Require D permission)
# ============================================================================


async def unlink(
    client: OdooClient, model: str, ids: List[int], **kwargs
) -> Dict[str, Any]:
    """
    Delete records from a model.

    Args:
        client: OdooClient instance
        model: Odoo model name
        ids: Record IDs to delete

    Returns:
        Dict with 'success' status and count of deleted records
    """
    try:
        result = await client.unlink(model, ids)
        return {
            "success": result,
            "count": len(ids),
            "model": model,
            "status": "deleted",
        }
    except PermissionError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unlink failed for {model}: {str(e)}")
        return {"error": f"Unlink failed: {str(e)}"}


# ============================================================================
# Tool registry mapping
# ============================================================================

TOOLS_REGISTRY = {
    # Read operations
    "search": search,
    "read": read,
    "search_read": search_read,
    "search_count": search_count,
    "fields_get": fields_get,
    "default_get": default_get,
    # Write operations
    "create": create,
    "write": write,
    # Delete operations
    "unlink": unlink,
}
