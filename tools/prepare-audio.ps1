param([string]$Python='.tts-venv/Scripts/python.exe')
$ErrorActionPreference='Stop'
# Install backend/requirements-audio.txt into a separate environment first.
$root=Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
  New-Item -ItemType Directory -Force models,audio-cache | Out-Null
  $model='models/v5_cis_base_nostress.pt'
  $expected='0405777e332906f0644e08a680f7cfdc2137ea864090079c1fdd30a43c1b8761'
  if(!(Test-Path $model) -or (Get-FileHash $model -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected){
    & curl.exe --fail --location --continue-at - --limit-rate 1M --connect-timeout 20 --max-time 900 --retry 2 --retry-delay 5 --output $model https://models.silero.ai/models/tts/ru/v5_cis_base_nostress.pt
    if($LASTEXITCODE -ne 0){throw 'Model download failed; run again to resume'}
  }
  if((Get-FileHash $model -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected){throw 'Model differs from the verified version; do not generate'}
  if(!(Test-Path models/LICENSE_CIS)){
    & curl.exe --fail --location --max-time 45 --output models/LICENSE_CIS https://raw.githubusercontent.com/snakers4/silero-models/master/LICENSE_CIS
    if($LASTEXITCODE -ne 0){throw 'License download failed'}
  }
  $sha=(Get-FileHash $model -Algorithm SHA256).Hash.ToLowerInvariant()
  $previous=$env:PYTHONPATH
  try {
    $env:PYTHONPATH=Join-Path $root 'backend'
    & $Python -m app.prepare_audio --model $model --expected-sha256 $sha --output audio-cache
    if($LASTEXITCODE -ne 0){throw 'Speech generation failed'}
  } finally { $env:PYTHONPATH=$previous }
  Copy-Item models/LICENSE_CIS audio-cache/LICENSE_CIS
  & docker compose cp audio-cache/. api-be:/data/audio/
  if($LASTEXITCODE -ne 0){throw 'Audio deployment failed'}
  Write-Output 'Audio files prepared and copied to persistent volume. Reload Settings.'
} finally { Pop-Location }
