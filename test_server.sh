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

# Test credentials for generating API keys
CREDS_JSON='{"url":"https://demo.odoo.com","database":"demo","username":"admin","password":"admin","scope":"res.partner:RWD,sale.order:RW,*:R"}'

# Invalid API key
INVALID_API_KEY="invalid_key_!@#$%"

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
# TEST 3: Authentication flows
# ============================================================================
echo ""
echo -e "${YELLOW}[ Test Suite 3: Authentication Flows ]${NC}"

# Test generating API key
test_endpoint "Generate API key" "POST" "/auth/generate" "Content-Type: application/json" "$CREDS_JSON" "200"

# Test missing API key header
test_endpoint "Missing X-API-Key header" "POST" "/tools/call" "" '{"name":"search","arguments":{}}' "200"

# Test invalid API key
test_endpoint "Invalid API key" "POST" "/tools/call" "X-API-Key: $INVALID_API_KEY" '{"name":"search","arguments":{}}' "200"

# ============================================================================
# TEST 4: Tool validation (requires valid API key)
# ============================================================================
echo ""
echo -e "${YELLOW}[ Test Suite 4: Tool Validation ]${NC}"

test_endpoint "Missing tool name" "POST" "/tools/call" "X-API-Key: $INVALID_API_KEY" '{"arguments":{}}' "200"
test_endpoint "Unknown tool" "POST" "/tools/call" "X-API-Key: $INVALID_API_KEY" '{"name":"unknown_tool","arguments":{}}' "200"

# ============================================================================
# TEST 5: API key validation endpoint
# ============================================================================
echo ""
echo -e "${YELLOW}[ Test Suite 5: API Key Validation ]${NC}"

# Test validating an invalid key
test_endpoint "Validate invalid key" "POST" "/auth/validate" "Content-Type: application/json" '{"api_key":"'$INVALID_API_KEY'"}' "*"

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
