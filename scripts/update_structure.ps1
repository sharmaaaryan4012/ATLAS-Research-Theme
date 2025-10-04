# Go to parent directory of scripts
Set-Location (Split-Path $PSScriptRoot -Parent)

# Generate tree and exclude venv
tree /A /F | Select-String -NotMatch "\\venv\\" | Out-File "structure.txt" -Encoding utf8

Write-Host " Project structure updated in structure.txt (excluding venv)."
