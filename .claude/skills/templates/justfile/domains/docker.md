# Docker Container Recipes

> Build, run, push, and compose patterns

## Standard docker.just

```just
# docker.just
# Container operations

# === Meta-task ===
docker: docker:build docker:run

# === Build ===
docker:build tag=TAG:
    @just _log "Building {{IMAGE}}:{{tag}}..."
    {{DOCKER}} build -t {{IMAGE}}:{{tag}} .

docker:build:no-cache tag=TAG:
    {{DOCKER}} build --no-cache -t {{IMAGE}}:{{tag}} .

# === Run ===
docker:run tag=TAG:
    @just _log "Running {{IMAGE}}:{{tag}}..."
    {{DOCKER}} run --rm -it {{IMAGE}}:{{tag}}

docker:run:detach tag=TAG name=APP:
    {{DOCKER}} run -d --name {{name}} {{IMAGE}}:{{tag}}

docker:shell tag=TAG:
    {{DOCKER}} run --rm -it {{IMAGE}}:{{tag}} /bin/sh

# === Push ===
docker:push tag=TAG:
    @just _log "Pushing to {{REGISTRY}}..."
    {{DOCKER}} tag {{IMAGE}}:{{tag}} {{REGISTRY}}/{{IMAGE}}:{{tag}}
    {{DOCKER}} push {{REGISTRY}}/{{IMAGE}}:{{tag}}

# === Cleanup ===
docker:clean:
    @just _log "Cleaning Docker resources..."
    {{DOCKER}} system prune -f
```

---

## Pattern Variations

### Multi-Platform Builds

```just
docker:build:multi tag=TAG:
    {{DOCKER}} buildx build \
        --platform linux/amd64,linux/arm64 \
        -t {{IMAGE}}:{{tag}} \
        --push \
        .

docker:build:amd64 tag=TAG:
    {{DOCKER}} build --platform linux/amd64 -t {{IMAGE}}:{{tag}}-amd64 .

docker:build:arm64 tag=TAG:
    {{DOCKER}} build --platform linux/arm64 -t {{IMAGE}}:{{tag}}-arm64 .
```

### Build Arguments

```just
docker:build tag=TAG:
    {{DOCKER}} build \
        --build-arg VERSION={{VERSION}} \
        --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
        --build-arg GIT_SHA=$(git rev-parse HEAD) \
        -t {{IMAGE}}:{{tag}} \
        .
```

### Multi-Stage Targets

```just
# Build specific stage
docker:build:dev:
    {{DOCKER}} build --target development -t {{IMAGE}}:dev .

docker:build:prod:
    {{DOCKER}} build --target production -t {{IMAGE}}:prod .

docker:build:test:
    {{DOCKER}} build --target test -t {{IMAGE}}:test .
```

---

## Docker Compose Patterns

```just
# === Compose Up/Down ===
compose:up:
    {{DOCKER}} compose up -d

compose:down:
    {{DOCKER}} compose down

compose:restart:
    {{DOCKER}} compose restart

# === Logs ===
compose:logs service="":
    {{DOCKER}} compose logs -f {{service}}

# === Exec ===
compose:shell service:
    {{DOCKER}} compose exec {{service}} /bin/sh

# === Build ===
compose:build:
    {{DOCKER}} compose build

compose:build:no-cache:
    {{DOCKER}} compose build --no-cache

# === Profiles ===
compose:up:dev:
    {{DOCKER}} compose --profile dev up -d

compose:up:test:
    {{DOCKER}} compose --profile test up -d
```

---

## Development Patterns

```just
# Development container with volume mounts
docker:dev:
    {{DOCKER}} run --rm -it \
        -v $(pwd)/src:/app/src \
        -v $(pwd)/tests:/app/tests \
        -p 8000:8000 \
        {{IMAGE}}:dev

# Development with hot reload
docker:dev:watch:
    {{DOCKER}} run --rm -it \
        -v $(pwd)/src:/app/src \
        -p 8000:8000 \
        {{IMAGE}}:dev \
        uvicorn app.main:app --reload --host 0.0.0.0
```

---

## Testing Patterns

```just
# Run tests in container
docker:test:
    {{DOCKER}} run --rm {{IMAGE}}:test pytest

# Run tests with coverage
docker:test:cov:
    {{DOCKER}} run --rm \
        -v $(pwd)/coverage:/app/coverage \
        {{IMAGE}}:test \
        pytest --cov=app --cov-report=html:coverage/

# Integration tests with dependencies
docker:test:int:
    {{DOCKER}} compose -f docker-compose.test.yml up -d
    {{DOCKER}} compose -f docker-compose.test.yml run --rm test pytest tests/integration
    {{DOCKER}} compose -f docker-compose.test.yml down
```

---

## Registry Patterns

```just
# Login to registry
docker:login:
    echo "${DOCKER_TOKEN}" | {{DOCKER}} login {{REGISTRY}} -u "${DOCKER_USER}" --password-stdin

# Pull latest
docker:pull tag="latest":
    {{DOCKER}} pull {{REGISTRY}}/{{IMAGE}}:{{tag}}

# Tag and push
docker:release tag:
    {{DOCKER}} tag {{IMAGE}}:latest {{REGISTRY}}/{{IMAGE}}:{{tag}}
    {{DOCKER}} push {{REGISTRY}}/{{IMAGE}}:{{tag}}
    {{DOCKER}} tag {{IMAGE}}:latest {{REGISTRY}}/{{IMAGE}}:latest
    {{DOCKER}} push {{REGISTRY}}/{{IMAGE}}:latest
```

---

## Cleanup Patterns

```just
docker:clean:
    @just _log "Pruning unused resources..."
    {{DOCKER}} system prune -f

docker:clean:all: (_confirm "Remove ALL Docker resources?")
    {{DOCKER}} system prune -a -f
    {{DOCKER}} volume prune -f

docker:clean:images:
    {{DOCKER}} image prune -a -f

docker:clean:volumes: (_confirm "Remove all unused volumes?")
    {{DOCKER}} volume prune -f

docker:clean:app:
    {{DOCKER}} rmi {{IMAGE}}:* 2>/dev/null || true
```

---

## CI Patterns

```just
# CI build with cache
docker:ci:build:
    {{DOCKER}} build \
        --cache-from {{REGISTRY}}/{{IMAGE}}:latest \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        -t {{IMAGE}}:{{VERSION}} \
        .

# CI push
docker:ci:push:
    {{DOCKER}} tag {{IMAGE}}:{{VERSION}} {{REGISTRY}}/{{IMAGE}}:{{VERSION}}
    {{DOCKER}} push {{REGISTRY}}/{{IMAGE}}:{{VERSION}}
    {{DOCKER}} tag {{IMAGE}}:{{VERSION}} {{REGISTRY}}/{{IMAGE}}:latest
    {{DOCKER}} push {{REGISTRY}}/{{IMAGE}}:latest
```

