$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot\.."

if (-not (Test-Path "backend\.venv")) {
    throw "Backend virtual environment not found. Run scripts\setup_backend.ps1 first."
}

& .\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

Pop-Location
