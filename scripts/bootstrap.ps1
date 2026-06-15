param(
<<<<<<< HEAD
    [switch]$SkipCheck,
    [string]$SecretKey = $env:SECRET_KEY,
    [string]$FieldEncryptionKey = $env:FIELD_ENCRYPTION_KEY,
    [string]$ExcelExportPassword = $env:EXCEL_EXPORT_PASSWORD,
    [string]$DatabaseUrl = $env:DATABASE_URL,
    [string]$RedisUrl = $env:REDIS_URL,
    [string]$CorsAllowedOrigins = $env:CORS_ALLOWED_ORIGINS,
    [string]$FcmServerKey = $env:FCM_SERVER_KEY
=======
    [switch]$SkipCheck
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
)

$ErrorActionPreference = "Stop"

# Force UTF-8 for this session to avoid encoding issues on Windows
$OutputEncoding = [System.Text.Encoding]::UTF8
<<<<<<< HEAD
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try { chcp 65001 > $null } catch {}
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
$env:PYTHONUTF8 = 1

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot "venv\Scripts\python.exe"
$envFile = Join-Path $projectRoot ".env"

<<<<<<< HEAD
function Test-WindowsGisRuntime {
    if ($env:OS -ne "Windows_NT") {
        return $true
    }

    $candidateRoots = @()
    if ($env:OSGEO4W_ROOT) {
        $candidateRoots += $env:OSGEO4W_ROOT
    }
    $candidateRoots += @(
        "C:\OSGeo4W",
        "C:\OSGeo4W64",
        "C:\Program Files\QGIS 3.40.0",
        "C:\Program Files\QGIS 3.38.0",
        "C:\Program Files\QGIS 3.36.0",
        "C:\Program Files\QGIS 3.34.0"
    )

    foreach ($root in $candidateRoots) {
        if (-not $root -or -not (Test-Path $root)) {
            continue
        }

        $binCandidates = @(
            (Join-Path $root "bin"),
            (Join-Path $root "apps\gdal\bin")
        )
        foreach ($binPath in $binCandidates) {
            if (-not (Test-Path $binPath)) {
                continue
            }

            $gdalDll = Get-ChildItem -LiteralPath $binPath -Filter "gdal*.dll" -ErrorAction SilentlyContinue | Select-Object -First 1
            $projCandidates = @(
                (Join-Path $root "share\proj"),
                (Join-Path $root "apps\proj\share\proj")
            )
            $projPath = $projCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

            if ($gdalDll -and $projPath) {
                $env:OSGEO4W_ROOT = $root
                return $true
            }
        }
    }

    Write-Error @"
Khong tim thay runtime GDAL/PROJ tren Windows.
SCMD Pro khong the khoi dong GeoDjango neu thieu native GIS runtime, va web process se chet truoc khi phuc vu /login/.
Hay cai OSGeo4W hoac QGIS, hoac dat bien OSGEO4W_ROOT den thu muc cai dat hop le truoc khi chay bootstrap.
"@
    return $false
}

function New-RandomUrlSafeString {
    param([int]$Bytes = 32)

    $buffer = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
    return [Convert]::ToBase64String($buffer).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

function New-Base64Secret {
    param([int]$Bytes = 32)

    $buffer = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buffer)
    return [Convert]::ToBase64String($buffer)
}

if (-not $SecretKey) { $SecretKey = New-RandomUrlSafeString }
if (-not $FieldEncryptionKey) { $FieldEncryptionKey = New-Base64Secret }
if (-not $ExcelExportPassword) { $ExcelExportPassword = New-RandomUrlSafeString -Bytes 24 }
if (-not $DatabaseUrl) { $DatabaseUrl = "sqlite:///db.sqlite3" }
if (-not $RedisUrl) { $RedisUrl = "redis://localhost:6379/0" }
if (-not $CorsAllowedOrigins) { $CorsAllowedOrigins = "http://localhost:3000" }
if (-not $FcmServerKey) { $FcmServerKey = "" }

if (-not (Test-Path $envFile)) {
@"
SECRET_KEY=$SecretKey
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
DATABASE_URL=$DatabaseUrl
REDIS_URL=$RedisUrl
CORS_ALLOWED_ORIGINS=$CorsAllowedOrigins
FCM_SERVER_KEY=$FcmServerKey
FIELD_ENCRYPTION_KEY=$FieldEncryptionKey
EXCEL_EXPORT_PASSWORD=$ExcelExportPassword
=======
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
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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

<<<<<<< HEAD
[void](Test-WindowsGisRuntime)

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
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
