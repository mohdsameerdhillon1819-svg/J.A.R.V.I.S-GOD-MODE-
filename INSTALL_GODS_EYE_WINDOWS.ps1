# Installs official God's Eye View as JARVIS's sole world_map plugin UI.
# Review this script before running it. No private API keys are copied here.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$repo = Join-Path $PSScriptRoot "external\gods-eye-view"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Install Git for Windows and reopen VS Code." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "Install supported Node.js/npm and reopen VS Code." }
$nodeVersion = (& node --version).Trim()
Write-Host "Node: $nodeVersion"
if ($nodeVersion -notmatch '^v(24|26)\.') { throw "Node 24.14+ or supported Node 26 is required." }
if ($nodeVersion -match '^v24\.(\d+)\.' -and [int]$Matches[1] -lt 14) { throw "Node 24.14+ required." }
New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot "external") | Out-Null
if (-not (Test-Path (Join-Path $repo "package.json"))) {
  & git clone --depth 1 https://github.com/bilawalsidhu/gods-eye-view.git $repo
  if ($LASTEXITCODE -ne 0) { throw "Git clone failed. Check internet connection." }
}
Set-Location $repo
& npm ci
if ($LASTEXITCODE -ne 0) { throw "npm ci failed. Check output above." }
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Vite serves /public files at site root. Inject into index.html idempotently.
$from = Join-Path $PSScriptRoot "integrations\gods_eye_gestures.js"
$to = Join-Path $repo "public\jarvis_gesture_overlay.js"
if (-not (Test-Path $from)) { throw "Missing JARVIS hand gesture overlay: $from" }
Copy-Item -Path $from -Destination $to -Force
$engineFrom = Join-Path $PSScriptRoot "integrations\jarvis_gesture_engine.js"
$engineTo = Join-Path $repo "public\jarvis_gesture_engine.js"
if (-not (Test-Path $engineFrom)) { throw "Missing gesture engine: $engineFrom" }
Copy-Item -LiteralPath $engineFrom -Destination $engineTo -Force
$index = Join-Path $repo "index.html"
$content = [System.IO.File]::ReadAllText($index)
$tag = '<script defer src="/jarvis_gesture_engine.js"></script>' + "`n" + '<script defer src="/jarvis_gesture_overlay.js"></script>'
# Always ensure engine loads before overlay even on existing installations.
$content = $content.Replace('<script defer src="/jarvis_gesture_overlay.js"></script>', '')
$content = $content.Replace('<script defer src="/jarvis_gesture_engine.js"></script>', '')
if ($true) {
  if ($content -notmatch '(?i)</body>') { throw "Upstream index.html changed; could not insert JARVIS gesture overlay." }
  $content = [regex]::Replace($content, '(?i)</body>', ($tag + "`n</body>"), 1)
  [System.IO.File]::WriteAllText($index, $content, (New-Object System.Text.UTF8Encoding($false)))
}
Write-Host "Official 3D God's Eye View installed as world_map plugin. Hand overlay injected."
Write-Host "Start from JARVIS: Open world map. Or run OPEN_MAP_WINDOWS.bat."
Write-Host "Provider keys: set locally in official app POWER UP -> Provider Settings."

# Install MediaPipe locally, to avoid CDN import failures in gesture setup.
Set-Location $PSScriptRoot
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'FIX_GESTURES_WINDOWS.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Local MediaPipe gesture setup failed. Review the errors above.' }
