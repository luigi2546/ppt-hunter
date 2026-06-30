$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot\..\backend"

$python = if ($env:PYTHON) { $env:PYTHON } else { "python" }

if (-not (Test-Path ".venv")) {
    & $python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Pop-Location
