param(
    [switch]$Dev = $true
)

$ErrorActionPreference = "Stop"

$CompanionDir = Join-Path $PSScriptRoot "..\..\companion"
if (-not (Test-Path $CompanionDir)) {
    throw "Diretório companion não encontrado em $CompanionDir"
}

Push-Location $CompanionDir
try {
    Write-Host "Iniciando AyuGram Native Shell (Electron)..."
    if ($Dev) {
        npm run dev
    } else {
        npm run build
        npx electron .
    }
}
finally {
    Pop-Location
}
