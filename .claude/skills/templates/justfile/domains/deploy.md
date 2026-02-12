# Deployment Recipes

> Environment-driven deployment, build artifacts, and release patterns

## Standard deploy.just

```just
# deploy.just
# Deployment operations

# === Dispatch ===
deploy env: (_require_env "AWS_PROFILE")
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{env}}" in
        stage|staging) just deploy:stage ;;
        prod|production) just deploy:prod ;;
        *) echo "Unknown environment: {{env}}" && exit 1 ;;
    esac

# === Stage ===
deploy:stage: build
    @just _log "Deploying to staging..."
    ./scripts/deploy.sh stage
    @just _log "Staging deployment complete"

# === Production ===
deploy:prod: build (_require_env "AWS_PROFILE") (_confirm "Deploy to PRODUCTION?")
    @just _log "Deploying to production..."
    ./scripts/deploy.sh prod
    @just _log "Production deployment complete"

# === Build ===
build:
    @just _log "Building artifacts..."
    {{UV}} run python -m build
    @just _log "Build complete"

# === Verify ===
deploy:verify env:
    @just _log "Verifying {{env}} deployment..."
    ./scripts/verify-deploy.sh {{env}}
```

---

## Environment Dispatch Pattern

```just
deploy env:
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{env}}" in
        dev|development)
            just deploy:dev
            ;;
        stage|staging)
            just deploy:stage
            ;;
        prod|production)
            just deploy:prod
            ;;
        *)
            echo "Unknown environment: {{env}}"
            echo "Valid: dev, stage, prod"
            exit 1
            ;;
    esac
```

---

## Cloud Provider Patterns

### AWS

```just
deploy:aws env: (_require "aws") (_require_env "AWS_PROFILE")
    @just _log "Deploying to AWS {{env}}..."
    aws s3 sync dist/ s3://{{APP}}-{{env}}/
    aws cloudfront create-invalidation --distribution-id ${CF_DIST_ID} --paths "/*"

deploy:lambda env:
    @just _log "Deploying Lambda to {{env}}..."
    aws lambda update-function-code \
        --function-name {{APP}}-{{env}} \
        --zip-file fileb://dist/lambda.zip

deploy:ecs env:
    aws ecs update-service \
        --cluster {{APP}}-{{env}} \
        --service {{APP}} \
        --force-new-deployment
```

### GCP

```just
deploy:gcp env: (_require "gcloud")
    @just _log "Deploying to GCP {{env}}..."
    gcloud app deploy --project={{APP}}-{{env}} --quiet

deploy:cloud-run env:
    gcloud run deploy {{APP}} \
        --image={{REGISTRY}}/{{APP}}:{{VERSION}} \
        --project={{APP}}-{{env}} \
        --region=us-central1
```

### Kubernetes

```just
deploy:k8s env: (_require "kubectl")
    @just _log "Deploying to Kubernetes {{env}}..."
    kubectl config use-context {{env}}
    kubectl apply -f k8s/{{env}}/
    kubectl rollout status deployment/{{APP}}

deploy:helm env:
    helm upgrade --install {{APP}} ./helm/{{APP}} \
        -f helm/values-{{env}}.yaml \
        --namespace {{APP}}-{{env}}
```

### Vercel/Netlify

```just
deploy:vercel env="preview":
    @just _log "Deploying to Vercel..."
    vercel --prod={{if env == "prod" { "true" } else { "false" }}}

deploy:netlify:
    netlify deploy --prod
```

---

## Docker-Based Deployment

```just
deploy:docker env: docker:build
    @just _log "Deploying {{APP}}:{{VERSION}} to {{env}}..."

    # Tag for environment
    {{DOCKER}} tag {{IMAGE}}:{{VERSION}} {{REGISTRY}}/{{IMAGE}}:{{env}}
    {{DOCKER}} push {{REGISTRY}}/{{IMAGE}}:{{env}}

    # Tag as latest for this env
    {{DOCKER}} tag {{IMAGE}}:{{VERSION}} {{REGISTRY}}/{{IMAGE}}:{{env}}-latest
    {{DOCKER}} push {{REGISTRY}}/{{IMAGE}}:{{env}}-latest

    @just _log "Image pushed. Trigger deployment..."
    ./scripts/trigger-deploy.sh {{env}}
```

---

## Build Artifact Patterns

```just
# Python package
build:py:
    {{UV}} run python -m build
    @just _log "Built: dist/"

# Docker image
build:docker:
    {{DOCKER}} build -t {{IMAGE}}:{{VERSION}} .

# Lambda zip
build:lambda:
    @just _log "Building Lambda package..."
    mkdir -p dist
    cd src && zip -r ../dist/lambda.zip .
    @just _log "Built: dist/lambda.zip"

# Static site
build:static:
    npm run build
    @just _log "Built: dist/"

# All artifacts
build: build:py build:docker
    @just _log "All artifacts built"
```

---

## Release Patterns

```just
# Create release
release version: lint test build
    @just _log "Creating release {{version}}..."
    git tag -a "v{{version}}" -m "Release {{version}}"
    git push origin "v{{version}}"
    @just _log "Release v{{version}} created"

# Semantic release
release:patch: (_get_next_version "patch")
    just release $(just _get_next_version patch)

release:minor: (_get_next_version "minor")
    just release $(just _get_next_version minor)

release:major: (_get_next_version "major")
    just release $(just _get_next_version major)

[private]
_get_next_version type:
    #!/usr/bin/env bash
    current=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "0.0.0")
    IFS='.' read -r major minor patch <<< "$current"
    case "{{type}}" in
        major) echo "$((major+1)).0.0" ;;
        minor) echo "${major}.$((minor+1)).0" ;;
        patch) echo "${major}.${minor}.$((patch+1))" ;;
    esac
```

---

## Rollback Patterns

```just
# Quick rollback
rollback env: (_confirm "Rollback {{env}} to previous version?")
    @just _log "Rolling back {{env}}..."
    ./scripts/rollback.sh {{env}}

# Rollback to specific version
rollback:to env version: (_confirm "Rollback {{env}} to {{version}}?")
    @just _log "Rolling back {{env}} to {{version}}..."
    ./scripts/rollback.sh {{env}} {{version}}

# Kubernetes rollback
rollback:k8s env:
    kubectl config use-context {{env}}
    kubectl rollout undo deployment/{{APP}}
```

---

## Verification Patterns

```just
# Health check
deploy:verify env:
    @just _log "Verifying {{env}}..."
    curl -sf "https://{{env}}.{{APP}}.com/health" || \
        (echo "Health check failed" && exit 1)
    @just _log "{{env}} is healthy"

# Smoke tests
deploy:smoke env:
    @just _log "Running smoke tests on {{env}}..."
    ENV={{env}} {{PYTEST}} tests/smoke -v

# Full verification
deploy:verify:full env: (deploy:verify env) (deploy:smoke env)
    @just _log "Full verification complete for {{env}}"
```

