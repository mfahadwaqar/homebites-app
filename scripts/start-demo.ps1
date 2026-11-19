param([string]$Bind = '127.0.0.1:8000')
$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectDirectory
$demoPython = Join-Path $projectDirectory '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $demoPython)) { throw 'Create the project .venv first; see docs/local-testing.md.' }
docker compose up -d --wait db
if ($LASTEXITCODE -ne 0) { throw 'The local database could not start.' }
& $demoPython manage.py migrate --check
if ($LASTEXITCODE -ne 0) { throw 'Apply migrations with manage.py migrate before starting the demo.' }
& $demoPython manage.py expire_demo_holds
if ($LASTEXITCODE -ne 0) { throw 'Expired payment holds could not be released.' }
& $demoPython manage.py refresh_demo_availability
if ($LASTEXITCODE -ne 0) { throw 'Demo preparation needs attention; read the message above or run seed_demo for initial setup.' }
& $demoPython manage.py runserver $Bind
