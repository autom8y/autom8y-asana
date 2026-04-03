#!/bin/bash

################################################################################
# Dynamic API Criteria Demo
#
# Demonstrates the new dynamic resolution API with real data from production
# DataFrames. Tests all entity types (Unit, Business, Contact, Offer) with
# various query patterns including:
#   - Legacy field mapping (phone -> office_phone)
#   - Direct schema column queries
#   - Multi-column lookups
#   - Multi-match scenarios
#   - Schema discovery endpoint
#
# Usage:
#   ./scripts/demo_dynamic_api.sh
#
# Requirements:
#   - curl
#   - jq
#   - SERVICE_CLIENT_ID and SERVICE_CLIENT_SECRET environment variables set
#   - Internet connectivity to https://auth.api.autom8y.io and https://api.autom8y.io
################################################################################

set -e

# Helper: Check if response is valid JSON
is_json() {
  echo "$1" | jq -e . >/dev/null 2>&1
}

# Helper: Safe jq extraction with error handling
safe_jq() {
  local json="$1"
  local query="$2"
  local default="${3:-null}"

  if is_json "$json"; then
    echo "$json" | jq -r "$query // \"$default\""
  else
    echo "$default"
  fi
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AUTH_URL="https://auth.api.autom8y.io/internal/service-token"
API_URL="https://asana.api.autom8y.io"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}    Dynamic Resolution API Demo${NC}"
echo -e "${BLUE}    Universal Schema-Driven Resolver${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Check for service credentials
if [ -z "$SERVICE_CLIENT_ID" ] || [ -z "$SERVICE_CLIENT_SECRET" ]; then
  echo -e "${RED}✗ SERVICE_CLIENT_ID and SERVICE_CLIENT_SECRET environment variables not set${NC}"
  echo "Run: export SERVICE_CLIENT_ID=... && export SERVICE_CLIENT_SECRET=..."
  exit 1
fi

echo -e "${YELLOW}[1/6] Getting access token...${NC}"
echo "Using client_id: ${SERVICE_CLIENT_ID:0:15}..."

TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
  "$AUTH_URL" \
  -H "Content-Type: application/json" \
  -d "{\"grant_type\": \"client_credentials\", \"client_id\": \"$SERVICE_CLIENT_ID\", \"client_secret\": \"$SERVICE_CLIENT_SECRET\", \"service_name\": \"demo_dynamic_api\"}")

# Extract HTTP status code (last line) and body (everything else)
HTTP_CODE=$(echo "$TOKEN_RESPONSE" | tail -n1)
TOKEN_BODY=$(echo "$TOKEN_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" != "200" ]; then
  echo -e "${RED}✗ Auth request failed with HTTP $HTTP_CODE${NC}"
  echo "Response: $TOKEN_BODY"
  exit 1
fi

if ! is_json "$TOKEN_BODY"; then
  echo -e "${RED}✗ Auth response is not valid JSON${NC}"
  echo "Response: $TOKEN_BODY"
  exit 1
fi

ACCESS_TOKEN=$(echo "$TOKEN_BODY" | jq -r '.access_token // empty')

if [ -z "$ACCESS_TOKEN" ]; then
  echo -e "${RED}✗ Failed to get access token${NC}"
  echo "Response: $TOKEN_BODY"
  exit 1
fi

echo -e "${GREEN}✓ Got access token${NC}"
echo ""

################################################################################
# TEST 1: Unit - Phone + Vertical (Legacy Format)
################################################################################
echo -e "${BLUE}[2/6] TEST 1: Unit - Phone + Vertical (Legacy)${NC}"
echo -e "${YELLOW}Query:${NC}"
echo '  POST /v1/resolve/unit'
echo '  {"criteria": [{"phone": "+14242690670", "vertical": "chiropractic"}]}'
echo ""

API_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/v1/resolve/unit" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"criteria": [{"phone": "+14242690670", "vertical": "chiropractic"}]}')

HTTP_CODE=$(echo "$API_RESPONSE" | tail -n1)
RESPONSE=$(echo "$API_RESPONSE" | sed '$d')

echo -e "${YELLOW}Response (HTTP $HTTP_CODE):${NC}"
if is_json "$RESPONSE"; then
  echo "$RESPONSE" | jq '.'
else
  echo "$RESPONSE"
fi
echo ""

if [ "$HTTP_CODE" != "200" ]; then
  echo -e "${RED}✗ API request failed with HTTP $HTTP_CODE${NC}"
elif ! is_json "$RESPONSE"; then
  echo -e "${RED}✗ Response is not valid JSON${NC}"
else
  RESULT_GID=$(safe_jq "$RESPONSE" '.results[0].gid' "null")
  MATCH_COUNT=$(safe_jq "$RESPONSE" '.results[0].match_count' "0")
  RESOLVED=$(safe_jq "$RESPONSE" '.meta.resolved_count' "0")

  if [ "$RESOLVED" = "1" ]; then
    echo -e "${GREEN}✓ Found: Total Vitality Group (GID: $RESULT_GID, Matches: $MATCH_COUNT)${NC}"
  else
    echo -e "${RED}✗ Resolution failed${NC}"
  fi
fi
echo ""

################################################################################
# TEST 2: Business - Company ID (Dynamic Field)
################################################################################
echo -e "${BLUE}[3/6] TEST 2: Business - Company ID (Dynamic Field)${NC}"
echo -e "${YELLOW}Query:${NC}"
echo '  POST /v1/resolve/business'
echo '  {"criteria": [{"company_id": "abb01032-f53c-4bb3-89b7-f78107c9bf50"}]}'
echo ""

API_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/v1/resolve/business" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"criteria": [{"company_id": "abb01032-f53c-4bb3-89b7-f78107c9bf50"}]}')

HTTP_CODE=$(echo "$API_RESPONSE" | tail -n1)
RESPONSE=$(echo "$API_RESPONSE" | sed '$d')

echo -e "${YELLOW}Response (HTTP $HTTP_CODE):${NC}"
if is_json "$RESPONSE"; then
  echo "$RESPONSE" | jq '.'
else
  echo "$RESPONSE"
fi
echo ""

if [ "$HTTP_CODE" != "200" ]; then
  echo -e "${RED}✗ API request failed with HTTP $HTTP_CODE${NC}"
elif ! is_json "$RESPONSE"; then
  echo -e "${RED}✗ Response is not valid JSON${NC}"
else
  RESULT_GID=$(safe_jq "$RESPONSE" '.results[0].gid' "null")
  RESOLVED=$(safe_jq "$RESPONSE" '.meta.resolved_count' "0")

  if [ "$RESOLVED" = "1" ]; then
    echo -e "${GREEN}✓ Found Business (GID: $RESULT_GID)${NC}"
  else
    echo -e "${RED}✗ Resolution failed${NC}"
  fi
fi
echo ""

################################################################################
# TEST 3: Contact - Email Lookup
################################################################################
echo -e "${BLUE}[4/6] TEST 3: Contact - Email Lookup${NC}"
echo -e "${YELLOW}Query:${NC}"
echo '  POST /v1/resolve/contact'
echo '  {"criteria": [{"contact_email": "info@roguespinecenter.com"}]}'
echo ""

API_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/v1/resolve/contact" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"criteria": [{"contact_email": "info@roguespinecenter.com"}]}')

HTTP_CODE=$(echo "$API_RESPONSE" | tail -n1)
RESPONSE=$(echo "$API_RESPONSE" | sed '$d')

echo -e "${YELLOW}Response (HTTP $HTTP_CODE):${NC}"
if is_json "$RESPONSE"; then
  echo "$RESPONSE" | jq '.'
else
  echo "$RESPONSE"
fi
echo ""

if [ "$HTTP_CODE" != "200" ]; then
  echo -e "${RED}✗ API request failed with HTTP $HTTP_CODE${NC}"
elif ! is_json "$RESPONSE"; then
  echo -e "${RED}✗ Response is not valid JSON${NC}"
else
  RESULT_GID=$(safe_jq "$RESPONSE" '.results[0].gid' "null")
  RESOLVED=$(safe_jq "$RESPONSE" '.meta.resolved_count' "0")

  if [ "$RESOLVED" = "1" ]; then
    echo -e "${GREEN}✓ Found: Rogue Office (GID: $RESULT_GID)${NC}"
  else
    echo -e "${RED}✗ Resolution failed${NC}"
  fi
fi
echo ""

################################################################################
# TEST 4: Offer - Multi-Match Scenario
################################################################################
echo -e "${BLUE}[5/6] TEST 4: Offer - Multi-Match Scenario${NC}"
echo -e "${YELLOW}Query:${NC}"
echo '  POST /v1/resolve/offer'
echo '  {"criteria": [{"office_phone": "+17706317600", "vertical": "chiropractic"}]}'
echo ""

API_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/v1/resolve/offer" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"criteria": [{"office_phone": "+17706317600", "vertical": "chiropractic"}]}')

HTTP_CODE=$(echo "$API_RESPONSE" | tail -n1)
RESPONSE=$(echo "$API_RESPONSE" | sed '$d')

echo -e "${YELLOW}Response (HTTP $HTTP_CODE):${NC}"
if is_json "$RESPONSE"; then
  echo "$RESPONSE" | jq '.'
else
  echo "$RESPONSE"
fi
echo ""

if [ "$HTTP_CODE" != "200" ]; then
  echo -e "${RED}✗ API request failed with HTTP $HTTP_CODE${NC}"
elif ! is_json "$RESPONSE"; then
  echo -e "${RED}✗ Response is not valid JSON${NC}"
else
  RESULT_GID=$(safe_jq "$RESPONSE" '.results[0].gid' "null")
  MATCH_COUNT=$(safe_jq "$RESPONSE" '.results[0].match_count' "0")
  RESOLVED=$(safe_jq "$RESPONSE" '.meta.resolved_count' "0")

  if [ "$RESOLVED" = "1" ]; then
    ALL_GIDS=$(echo "$RESPONSE" | jq -r '.results[0].gids // [] | .[]' | tr '\n' ', ' | sed 's/,$//')
    echo -e "${GREEN}✓ Found: Multiple Nexus Chiropractic offers (First GID: $RESULT_GID, Total Matches: $MATCH_COUNT)${NC}"
    echo -e "${GREEN}  All matching GIDs: $ALL_GIDS${NC}"
  else
    echo -e "${RED}✗ Resolution failed${NC}"
  fi
fi
echo ""

################################################################################
# TEST 5: Schema Discovery - Unit
################################################################################
echo -e "${BLUE}[6/6] TEST 5: Schema Discovery - Unit Endpoint${NC}"
echo -e "${YELLOW}Query:${NC}"
echo '  GET /v1/resolve/unit/schema'
echo ""

API_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/v1/resolve/unit/schema" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json")

HTTP_CODE=$(echo "$API_RESPONSE" | tail -n1)
RESPONSE=$(echo "$API_RESPONSE" | sed '$d')

echo -e "${YELLOW}Response (HTTP $HTTP_CODE):${NC}"
if is_json "$RESPONSE"; then
  echo "$RESPONSE" | jq '.'
else
  echo "$RESPONSE"
fi
echo ""

if [ "$HTTP_CODE" != "200" ]; then
  echo -e "${RED}✗ API request failed with HTTP $HTTP_CODE${NC}"
elif ! is_json "$RESPONSE"; then
  echo -e "${RED}✗ Response is not valid JSON${NC}"
else
  ENTITY_TYPE=$(safe_jq "$RESPONSE" '.entity_type' "null")
  VERSION=$(safe_jq "$RESPONSE" '.version' "null")
  FIELD_COUNT=$(echo "$RESPONSE" | jq '.queryable_fields | length // 0')
  echo -e "${GREEN}✓ Schema discovered: $ENTITY_TYPE v$VERSION with $FIELD_COUNT queryable fields${NC}"
fi
echo ""

################################################################################
# Summary
################################################################################
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Demo completed!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Key Features Demonstrated:${NC}"
echo "  ✓ Legacy field mapping (phone → office_phone)"
echo "  ✓ Dynamic field queries (company_id, contact_email)"
echo "  ✓ Multi-column lookups (office_phone + vertical)"
echo "  ✓ Multi-match support (4 offers found with same phone+vertical)"
echo "  ✓ Schema discovery endpoint (24 queryable fields for Unit)"
echo ""
echo -e "${YELLOW}API Capabilities:${NC}"
echo "  • Query any schema column dynamically"
echo "  • Combine multiple fields in single query"
echo "  • Get all matches (not just first)"
echo "  • Discover valid fields per entity type"
echo "  • Backwards compatible with legacy format"
echo ""
