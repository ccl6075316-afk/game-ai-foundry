<#!
.SYNOPSIS
Delete only reviewed, unchanged, ignored cache files. Default is a dry run.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Plan,
    [Parameter(Mandatory)][string]$WorkspaceRoot,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$rootPath = [IO.Path]::GetFullPath($WorkspaceRoot).TrimEnd('\')
$planPath = [IO.Path]::GetFullPath($Plan)
if (-not $planPath.StartsWith($rootPath + '\output\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Plan must be in the workspace output directory.'
}
$review = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
if ([IO.Path]::GetFullPath($review.workspace).TrimEnd('\') -ne $rootPath) { throw 'Workspace mismatch.' }
$cacheRoots = @($review.directories | ForEach-Object { [IO.Path]::GetFullPath($_).TrimEnd('\') })
$protectedRoot = Join-Path $rootPath 'projects\fishing-2d\game\.godot'
$runningProjects = @()
Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(Godot|blender)' } | ForEach-Object {
    if ($_.CommandLine -match '--path\s+(?:"([^"]+)"|(\S+))') {
        $projectPath = if ($Matches[1]) { $Matches[1] } else { $Matches[2] }
        $runningProjects += [IO.Path]::GetFullPath($projectPath).TrimEnd('\')
    }
}

# Validate all directory boundaries before the first deletion. Refuse symlink /
# junction ancestors, tracked files, non-ignored roots and active projects.
$excludedRoots = @{}
foreach ($cacheRoot in $cacheRoots) {
    if (-not $cacheRoot.StartsWith($rootPath + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Cache outside workspace.' }
    if (($cacheRoot -split '[\\/]')[-1] -notin @('.godot', '__pycache__', '.pytest_cache')) { throw 'Unrecognized cache directory.' }
    if ($cacheRoot -eq $protectedRoot) { throw 'Current game import cache is protected.' }
    foreach ($activeProject in $runningProjects) {
        if ($cacheRoot -eq $activeProject -or $cacheRoot.StartsWith($activeProject + '\', [StringComparison]::OrdinalIgnoreCase)) {
            $excludedRoots[$cacheRoot] = 'active_project'
        }
    }
    $ancestor = $cacheRoot
    while ($ancestor.Length -ge $rootPath.Length) {
        if (Test-Path -LiteralPath $ancestor) {
            if ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point: $ancestor" }
        }
        if ($ancestor -eq $rootPath) { break }
        $ancestor = [IO.Path]::GetDirectoryName($ancestor)
    }
    $gameRepo = Join-Path $rootPath 'projects\fishing-2d'
    $repoPath = if ($cacheRoot.StartsWith($gameRepo + '\', [StringComparison]::OrdinalIgnoreCase)) { $gameRepo } else { $rootPath }
    $tracked = @(& git -C $repoPath ls-files -- $cacheRoot)
    if ($LASTEXITCODE -ne 0) { throw 'Git tracking check failed.' }
    if ($tracked.Count -gt 0) { throw "Tracked cache directory: $cacheRoot" }
    & git -C $repoPath check-ignore -q -- $cacheRoot
    if ($LASTEXITCODE -ne 0) { throw "Cache is no longer ignored: $cacheRoot" }
}

$eligible = @()
$skipped = @()
$deleted = @()
foreach ($entry in $review.files) {
    $filePath = [IO.Path]::GetFullPath($entry.path)
    $owners = @($cacheRoots | Where-Object { $filePath.StartsWith($_ + '\', [StringComparison]::OrdinalIgnoreCase) })
    if ($owners.Count -ne 1) { throw "File not in one reviewed cache root: $filePath" }
    if ($excludedRoots.ContainsKey($owners[0])) { $skipped += @{path=$filePath; reason='active_project'}; continue }
    if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) { $skipped += @{path=$filePath; reason='already_missing'}; continue }
    $item = Get-Item -LiteralPath $filePath -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse file: $filePath" }
    $fileParent = [IO.Path]::GetDirectoryName($filePath)
    while ($fileParent.Length -ge $owners[0].Length) {
        if ((Get-Item -LiteralPath $fileParent -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse ancestor: $fileParent" }
        if ($fileParent -eq $owners[0]) { break }
        $fileParent = [IO.Path]::GetDirectoryName($fileParent)
    }
    if ($item.Length -ne $entry.bytes -or (Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) {
        $skipped += @{path=$filePath; reason='changed_since_review'}; continue
    }
    $eligible += $entry
}

$reportName = if ($Apply) { 'cleanup-execution.json' } else { 'cleanup-preflight.json' }
$reportPath = Join-Path ([IO.Path]::GetDirectoryName($planPath)) $reportName
$report = [ordered]@{command='maintenance.clear-reviewed-caches'; apply=[bool]$Apply; ok=$false; plan=$planPath;
    eligible_files=$eligible.Count; eligible_bytes=($eligible | Measure-Object -Property bytes -Sum).Sum;
    running_projects=$runningProjects; skipped=$skipped; deleted_files=0; deleted_bytes=0; errors=@()}
try {
    if ($Apply) {
        foreach ($entry in $eligible) {
            # Recheck immediately before each non-recursive, literal-path deletion.
            if ((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) {
                $report.skipped += @{path=$entry.path; reason='changed_during_execution'}; continue
            }
            Remove-Item -LiteralPath $entry.path -Force
            $deleted += $entry
        }
        # Only remove empty cache directories. Never recursively delete a tree.
        foreach ($cacheRoot in $cacheRoots) {
            if ($excludedRoots.ContainsKey($cacheRoot) -or -not (Test-Path -LiteralPath $cacheRoot)) { continue }
            $emptyCandidates = @(Get-ChildItem -LiteralPath $cacheRoot -Directory -Recurse -Force | Sort-Object { $_.FullName.Length } -Descending)
            $emptyCandidates += Get-Item -LiteralPath $cacheRoot -Force
            foreach ($directory in $emptyCandidates) {
                if ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
                if (@(Get-ChildItem -LiteralPath $directory.FullName -Force).Count -eq 0) {
                    Remove-Item -LiteralPath $directory.FullName -Force
                }
            }
        }
    }
    $report.ok=$true
} catch {
    $report.errors += $_.Exception.Message
    throw
} finally {
    $report.deleted_files=$deleted.Count
    $report.deleted_bytes=[long](($deleted | Measure-Object -Property bytes -Sum).Sum)
    $report['deleted']=$deleted
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding utf8
    [PSCustomObject]@{ok=$report.ok; apply=[bool]$Apply; eligible_files=$report.eligible_files; skipped_files=$report.skipped.Count;
        deleted_files=$report.deleted_files; deleted_bytes=$report.deleted_bytes; report=$reportPath} | ConvertTo-Json
}
