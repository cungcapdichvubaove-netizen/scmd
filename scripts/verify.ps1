$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot "venv\Scripts\python.exe"

Push-Location $projectRoot
try {
    $misplacedPythonFiles = Get-ChildItem -Path $projectRoot -Recurse -File -Filter *.py |
        Where-Object {
            $_.FullName -notmatch '\\venv\\|\\node_modules\\' -and
            $_.FullName -match '\\static\\|\\staticfiles\\|\\templates\\'
        }

    if ($misplacedPythonFiles) {
        $paths = $misplacedPythonFiles | ForEach-Object { $_.FullName.Replace($projectRoot + '\', '') }
        throw "Python source file found in serve-able/template path:`n$($paths -join "`n")"
    }

    & $venvPython manage.py check
}
finally {
    Pop-Location
}
