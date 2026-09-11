param(
    [int]$Port = 8000,
    [switch]$NoReload
)

$ProjectRoot = $PSScriptRoot
$ProjectVenv = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ParentVenv = Join-Path (Split-Path $ProjectRoot -Parent) ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $ProjectVenv) {
    $Python = $ProjectVenv
} elseif (Test-Path -LiteralPath $ParentVenv) {
    $Python = $ParentVenv
} else {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

$UvicornArguments = @("-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", $Port)
if (-not $NoReload) {
    $UvicornArguments += "--reload"
}

Push-Location $ProjectRoot
try {
    & $Python @UvicornArguments
} finally {
    Pop-Location
}
