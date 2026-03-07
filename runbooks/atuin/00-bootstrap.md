# Bootstrap autom8y-asana Environment

First-time environment setup for the autom8y-asana SDK and API service. Configures Asana Personal Access Token (PAT) for API access.

**Time:** ~3 minutes

**Prerequisites:**
- Atuin Desktop installed
- Asana Personal Access Token (PAT) from [Asana Developer Console](https://app.asana.com/0/my-apps)

**Environment location:** `~/.config/autom8y/envs/autom8y-asana/runbook.env`

---

## Path Configuration

Auto-configures repository paths on first run. This enables portable runbooks that work regardless of where you cloned the repository.

```
---
type: script
name: configure_paths
interpreter: bash
terminalRows: 10
---
PATHS_FILE="${HOME}/.config/autom8y/paths.env"
REPO_PATH=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
VAR_NAME="AUTOM8Y_ASANA_PATH"

if [ ! -f "$PATHS_FILE" ] || ! grep -q "^export ${VAR_NAME}=" "$PATHS_FILE" 2>/dev/null; then
    echo "=== Auto-configuring repository path ==="
    mkdir -p "$(dirname "$PATHS_FILE")"
    [ ! -f "$PATHS_FILE" ] && printf '%s\n' "# autom8y Repository Paths" "" > "$PATHS_FILE"
    echo "export ${VAR_NAME}=\"${REPO_PATH}\"" >> "$PATHS_FILE"
    echo "Configured: ${VAR_NAME}=${REPO_PATH}"
else
    echo "Path already configured."
fi

source "$PATHS_FILE"
echo "AUTOM8Y paths loaded from: $PATHS_FILE"
echo "  AUTOM8Y_ASANA_PATH: ${AUTOM8Y_ASANA_PATH:-not set}"
```

---

## Step 1: Setup Environment

Create your runbook environment file (first time only).

```
---
type: run
name: setup_env
---
cd ${AUTOM8Y_ASANA_PATH} && just setup-env
```

**Note:** After setup, edit `~/.config/autom8y/envs/autom8y-asana/runbook.env` to add your `ASANA_PAT` from the Asana Developer Console.

---

## Step 2: Environment Check

Verify required environment variables are set.

```
---
type: run
name: check_env
---
cd ${AUTOM8Y_ASANA_PATH} && just check-env
```

---

## Step 3: Verify Asana Connectivity

Test that your PAT can authenticate with the Asana API.

```
---
type: script
name: test_asana_api
interpreter: bash
terminalRows: 12
---
# Load environment
ENV_FILE="${HOME}/.config/autom8y/envs/autom8y-asana/runbook.env"
if [ -f "$ENV_FILE" ]; then
    set -a && source "$ENV_FILE" && set +a
fi

if [ -z "${ASANA_PAT:-}" ]; then
    echo "ERROR: ASANA_PAT not set"
    echo "Run: just setup-env, then add your PAT"
    exit 1
fi

echo "Testing Asana API connectivity..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer ${ASANA_PAT}" \
    "https://app.asana.com/api/1.0/users/me")

STATUS=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$STATUS" -eq 200 ]; then
    echo "SUCCESS: Asana API reachable"
    echo "$BODY" | jq -r '.data | "User: \(.name) (\(.email))"'
else
    echo "ERROR: Asana API returned status $STATUS"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    exit 1
fi
```

---

## Bootstrap Complete

If all steps passed, your environment is configured correctly.

**Next steps:**
- `01-authentication.md` - PAT validation and Asana API testing
- `02-local-development.md` - Development server and testing
