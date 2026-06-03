param(
    [switch]$SkipCheck
)

$ErrorActionPreference = "Stop"

# Force UTF-8 for this session to avoid encoding issues on Windows
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = 1

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot "venv\Scripts\python.exe"
$envFile = Join-Path $projectRoot ".env"

if (-not (Test-Path $envFile)) {
@"
SECRET_KEY=scmd-bootstrap-local-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
CORS_ALLOWED_ORIGINS=http://localhost:3000
FCM_SERVER_KEY=
"@ | Set-Content -Path $envFile -Encoding UTF8
}

# Kiểm tra xem venv có bị hỏng do di chuyển thư mục hay không
if (Test-Path $venvPython) {
    try {
        & $venvPython -c "import sys" 2>$null
    } catch {
        Write-Warning "Virtual environment bi loi (co the do di chuyen thu muc). Dang xoa de tao lai..."
        Remove-Item -Recurse -Force (Join-Path $projectRoot "venv")
    }
}

if (-not (Test-Path $venvPython)) {
    python -m venv (Join-Path $projectRoot "venv")
}

Write-Host "Updating pip and installing dependencies..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -r (Join-Path $projectRoot "requirements-dev.txt") --no-cache-dir

if (-not $SkipCheck) {
    Push-Location $projectRoot
    try {
        & $venvPython manage.py check
    }
    finally {
        Pop-Location
    }
}
