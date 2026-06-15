param(
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try { chcp 65001 > $null } catch {}

$defaultProjectRoot = Split-Path -Parent $PSCommandPath
$script:ProjectRoot = if ($env:SCMDPRO_ROOT) { $env:SCMDPRO_ROOT } else { $defaultProjectRoot }
$script:ComposeFile = Join-Path $script:ProjectRoot "docker-compose.yml"
$script:AppUrl = "http://localhost:8000"
$script:LogFile = Join-Path (Split-Path -Parent $PSCommandPath) "deploy-scmdpro.log"
$script:InfraServices = @("db", "redis")
$script:AppServices = @("web", "celery_worker", "celery_beat")
$script:AppImages = @("scmd_pro-web:latest", "scmd_pro-celery_worker:latest", "scmd_pro-celery_beat:latest")
$script:HealthUrls = @(
    "$script:AppUrl/login/",
    "$script:AppUrl/admin/login/"
)
$script:TailwindBuildArtifact = Join-Path $script:ProjectRoot "theme\static\css\dist\styles.css"
$script:AdminUsername = if ($env:SCMD_ADMIN_USERNAME) { $env:SCMD_ADMIN_USERNAME } elseif ($env:DJANGO_SUPERUSER_USERNAME) { $env:DJANGO_SUPERUSER_USERNAME } else { "admin" }
$script:DotEnvFile = Join-Path $script:ProjectRoot ".env"

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

function Get-DotEnvValue([string[]]$Keys) {
    if (-not (Test-Path $script:DotEnvFile)) {
        return $null
    }

    foreach ($line in Get-Content -LiteralPath $script:DotEnvFile -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $trimmed = $line.Trim()
        if ($trimmed.StartsWith("#")) {
            continue
        }

        foreach ($key in $Keys) {
            if ($trimmed -match ("^{0}\s*=\s*(.*)$" -f [regex]::Escape($key))) {
                $value = $Matches[1].Trim()
                if ($value.Length -ge 2) {
                    if (
                        ($value.StartsWith('"') -and $value.EndsWith('"')) -or
                        ($value.StartsWith("'") -and $value.EndsWith("'"))
                    ) {
                        $value = $value.Substring(1, $value.Length - 2)
                    }
                }

                if (-not [string]::IsNullOrWhiteSpace($value)) {
                    return $value
                }
            }
        }
    }

    return $null
}

function Assert-BootstrapAdminPassword {
    $password = if ($env:SCMD_ADMIN_PASSWORD) {
        $env:SCMD_ADMIN_PASSWORD
    } elseif ($env:DJANGO_SUPERUSER_PASSWORD) {
        $env:DJANGO_SUPERUSER_PASSWORD
    } else {
        Get-DotEnvValue -Keys @("SCMD_ADMIN_PASSWORD", "DJANGO_SUPERUSER_PASSWORD")
    }

    if (-not $password) {
        throw "Thieu bootstrap admin password. Cau hinh SCMD_ADMIN_PASSWORD hoac DJANGO_SUPERUSER_PASSWORD trong .env hoac environment truoc khi deploy."
    }
}

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

    if (-not (Test-Path $script:TailwindBuildArtifact)) {
        throw "Khong tim thay Tailwind build artifact: $script:TailwindBuildArtifact. Can build frontend asset truoc khi deploy."
    }

    Assert-BootstrapAdminPassword
}

function Invoke-Cleanup {
    Write-Step "0/6" "Dọn dẹp tài nguyên dư thừa (Hygiene)"
    $junkItems = @(
        "dump.rdb",
        "celerybeat-schedule*",
        "reset_project.py",
        "tmp-edge-profile",
        "tmpedge2"
    )

    foreach ($item in $junkItems) {
        $target = Join-Path $script:ProjectRoot $item
        if (Test-Path $target) {
            Write-Info "Đang xóa: $item"
            Remove-Item -Path $target -Recurse -Force -ErrorAction SilentlyContinue
        }
    }

    Write-Info "Đang dọn dẹp Python cache (__pycache__, .pyc)"
    Get-ChildItem -Path $script:ProjectRoot -Include "__pycache__", "*.pyc" -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    
    Write-Ok "Dọn dẹp hoàn tất."
}

function Invoke-Compose([string[]]$ComposeArgs, [switch]$IgnoreFailure) {
    $allArgs = @("compose", "--project-directory", $script:ProjectRoot, "-f", $script:ComposeFile) + $ComposeArgs
    Write-Info ("docker " + ($allArgs -join " "))
    [void](Invoke-DockerProcess -ArgumentList $allArgs -IgnoreFailure:$IgnoreFailure)
}

function Invoke-DjangoExec([string[]]$CommandArgs, [string]$ErrorText) {
    $dockerArgs = @(
        "compose",
        "--project-directory", $script:ProjectRoot,
        "-f", $script:ComposeFile,
        "exec",
        "-T",
        "web"
    ) + $CommandArgs

    $result = Invoke-DockerProcess -ArgumentList $dockerArgs -IgnoreFailure
    if ($result.ExitCode -ne 0) {
        throw $ErrorText
    }
}

function Invoke-DjangoRun([string[]]$CommandArgs, [string]$ErrorText) {
    $pass = if ($env:SCMD_ADMIN_PASSWORD) { $env:SCMD_ADMIN_PASSWORD }
            elseif ($env:DJANGO_SUPERUSER_PASSWORD) { $env:DJANGO_SUPERUSER_PASSWORD }
            else { Get-DotEnvValue -Keys @("SCMD_ADMIN_PASSWORD", "DJANGO_SUPERUSER_PASSWORD") }

    $dockerArgs = @(
        "compose",
        "--project-directory", $script:ProjectRoot,
        "-f", $script:ComposeFile,
        "run",
        "--rm"
    )

    if ($pass) {
        $dockerArgs += @("-e", "SCMD_ADMIN_PASSWORD=$pass", "-e", "DJANGO_SUPERUSER_PASSWORD=$pass")
    }

    $dockerArgs += @(
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

function Test-LocalImage([string]$ImageName) {
    $result = Invoke-DockerProcess -ArgumentList @("image", "inspect", $ImageName) -IgnoreFailure
    return ($result.ExitCode -eq 0)
}

function Test-OfflineRegistryFailure([string]$Message) {
    if (-not $Message) {
        return $false
    }

    return (
        $Message -match "lookup registry-1\.docker\.io" -or
        $Message -match "no such host" -or
        $Message -match "failed to resolve source metadata"
    )
}

function Assert-LocalFallbackImages {
    $missingImages = @()
    foreach ($image in $script:AppImages) {
        if (-not (Test-LocalImage -ImageName $image)) {
            $missingImages += $image
        }
    }

    if ($missingImages.Count -gt 0) {
        throw "Khong the fallback vi thieu image local: $($missingImages -join ', ')"
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
        foreach ($endpoint in $script:HealthUrls) {
            if (Test-HttpHealthy -Url $endpoint) {
                Write-Ok "HTTP endpoint san sang: $endpoint"
                return
            }
        }

        Start-Sleep -Seconds 5
        $elapsed += 5
        Write-Host "  ... dang cho SCMD Pro san sang $elapsed/$TimeoutSec giay" -ForegroundColor Gray
    }

    throw "Health check timeout sau $TimeoutSec giay."
}

try {
    Set-Content -Path $script:LogFile -Value ("[{0}] DEPLOY START" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -Encoding UTF8
    Assert-Project
    Invoke-Cleanup
    $usedLocalImageFallback = $false

    Write-Header "SCMD Pro - Deploy"
    Write-Host "  Project root: $script:ProjectRoot" -ForegroundColor White
    Write-Host "  Compose file: $script:ComposeFile" -ForegroundColor White
    Write-Host "  App URL     : $script:AppUrl" -ForegroundColor White
    if ($SkipBuild) {
        Write-Host "  Mode        : restart" -ForegroundColor White
    } else {
        Write-Host "  Mode        : rebuild" -ForegroundColor White
    }

    Write-Step "1/6" "Validate compose configuration"
    Invoke-Compose -ComposeArgs @("config")
    Write-Ok "Compose hop le."

    if (-not $SkipBuild) {
        Write-Step "2/6" "Build image cho SCMD Pro app stack"
        try {
            Invoke-Compose -ComposeArgs (@("build") + $script:AppServices)
            Write-Ok "Build image thanh cong."
        } catch {
            $buildError = $_.Exception.Message
            if (Test-OfflineRegistryFailure -Message $buildError) {
                Write-Warn "Build image that bai do khong truy cap duoc Docker Hub."
                Assert-LocalFallbackImages
                Write-Warn "Tim thay day du image local. Chuyen sang fast restart de tiep tuc deploy."
                $SkipBuild = $true
                $usedLocalImageFallback = $true
            } else {
                throw
            }
        }
    } else {
        Write-Step "2/6" "Bo qua build image theo yeu cau"
        Write-Warn "SkipBuild duoc bat. Script chi restart stack va van chay migrate/check."
    }

    if ($usedLocalImageFallback) {
        Write-Step "2/6" "Bo qua build image va su dung image local"
        Write-Warn "Script se dung image local da ton tai, sau do van migrate/check day du."
    }

    Write-Step "3/6" "Khoi dong DB va Redis"
    Invoke-Compose -ComposeArgs (@("up", "-d") + $script:InfraServices)
    Write-Ok "DB va Redis da khoi dong."

    Write-Step "4/6" "Dong bo schema va kiem tra Django"
    Invoke-DjangoRun -CommandArgs @("manage.py", "migrate", "--noinput") -ErrorText "python manage.py migrate that bai."
    Write-Ok "Migration thanh cong."
    Invoke-DjangoRun -CommandArgs @("create_superuser_auto.py") -ErrorText "Dong bo tai khoan admin that bai."
    Write-Ok "Tai khoan admin da duoc dong bo."
    Invoke-DjangoRun -CommandArgs @("manage.py", "check") -ErrorText "python manage.py check that bai."
    Write-Ok "Django system check thanh cong."

    Write-Step "5/6" "Khoi dong web, celery_worker, celery_beat"
    Invoke-Compose -ComposeArgs (@("up", "-d", "--force-recreate") + $script:AppServices)
    Write-Ok "App stack da khoi dong."

    Write-Step "6/6" "Health check"
    Wait-AppHealth -TimeoutSec 300

    Write-Header "DEPLOY THANH CONG"
    Write-Host "  SCMD Pro san sang tai $script:AppUrl" -ForegroundColor Green
    Write-Host "  Tai khoan admin: $script:AdminUsername" -ForegroundColor Green
    Write-Host "  Mat khau admin : da dong bo tu cau hinh moi truong" -ForegroundColor Green
    Write-Host "  Log file: $script:LogFile" -ForegroundColor Green
} catch {
    Write-Header "DEPLOY THAT BAI"
    Write-Err $_.Exception.Message
    Write-Host "  Kiem tra logs: docker compose --project-directory `"$script:ProjectRoot`" -f `"$script:ComposeFile`" logs --tail=150 web celery_worker celery_beat db redis" -ForegroundColor Yellow
    Write-Host "  Log file: $script:LogFile" -ForegroundColor Yellow
    exit 1
}
