Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$script:ProjectRoot = if ($env:SCMDPRO_ROOT) { $env:SCMDPRO_ROOT } else { "D:\SCMD Pro" }
$script:ComposeFile = Join-Path $script:ProjectRoot "docker-compose.yml"
$script:AppUrl = "http://localhost:8000"
$script:LogFile = Join-Path (Split-Path -Parent $PSCommandPath) "check-health-scmdpro.log"
$script:RequiredServices = @("web", "celery_worker", "celery_beat", "db", "redis")
$script:HealthUrls = @(
    "$script:AppUrl/login/",
    "$script:AppUrl/admin/login/"
)
$script:DbUser = "scmd_user"
$script:DbName = "scmd_db"
$script:HasFailure = $false

function Write-Header([string]$Text) {
    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "=========================================================" -ForegroundColor Cyan
}

function Write-Step([string]$Text) {
    Write-Host ""
    Write-Host $Text -ForegroundColor Yellow
}

function Write-Ok([string]$Text) { Write-Host "  OK   $Text" -ForegroundColor Green }
function Write-Warn([string]$Text) { Write-Host "  WARN $Text" -ForegroundColor Yellow }
function Write-Err([string]$Text) {
    Write-Host "  ERR  $Text" -ForegroundColor Red
    $script:HasFailure = $true
}
function Write-Info([string]$Text) { Write-Host "  INFO $Text" -ForegroundColor DarkGray }

function Invoke-DockerProcess([string[]]$ArgumentList, [switch]$IgnoreFailure) {
    $stdoutFile = [System.IO.Path]::GetTempFileName()
    $stderrFile = [System.IO.Path]::GetTempFileName()

    try {
        $process = Start-Process -FilePath "docker" -ArgumentList $ArgumentList -NoNewWindow -PassThru -Wait `
            -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile

        $stdout = if (Test-Path $stdoutFile) { Get-Content -Raw $stdoutFile } else { "" }
        $stderr = if (Test-Path $stderrFile) { Get-Content -Raw $stderrFile } else { "" }

        if ($stdout) {
            $stdout.TrimEnd() | Tee-Object -FilePath $script:LogFile -Append | Out-Host
        }
        if ($stderr) {
            $stderr.TrimEnd() | Tee-Object -FilePath $script:LogFile -Append | Out-Host
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

function Invoke-Compose([string[]]$ComposeArgs) {
    $allArgs = @("compose", "--project-directory", $script:ProjectRoot, "-f", $script:ComposeFile) + $ComposeArgs
    Write-Info ("docker " + ($allArgs -join " "))
    $result = Invoke-DockerProcess -ArgumentList $allArgs -IgnoreFailure
    if ($result.ExitCode -ne 0) {
        throw "Lenh docker compose that bai: docker $($allArgs -join ' ')"
    }

    return @($result.StdOut -split [Environment]::NewLine)
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

function Test-ServiceRunning([string]$ServiceName) {
    $result = Invoke-DockerProcess -ArgumentList @("compose", "--project-directory", $script:ProjectRoot, "-f", $script:ComposeFile, "ps", "--status", "running", "-q", $ServiceName) -IgnoreFailure
    return ($result.ExitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace($result.StdOut.Trim()))
}

function Invoke-DjangoCheck {
    if (-not (Test-ServiceRunning -ServiceName "web")) {
        Write-Warn "Service web chua running, bo qua manage.py check."
        return $false
    }

    $result = Invoke-DockerProcess -ArgumentList @(
        "compose", "--project-directory", $script:ProjectRoot, "-f", $script:ComposeFile,
        "exec", "-T", "web", "python", "manage.py", "check"
    ) -IgnoreFailure
    if ($result.ExitCode -ne 0) {
        Write-Err "manage.py check that bai."
        return $false
    }

    Write-Ok "manage.py check thanh cong."
    return $true
}

function Test-Database {
    if (-not (Test-ServiceRunning -ServiceName "db")) {
        Write-Err "Service db khong running."
        return
    }

    $result = Invoke-DockerProcess -ArgumentList @(
        "compose", "--project-directory", $script:ProjectRoot, "-f", $script:ComposeFile,
        "exec", "-T", "db", "pg_isready", "-U", $script:DbUser, "-d", $script:DbName
    ) -IgnoreFailure
    if ($result.ExitCode -ne 0) {
        Write-Err "PostgreSQL chua san sang."
        return
    }

    Write-Ok "PostgreSQL san sang."
}

function Test-Redis {
    if (-not (Test-ServiceRunning -ServiceName "redis")) {
        Write-Err "Service redis khong running."
        return
    }

    $result = Invoke-DockerProcess -ArgumentList @(
        "compose", "--project-directory", $script:ProjectRoot, "-f", $script:ComposeFile,
        "exec", "-T", "redis", "redis-cli", "ping"
    ) -IgnoreFailure
    if ($result.ExitCode -ne 0 -or -not ($result.StdOut -match "PONG")) {
        Write-Err "Redis khong tra ve PONG."
        return
    }

    Write-Ok "Redis san sang."
}

try {
    Set-Content -Path $script:LogFile -Value ("[{0}] HEALTH CHECK START" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
    Assert-Project

    Write-Header "SCMD Pro - Health check"
    Write-Host "  Project root: $script:ProjectRoot" -ForegroundColor White
    Write-Host "  Compose file: $script:ComposeFile" -ForegroundColor White
    Write-Host "  App URL     : $script:AppUrl" -ForegroundColor White

    Write-Step "Validate compose configuration"
    Invoke-Compose -ComposeArgs @("config") | Out-Null
    Write-Ok "Compose hop le."

    Write-Step "Service status"
    $psOutput = Invoke-Compose -ComposeArgs @("ps")
    $missingServices = @()
    foreach ($service in $script:RequiredServices) {
        if (-not ($psOutput -match "(^|\s)$service(\s|$)")) {
            $missingServices += $service
        }
    }

    if ($missingServices.Count -gt 0) {
        Write-Warn "Khong thay day du service trong compose ps: $($missingServices -join ', ')"
    } else {
        Write-Ok "Da nhan dien du 5 service can thiet."
    }

    foreach ($service in $script:RequiredServices) {
        if (Test-ServiceRunning -ServiceName $service) {
            Write-Ok "Service $service dang running."
        } else {
            Write-Err "Service $service khong running."
        }
    }

    Write-Step "Infrastructure checks"
    Test-Database
    Test-Redis

    Write-Step "Django runtime check"
    [void](Invoke-DjangoCheck)

    Write-Step "HTTP checks"
    foreach ($url in $script:HealthUrls) {
        if (Test-HttpHealthy -Url $url) {
            Write-Ok "HTTP OK: $url"
        } else {
            Write-Err "HTTP loi: $url"
        }
    }

    Write-Host ""
    Write-Host "  Log file: $script:LogFile" -ForegroundColor Yellow
    if ($script:HasFailure) {
        exit 1
    }
} catch {
    Write-Header "HEALTH CHECK THAT BAI"
    Write-Err $_.Exception.Message
    Write-Host "  Log file: $script:LogFile" -ForegroundColor Yellow
    exit 1
}
