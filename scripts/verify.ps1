$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot "venv\Scripts\python.exe"
<<<<<<< HEAD
$releaseCheck = Join-Path $projectRoot "scripts\release_contract_check.py"
=======
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34

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

<<<<<<< HEAD
    & $venvPython $releaseCheck
=======
    & $venvPython manage.py check
>>>>>>> 51661ed7e1165a088e9f7635fb9a4a3d23400f34
}
finally {
    Pop-Location
}
