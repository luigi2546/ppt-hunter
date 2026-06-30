$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot\.."

if (-not (Test-Path "backend\.venv")) {
    throw "Backend virtual environment not found. Run scripts\setup_backend.ps1 first."
}

$concurrency = if ($env:CELERY_WORKER_CONCURRENCY) { $env:CELERY_WORKER_CONCURRENCY } else { "8" }
$env:PYTHONPATH = "$PWD\backend"
& .\backend\.venv\Scripts\celery.exe -A app.tasks.celery_app worker --loglevel=info --pool=threads --concurrency=$concurrency

Pop-Location
