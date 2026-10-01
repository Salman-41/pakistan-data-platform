# Deployment

Local API + web are verified at test/build level. Compose provides API, web, optional Redis, and opt-in PostgreSQL. No hosted demo is deployed. Configure HTTPS, trusted proxy/client-IP handling, access controls for writes, resource budgets and backup policy before internet exposure. Current API is public read-only analytics and has an in-process limiter, not a shared quota.

Postgres: set PAKDATA_DATABASE_URL, run `alembic upgrade head`, then `python -m warehouse.load --help` for mirror import. This integration requires a real service test before relying on it. Never use example passwords in production. A production Next.js API URL is compiled at build time.
