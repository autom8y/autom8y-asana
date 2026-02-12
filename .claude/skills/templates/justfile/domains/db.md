# Database Operations Recipes

> Migrations, reset, seed, and environment-aware operations

## Standard db.just

```just
# db.just
# Database operations

# === Meta-task ===
db: db:migrate db:status

# === Migrations ===
db:migrate:
    @just _log "Running migrations..."
    {{UV}} run alembic upgrade head

db:migrate:down:
    {{UV}} run alembic downgrade -1

db:migrate:new name:
    {{UV}} run alembic revision --autogenerate -m "{{name}}"

db:status:
    {{UV}} run alembic current
    {{UV}} run alembic history --verbose

# === Reset (destructive) ===
db:reset: (_confirm "Reset database? This will DELETE all data.")
    @just _log "Resetting database..."
    {{UV}} run alembic downgrade base
    {{UV}} run alembic upgrade head
    @just _log "Database reset complete"

# === Seed ===
db:seed:
    @just _log "Seeding database..."
    {{UV}} run python scripts/seed.py

db:seed:dev:
    {{UV}} run python scripts/seed.py --env dev

# === Shell ===
db:shell:
    @just _require psql
    psql "${DATABASE_URL}"
```

---

## Environment-Aware Patterns

### Production Guards

```just
db:reset: (_require_env "DATABASE_URL") (_confirm "Reset database?")
    #!/usr/bin/env bash
    set -euo pipefail

    # Block in production
    if [[ "${DATABASE_URL}" == *"prod"* ]] || [[ "${ENV:-}" == "production" ]]; then
        echo "ERROR: Cannot reset production database" >&2
        exit 1
    fi

    just _log "Resetting database..."
    {{UV}} run alembic downgrade base
    {{UV}} run alembic upgrade head
```

### Environment-Specific Migrations

```just
db:migrate env="development":
    @just _log "Migrating {{env}} database..."
    ENV={{env}} {{UV}} run alembic upgrade head

db:migrate:prod: (_require_env "PROD_DATABASE_URL") (_confirm "Migrate PRODUCTION database?")
    DATABASE_URL="${PROD_DATABASE_URL}" {{UV}} run alembic upgrade head
```

---

## Migration Framework Patterns

### Alembic (SQLAlchemy)

```just
db:migrate:
    {{UV}} run alembic upgrade head

db:migrate:down steps="1":
    {{UV}} run alembic downgrade -{{steps}}

db:migrate:new name:
    {{UV}} run alembic revision --autogenerate -m "{{name}}"

db:migrate:history:
    {{UV}} run alembic history --verbose

db:migrate:current:
    {{UV}} run alembic current
```

### Django

```just
db:migrate:
    {{UV}} run python manage.py migrate

db:migrate:new app name:
    {{UV}} run python manage.py makemigrations {{app}} --name {{name}}

db:migrate:show:
    {{UV}} run python manage.py showmigrations

db:migrate:rollback app migration:
    {{UV}} run python manage.py migrate {{app}} {{migration}}
```

### Prisma

```just
db:migrate:
    npx prisma migrate deploy

db:migrate:dev name:
    npx prisma migrate dev --name {{name}}

db:migrate:reset: (_confirm "Reset database?")
    npx prisma migrate reset

db:generate:
    npx prisma generate
```

### golang-migrate

```just
db:migrate:
    migrate -path ./migrations -database "${DATABASE_URL}" up

db:migrate:down:
    migrate -path ./migrations -database "${DATABASE_URL}" down 1

db:migrate:new name:
    migrate create -ext sql -dir ./migrations -seq {{name}}
```

---

## Backup and Restore

```just
# Backup
db:backup name=`date +%Y%m%d_%H%M%S`:
    @just _log "Creating backup: {{name}}"
    pg_dump "${DATABASE_URL}" > backups/{{name}}.sql
    @just _log "Backup complete: backups/{{name}}.sql"

db:backup:prod: (_require_env "PROD_DATABASE_URL")
    @just _log "Backing up production..."
    pg_dump "${PROD_DATABASE_URL}" | gzip > backups/prod_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore
db:restore file: (_confirm "Restore database from {{file}}?")
    @just _log "Restoring from {{file}}..."
    psql "${DATABASE_URL}" < {{file}}

db:restore:gz file: (_confirm "Restore database from {{file}}?")
    gunzip -c {{file}} | psql "${DATABASE_URL}"
```

---

## Seed Patterns

```just
# Development seed
db:seed:
    {{UV}} run python scripts/seed.py

# Fixtures
db:seed:fixtures:
    {{UV}} run python scripts/load_fixtures.py

# Test data
db:seed:test:
    {{UV}} run python scripts/seed.py --test

# Factory-generated data
db:seed:factory count="100":
    {{UV}} run python scripts/seed.py --count {{count}}
```

---

## Shell and Query

```just
# Interactive shell
db:shell:
    @just _require psql
    psql "${DATABASE_URL}"

# MySQL variant
db:shell:mysql:
    @just _require mysql
    mysql -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}"

# Run SQL file
db:sql file:
    psql "${DATABASE_URL}" -f {{file}}

# Quick query
db:query sql:
    psql "${DATABASE_URL}" -c "{{sql}}"
```

---

## Health and Stats

```just
db:status:
    @just _log "Database status:"
    psql "${DATABASE_URL}" -c "SELECT version();"
    @just _log "Connection test: OK"

db:stats:
    psql "${DATABASE_URL}" -c "
        SELECT schemaname, tablename,
               pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
    "

db:connections:
    psql "${DATABASE_URL}" -c "
        SELECT count(*) as total_connections,
               count(*) FILTER (WHERE state = 'active') as active,
               count(*) FILTER (WHERE state = 'idle') as idle
        FROM pg_stat_activity;
    "
```

---

## Docker Database Patterns

```just
# Start local DB
db:up:
    {{DOCKER}} compose up -d postgres

db:down:
    {{DOCKER}} compose stop postgres

db:logs:
    {{DOCKER}} compose logs -f postgres

# Fresh local DB
db:fresh: db:down
    {{DOCKER}} compose rm -f postgres
    {{DOCKER}} volume rm {{APP}}_postgres_data 2>/dev/null || true
    {{DOCKER}} compose up -d postgres
    sleep 3
    just db:migrate
    just db:seed:dev
```

