# PPT Hunter AWS S3 Setup Guide

This guide configures PPT Hunter to store downloaded PowerPoint files and ZIP exports in a private Amazon S3 bucket.

Use this when you want AWS S3 for file storage. PPT Hunter still needs a database, Redis queue, backend, worker, and frontend. S3 only replaces the file-storage part.

## Target Architecture

```text
Next.js frontend
  -> FastAPI backend
      -> PostgreSQL database
      -> Redis queue
      -> Celery worker
          -> Search providers
          -> private S3 bucket
          -> Elasticsearch/OpenSearch
```

## Part 1: Create a Private S3 Bucket

1. Open the AWS Console.
2. Go to S3.
3. Choose **Create bucket**.
4. Bucket name: `ppt-hunter-private` or another globally unique name.
5. Region: `eu-north-1` unless you have a reason to use another region.
6. Keep **Block all public access** enabled.
7. Leave static website hosting disabled.
8. Create the bucket.

Do not make this bucket public. PPT Hunter downloads files through the backend and builds ZIP exports through the API.

## Part 2: Add a Bucket Lifecycle Rule

This is optional but recommended for cost control.

1. Open the bucket.
2. Go to **Management**.
3. Create a lifecycle rule.
4. Apply it to the whole bucket.
5. Expire incomplete multipart uploads after 7 days.
6. If this is a temporary collection project, expire `exports/` after 7 to 30 days.

Keep `raw/` as long as you need the original decks.

## Part 3: Create a Least-Privilege IAM User

Create an IAM policy that only allows PPT Hunter to read and write this one bucket.

Replace `ppt-hunter-private` with your actual bucket name:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PptHunterBucketList",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::ppt-hunter-privat"
    },
    {
      "Sid": "PptHunterObjectReadWrite",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:AbortMultipartUpload"
      ],
      "Resource": "arn:aws:s3:::ppt-hunter-privat/*"
    }
  ]
}
```

Then:

1. Go to IAM.
2. Create a user named `ppt-hunter-storage`.
3. Attach the custom policy above.
4. Create an access key for application use.
5. Save the access key ID and secret access key in your password manager.

Do not use `AmazonS3FullAccess` for the app unless this is a disposable test account.

## Part 4: Configure `.env`

Copy `.env.example` to `.env`, then set:

```env
STORAGE_BACKEND=s3
AWS_S3_BUCKET=ppt-hunter-private
AWS_REGION=eu-north-1
AWS_S3_ENDPOINT_URL=
AWS_ACCESS_KEY_ID=<your-access-key-id>
AWS_SECRET_ACCESS_KEY=<your-secret-access-key>
```

Keep these values server-side only. Do not expose AWS keys in frontend code or `NEXT_PUBLIC_*` variables.

You still need the rest of the app settings:

```env
DATABASE_URL=<postgres-url>
REDIS_URL=<redis-url>
ELASTICSEARCH_URL=<elasticsearch-or-opensearch-url>
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

For local development, you can use the Docker Compose PostgreSQL, Redis, and Elasticsearch services, while S3 stores files remotely.

## Part 5: Install Dependencies

Run:

```powershell
.\scripts\setup_backend.ps1
```

This installs the backend dependencies, including `boto3` for AWS S3.

## Part 6: Start the App

Start the API, worker, and frontend in three terminals:

```powershell
.\scripts\run_backend.ps1
.\scripts\run_worker.ps1
.\scripts\run_frontend.ps1
```

Open:

```text
Frontend: http://localhost:3000
API docs: http://localhost:8000/docs
```

## Part 7: Verify S3 Uploads

In the frontend:

1. Select `Internet Archive` or `All configured sources`.
2. Search for a small test query.
3. Queue a download.
4. Wait for the worker to finish.

Then check S3:

```powershell
aws s3 ls s3://ppt-hunter-private/raw/
```

You should see files named like:

```text
raw/<document-id>.pptx
```

Export a ZIP from the frontend, then check:

```powershell
aws s3 ls s3://ppt-hunter-private/exports/
```

## Part 8: Troubleshooting

If downloads work locally but S3 is empty:

- Confirm `STORAGE_BACKEND=s3`.
- Confirm the backend and worker both load the same `.env`.
- Confirm `AWS_S3_BUCKET` matches the real bucket name.
- Confirm the IAM policy references the same bucket.
- Check the worker logs for `AccessDenied`, `NoSuchBucket`, or region errors.

If extraction fails after upload:

- Keep `STORAGE_DIR=./storage` writable.
- The app uses local cache for extraction and ZIP creation.
- If the local cache is missing, it restores the file from S3 using `storage_key`.

If you see region redirects:

- Set `AWS_REGION` to the bucket's actual region.

## Security Checklist

- Keep the bucket private.
- Keep S3 Block Public Access enabled.
- Use a bucket-specific IAM policy.
- Rotate keys if they were pasted into chat, committed, or shared.
- Do not add AWS credentials to frontend environment variables.
- Do not commit `.env`.

## Summary

Use these settings for AWS S3:

```env
STORAGE_BACKEND=s3
AWS_S3_BUCKET=<your-private-bucket>
AWS_REGION=<bucket-region>
AWS_ACCESS_KEY_ID=<server-only-key>
AWS_SECRET_ACCESS_KEY=<server-only-secret>
```

PPT Hunter stores original decks under `raw/` and generated ZIP exports under `exports/`.

## Public Archive Page

PPT Hunter can also generate a static public archive page like:

```text
index.html
portal_manifest.json
metadata/documents.csv
metadata/documents.json
raw/<document-id>.pptx
```

Set these optional values in `.env`:

```env
PUBLIC_ARCHIVE_TITLE=Research Document Archive
PUBLIC_ARCHIVE_BASE_URL=https://your-cloudfront-domain.example.com
PUBLIC_ARCHIVE_TARGET_FILES=200000
```

Then publish the page from the frontend with **Publish page**, or run:

```bash
curl -X POST http://127.0.0.1:8000/api/exports/portal
```

If you serve the bucket through CloudFront, point CloudFront's default root object to `index.html`. The page reads `portal_manifest.json`, shows collection totals, lists daily files, and links to the metadata CSV/JSON.

For public downloads, CloudFront or the bucket policy must allow read access to:

```text
index.html
portal_manifest.json
metadata/*
raw/*
```
