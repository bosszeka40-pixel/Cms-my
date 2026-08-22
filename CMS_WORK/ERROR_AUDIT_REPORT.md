# Strict CMS Audit Report

## Phase 1: Core review

Checked area:
- backend/cms_core.py
- database models
- authentication layer
- plugin system
- learning memory
- wallet/trade storage

## Findings

### HIGH-001 Database separation risk

Finding:
- cms_core.py defines a default sqlite database (`cms_core.db`).
- The application entry point also uses another market database (`cms_v12.db`).

Risk:
- Production data can be split between multiple sqlite files.
- Backups and migrations become difficult.

Recommendation:
- Create one database configuration source through environment variables.

### HIGH-002 Schema migration weakness

Finding:
- Schema changes are partially handled with manual ALTER TABLE checks.

Risk:
- Future migrations may fail when multiple environments exist.

Recommendation:
- Add Alembic migrations.

### MEDIUM-001 Session management review required

Finding:
- Authentication uses session storage and database users.

Risk:
- Production deployment requires strict secret management and HTTPS-only sessions.

Recommendation:
- Enforce production security settings.

### MEDIUM-002 Learning memory trust boundary

Finding:
- Successful strategy tests can create new adaptive strategy entries.

Risk:
- Bad test data could influence catalog logic.

Recommendation:
- Add validation thresholds and audit approval.

## Next audit targets

1. hft_brain.py
2. bot.py
3. strategy_manager
4. risk_management
5. API endpoints
6. deployment configuration
