<# 
 pull_from_github.ps1
 - Safely pulls latest changes from GitHub.
 - Default behavior: stash local changes, fetch/prune, pull with rebase, then pop stash.
 - Place this file in the project's scripts/ directory.

 Optional flags:
   -NoStash     : do not stash local changes before pulling
   -Merge       : use merge instead of rebase
#>

param(
    [switch]$NoStash,
    [switch]$Merge
)

# Move to project root (parent of scripts/)
Set-Location (Split-Path $PSScriptRoot -Parent)

# Sanity checks
try {
    git --version *>$null
} catch {
    Write-Host "Git is not available on PATH. Install Git and try again."
    exit 1
}

# Verify repo
$gitDir = Join-Path $PWD ".git"
if (-not (Test-Path $gitDir)) {
    Write-Host "This folder does not appear to be a Git repository (.git not found)."
    exit 1
}

# Determine current branch
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if (-not $branch) {
    Write-Host "Unable to determine current branch."
    exit 1
}

# Verify remote
try {
    $origin = (git remote get-url origin).Trim()
} catch {
    Write-Host "No 'origin' remote configured. Add it first:"
    Write-Host "  git remote add origin https://github.com/<user>/<repo>.git"
    exit 1
}

Write-Host "Repository: $PWD"
Write-Host "Remote:    $origin"
Write-Host "Branch:    $branch"
Write-Host ""

# Optionally stash local changes
$didStash = $false
if (-not $NoStash) {
    $status = (git status --porcelain)
    if ($status) {
        $stamp = (Get-Date -Format "yyyy-MM-dd_HH-mm-ss")
        Write-Host "Stashing local changes..."
        git stash push -u -m "auto-stash before pull $stamp" | Out-Null
        $didStash = $true
    }
}

# Fetch with prune
Write-Host "Fetching from origin (with prune)..."
git fetch --all --prune

# Pull strategy
if ($Merge) {
    Write-Host "Pulling with merge..."
    $pullCmd = "pull origin $branch"
} else {
    Write-Host "Pulling with rebase..."
    $pullCmd = "pull --rebase origin $branch"
}

# Execute pull
$pullOk = $true
try {
    git $pullCmd
} catch {
    $pullOk = $false
}

# If rebase conflicts occurred
if (-not $Merge) {
    $state = ""
    if (Test-Path ".git\rebase-merge" -or Test-Path ".git\rebase-apply") {
        $state = "rebase"
    }
    if ($state -eq "rebase") {
        Write-Host ""
        Write-Host "Rebase conflicts detected."
        Write-Host "Resolve conflicts (files marked <<<<<<<, =======, >>>>>>>), then run:"
        Write-Host "  git add <fixed-files>"
        Write-Host "  git rebase --continue"
        Write-Host "If you need to abort:"
        Write-Host "  git rebase --abort"
        Write-Host ""
        Write-Host "After finishing the rebase, if we stashed changes, run:"
        if ($didStash) { Write-Host "  git stash pop" }
        exit 2
    }
}

# Pop stash if we created one
if ($didStash) {
    Write-Host ""
    Write-Host "Restoring stashed changes..."
    try {
        git stash pop
    } catch {
        Write-Host "Stash pop reported conflicts."
        Write-Host "Resolve them, then 'git add <files>' and commit as needed."
    }
}

Write-Host ""
Write-Host "Pull complete. Recent commits:"
git log --oneline --decorate --graph -n 8

Write-Host ""
Write-Host "Status:"
git status
