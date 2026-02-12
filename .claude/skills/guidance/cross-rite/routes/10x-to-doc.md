# 10x-to-Doc Handoff Checklist

> Artifact checklist for handing off documentation work to docs.

## When to Use

This route is **required** when:
- New user-facing feature implemented
- API endpoints added, modified, or deprecated
- Configuration options changed (environment variables, settings)
- Breaking changes affecting existing users
- User workflows significantly altered

## Artifact Checklist

### Feature Summary

- [ ] Feature name and one-sentence description
- [ ] User-facing behavior documented (what users will see/do)
- [ ] Screenshots or diagrams (if UI changes)
- [ ] Prerequisites for using the feature
- [ ] Limitations or known constraints

**Location**: Handoff artifact or `docs/features/` draft

**Format**:
```markdown
## Feature: Dark Mode Toggle

**Description**: Users can switch between light and dark themes in application settings.

**User Behavior**:
1. Navigate to Settings > Appearance
2. Toggle "Dark Mode" switch
3. Theme applies immediately, persists across sessions

**Prerequisites**: User must be logged in

**Limitations**: Custom themes not supported in v1
```

### API Changes

- [ ] New endpoints documented (path, method, parameters, response)
- [ ] Modified endpoints documented (what changed, migration path)
- [ ] Deprecated endpoints marked with deprecation timeline
- [ ] Request/response examples provided
- [ ] Error responses documented
- [ ] Authentication requirements noted

**Format**:
```markdown
### POST /api/v2/preferences

**Added in**: v2.1.0

**Request**:
```json
{
  "theme": "dark",
  "notifications": true
}
```

**Response** (200 OK):
```json
{
  "id": "pref_123",
  "updated_at": "2026-01-05T12:00:00Z"
}
```

**Errors**:
- 400: Invalid theme value
- 401: Authentication required
```

### Configuration Changes

- [ ] New environment variables documented
- [ ] Modified environment variables with migration notes
- [ ] Deprecated configuration with removal timeline
- [ ] Default values and valid ranges specified
- [ ] Example configuration files updated

**Format**:
```
| Variable | Added/Changed | Default | Description |
|----------|---------------|---------|-------------|
| THEME_DEFAULT | Added | light | Default theme for new users |
| SESSION_TIMEOUT | Changed | 30m (was 1h) | Session expiry duration |
| OLD_SETTING | Deprecated | - | Remove in v3.0, use NEW_SETTING |
```

### Migration Notes

- [ ] Breaking changes clearly identified
- [ ] Step-by-step migration instructions
- [ ] Before/after examples
- [ ] Rollback guidance (if migration fails)
- [ ] Timeline for deprecation (if applicable)

**Format**:
```markdown
## Migration: Settings API v1 to v2

### Breaking Changes
- `GET /settings` response schema changed
- `theme` field moved from root to `preferences.theme`

### Migration Steps
1. Update API client to use `/api/v2/settings`
2. Update response parsing for new schema
3. Test in staging environment
4. Deploy during maintenance window

### Before (v1)
```json
{ "theme": "dark", "lang": "en" }
```

### After (v2)
```json
{ "preferences": { "theme": "dark" }, "locale": "en-US" }
```
```

### User Impact Assessment

- [ ] Who is affected (all users, specific roles, specific plans)
- [ ] Is user action required (opt-in, mandatory migration, automatic)
- [ ] Communication needed (release notes, email, in-app notification)
- [ ] Training materials needed (help articles, videos, tooltips)

## Validation

Run before handoff:
```bash
ari hook handoff-validate --route=doc
```

Expected output:
```
[PASS] Feature summary provided in handoff artifact
[PASS] API changes documented: 2 new endpoints, 1 deprecated
[PASS] Configuration changes documented: 3 new env vars
[WARN] Migration notes: breaking change detected, ensure rollback documented
[INFO] User impact: affects all users, communication recommended
```

## HANDOFF Artifact Template

Create `HANDOFF-10x-dev-to-docs-YYYY-MM-DD.md`:

```yaml
---
artifact_id: HANDOFF-10x-dev-to-docs-2026-01-05
schema_version: "1.0"
source_rite: 10x-dev
target_rite: docs
handoff_type: assessment
priority: medium
blocking: false
initiative: "feature-name"
created_at: "2026-01-05T12:00:00Z"
status: pending
items:
  - id: DOC-001
    summary: "Document dark mode toggle feature for end users"
    priority: medium
    assessment_questions:
      - "What user-facing documentation is needed?"
      - "Should this be a help article or tooltip?"
      - "Are screenshots needed?"
  - id: DOC-002
    summary: "Update API documentation for preferences endpoint"
    priority: high
    assessment_questions:
      - "OpenAPI spec update or manual docs?"
      - "Are code examples in all supported languages needed?"
source_artifacts:
  - "src/api/preferences.ts"
  - "docs/drafts/dark-mode-feature.md"
---
```

## After Handoff

Doc rite will:
1. Review feature for documentation scope
2. Determine documentation deliverables (help article, API docs, changelog)
3. Create or update documentation
4. Request review from source rite for accuracy
5. Return HANDOFF-RESPONSE with published documentation links

## Common Issues

| Issue | Resolution |
|-------|------------|
| Vague feature description | Provide user journey, not implementation details |
| Missing API examples | Include request/response for happy path and common errors |
| No migration path | Document before/after, even for non-breaking changes |
| Unclear user impact | Specify who, what action, and when |
| No screenshots | Provide UI mockups or staging environment access |
