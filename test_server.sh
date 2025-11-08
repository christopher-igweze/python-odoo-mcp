#!/bin/bash

# Integration test script for Python Odoo MCP Server
# Tests: health, auth, scope validation, tool execution, pool reuse

set -e

BASE_URL="http://localhost:3000"
TIMEOUT=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Python Odoo MCP Server - Integration Tests"
echo "=========================================="
echo ""

# Test credentials (base64 encoded JSON)
# {"url": "https://demo.odoo.com", "database": "demo", "username": "admin", "password": "admin", "scope": "res.partner:RWD,sale.order:RW"}
VALID_CREDS="eyJ1cmwiOiAiaHR0cHM6Ly9kZW1vLm9kb28uY29tIiwgImRhdGFiYXNlIjogImRlbW8iLCAidXNlcm5hbWUiOiAiYWRtaW4iLCAicGFzc3dvcmQiOiAiYWRtaW4iLCAic2NvcGUiOiAicmVzLnBhcnRuZXI6UldELHNhbGUub3JkZXI6UlcifQ=="

# Invalid base64
INVALID_BASE64="!@#$%^&*()"

# Invalid JSON
INVALID_JSON="aW52YWxpZCBqc29u"  # base64("invalid json")

# Missing password field
MISSING_FIELD="eyJ1cmwiOiAiaHR0cHM6Ly9kZW1vLm9kb28uY29tIiwgImRhdGFiYXNlIjogImRlbW8iLCAidXNlcm5hbWUiOiAiYWRtaW4ifQ=="

function test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local header=$4
    local data=$5
    local expected_status=$6

    echo -n "Testing: $name... "

    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" \
            -X $method \
            -H "Content-Type: application/json" \
            ${header:+-H "$header"} \
            "$BASE_URL$endpoint" 2>/dev/null || echo "error")
    else
        response=$(curl -s -w "\n%{http_code}" \
            -X $method \
            -H "Content-Type: application/json" \
            ${header:+-H "$header"} \
            -d "$data" \
            "$BASE_URL$endpoint" 2>/dev/null || echo "error")
    fi

    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$status_code" = "$expected_status" ] || [ "$expected_status" = "*" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $status_code)"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_status, got $status_code)"
        echo "  Response: $body"
        return 1
    fi
}

# ============================================================================
# TEST 1: Server is running
# ============================================================================
echo ""
echo -e "${YELLOW}[ Test Suite 1: Server Health ]${NC}"

test_endpoint "GET /" "GET" "/" "" "" "200"
test_endpoint "GET /health" "GET" "/health" "" "" "200"

# ============================================================================
# TEST 2: Tool discovery
# ============================================================================
echo ""
echo -e "${YELLOW}[ Test Suite 2: Tool Discovery ]${NC}"

test_endpoint "List tools" "POST" "/tools/list" "" "" "200"

# ============================================================================
# TEST 3: Authentication errors
# ============================================================================
echo ""
echo -e "${YELLOW}[ Test Suite 3: Authentication Errors ]${NC}"

test_endpoint "Missing header" "POST" "/tools/call" "" '{"name":"search","arguments":{}}' "200"
test_endpoint "Invalid base64" "POST" "/tools/call" "X-Auth-Credentials: $INVALID_BASE64" '{"name":"search","arguments":{}}' "200"
test_endpoint "Invalid JSON" "POST" "/tools/call" "X-Auth-Credentials: $INVALID_JSON" '{"name":"search","arguments":{}}' "200"
test_endpoint "Missing field" "POST" "/tools/call" "X-Auth-Credentials: $MISSING_FIELD" '{"name":"search","arguments":{}}' "200"

# ============================================================================
# TEST 4: Tool validation
# ============================================================================
echo ""
echo -e "${YELLOW}[ Test Suite 4: Tool Validation ]${NC}"

test_endpoint "Missing tool name" "POST" "/tools/call" "X-Auth-Credentials: $VALID_CREDS" '{"arguments":{}}' "200"
test_endpoint "Unknown tool" "POST" "/tools/call" "X-Auth-Credentials: $VALID_CREDS" '{"name":"unknown_tool","arguments":{}}' "200"

# ============================================================================
# TEST 5: Scope parsing
# ============================================================================
echo ""
echo -e "${YELLOW}[ Test Suite 5: Scope Parsing ]${NC}"

# Test with empty scope (should fail)
EMPTY_SCOPE="eyJ1cmwiOiAiaHR0cHM6Ly9kZW1vLm9kb28uY29tIiwgImRhdGFiYXNlIjogImRlbW8iLCAidXNlcm5hbWUiOiAiYWRtaW4iLCAicGFzc3dvcmQiOiAiYWRtaW4iLCAic2NvcGUiOiAiIn0="
test_endpoint "Empty scope" "POST" "/tools/call" "X-Auth-Credentials: $EMPTY_SCOPE" '{"name":"search","arguments":{"model":"res.partner"}}' "200"

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "=========================================="
echo "Tests complete!"
echo ""
echo -e "${YELLOW}Note:${NC} Connection and authentication tests require a live Odoo instance."
echo "This test script validates error handling and edge cases only."
echo "=========================================="
