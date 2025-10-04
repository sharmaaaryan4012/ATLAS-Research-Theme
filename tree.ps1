# Navigate to project folder
Set-Location "C:\Users\sharm\OneDrive\Desktop\Projects\ATLAS - Research Theme"

# Generate tree and exclude venv
tree /A /F | Select-String -NotMatch "\\venv\\" | Out-File "structure.txt" -Encoding utf8

Write-Host "Project structure updated in structure.txt (excluding venv)."
