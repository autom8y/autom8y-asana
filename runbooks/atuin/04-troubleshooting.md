# Troubleshooting

Common issues and solutions for autom8y-asana development and API usage.

**Time:** as needed

---

## Environment Issues

### ASANA_PAT Not Set

```
---
type: script
name: diagnose_pat
interpreter: bash
terminalRows: 15
---
echo "=== PAT Diagnostic ==="

ENV_FILE="${HOME}/.config/autom8y/envs/autom8y-asana/runbook.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: Environment file not found"
    echo "Location: $ENV_FILE"
    echo ""
    echo "FIX: Run 'just setup-env' to create it"
    exit 1
fi

echo "Environment file: $ENV_FILE"
echo ""

# Check if ASANA_PAT is in the file
if grep -q "^ASANA_PAT=" "$ENV_FILE"; then
    echo "ASANA_PAT is defined in file"

    # Load and check value
    set -a && source "$ENV_FILE" && set +a

    if [ -z "${ASANA_PAT:-}" ]; then
        echo "ERROR: ASANA_PAT is empty"
        echo ""
        echo "FIX: Edit $ENV_FILE and add your PAT"
    else
        echo "ASANA_PAT is set: ****${ASANA_PAT: -4}"
    fi
else
    echo "ERROR: ASANA_PAT not found in file"
    echo ""
    echo "FIX: Add this line to $ENV_FILE:"
    echo "  ASANA_PAT=your_personal_access_token"
fi
```

---

### Path Configuration Issues

```
---
type: script
name: diagnose_paths
interpreter: bash
terminalRows: 12
---
echo "=== Path Diagnostic ==="

PATHS_FILE="${HOME}/.config/autom8y/paths.env"

if [ ! -f "$PATHS_FILE" ]; then
    echo "ERROR: Paths file not found"
    echo "Location: $PATHS_FILE"
    echo ""
    echo "FIX: Run 'just bootstrap-paths' from the repository"
    exit 1
fi

echo "Paths file: $PATHS_FILE"
echo ""
echo "Contents:"
cat "$PATHS_FILE"
echo ""

# Load and check
source "$PATHS_FILE"
if [ -z "${AUTOM8Y_ASANA_PATH:-}" ]; then
    echo "ERROR: AUTOM8Y_ASANA_PATH not set"
    echo "FIX: Run 'just bootstrap-paths'"
elif [ ! -d "${AUTOM8Y_ASANA_PATH}" ]; then
    echo "ERROR: Path does not exist: ${AUTOM8Y_ASANA_PATH}"
    echo "FIX: Run 'just bootstrap-paths' to update"
else
    echo "AUTOM8Y_ASANA_PATH: ${AUTOM8Y_ASANA_PATH} (valid)"
fi
```

---

## Authentication Issues

### Test PAT Validity

```
---
type: script
name: test_pat_validity
interpreter: bash
terminalRows: 15
---
echo "=== PAT Validity Test ==="

# Load environment
ENV_FILE="${HOME}/.config/autom8y/envs/autom8y-asana/runbook.env"
if [ -f "$ENV_FILE" ]; then
    set -a && source "$ENV_FILE" && set +a
fi

if [ -z "${ASANA_PAT:-}" ]; then
    echo "ERROR: ASANA_PAT not configured"
    exit 1
fi

echo "Testing PAT: ****${ASANA_PAT: -4}"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${ASANA_PAT}" \
    "https://app.asana.com/api/1.0/users/me")

STATUS=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

case "$STATUS" in
    200)
        echo "SUCCESS: PAT is valid"
        echo "$BODY" | jq -r '.data | "Authenticated as: \(.name) (\(.email))"'
        ;;
    401)
        echo "ERROR: Invalid PAT (401 Unauthorized)"
        echo ""
        echo "Possible causes:"
        echo "  - PAT is incorrect or mistyped"
        echo "  - PAT has been revoked"
        echo "  - PAT has expired"
        echo ""
        echo "FIX: Generate a new PAT at https://app.asana.com/0/my-apps"
        ;;
    403)
        echo "ERROR: Forbidden (403)"
        echo "PAT is valid but lacks required permissions"
        ;;
    *)
        echo "ERROR: Unexpected status $STATUS"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
        ;;
esac
```

---

## Rate Limiting

### Check Rate Limit Status

```
---
type: script
name: check_rate_limit
interpreter: bash
terminalRows: 12
---
echo "=== Rate Limit Check ==="

# Load environment
ENV_FILE="${HOME}/.config/autom8y/envs/autom8y-asana/runbook.env"
if [ -f "$ENV_FILE" ]; then
    set -a && source "$ENV_FILE" && set +a
fi

if [ -z "${ASANA_PAT:-}" ]; then
    echo "ERROR: ASANA_PAT not configured"
    exit 1
fi

# Make request and capture headers
HEADERS=$(curl -s -I \
    -H "Authorization: Bearer ${ASANA_PAT}" \
    "https://app.asana.com/api/1.0/users/me")

echo "Rate limit headers:"
echo "$HEADERS" | grep -i "x-asana" || echo "(no rate limit headers found)"
echo ""
echo "If rate limited, you'll see:"
echo "  X-Asana-Retry-After: <seconds to wait>"
```

---

## Connection Issues

### Test Asana API Connectivity

```
---
type: script
name: test_connectivity
interpreter: bash
terminalRows: 12
---
echo "=== Connectivity Test ==="

# Test DNS resolution
echo "1. DNS resolution..."
if host app.asana.com > /dev/null 2>&1; then
    echo "   SUCCESS: app.asana.com resolves"
else
    echo "   ERROR: Cannot resolve app.asana.com"
    echo "   Check your DNS settings"
    exit 1
fi

# Test HTTPS connection
echo "2. HTTPS connection..."
if curl -s --max-time 10 -o /dev/null -w "%{http_code}" https://app.asana.com > /dev/null; then
    echo "   SUCCESS: HTTPS connection works"
else
    echo "   ERROR: Cannot connect to app.asana.com"
    echo "   Check firewall/proxy settings"
    exit 1
fi

# Test API endpoint
echo "3. API endpoint..."
STATUS=$(curl -s --max-time 10 -o /dev/null -w "%{http_code}" \
    "https://app.asana.com/api/1.0/users/me" \
    -H "Authorization: Bearer invalid")

if [ "$STATUS" = "401" ]; then
    echo "   SUCCESS: API endpoint responds (401 expected without valid PAT)"
else
    echo "   WARNING: Unexpected status $STATUS"
fi

echo ""
echo "=== Connectivity OK ==="
```

---

## Development Server Issues

### Port Already in Use

```
---
type: script
name: check_port
interpreter: bash
terminalRows: 10
---
PORT="${1:-8000}"
echo "=== Checking port $PORT ==="

if lsof -i :$PORT > /dev/null 2>&1; then
    echo "Port $PORT is in use by:"
    lsof -i :$PORT
    echo ""
    echo "FIX: Either stop the process or use a different port:"
    echo "  just serve-api port=8080"
else
    echo "Port $PORT is available"
fi
```

---

### Check Server Health

```
---
type: script
name: diagnose_server
interpreter: bash
terminalRows: 12
---
PORT="${1:-8000}"
URL="http://localhost:$PORT/health"

echo "=== Server Diagnostic ==="
echo "Checking: $URL"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 5 "$URL" 2>&1)
STATUS=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

case "$STATUS" in
    200)
        echo "SUCCESS: Server is healthy"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
        ;;
    000)
        echo "ERROR: Cannot connect to server"
        echo ""
        echo "Possible causes:"
        echo "  - Server not running"
        echo "  - Wrong port"
        echo ""
        echo "FIX: Start the server with: just serve-api"
        ;;
    *)
        echo "ERROR: Server returned status $STATUS"
        echo "$BODY"
        ;;
esac
```

---

## Quick Reference

| Issue | Diagnostic | Solution |
|-------|------------|----------|
| PAT not set | `diagnose_pat` | Add PAT to env file |
| Invalid PAT | `test_pat_validity` | Regenerate at Asana |
| Path not found | `diagnose_paths` | Run `just bootstrap-paths` |
| Rate limited | `check_rate_limit` | Wait for retry-after |
| Can't connect | `test_connectivity` | Check network/firewall |
| Server not responding | `diagnose_server` | Start with `just serve-api` |
| Port in use | `check_port` | Use alternate port |

