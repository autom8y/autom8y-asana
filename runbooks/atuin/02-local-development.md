# Local Development

Development workflows for autom8_asana: running the API server, testing, and Docker builds.

**Time:** varies

---

## Prerequisites

- Complete [00-bootstrap.md](./00-bootstrap.md) first
- Complete [01-authentication.md](./01-authentication.md) (PAT configured)

---

## Environment Check

Verify environment is configured before development.

```
---
type: run
name: check_env
---
cd ${AUTOM8Y_ASANA_PATH} && just check-env
```

---

## Start Development Server

Start the API server with hot reload for development.

```
---
type: run
name: serve_api
pty: true
global: true
terminalRows: 15
---
cd ${AUTOM8Y_ASANA_PATH} && just serve-api
```

**Note:** Server runs at `http://localhost:8000` by default. Use `just serve-api port=8080` for alternate port.

---

## Health Check

Verify the development server is running.

```
---
type: run
name: health_check
---
cd ${AUTOM8Y_ASANA_PATH} && just health
```

---

## Run Tests

Execute the test suite.

```
---
type: run
name: run_tests
terminalRows: 20
---
cd ${AUTOM8Y_ASANA_PATH} && just test
```

---

## Run Tests with Coverage

Execute tests with coverage report.

```
---
type: run
name: run_tests_coverage
terminalRows: 20
---
cd ${AUTOM8Y_ASANA_PATH} && just test-cov
```

---

## Code Quality Checks

Run linting, formatting, and type checking.

```
---
type: run
name: check_all
terminalRows: 15
---
cd ${AUTOM8Y_ASANA_PATH} && just check-all
```

---

## Docker Build

Build the Docker image for deployment.

```
---
type: run
name: docker_build
terminalRows: 15
---
cd ${AUTOM8Y_ASANA_PATH} && just docker-build
```

---

## Docker Run

Run the service in Docker container.

```
---
type: run
name: docker_run
pty: true
global: true
terminalRows: 15
---
cd ${AUTOM8Y_ASANA_PATH} && just docker-run
```

---

## Docker Build and Run

Build and run in one step.

```
---
type: run
name: docker_serve
pty: true
global: true
terminalRows: 15
---
cd ${AUTOM8Y_ASANA_PATH} && just docker-serve
```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `just serve-api` | Start dev server (port 8000) |
| `just serve-api port=8080` | Start on alternate port |
| `just health` | Check server health |
| `just test` | Run tests |
| `just test-cov` | Tests with coverage |
| `just check-all` | Format + lint + typecheck + test |
| `just docker-build` | Build Docker image |
| `just docker-run` | Run in Docker |
| `just docker-serve` | Build and run Docker |

---

## Troubleshooting

### Port Already in Use

```
Cause: Another process using port 8000
ACTION: Use alternate port: just serve-api port=8080
```

### Missing Dependencies

```
Cause: Dependencies not installed
ACTION: Run: uv sync
```

### Import Errors

```
Cause: Package not in editable mode
ACTION: Run: uv pip install -e .
```

