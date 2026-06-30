$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot\.."
$python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
& $python -m compileall backend\app
Pop-Location
