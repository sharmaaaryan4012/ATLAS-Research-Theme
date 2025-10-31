<# 
 pull_from_github.ps1
 - Safely pulls latest changes from GitHub.
 - Stashes local changes, fetch/prune, pull (rebase by default), then pops stash.
 - Put this file in the project's scripts/ directory.

 Flags:
   -NoStash  : do not stash local changes
   -Merge    : use merge instead of rebase
#>

param(
    [switch]$NoStash,
    [switch]$Merge
)

# Move to project root (parent of scripts/)
Set-Location (Split-Path $PSScriptRoot -Parent)

# Ensure we're inside a git repo
if (-not (Test-Path ".git")) {
    Write-Host "This folder does not appear to be a Git repository (.git not found)."
    exit 1
}

# Ensure git is available
try { git --version *>$null } catch {
    Write-Host "Git is not available on PATH. Install Git and try again."
    exit 1
}

# Current branch
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if (-not $branch) {
    Write-Host "Unable to determine current branch."
    exit 1
}

# Remote origin check
try { $origin = (git remote get-url origin).Trim() } catch {
    Write-Host "No 'origin' remote configured. Add it first:"
    Write-Host "  git remote add origin https://github.com/<user>/<repo>.git"
    exit 1
}

Write-Host "Repository: $PWD"
Write-Host "Remote:    $origin"
Write-Host "Branch:    $branch"
Write-Host ""

# Optionally stash changes
$didStash = $false
if (-not $NoStash) {
    $dirty = (git status --porcelain)
    if ($dirty) {
        $stamp = (Get-Date -Format "yyyy-MM-dd_HH-mm-ss")
        Write-Host "Stashing local changes..."
        git stash push -u -m "auto-stash before pull $stamp" | Out-Null
        $didStash = $true
    }
}

# Fetch (with prune)
Write-Host "Fetching from origin (with prune)..."
git fetch --all --prune

# Build the pull command as arguments (avoid passing a single string)
if ($Merge) {
    Write-Host "Pulling with merge..."
    $args = @("pull", "origin", $branch)
} else {
    Write-Host "Pulling with rebase..."
    $args = @("pull", "--rebase", "origin", $branch)
}

# Execute pull
$pullExit = 0
& git @args
$pullExit = $LASTEXITCODE

# Detect ongoing rebase (must use logical operator across two Test-Path calls)
$rebaseInProgress = ((Test-Path ".git\rebase-merge") -or (Test-Path ".git\rebase-apply"))

if (-not $Merge -and $rebaseInProgress) {
    Write-Host ""
    Write-Host "Rebase conflicts detected."
    Write-Host "Resolve conflicts (look for <<<<<<<, =======, >>>>>>>), then run:"
    Write-Host "  git add <fixed-files>"
    Write-Host "  git rebase --continue"
    Write-Host "If you need to abort the rebase:"
    Write-Host "  git rebase --abort"
    if ($didStash) {
        Write-Host ""
        Write-Host "After finishing the rebase, restore your stash (if any):"
        Write-Host "  git stash pop"
    }
    exit 2
}

if ($pullExit -ne 0) {
    Write-Host ""
    Write-Host "Pull failed (exit code $pullExit). Check the messages above."
    if ($didStash) {
        Write-Host "You still have a stash saved. Restore later with: git stash pop"
    }
    exit $pullExit
}

# Pop stash if we created one
if ($didStash) {
    Write-Host ""
    Write-Host "Restoring stashed changes..."
    git stash pop
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Stash pop reported conflicts. Resolve them, then 'git add <files>' and commit."
    }
}

Write-Host ""
Write-Host "Pull complete. Recent commits:"
git log --oneline --decorate --graph -n 8

Write-Host ""
Write-Host "Status:"
git status
