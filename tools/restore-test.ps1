param([Parameter(Mandatory=$true)][string]$BackupDirectory)
$ErrorActionPreference='Stop'
# Intentionally no project/database parameters: this helper cannot restore the production DB.
$compose=@('compose','-p','liga-mvp-tests','-f','compose.yaml','-f','compose.test.yaml')
$actual=& docker @compose exec -T postgres psql -U liga -d liga_test -Atc 'SELECT current_database()'
if($LASTEXITCODE -ne 0 -or $actual.Trim() -ne 'liga_test'){throw 'Isolated test database required'}
$backup=(Resolve-Path -LiteralPath $BackupDirectory).Path
$checks=Get-Content -LiteralPath (Join-Path $backup 'checksums.json') -Raw | ConvertFrom-Json
foreach($entry in $checks){
  $file=Join-Path $backup $entry.File
  if((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $entry.Hash){throw 'Backup checksum mismatch'}
}
& docker @compose stop api-be mobile-app
& docker @compose cp (Join-Path $backup 'database.dump') postgres:/tmp/league-restore.dump
if($LASTEXITCODE -ne 0){throw 'Cannot copy database archive'}
& docker @compose exec -T postgres pg_restore -U liga -d liga_test --clean --if-exists --no-owner --exit-on-error /tmp/league-restore.dump
if($LASTEXITCODE -ne 0){throw 'Test database restore failed'}
& docker @compose start api-be
if(Test-Path -LiteralPath (Join-Path $backup 'files.tar.gz')){
  & docker @compose cp (Join-Path $backup 'files.tar.gz') api-be:/tmp/league-files-restore.tar.gz
  & docker @compose exec -T api-be tar --no-same-owner -C /data -xzf /tmp/league-files-restore.tar.gz
  if($LASTEXITCODE -ne 0){throw 'Test file volume restore failed'}
}
& docker @compose start mobile-app
Write-Output 'Restored only liga-mvp-tests / liga_test. Production was not modified.'
