# CMS deployment matrix

The application is a FastAPI service and uses `Dockerfile` as the portable deployment baseline.

## Supported deployment configurations

- Render: `render.yaml`
- Railway: `railway.toml` (uses `Dockerfile`)
- Fly.io: `fly.toml` (uses `Dockerfile`, internal port 8000)
- Heroku-compatible PaaS: `Procfile`
- Vercel: `vercel.json` using `@vercel/python`
- Docker-compatible hosts: `Dockerfile`

## Runtime contract

The service starts from `backend.main:app` and listens on the platform-provided port where the platform requires one. Container deployments expose port 8000.

## Health check

`GET /` is the common health endpoint used by the deployment configurations.

## Platform rule

Do not duplicate application logic for each host. Deployment files only adapt the same FastAPI application to the platform runtime.
