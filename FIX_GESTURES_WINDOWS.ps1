# Run from inside the JARVIS Mark-LVII project folder, in VS Code PowerShell.
# Installs MediaPipe locally into the official 3D globe. Does not read or store API keys.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$repo = Join-Path $PSScriptRoot 'external\gods-eye-view'
if (-not (Test-Path (Join-Path $repo 'package.json'))) {
  throw 'Official Gods Eye app not found. First run INSTALL_GODS_EYE_WINDOWS.ps1.'
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw 'Node.js/npm not found. Install Node.js, restart VS Code and retry.'
}
$packageVersion='0.10.21'
Write-Host "Installing local MediaPipe $packageVersion..."
Push-Location $repo
try {
  & npm install --no-save --package-lock=false --ignore-scripts "@mediapipe/tasks-vision@$packageVersion"
  if ($LASTEXITCODE -ne 0) { throw 'MediaPipe npm installation failed. Check npm/network output above.' }
  $package = Join-Path $repo 'node_modules\@mediapipe\tasks-vision'
  $assetRoot = Join-Path $repo 'public\jarvis_mediapipe'
  $wasmTarget = Join-Path $assetRoot 'wasm'
  New-Item -ItemType Directory -Force -Path $wasmTarget | Out-Null
  $bundle=Join-Path $package 'vision_bundle.mjs'
  if (-not (Test-Path $bundle)) { throw "MediaPipe ESM module missing: $bundle" }
  Copy-Item -LiteralPath $bundle -Destination (Join-Path $assetRoot 'vision_bundle.mjs') -Force
  $wasmSource=Join-Path $package 'wasm'
  if (-not (Test-Path $wasmSource)) { throw "MediaPipe WASM directory missing: $wasmSource" }
  Copy-Item -Path (Join-Path $wasmSource '*') -Destination $wasmTarget -Recurse -Force
  $modelTarget=Join-Path $assetRoot 'hand_landmarker.task'
  if (-not (Test-Path $modelTarget)) {
    Write-Host 'Downloading the official hand recognition model (one-time)...'
    try {
      Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task' -OutFile $modelTarget -TimeoutSec 90 -ErrorAction Stop
    } catch {
      Remove-Item $modelTarget -ErrorAction SilentlyContinue
      Write-Warning 'Model download failed; the overlay will try the official remote model when started.'
    }
  }
  $from=Join-Path $PSScriptRoot 'integrations\gods_eye_gestures.js'
  $to=Join-Path $repo 'public\jarvis_gesture_overlay.js'
  if (-not (Test-Path $from)) { throw "Cannot find gesture overlay: $from" }
  Copy-Item -LiteralPath $from -Destination $to -Force
  $engineFrom=Join-Path $PSScriptRoot 'integrations\jarvis_gesture_engine.js'
  $engineTo=Join-Path $repo 'public\jarvis_gesture_engine.js'
  if (-not (Test-Path $engineFrom)) { throw "Gesture engine missing: $engineFrom" }
  Copy-Item -LiteralPath $engineFrom -Destination $engineTo -Force
  $index=Join-Path $repo 'index.html'
  $content=[System.IO.File]::ReadAllText($index)
  # Remove old script entries before inserting in the correct load order.
  $content=$content.Replace('<script defer src="/jarvis_gesture_overlay.js"></script>', '')
  $content=$content.Replace('<script defer src="/jarvis_gesture_engine.js"></script>', '')
  $tag='<script defer src="/jarvis_gesture_engine.js"></script>' + "`n" + '<script defer src="/jarvis_gesture_overlay.js"></script>'
  if ($content -notmatch '(?i)</body>') { throw 'Unable to inject gestures: closing body tag not found.' }
  $content=[regex]::Replace($content,'(?i)</body>',($tag+"`n</body>"),1)
  [System.IO.File]::WriteAllText($index,$content,(New-Object System.Text.UTF8Encoding($false)))
  # Expose the official renderer camera port rather than relying on synthetic mouse events.
  $mainJs=Join-Path $repo 'src\main.js'
  if (-not (Test-Path $mainJs)) { throw 'Official upstream src/main.js is missing; cannot connect hand gestures to its camera.' }
  $mainText=[System.IO.File]::ReadAllText($mainJs)
  $marker='// JARVIS_GESTURE_CAMERA_BRIDGE_V1'
  if (-not $mainText.Contains($marker)) {
    $bridgeCode=@'

// JARVIS_GESTURE_CAMERA_BRIDGE_V1
// Connect local webcam gestures to the official renderer camera port.
application.subscribe((state) => {
  if (state.status === 'ready') {
    window.__jarvisGodsEyeCamera = application.getComponents()?.scene?.renderer?.camera ?? null;
  } else if (state.status === 'destroyed' || state.status === 'failed') {
    window.__jarvisGodsEyeCamera = null;
  }
});
'@
    [System.IO.File]::WriteAllText($mainJs,$mainText+$bridgeCode,(New-Object System.Text.UTF8Encoding($false)))
  }

  if (-not (Test-Path (Join-Path $assetRoot 'vision_bundle.mjs'))) { throw 'Local MediaPipe installation incomplete.' }
  Write-Host ''
  Write-Host 'SUCCESS: Gesture overlay + MediaPipe module + WASM installed locally.' -ForegroundColor Green
  Write-Host 'Restart the Gods Eye map, then hard refresh with Ctrl+Shift+R and click JARVIS HANDS.'
  if (-not (Test-Path $modelTarget)) { Write-Warning 'Model is not local. Camera gestures need access to the official model URL.' }
} finally { Pop-Location }
