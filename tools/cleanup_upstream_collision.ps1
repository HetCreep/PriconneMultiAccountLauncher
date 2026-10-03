#requires -Version 5.1
<#
.SYNOPSIS
    Remove PriconneMultiAccountLauncher install residue caused by the upstream-AppId-collision bug.

.DESCRIPTION
    Before AppId fix (commit XXXX), this fork's setup.iss reused
    fa0311/DMMGamePlayerFastLauncher's AppId GUID. Inno Setup therefore treated
    both installers as the same product:
      - upstream's installer would extract DMMGamePlayerFastLauncher.exe into
        %APPDATA%\PriconneMultiAccountLauncher\ (this fork's install dir),
      - both uninstallers shared a single Apps & Features registry entry,
      - scheduled tasks created by the pre-rebrand binary still reference the
        stale path.

    This script:
      1. Lists every artifact it intends to remove (dry-run by default).
      2. With -Execute, removes ONLY this fork's own artifacts that point at
         the upstream binary by mistake:
            - stale scheduled tasks `schtasks_v1_<USER>_*` whose Execute target
              references the old DMMGamePlayerFastLauncher binary (these were
              created BY THIS FORK's pre-rebrand binary — they're ours, not
              upstream's),
            - stale data\schtasks\*.xml that hardcode the old binary path
              (same — written by us, not upstream),
            - the OLD Apps & Features entry whose AppId equals the legacy
              shared GUID (only if it points at this fork's install dir —
              this is OUR registry entry from the AppId-collision era).

    Hands-off rule (matches setup.iss [Code] policy):
      - DMMGamePlayerFastLauncher.exe is NEVER touched even if found in this
        dir. We don't interfere with upstream files. Delete it yourself if
        you want — see the "Optional manual cleanup" hint at the end.
      - Account data under data\account\ and data\backup\ is NEVER touched.

.PARAMETER Execute
    Actually perform the deletions. Without this switch the script only reports.

.PARAMETER InstallDir
    Optional override of the install dir. Defaults to
    %APPDATA%\PriconneMultiAccountLauncher.
#>

[CmdletBinding()]
param(
    [switch]$Execute,
    [string]$InstallDir = (Join-Path $env:APPDATA "PriconneMultiAccountLauncher")
)

$ErrorActionPreference = "Stop"

$OLD_SHARED_APPID = "{58BB9490-BCCC-4EC6-ACF7-B5A4EC8B3755}"
$LEGACY_EXE_NAME  = "DMMGamePlayerFastLauncher.exe"

function Write-Section($title) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host $title -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
}

Write-Section "Plan"
Write-Host "Install dir : $InstallDir"
Write-Host "Execute mode: $($Execute.IsPresent)"
if (-not $Execute) {
    Write-Host "(dry-run — re-run with -Execute to apply)" -ForegroundColor Yellow
}

# 1. Stale scheduled tasks
Write-Section "Stale scheduled tasks"
$staleTasks = @()
$user = $env:USERNAME
$taskPattern = "schtasks_v1_${user}_*"
$allMatching = Get-ScheduledTask -TaskName $taskPattern -ErrorAction SilentlyContinue
foreach ($t in $allMatching) {
    $exe = $t.Actions.Execute
    if ($exe -match $LEGACY_EXE_NAME) {
        Write-Host ("  [LEGACY] {0}  -->  {1}" -f $t.TaskName, $exe) -ForegroundColor Yellow
        $staleTasks += $t
    } else {
        Write-Host ("  [keep ] {0}  -->  {1}" -f $t.TaskName, $exe)
    }
}
if ($staleTasks.Count -eq 0) {
    Write-Host "  (no legacy scheduled tasks found)"
}

# 2. Upstream binary in this dir (informational only — NEVER auto-deleted)
Write-Section "Upstream binary in install dir (NOT touched by this script)"
$legacyExe = Join-Path $InstallDir $LEGACY_EXE_NAME
if (Test-Path $legacyExe) {
    $sz = [math]::Round((Get-Item $legacyExe).Length / 1MB, 2)
    Write-Host ("  [HANDS-OFF] {0}  ({1} MB)" -f $legacyExe, $sz) -ForegroundColor DarkYellow
    Write-Host "  ^ Belongs to upstream fa0311/DMMGamePlayerFastLauncher. We don't" -ForegroundColor DarkYellow
    Write-Host "    interfere with their files. Delete manually if you want it gone:" -ForegroundColor DarkYellow
    Write-Host "        Remove-Item `"$legacyExe`" -Force" -ForegroundColor DarkYellow
} else {
    Write-Host "  (no upstream binary at $legacyExe)"
}

# 3. Stale schtask XML
Write-Section "Stale schtask XML files"
$xmlDir = Join-Path $InstallDir "data\schtasks"
$staleXml = @()
if (Test-Path $xmlDir) {
    foreach ($f in Get-ChildItem -Path $xmlDir -Filter "*.xml" -File -ErrorAction SilentlyContinue) {
        $content = Get-Content -Path $f.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match $LEGACY_EXE_NAME) {
            Write-Host ("  [LEGACY] {0}" -f $f.FullName) -ForegroundColor Yellow
            $staleXml += $f
        } else {
            Write-Host ("  [keep ] {0}" -f $f.FullName)
        }
    }
}
if ($staleXml.Count -eq 0) {
    Write-Host "  (no stale schtask XML found)"
}

# 4. Old Apps & Features entry (legacy shared AppId)
Write-Section "Apps & Features entry for legacy AppId"
$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\${OLD_SHARED_APPID}_is1"
$legacyEntry = $null
if (Test-Path $uninstallKey) {
    $legacyEntry = Get-ItemProperty -Path $uninstallKey -ErrorAction SilentlyContinue
    Write-Host ("  Found: {0}" -f $uninstallKey)
    Write-Host ("    DisplayName    : {0}" -f $legacyEntry.DisplayName)
    Write-Host ("    InstallLocation: {0}" -f $legacyEntry.InstallLocation)
    Write-Host ("    UninstallString: {0}" -f $legacyEntry.UninstallString)
    if ($legacyEntry.InstallLocation -and ($legacyEntry.InstallLocation -ne $InstallDir)) {
        Write-Host "  ! InstallLocation differs from target — will SKIP to avoid affecting other installs" -ForegroundColor Red
        $legacyEntry = $null
    }
} else {
    Write-Host "  (no legacy Apps & Features entry)"
}

# Execute phase
if (-not $Execute) {
    Write-Section "Done (dry-run)"
    Write-Host "Re-run with -Execute to perform the deletions above." -ForegroundColor Yellow
    Write-Host "Account data under data\account\ and data\backup\ is NEVER touched." -ForegroundColor Green
    return
}

Write-Section "Executing"

foreach ($t in $staleTasks) {
    try {
        Unregister-ScheduledTask -TaskName $t.TaskName -Confirm:$false -ErrorAction Stop
        Write-Host ("  removed task: {0}" -f $t.TaskName) -ForegroundColor Green
    } catch {
        Write-Host ("  FAILED to remove task {0}: {1}" -f $t.TaskName, $_.Exception.Message) -ForegroundColor Red
    }
}

# Upstream binary deliberately left alone — see "Hands-off rule" in header.

foreach ($f in $staleXml) {
    try {
        Remove-Item -Path $f.FullName -Force -ErrorAction Stop
        Write-Host ("  removed XML: {0}" -f $f.FullName) -ForegroundColor Green
    } catch {
        Write-Host ("  FAILED to remove {0}: {1}" -f $f.FullName, $_.Exception.Message) -ForegroundColor Red
    }
}

if ($legacyEntry) {
    try {
        Remove-Item -Path $uninstallKey -Recurse -Force -ErrorAction Stop
        Write-Host ("  removed legacy Apps & Features entry") -ForegroundColor Green
    } catch {
        Write-Host ("  FAILED to remove registry key: {0}" -f $_.Exception.Message) -ForegroundColor Red
    }
}

Write-Section "Done"
Write-Host "Now re-install the latest PriconneMultiAccountLauncher build." -ForegroundColor Green
Write-Host "Account data under data\account\ and data\backup\ remained intact." -ForegroundColor Green
