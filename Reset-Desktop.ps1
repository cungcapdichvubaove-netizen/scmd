Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
<<<<<<< HEAD
$OutputEncoding = [System.Text.Encoding]::UTF8
try { chcp 65001 > $null } catch {}

$defaultProjectRoot = Split-Path -Parent $PSCommandPath
$script:ProjectRoot = if ($env:SCMDPRO_ROOT) { $env:SCMDPRO_ROOT } else { $defaultProjectRoot }
$script:ComposeFile = Join-Path $script:ProjectRoot "docker-compose.yml"
$script:AppUrl = "http://localhost:8000"
$script:LogFile = Join-Path (Split-Path -Parent $PSCommandPath) "reset-scmdpro.log"
=======
try { chcp 65001 > $null } catch {}

$defaultProjectRoot = Split-Path -Parent $PSCommandPath
$script:ProjectRoot = if ($env:SCMDERP_ROOT) { $env:SCMDERP_ROOT } else { $defaultProjectRoot }
$script:ComposeFile = Join-Path $script:ProjectRoot "docker-compose.yml"
$script:AppUrl = "http://localhost:8000"
$script:LogFile = Join-Path (Split-Path -Parent $PSCommandPath) "reset-scmderp.log"
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
$script:DbService = "db"
$script:AppServices = @("web", "celery_worker", "celery_beat")
$script:InfraServices = @("db", "redis")
$script:HealthEndpoints = @(
    "$script:AppUrl/",
<<<<<<< HEAD
    "$script:AppUrl/admin/login/"
=======
    "$script:AppUrl/admin/login/",
    "$script:AppUrl/api/docs/"
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
)
$script:DbName = "scmd_db"
$script:DbUser = "scmd_user"
$script:AdminUsername = if ($env:SCMD_ADMIN_USERNAME) { $env:SCMD_ADMIN_USERNAME } elseif ($env:DJANGO_SUPERUSER_USERNAME) { $env:DJANGO_SUPERUSER_USERNAME } else { "admin" }
<<<<<<< HEAD
=======
$script:AdminPassword = if ($env:SCMD_ADMIN_PASSWORD) { $env:SCMD_ADMIN_PASSWORD } elseif ($env:DJANGO_SUPERUSER_PASSWORD) { $env:DJANGO_SUPERUSER_PASSWORD } else { "ScmdAdmin2026!" }
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

function Write-Header([string]$Text) {
    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "=========================================================" -ForegroundColor Cyan
}

function Write-Step([string]$Step, [string]$Text) {
    Write-Host ""
    Write-Host "[$Step] $Text" -ForegroundColor Yellow
}

function Write-Ok([string]$Text) { Write-Host "  OK   $Text" -ForegroundColor Green }
function Write-Warn([string]$Text) { Write-Host "  WARN $Text" -ForegroundColor Yellow }
function Write-Err([string]$Text) { Write-Host "  ERR  $Text" -ForegroundColor Red }
function Write-Info([string]$Text) { Write-Host "  INFO $Text" -ForegroundColor DarkGray }

function Write-LogChunk([string]$Content) {
    if (-not $Content) {
        return
    }

    $normalized = $Content.TrimEnd()
    if (-not $normalized) {
        return
    }

    Add-Content -Path $script:LogFile -Value $normalized -Encoding UTF8
    Write-Host $normalized
}

function Invoke-DockerProcess([string[]]$ArgumentList, [switch]$IgnoreFailure) {
    $stdoutFile = [System.IO.Path]::GetTempFileName()
    $stderrFile = [System.IO.Path]::GetTempFileName()

    try {
        $process = Start-Process -FilePath "docker" -ArgumentList $ArgumentList -NoNewWindow -PassThru -Wait `
            -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile

        $stdout = if (Test-Path $stdoutFile) { Get-Content -Raw -Encoding UTF8 $stdoutFile } else { "" }
        $stderr = if (Test-Path $stderrFile) { Get-Content -Raw -Encoding UTF8 $stderrFile } else { "" }

        if ($stdout) {
            Write-LogChunk -Content $stdout
        }
        if ($stderr) {
            Write-LogChunk -Content $stderr
        }

        if (-not $IgnoreFailure -and $process.ExitCode -ne 0) {
            throw (($stderr, $stdout) -join [Environment]::NewLine).Trim()
        }

        return @{
            ExitCode = $process.ExitCode
            StdOut = $stdout
            StdErr = $stderr
        }
    } finally {
        Remove-Item $stdoutFile, $stderrFile -Force -ErrorAction SilentlyContinue
    }
}

function Assert-Project {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Khong tim thay docker trong PATH."
    }

    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop chua san sang."
    }

    foreach ($path in @($script:ProjectRoot, $script:ComposeFile, (Join-Path $script:ProjectRoot "manage.py"))) {
        if (-not (Test-Path $path)) {
            throw "Khong tim thay $path"
        }
    }
}

function Invoke-Compose([string[]]$ComposeArgs, [switch]$IgnoreFailure) {
    $allArgs = @("compose", "--project-directory", $script:ProjectRoot, "-f", $script:ComposeFile) + $ComposeArgs
    Write-Info ("docker " + ($allArgs -join " "))
    [void](Invoke-DockerProcess -ArgumentList $allArgs -IgnoreFailure:$IgnoreFailure)
}

function Invoke-DjangoRun([string[]]$CommandArgs, [string]$ErrorText) {
<<<<<<< HEAD
    # Lấy mật khẩu từ session môi trường để truyền vào container
    $pass = if ($env:SCMD_ADMIN_PASSWORD) { $env:SCMD_ADMIN_PASSWORD }
            elseif ($env:DJANGO_SUPERUSER_PASSWORD) { $env:DJANGO_SUPERUSER_PASSWORD }

=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    $dockerArgs = @(
        "compose",
        "--project-directory", $script:ProjectRoot,
        "-f", $script:ComposeFile,
        "run",
<<<<<<< HEAD
        "--rm"
    )

    if ($pass) {
        $dockerArgs += @("-e", "SCMD_ADMIN_PASSWORD=$pass", "-e", "DJANGO_SUPERUSER_PASSWORD=$pass")
    }

    $dockerArgs += @(
=======
        "--rm",
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
        "--no-deps",
        "--entrypoint",
        "python",
        "web"
    ) + $CommandArgs

    $result = Invoke-DockerProcess -ArgumentList $dockerArgs -IgnoreFailure
    if ($result.ExitCode -ne 0) {
        throw $ErrorText
    }
}

function Test-HttpHealthy([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 10 -MaximumRedirection 0 -ErrorAction Stop
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    } catch {
        $hasResponse = $_.Exception.PSObject.Properties.Match('Response').Count -gt 0
        if ($hasResponse -and $_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
            return ($statusCode -ge 200 -and $statusCode -lt 500)
        }
        return $false
    }
}

function Wait-AppHealth([int]$TimeoutSec = 300) {
    $elapsed = 0
    while ($elapsed -lt $TimeoutSec) {
        foreach ($endpoint in $script:HealthEndpoints) {
            if (Test-HttpHealthy -Url $endpoint) {
                Write-Ok "HTTP endpoint san sang: $endpoint sau $elapsed giay."
                return
            }
        }

        Start-Sleep -Seconds 5
        $elapsed += 5
        Write-Host "  ... dang cho Django san sang $elapsed/$TimeoutSec giay" -ForegroundColor Gray
    }

    throw "Health check timeout sau $TimeoutSec giay."
}

function Backup-Database {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
<<<<<<< HEAD
    $backupFile = Join-Path (Split-Path -Parent $PSCommandPath) "scmdpro-backup-$timestamp.sql"
=======
    $backupFile = Join-Path (Split-Path -Parent $PSCommandPath) "scmderp-backup-$timestamp.sql"
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    Write-Step "0/5" "Backup PostgreSQL truoc khi reset"

    & docker compose --project-directory $script:ProjectRoot -f $script:ComposeFile up -d $script:DbService | Out-Null
    & docker compose --project-directory $script:ProjectRoot -f $script:ComposeFile exec -T $script:DbService pg_dump -U $script:DbUser $script:DbName > $backupFile
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Backup that bai. Tiep tuc reset de tranh block."
    } else {
        Write-Ok "Backup thanh cong: $backupFile"
    }
}

function Invoke-DjangoMigrate {
    Invoke-DjangoRun -CommandArgs @("manage.py", "migrate", "--noinput") -ErrorText "python manage.py migrate that bai trong container web."
    Write-Ok "Migration thanh cong."
}

function Invoke-DjangoCheck {
    Invoke-DjangoRun -CommandArgs @("manage.py", "check") -ErrorText "python manage.py check that bai trong container web."
    Write-Ok "Django system check thanh cong."
}

function Invoke-AdminSync {
    Invoke-DjangoRun -CommandArgs @("create_superuser_auto.py") -ErrorText "Dong bo tai khoan admin that bai trong container web."
    Write-Ok "Tai khoan admin da duoc dong bo."
}

function Invoke-SeedData {
    Invoke-DjangoRun -CommandArgs @("manage.py", "seed_data") -ErrorText "python manage.py seed_data that bai trong container web."
    Write-Ok "Seed data thanh cong."
}

function Show-ComposeHint {
    Write-Host "  Log file: $script:LogFile" -ForegroundColor Yellow
    Write-Host "  Kiem tra logs: docker compose --project-directory `"$script:ProjectRoot`" -f `"$script:ComposeFile`" logs --tail=120 web celery_worker celery_beat db redis" -ForegroundColor Yellow
}

try {
    Set-Content -Path $script:LogFile -Value ("[{0}] RESET START" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -Encoding UTF8
    Assert-Project

<<<<<<< HEAD
    Write-Header "SCMD Pro - Factory reset"
    Write-Host ""
    Write-Host "  Project root: $script:ProjectRoot" -ForegroundColor White
    Write-Host "  Canh bao: lenh nay se xoa volumes Docker va rebuild stack SCMD Pro." -ForegroundColor Yellow
=======
    Write-Header "SCMDERP - FACTORY RESET"
    Write-Host ""
    Write-Host "  Project root: $script:ProjectRoot" -ForegroundColor White
    Write-Host "  Canh bao: lenh nay se xoa volumes Docker va rebuild stack SCMDERP." -ForegroundColor Yellow
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    Read-Host "Nhan Enter de tiep tuc, hoac Ctrl+C de huy" | Out-Null

    $backupChoice = Read-Host "Backup database truoc khi reset? (y/n)"
    if ($backupChoice -match '^[Yy]$') {
        Backup-Database
    }

<<<<<<< HEAD
    Write-Step "0.5/5" "Validate stack SCMD Pro"
=======
    Write-Step "0.5/5" "Validate stack SCMDERP"
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    Invoke-Compose -ComposeArgs @("config")
    Write-Ok "Compose hop le."

    Write-Step "1/5" "Dung stack va xoa volumes"
    Invoke-Compose -ComposeArgs @("down", "-v", "--remove-orphans") -IgnoreFailure
    Write-Ok "Stack da duoc don sach."

    Write-Step "2/5" "Build lai image cho web va Celery"
    Invoke-Compose -ComposeArgs (@("build") + $script:AppServices)
    Write-Ok "Build image thanh cong."

    Write-Step "3/5" "Khoi dong ha tang DB va Redis"
    Invoke-Compose -ComposeArgs (@("up", "-d") + $script:InfraServices)
    Write-Ok "Ha tang da khoi dong."

    Write-Step "4/5" "Ap dung migration va kiem tra Django"
    Invoke-DjangoMigrate
    Invoke-AdminSync
    Invoke-DjangoCheck

    Write-Step "4.5/5" "Khoi dong app stack"
    Invoke-Compose -ComposeArgs (@("up", "-d", "--force-recreate") + $script:AppServices)

    $seedChoice = Read-Host "Nap du lieu mau bang seed_data sau reset? (y/n)"
    if ($seedChoice -match '^[Yy]$') {
        Invoke-SeedData
    }

    Write-Step "5/5" "Health check"
    Wait-AppHealth -TimeoutSec 300

    Write-Header "RESET THANH CONG"
<<<<<<< HEAD
    Write-Host "  SCMD Pro san sang tai $script:AppUrl" -ForegroundColor Green
    Write-Host "  Tai khoan admin: $script:AdminUsername" -ForegroundColor Green
    Write-Host "  Mat khau admin : da dong bo tu cau hinh moi truong" -ForegroundColor Green
=======
    Write-Host "  SCMDERP san sang tai $script:AppUrl" -ForegroundColor Green
    Write-Host "  Tai khoan admin: $script:AdminUsername" -ForegroundColor Green
    Write-Host "  Mat khau admin : $script:AdminPassword" -ForegroundColor Green
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
    Write-Host "  Log file: $script:LogFile" -ForegroundColor Green
} catch {
    Write-Header "RESET THAT BAI"
    Write-Err $_.Exception.Message
    Show-ComposeHint
    exit 1
}
