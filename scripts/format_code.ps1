# Move to project root (parent of scripts/)
Set-Location (Split-Path $PSScriptRoot -Parent)

# Resolve python in venv; fall back to system python if venv isn't present
$venv_python = Join-Path $PWD "venv\Scripts\python.exe"
if (Test-Path $venv_python) {
    $python = $venv_python
} else {
    $python = "python"
}

Write-Host "Running isort (import sorting)..."
& $python -m isort . --profile black

Write-Host "Running black (code formatting)..."
& $python -m black .

Write-Host "Code formatted successfully with isort + black."
