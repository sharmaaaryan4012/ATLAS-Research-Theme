Set-Location "C:\Users\sharm\OneDrive\Desktop\Projects\ATLAS - Research Theme"

# Stage all changes
git add .

# Commit with timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
git commit -m "Auto update on $timestamp"

# Push to GitHub
git push origin main

Write-Host "`n Project pushed to GitHub successfully!"
