# Go to parent directory of scripts
Set-Location (Split-Path $PSScriptRoot -Parent)

# Stage all changes
git add .

# Commit with timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
git commit -m "Auto update on $timestamp"

# Push to GitHub
git push origin main

Write-Host "` Project pushed to GitHub successfully!"
