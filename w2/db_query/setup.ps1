<#
.SYNOPSIS
    Windows equivalent of `make setup` from the Makefile.
.DESCRIPTION
    Installs backend (uv) and frontend (npm) dependencies, then applies
    database migrations. Also used as the entry point for other common
    dev tasks via -Task parameter.
    
    .\setup.ps1                 # Run full setup (install + db-upgrade)
    .\setup.ps1 -Task install   # Install dependencies only
    .\setup.ps1 -Task dev       # Start backend + frontend dev servers
    .\setup.ps1 -Task db-upgrade
#>

[CmdletBinding()]
param(
    [ValidateSet('setup', 'install', 'install-backend', 'install-frontend',
                 'db-upgrade', 'db-migrate', 'dev', 'dev-backend', 'dev-frontend',
                 'test', 'test-backend', 'lint', 'format', 'clean', 'help')]
    [string]$Task = 'setup',
    [string]$Message,
    [string]$Revision
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    OK  $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    !!  $msg" -ForegroundColor Yellow }

function Test-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Install-UvIfNeeded {
    if (Test-Command 'uv') { return }
    Write-Step 'uv not found - installing uv'
    $bootstrap = "powershell -ExecutionPolicy ByPass -r ""irm https://astral.sh/uv/install.ps1 | iex"""
    Invoke-Expression $bootstrap
    # Refresh PATH for this session
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
    if (-not (Test-Command 'uv')) {
        throw "uv installation failed. Please install manually: https://docs.astral.sh/uv/"
    }
}

function Install-PythonIfNeeded {
    if (Test-Command 'python') { return }
    Install-UvIfNeeded
    Write-Step 'python not found - provisioning via uv'
    & uv python install 3.12
}

function Run-InstallBackend {
    Install-UvIfNeeded
    Install-PythonIfNeeded
    Write-Step 'Installing backend dependencies (uv sync --extra dev)'
    Push-Location $Backend
    try { & uv sync --extra dev; Write-Ok 'backend deps installed' }
    finally { Pop-Location }
}

function Run-InstallFrontend {
    if (-not (Test-Command 'npm')) {
        throw "npm not found. Install Node.js first: https://nodejs.org/"
    }
    Write-Step 'Installing frontend dependencies (npm install)'
    Push-Location $Frontend
    try { & npm install; Write-Ok 'frontend deps installed' }
    finally { Pop-Location }
}

function Run-Install {
    Run-InstallBackend
    Run-InstallFrontend
}

function Run-DbUpgrade {
    Write-Step 'Applying database migrations (alembic upgrade head)'
    Push-Location $Backend
    try { & uv run alembic upgrade head; Write-Ok 'migrations applied' }
    finally { Pop-Location }
}

function Run-DbMigrate {
    if (-not $Message) {
        throw "Usage: .\setup.ps1 -Task db-migrate -Message `"your migration message`""
    }
    Push-Location $Backend
    try { & uv run alembic revision --autogenerate -m $Message }
    finally { Pop-Location }
}

function Run-Dev {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Push-Location '$Backend'; uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Push-Location '$Frontend'; npm run dev"
    Write-Host 'Backend:  http://localhost:8000'
    Write-Host 'Frontend: http://localhost:5173'
}

function Run-DevBackend {
    Push-Location $Backend
    try { & uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 }
    finally { Pop-Location }
}

function Run-DevFrontend {
    Push-Location $Frontend
    try { & npm run dev }
    finally { Pop-Location }
}

function Run-TestBackend {
    Push-Location $Backend
    try { & uv run pytest -v }
    finally { Pop-Location }
}

function Run-Test {
    Run-TestBackend
    Push-Location $Frontend
    try { & npm test }
    finally { Pop-Location }
}

function Run-Lint {
    Push-Location $Backend
    try { & uv run ruff check app tests }
    finally { Pop-Location }
    Push-Location $Frontend
    try { & npm run lint }
    finally { Pop-Location }
}

function Run-Format {
    Push-Location $Backend
    try { & uv run ruff format app tests }
    finally { Pop-Location }
}

function Run-Clean {
    Write-Step 'Cleaning backend artifacts'
    Get-ChildItem -Path $Backend -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    foreach ($d in '.pytest_cache', 'htmlcov', '.coverage', 'dist', 'build') {
        $p = Join-Path $Backend $d
        if (Test-Path $p) { Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue }
    }
    Write-Step 'Cleaning frontend artifacts'
    foreach ($d in 'node_modules', 'dist', '.vite') {
        $p = Join-Path $Frontend $d
        if (Test-Path $p) { Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue }
    }
    Write-Ok 'clean complete'
}

function Show-Help {
    Write-Host 'Database Query Tool - Windows setup.ps1 commands' -ForegroundColor Cyan
    Write-Host ''
    Write-Host '  .\setup.ps1                                Initial setup: install deps + run migrations'
    Write-Host '  .\setup.ps1 -Task install                  Install all dependencies'
    Write-Host '  .\setup.ps1 -Task install-backend          Install backend deps (uv sync --extra dev)'
    Write-Host '  .\setup.ps1 -Task install-frontend         Install frontend deps (npm install)'
    Write-Host '  .\setup.ps1 -Task db-upgrade               Apply database migrations'
    Write-Host '  .\setup.ps1 -Task db-migrate -Message "x"  Create a new migration'
    Write-Host '  .\setup.ps1 -Task dev                      Start backend + frontend dev servers'
    Write-Host '  .\setup.ps1 -Task dev-backend              Start backend only (port 8000)'
    Write-Host '  .\setup.ps1 -Task dev-frontend             Start frontend only (port 5173)'
    Write-Host '  .\setup.ps1 -Task test                     Run all tests'
    Write-Host '  .\setup.ps1 -Task test-backend             Run backend tests'
    Write-Host '  .\setup.ps1 -Task lint                     Run linters'
    Write-Host '  .\setup.ps1 -Task format                   Format backend code'
    Write-Host '  .\setup.ps1 -Task clean                    Clean build artifacts'
    Write-Host '  .\setup.ps1 -Task help                     Show this help'
}

switch ($Task) {
    'setup'            { Run-Install; Run-DbUpgrade; Write-Ok 'Setup complete!' }
    'install'          { Run-Install }
    'install-backend'  { Run-InstallBackend }
    'install-frontend' { Run-InstallFrontend }
    'db-upgrade'       { Run-DbUpgrade }
    'db-migrate'       { Run-DbMigrate }
    'dev'              { Run-Dev }
    'dev-backend'      { Run-DevBackend }
    'dev-frontend'     { Run-DevFrontend }
    'test'             { Run-Test }
    'test-backend'     { Run-TestBackend }
    'lint'             { Run-Lint }
    'format'           { Run-Format }
    'clean'            { Run-Clean }
    'help'             { Show-Help }
    default            { Show-Help }
}
