# PPT Hunter Supabase Setup Guide

This is the Supabase-first, no-Docker version of `setup_guide.md`.

The AWS guide configures S3 as PPT Hunter's private file-storage backend. For a Supabase-first setup, Supabase can replace both PostgreSQL and private file storage, but it does not replace the whole worker stack.

## What Supabase Replaces

Use Supabase for:

- PostgreSQL records: search runs, documents, metadata, dedupe hashes, statuses, summaries.
- Private file storage: downloaded `.ppt` and `.pptx` files, generated ZIP exports, extracted artifacts later.
- Optional auth later: user login, teams, row level security, admin roles.

Supabase does not replace:

- FastAPI backend.
- Celery worker.
- Redis queue.
- Elasticsearch search index.
- Next.js frontend hosting.
- Large-scale scraping/search provider APIs.

Recommended managed replacements for the rest:

- FastAPI and Celery worker: Render, Fly.io, Railway, DigitalOcean, or a small VPS.
- Redis: Upstash Redis, Redis Cloud, Railway Redis, or self-hosted Redis.
- Elasticsearch: Elastic Cloud, Bonsai, OpenSearch, Meilisearch, or Typesense.
- Frontend: Vercel, Netlify, Render, or the same server as the API.

## Target Architecture

```text
Next.js UI
  -> FastAPI API
      -> Supabase Postgres
      -> Redis
      -> Celery worker
          -> Search providers
          -> Supabase Storage
          -> Elasticsearch
```

## Part 1: Create Supabase Project

1. Go to `https://supabase.com`.
2. Create a new project.
3. Save these values from Project Settings:
   - Project URL
   - Service role key
   - Database password
   - Database connection string

Keep the service role key server-side only. Do not put it in the Next.js browser bundle.

## Part 2: Configure Supabase Postgres

In Supabase:

1. Open Project Settings.
2. Open Database.
3. Copy the connection string.
4. Use the pooled connection string for the web API.
5. Use `sslmode=require`.

Example `.env` value:

```env
DATABASE_URL=postgresql+psycopg://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres?sslmode=require
```

PPT Hunter should point directly at Supabase:

```env
DATABASE_URL=postgresql+psycopg://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres?sslmode=require
```

The current app creates tables on startup with SQLAlchemy. For production, we should move this to Alembic migrations before launch.

## Part 3: Configure Supabase Storage

Create one private bucket:

```text
ppt-hunter
```

Recommended folder layout:

```text
raw/
exports/
previews/
metadata/
ocr/
```

Keep the bucket private. The backend should download source files, upload them to Supabase Storage with the service role key, and expose downloads through API-controlled ZIP files or signed URLs.

Environment variables to reserve:

```env
STORAGE_BACKEND=supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-only-service-role-key>
SUPABASE_STORAGE_BUCKET=ppt-hunter
```

Important current-state note: PPT Hunter keeps a local cache at `STORAGE_DIR=./storage` for extraction and ZIP creation. When `STORAGE_BACKEND=supabase` is enabled, downloaded decks are also uploaded to Supabase Storage and ZIP exports are uploaded to `exports/`.

## Part 4: No-Docker Local Development

Copy `.env.example` to `.env`.

Fill in Supabase plus managed Redis/search values:

```env
ENVIRONMENT=development
API_CORS_ORIGINS=http://localhost:3000

DATABASE_URL=postgresql+psycopg://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres?sslmode=require
REDIS_URL=redis://<managed-redis-host>:6379/0
ELASTICSEARCH_URL=https://<managed-elasticsearch-host>
STORAGE_DIR=./storage
CELERY_WORKER_CONCURRENCY=8

STORAGE_BACKEND=supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-only-service-role-key>
SUPABASE_STORAGE_BUCKET=ppt-hunter

BRAVE_SEARCH_API_KEY=
DATAFORSEO_LOGIN=
DATAFORSEO_PASSWORD=
TIKA_SERVER_URL=

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Install backend dependencies:

```powershell
.\scripts\setup_backend.ps1
```

Start the API, worker, and frontend in three terminals:

```powershell
.\scripts\run_backend.ps1
.\scripts\run_worker.ps1
.\scripts\run_frontend.ps1
```

Open these URLs:

```text
Frontend: http://localhost:3000
API docs: http://localhost:8000/docs
```

The backend and worker scripts run from the repo root so the root `.env` file is loaded. The frontend script reads `NEXT_PUBLIC_API_BASE_URL` from the same `.env` file before starting Next.js.

Local requirements:

- Python 3.11 or newer.
- Node.js 20 or newer.
- A managed Redis URL or a local Redis install. This is required for Celery queues.
- A managed Elasticsearch/OpenSearch URL or a local search install. This can wait until after ingestion is working because indexing failures are ignored by the worker.

## Part 5: Internet Archive Collection

The AWS guide stores downloaded files in S3. In PPT Hunter, Internet Archive is already a search provider.

Use the frontend:

1. Select `All configured sources` or `Internet Archive`.
2. Enter a query.
3. Click `Find 500 + download all`.
4. Wait for the worker to download and process files.
5. Click `Queue all + ZIP` to export up to 500 downloaded decks.

Production notes:

- Keep result limits and worker concurrency controlled.
- Respect source site terms and robots policies.
- Store canonical URLs and SHA-256 hashes for dedupe.
- Keep failed downloads and error messages for retry/debugging.

## Part 6: Production Hosting Plan

Use Supabase for:

- Postgres
- Private storage
- Optional auth

Use a host for the backend:

- FastAPI service command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Celery worker command:

```bash
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=${CELERY_WORKER_CONCURRENCY:-8}
```

Set production environment variables:

```env
ENVIRONMENT=production
API_CORS_ORIGINS=https://your-frontend-domain.com
DATABASE_URL=postgresql+psycopg://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres?sslmode=require
REDIS_URL=<managed-redis-url>
ELASTICSEARCH_URL=<managed-elasticsearch-url>

STORAGE_BACKEND=supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-only-service-role-key>
SUPABASE_STORAGE_BUCKET=ppt-hunter

BRAVE_SEARCH_API_KEY=<optional>
DATAFORSEO_LOGIN=<optional>
DATAFORSEO_PASSWORD=<optional>
TIKA_SERVER_URL=<optional>
CELERY_WORKER_CONCURRENCY=8
```

For the frontend:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-api-domain.com
```

## Part 7: Security Rules

- Do not expose `SUPABASE_SERVICE_ROLE_KEY` in frontend code.
- Keep the storage bucket private.
- Use backend endpoints for ZIP exports and signed downloads.
- Enable row level security before adding user accounts.
- Add rate limiting before public launch.
- Store provider API keys only in backend/worker environment variables.
- Do not make mass-download features public without authentication.

## Part 8: What Is Already Wired

The current app is ready for Supabase Postgres by changing `DATABASE_URL`.

The backend has storage adapters for local disk, Supabase Storage, and AWS S3:

1. `local`, `supabase`, `s3`, and `aws_s3` storage modes.
2. Downloaded files upload to `ppt-hunter/raw/<document-id>.<ext>`.
3. Each document keeps a `storage_key`.
4. Extraction uses the local cache and can restore missing files from remote storage.
5. ZIP exports can include files restored from remote storage.
6. Generated ZIPs upload to `exports/` when remote storage is enabled.

Remaining production hardening:

1. Add Alembic migrations instead of startup schema patching.
2. Add authenticated signed download URLs.
3. Add user/team permissions before exposing mass download publicly.
4. Add lifecycle rules or retention cleanup for local cache and generated ZIPs.

## Summary

Use Supabase instead of AWS or Docker-managed Postgres for database and private file storage. Keep FastAPI, Celery, Redis, Elasticsearch, and Next.js as separate services. For today, create the Supabase project, create the private `ppt-hunter` bucket, fill in `.env`, and run the app with the PowerShell scripts.
