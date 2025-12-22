# Authentication Flows

All authentication workflows for autom8_asana: PAT validation, Asana API access, and workspace discovery.

**Time:** ~5 minutes

---

## Prerequisites

- Complete [00-bootstrap.md](./00-bootstrap.md) first
- `ASANA_PAT` configured in environment

---

## Prerequisite Check

Validates Asana PAT is available before proceeding.

```
---
type: script
name: validate_pat
interpreter: bash
terminalRows: 12
---
# Prerequisite validation with actionable error
ENV_FILE="${HOME}/.config/autom8y/envs/autom8-asana/runbook.env"

# Check env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: Environment file not found: $ENV_FILE"
    echo ""
    echo "Run: cd \${AUTOM8Y_ASANA_PATH} && just setup-env"
    exit 1
fi

# Load environment
set -a
source "$ENV_FILE"
set +a

# Check required credentials
if [ -z "${ASANA_PAT:-}" ]; then
    echo "ERROR: Missing ASANA_PAT"
    echo ""
    echo "Add your Personal Access Token to:"
    echo "  $ENV_FILE"
    exit 1
fi

echo "PAT validated:"
echo "  ASANA_PAT: ****${ASANA_PAT: -4}"
echo "  ENV_FILE: $ENV_FILE"
```

---

## Get Current User

Verify PAT works by fetching current user info from Asana API.

```
---
type: http
name: get_current_user
---
GET https://app.asana.com/api/1.0/users/me
Authorization: Bearer {{env.ASANA_PAT}}
Accept: application/json
```

---

## List Workspaces

Get all workspaces accessible with your PAT.

```
---
type: http
name: list_workspaces
---
GET https://app.asana.com/api/1.0/workspaces
Authorization: Bearer {{env.ASANA_PAT}}
Accept: application/json
```

---

## Test Full Authentication Flow

End-to-end test: load environment, validate PAT, call API.

```
---
type: script
name: test_auth_flow
interpreter: bash
terminalRows: 15
---
# Load environment
ENV_FILE="${HOME}/.config/autom8y/envs/autom8-asana/runbook.env"
if [ -f "$ENV_FILE" ]; then
    set -a && source "$ENV_FILE" && set +a
fi

echo "=== Authentication Flow Test ==="
echo ""

# Step 1: Validate PAT format
if [ -z "${ASANA_PAT:-}" ]; then
    echo "FAIL: ASANA_PAT not set"
    exit 1
fi
echo "1. PAT configured: ****${ASANA_PAT: -4}"

# Step 2: Call API
echo "2. Testing API call..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${ASANA_PAT}" \
    -H "Accept: application/json" \
    "https://app.asana.com/api/1.0/users/me")

STATUS=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$STATUS" -eq 200 ]; then
    USER_NAME=$(echo "$BODY" | jq -r '.data.name')
    USER_EMAIL=$(echo "$BODY" | jq -r '.data.email')
    echo "   SUCCESS: Authenticated as $USER_NAME ($USER_EMAIL)"
else
    echo "   FAIL: API returned status $STATUS"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    exit 1
fi

# Step 3: Get workspace count
echo "3. Checking workspaces..."
WS_RESPONSE=$(curl -s \
    -H "Authorization: Bearer ${ASANA_PAT}" \
    -H "Accept: application/json" \
    "https://app.asana.com/api/1.0/workspaces")

WS_COUNT=$(echo "$WS_RESPONSE" | jq '.data | length')
echo "   Found $WS_COUNT workspace(s)"

echo ""
echo "=== Authentication Flow Complete ==="
```

---

## Quick Reference

| Component | Value |
|-----------|-------|
| API Base URL | `https://app.asana.com/api/1.0` |
| Auth Header | `Authorization: Bearer <PAT>` |
| Rate Limit | 1500 requests/minute |

---

## Troubleshooting

### Invalid Token (401)

```
Cause: PAT is invalid, expired, or revoked
ACTION: Generate new PAT at https://app.asana.com/0/my-apps
```

### Forbidden (403)

```
Cause: PAT doesn't have access to requested resource
ACTION: Check workspace permissions in Asana
```

### Rate Limited (429)

```
Cause: Too many requests
ACTION: Wait 60 seconds before retrying
```

