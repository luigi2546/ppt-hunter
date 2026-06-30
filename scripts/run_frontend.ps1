$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Push-Location "$root\frontend"

if (-not (Test-Path "node_modules")) {
    npm install
}

if (-not $env:NEXT_PUBLIC_API_BASE_URL -and (Test-Path "$root\.env")) {
    $apiBase = Select-String -Path "$root\.env" -Pattern "^NEXT_PUBLIC_API_BASE_URL=(.*)$" | Select-Object -First 1
    if ($apiBase) {
        $env:NEXT_PUBLIC_API_BASE_URL = $apiBase.Matches[0].Groups[1].Value
    }
}

npm run dev

Pop-Location
