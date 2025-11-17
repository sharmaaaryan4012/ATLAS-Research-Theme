# github_push.ps1 — always push to main

# Go to project root (parent of scripts/)
Set-Location (Split-Path $PSScriptRoot -Parent)

# Ensure this is a git repo
if (-not (Test-Path ".git")) {
    Write-Host "Not a git repository (.git missing)."
    exit 1
}

# Ensure Git is on PATH
git --version *>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Git is not available on PATH."
    exit 1
}

# Make sure we are on local 'main' (create and track if missing)
$haveMain = $false
git show-ref --verify --quiet refs/heads/main
if ($LASTEXITCODE -eq 0) { $haveMain = $true }

if ($haveMain) {
    git switch main
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    # Try to track remote main
    git ls-remote --exit-code --heads origin main *>$null
    if ($LASTEXITCODE -eq 0) {
        git switch -c main --track origin/main
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        git switch -c main
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

# Ensure upstream is set to origin/main (safe if already set)
# IMPORTANT: quote '@{u}' so PowerShell doesn't parse it
$upstream = (git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null)
if (-not $upstream -or -not $upstream.EndsWith("origin/main")) {
    git branch --set-upstream-to=origin/main main 2>$null
}

# Rebase main on top of origin/main to avoid non-fast-forward errors
git fetch origin
git pull --rebase origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Pull (rebase) failed. Resolve conflicts, then run:"
    Write-Host "  git add <files>"
    Write-Host "  git rebase --continue"
    Write-Host "Or abort: git rebase --abort"
    exit 1
}

# Stage all changes
git add .

# Commit only if there are staged changes
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $msg = "Auto update on $timestamp"
    git commit -m $msg
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Committed: $msg"
} else {
    Write-Host "No changes to commit."
}

# Push to origin/main (set upstream if missing)
$upstream = (git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null)
if (-not $upstream -or -not $upstream.EndsWith("origin/main")) {
    git push -u origin main
} else {
    git push origin main
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Push failed. See errors above."
    exit $LASTEXITCODE
}

Write-Host "Pushed to origin/main."
