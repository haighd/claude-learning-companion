# Claude Learning Companion - Windows Updater
# Run with: PowerShell -ExecutionPolicy Bypass -File update.ps1

param(
    [switch]$Force,
    [switch]$SkipBackup,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

# === SECTION 1: SETUP & COLORS ===

if ($Help) {
    Write-Host "Usage: update.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Force       Skip confirmation prompts"
    Write-Host "  -SkipBackup  Skip backup creation (not recommended)"
    Write-Host "  -Help        Show this help"
    Write-Host ""
    Write-Host "This script safely updates the Claude Learning Companion while"
    Write-Host "preserving your customizations and data."
    exit 0
}

# Paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ClaudeDir = Join-Path $env:USERPROFILE ".claude"
$ClcDir = Join-Path $ClaudeDir "clc"
$VersionFile = Join-Path $ClcDir "VERSION"
$DbPath = Join-Path $ClcDir "memory\index.db"
$StockHashesFile = Join-Path $ScriptDir ".stock-hashes"

# GitHub repo info
$GithubRepo = "haighd/claude-learning-companion"
$GithubApiUrl = "https://api.github.com/repos/$GithubRepo/releases/latest"

# Backup directory (will be set later with timestamp)
$BackupDir = $null

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Claude Learning Companion Updater" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# === SECTION 2: HELPER FUNCTIONS ===

function Get-InstallType {
    $gitDir = Join-Path $ScriptDir ".git"
    if (Test-Path $gitDir) {
        return "git"
    }
    return "standalone"
}

function Get-CurrentVersion {
    if (Test-Path $VersionFile) {
        return (Get-Content $VersionFile -Raw).Trim()
    }
    return "0.0.0"
}

function Get-LatestVersion {
    param([string]$InstallType)

    if ($InstallType -eq "git") {
        try {
            Push-Location $ScriptDir
            git fetch origin 2>&1 | Out-Null
            $tags = git tag -l "v*" --sort=-version:refname 2>&1
            Pop-Location
            if ($tags) {
                return ($tags | Select-Object -First 1).Trim()
            }
        } catch {
            # Fall through to API
        }
    }

    # Use GitHub API
    try {
        $response = Invoke-RestMethod -Uri $GithubApiUrl -Headers @{"User-Agent"="CLC-Updater"}
        return $response.tag_name
    } catch {
        return $null
    }
}

function Compare-Versions {
    param(
        [string]$Current,
        [string]$Latest
    )

    # Strip 'v' prefix if present
    $Current = $Current -replace '^v', ''
    $Latest = $Latest -replace '^v', ''

    $currentParts = $Current.Split('.') | ForEach-Object { [int]$_ }
    $latestParts = $Latest.Split('.') | ForEach-Object { [int]$_ }

    for ($i = 0; $i -lt 3; $i++) {
        $c = if ($i -lt $currentParts.Count) { $currentParts[$i] } else { 0 }
        $l = if ($i -lt $latestParts.Count) { $latestParts[$i] } else { 0 }

        if ($l -gt $c) { return 1 }   # Update available
        if ($l -lt $c) { return -1 }  # Current is newer
    }
    return 0  # Same version
}

function Get-FileHash256 {
    param([string]$FilePath)

    if (-not (Test-Path $FilePath)) {
        return $null
    }
    return (Get-FileHash -Path $FilePath -Algorithm SHA256).Hash.ToLower()
}

function Test-FileModified {
    param([string]$FilePath)

    if (-not (Test-Path $StockHashesFile)) {
        return $false
    }

    $relativePath = $FilePath.Replace($ScriptDir, '').TrimStart('\', '/')
    $stockHashes = Get-Content $StockHashesFile | Where-Object { $_ -notmatch '^#' -and $_.Trim() }

    foreach ($line in $stockHashes) {
        if ($line -match "^([a-f0-9]+)\s+(.+)$") {
            $stockHash = $Matches[1]
            $stockFile = $Matches[2]

            if ($stockFile -eq $relativePath) {
                $currentHash = Get-FileHash256 -FilePath $FilePath
                return ($currentHash -ne $stockHash)
            }
        }
    }
    return $false
}

function New-Backup {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $script:BackupDir = Join-Path $ClaudeDir "clc-backup-$timestamp"

    Write-Host "[Backup] Creating backup at $BackupDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

    # Backup database
    $dbSrc = Join-Path $ClcDir "memory\index.db"
    if (Test-Path $dbSrc) {
        Copy-Item -Path $dbSrc -Destination $BackupDir
        Write-Host "  [+] Database (index.db)" -ForegroundColor Green
    }

    # Backup golden rules
    $goldenRules = Join-Path $ClcDir "memory\golden-rules.md"
    if (Test-Path $goldenRules) {
        Copy-Item -Path $goldenRules -Destination $BackupDir
        Write-Host "  [+] Golden rules" -ForegroundColor Green
    }

    # Backup CEO inbox
    $ceoInbox = Join-Path $ClcDir "ceo-inbox"
    if (Test-Path $ceoInbox) {
        Copy-Item -Path $ceoInbox -Destination $BackupDir -Recurse
        Write-Host "  [+] CEO inbox" -ForegroundColor Green
    }

    # Backup settings.json
    $settingsFile = Join-Path $ClaudeDir "settings.json"
    if (Test-Path $settingsFile) {
        Copy-Item -Path $settingsFile -Destination $BackupDir
        Write-Host "  [+] settings.json" -ForegroundColor Green
    }

    # Backup CLAUDE.md
    $claudeMd = Join-Path $ClaudeDir "CLAUDE.md"
    if (Test-Path $claudeMd) {
        Copy-Item -Path $claudeMd -Destination $BackupDir
        Write-Host "  [+] CLAUDE.md" -ForegroundColor Green
    }

    Write-Host ""
}

function Restore-Backup {
    if (-not $BackupDir -or -not (Test-Path $BackupDir)) {
        Write-Host "[Rollback] No backup available to restore" -ForegroundColor Red
        return
    }

    Write-Host "[Rollback] Restoring from backup..." -ForegroundColor Yellow

    # Restore database
    $dbBackup = Join-Path $BackupDir "index.db"
    if (Test-Path $dbBackup) {
        $dbDst = Join-Path $ClcDir "memory\index.db"
        Copy-Item -Path $dbBackup -Destination $dbDst -Force
        Write-Host "  [+] Database restored" -ForegroundColor Green
    }

    # Restore golden rules
    $goldenBackup = Join-Path $BackupDir "golden-rules.md"
    if (Test-Path $goldenBackup) {
        $goldenDst = Join-Path $ClcDir "memory\golden-rules.md"
        Copy-Item -Path $goldenBackup -Destination $goldenDst -Force
        Write-Host "  [+] Golden rules restored" -ForegroundColor Green
    }

    # Restore settings
    $settingsBackup = Join-Path $BackupDir "settings.json"
    if (Test-Path $settingsBackup) {
        $settingsDst = Join-Path $ClaudeDir "settings.json"
        Copy-Item -Path $settingsBackup -Destination $settingsDst -Force
        Write-Host "  [+] settings.json restored" -ForegroundColor Green
    }

    Write-Host "[Rollback] Complete. Your data has been restored." -ForegroundColor Green
}

function Show-ConflictPrompt {
    param(
        [string]$FilePath,
        [string]$NewFile
    )

    $fileName = Split-Path $FilePath -Leaf

    Write-Host ""
    Write-Host "+---------------------------------------------------------+" -ForegroundColor Yellow
    Write-Host "| File modified: $fileName" -ForegroundColor Yellow
    Write-Host "|" -ForegroundColor Yellow
    Write-Host "| Your version differs from the update." -ForegroundColor Yellow
    Write-Host "|" -ForegroundColor Yellow
    Write-Host "| [U] Update (overwrite your changes)" -ForegroundColor Yellow
    Write-Host "| [K] Keep (preserve your version)" -ForegroundColor Yellow
    Write-Host "| [D] Diff (show differences)" -ForegroundColor Yellow
    Write-Host "| [B] Backup + Update (save yours as .user-backup)" -ForegroundColor Yellow
    Write-Host "+---------------------------------------------------------+" -ForegroundColor Yellow

    while ($true) {
        $choice = Read-Host "Choice [U/K/D/B]"

        switch ($choice.ToUpper()) {
            "U" {
                Copy-Item -Path $NewFile -Destination $FilePath -Force
                Write-Host "  Updated: $fileName" -ForegroundColor Green
                return
            }
            "K" {
                Write-Host "  Kept: $fileName" -ForegroundColor Yellow
                return
            }
            "D" {
                Write-Host ""
                Write-Host "--- Your version ---" -ForegroundColor Cyan
                if (Test-Path $FilePath) {
                    Get-Content $FilePath | Select-Object -First 20
                }
                Write-Host ""
                Write-Host "--- New version ---" -ForegroundColor Green
                Get-Content $NewFile | Select-Object -First 20
                Write-Host ""
                # Loop back to prompt
            }
            "B" {
                $backupPath = "$FilePath.user-backup"
                Copy-Item -Path $FilePath -Destination $backupPath -Force
                Copy-Item -Path $NewFile -Destination $FilePath -Force
                Write-Host "  Backed up to: $backupPath" -ForegroundColor Cyan
                Write-Host "  Updated: $fileName" -ForegroundColor Green
                return
            }
            default {
                Write-Host "  Invalid choice. Please enter U, K, D, or B." -ForegroundColor Red
            }
        }
    }
}

function Invoke-DatabaseMigrations {
    $migratePy = Join-Path $ScriptDir "scripts\migrate_db.py"

    if (-not (Test-Path $migratePy)) {
        Write-Host "  No migration script found (skipping)" -ForegroundColor Yellow
        return
    }

    if (-not (Test-Path $DbPath)) {
        Write-Host "  Database not found (skipping migrations)" -ForegroundColor Yellow
        return
    }

    Write-Host "  Running database migrations..." -ForegroundColor Cyan

    # Find Python
    $pythonCmd = "python"
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    }

    try {
        & $pythonCmd $migratePy $DbPath 2>&1 | ForEach-Object {
            Write-Host "    $_" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  Migration warning: $_" -ForegroundColor Yellow
    }
}

# === SECTION 3: PRE-FLIGHT CHECKS ===

Write-Host "[Step 1/6] Pre-flight checks..." -ForegroundColor Yellow

$installType = Get-InstallType
Write-Host "  Install type: " -NoNewline
Write-Host $installType -ForegroundColor Green

$currentVersion = Get-CurrentVersion
Write-Host "  Current version: " -NoNewline
Write-Host $currentVersion -ForegroundColor Cyan

Write-Host "  Checking for updates..." -ForegroundColor Gray
$latestVersion = Get-LatestVersion -InstallType $installType

if (-not $latestVersion) {
    Write-Host ""
    Write-Host "[ERROR] Could not determine latest version" -ForegroundColor Red
    Write-Host "  Check your internet connection and try again." -ForegroundColor Yellow
    exit 1
}

Write-Host "  Latest version: " -NoNewline
Write-Host $latestVersion -ForegroundColor Cyan
Write-Host ""

$comparison = Compare-Versions -Current $currentVersion -Latest $latestVersion

if ($comparison -eq 0) {
    Write-Host "[OK] Already up to date ($currentVersion)" -ForegroundColor Green
    Write-Host ""
    exit 0
}

if ($comparison -lt 0) {
    Write-Host "[INFO] Your version ($currentVersion) is newer than released ($latestVersion)" -ForegroundColor Yellow
    Write-Host "  You may be running a development version." -ForegroundColor Yellow
    Write-Host ""

    if (-not $Force) {
        $continue = Read-Host "Continue anyway? [y/N]"
        if ($continue -notmatch "^[Yy]") {
            Write-Host "Aborted." -ForegroundColor Yellow
            exit 0
        }
    }
}

Write-Host "[OK] Update available: $currentVersion -> $latestVersion" -ForegroundColor Green
Write-Host ""

# === SECTION 4: BACKUP ===

if (-not $SkipBackup) {
    Write-Host "[Step 2/6] Creating backup..." -ForegroundColor Yellow
    New-Backup
} else {
    Write-Host "[Step 2/6] Skipping backup (--SkipBackup)" -ForegroundColor Yellow
    Write-Host ""
}

# === SECTION 5: CUSTOMIZATION DETECTION ===

Write-Host "[Step 3/6] Detecting customizations..." -ForegroundColor Yellow

$modifiedFiles = @()
$dashboardModified = $false

# Check key customizable files
$filesToCheck = @(
    "scripts\record-failure.sh",
    "scripts\record-heuristic.sh",
    "setup\hooks\golden-rule-enforcer.py",
    "agents\architect\personality.md",
    "agents\creative\personality.md",
    "agents\researcher\personality.md",
    "agents\skeptic\personality.md"
)

foreach ($file in $filesToCheck) {
    $fullPath = Join-Path $ScriptDir $file
    if ((Test-Path $fullPath) -and (Test-FileModified -FilePath $fullPath)) {
        $modifiedFiles += $file
    }
}

# Check dashboard
$dashboardDir = Join-Path $ScriptDir "dashboard-app"
if (Test-Path $dashboardDir) {
    $dashboardFiles = Get-ChildItem -Path $dashboardDir -Recurse -File -Include "*.tsx","*.ts","*.css" -ErrorAction SilentlyContinue |
                      Where-Object { $_.FullName -notmatch "node_modules" }

    foreach ($file in $dashboardFiles) {
        if (Test-FileModified -FilePath $file.FullName) {
            $dashboardModified = $true
            break
        }
    }
}

if ($modifiedFiles.Count -gt 0) {
    Write-Host "  Modified files detected:" -ForegroundColor Yellow
    foreach ($file in $modifiedFiles) {
        Write-Host "    - $file" -ForegroundColor Yellow
    }
}

if ($dashboardModified) {
    Write-Host "  [!] Dashboard has local modifications" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "+---------------------------------------------------------+" -ForegroundColor Yellow
    Write-Host "| Dashboard has been modified locally." -ForegroundColor Yellow
    Write-Host "| Updating will overwrite your changes." -ForegroundColor Yellow
    Write-Host "|" -ForegroundColor Yellow
    Write-Host "| [Y] Yes, update dashboard (overwrite my changes)" -ForegroundColor Yellow
    Write-Host "| [N] No, skip dashboard update (keep my changes)" -ForegroundColor Yellow
    Write-Host "+---------------------------------------------------------+" -ForegroundColor Yellow

    if (-not $Force) {
        $updateDashboard = Read-Host "Update dashboard? [y/N]"
        if ($updateDashboard -notmatch "^[Yy]") {
            Write-Host "  Dashboard will be skipped" -ForegroundColor Yellow
            $script:SkipDashboard = $true
        }
    }
}

Write-Host ""

# === SECTION 6: UPDATE EXECUTION ===

Write-Host "[Step 4/6] Updating..." -ForegroundColor Yellow

try {
    if ($installType -eq "git") {
        # Git-based update
        Write-Host "  Using git to update..." -ForegroundColor Cyan
        Push-Location $ScriptDir

        # Stash local changes
        $stashResult = git stash 2>&1
        $hasStash = $stashResult -notmatch "No local changes"

        # Pull latest
        git pull origin main 2>&1 | ForEach-Object {
            Write-Host "    $_" -ForegroundColor Gray
        }

        # Pop stash if we had one
        if ($hasStash) {
            Write-Host "  Restoring local changes..." -ForegroundColor Cyan
            git stash pop 2>&1 | Out-Null
        }

        Pop-Location
        Write-Host "  [OK] Git update complete" -ForegroundColor Green
    } else {
        # Standalone update - download release
        Write-Host "  Downloading latest release..." -ForegroundColor Cyan

        $response = Invoke-RestMethod -Uri $GithubApiUrl -Headers @{"User-Agent"="CLC-Updater"}
        $tarballUrl = $response.tarball_url

        $tempDir = Join-Path $env:TEMP "clc-update-$(Get-Date -Format 'yyyyMMddHHmmss')"
        $tarballPath = Join-Path $env:TEMP "clc-update.tar.gz"

        Invoke-WebRequest -Uri $tarballUrl -OutFile $tarballPath

        # Extract (requires tar, available in Windows 10+)
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
        tar -xzf $tarballPath -C $tempDir

        $extractedDir = Get-ChildItem -Path $tempDir -Directory | Select-Object -First 1

        # Copy updated files (skip modified ones based on user choice)
        $filesToUpdate = Get-ChildItem -Path $extractedDir.FullName -Recurse -File |
                         Where-Object { $_.FullName -notmatch "node_modules|\.git" }

        foreach ($file in $filesToUpdate) {
            $relativePath = $file.FullName.Replace($extractedDir.FullName, '').TrimStart('\')
            $destPath = Join-Path $ScriptDir $relativePath

            # Skip dashboard if user chose to keep
            if ($SkipDashboard -and $relativePath -match "^dashboard-app") {
                continue
            }

            # Check if file is modified
            if ((Test-Path $destPath) -and (Test-FileModified -FilePath $destPath)) {
                if (-not $Force) {
                    Show-ConflictPrompt -FilePath $destPath -NewFile $file.FullName
                }
            } else {
                $destDir = Split-Path $destPath -Parent
                if (-not (Test-Path $destDir)) {
                    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
                }
                Copy-Item -Path $file.FullName -Destination $destPath -Force
            }
        }

        # Cleanup
        Remove-Item -Path $tarballPath -Force -ErrorAction SilentlyContinue
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue

        Write-Host "  [OK] Standalone update complete" -ForegroundColor Green
    }
} catch {
    Write-Host ""
    Write-Host "[ERROR] Update failed: $_" -ForegroundColor Red
    Restore-Backup
    exit 1
}

Write-Host ""

# === SECTION 7: DATABASE MIGRATIONS ===

Write-Host "[Step 5/6] Database migrations..." -ForegroundColor Yellow
Invoke-DatabaseMigrations
Write-Host ""

# === SECTION 8: POST-UPDATE ===

Write-Host "[Step 6/6] Post-update tasks..." -ForegroundColor Yellow

# Update VERSION file in installed location
$installedVersionFile = Join-Path $ClcDir "VERSION"
$latestClean = $latestVersion -replace '^v', ''
Set-Content -Path $installedVersionFile -Value $latestClean -NoNewline
Write-Host "  Updated VERSION file to $latestClean" -ForegroundColor Green

# Update dependencies if dashboard installed
$dashboardFrontend = Join-Path $ClcDir "dashboard-app\frontend"
if ((Test-Path $dashboardFrontend) -and -not $SkipDashboard) {
    Write-Host "  Updating dashboard dependencies..." -ForegroundColor Cyan
    Push-Location $dashboardFrontend

    if (Get-Command bun -ErrorAction SilentlyContinue) {
        bun install 2>&1 | Out-Null
    } elseif (Get-Command npm -ErrorAction SilentlyContinue) {
        npm install 2>&1 | Out-Null
    }

    Pop-Location
    Write-Host "  [OK] Dependencies updated" -ForegroundColor Green
}

Write-Host ""

# === SECTION 9: SUCCESS ===

Write-Host "============================================" -ForegroundColor Green
Write-Host "  Update Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Updated: $currentVersion -> $latestClean" -ForegroundColor Cyan
Write-Host ""

if ($BackupDir) {
    Write-Host "Backup location: $BackupDir" -ForegroundColor Gray
    Write-Host "  (Safe to delete after verifying everything works)" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart Claude Code to pick up changes"
Write-Host "  2. Test the query system: python ~/.claude/clc/query/query.py --context"
Write-Host ""
