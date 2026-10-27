param([string]$Project='liga-mvp',[string]$Database='liga',[string]$BackupRoot='./backups',[switch]$DatabaseOnly)
$ErrorActionPreference='Stop'
$target=Join-Path $BackupRoot ($Project+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $target | Out-Null
$compose=@('compose','-p',$Project)
if($Project -eq 'liga-mvp-tests'){$compose+=@('-f','compose.yaml','-f','compose.test.yaml')}
& docker @compose exec -T postgres pg_dump -U liga -d $Database -Fc -f /tmp/league-backup.dump
if($LASTEXITCODE -ne 0){throw 'Database backup failed'}
& docker @compose cp postgres:/tmp/league-backup.dump (Join-Path $target 'database.dump')
if($LASTEXITCODE -ne 0){throw 'Cannot copy database backup'}
if(-not $DatabaseOnly){
  & docker @compose exec -T api-be tar -C /data -czf /tmp/league-files.tar.gz .
  if($LASTEXITCODE -ne 0){throw 'File volume backup failed'}
  & docker @compose cp api-be:/tmp/league-files.tar.gz (Join-Path $target 'files.tar.gz')
  if($LASTEXITCODE -ne 0){throw 'Cannot copy file volume backup'}
}
Get-ChildItem -LiteralPath $target -File | Get-FileHash -Algorithm SHA256 | Select-Object Hash,@{Name='File';Expression={Split-Path $_.Path -Leaf}} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $target 'checksums.json') -Encoding utf8
Write-Output ([IO.Path]::GetFullPath($target))
