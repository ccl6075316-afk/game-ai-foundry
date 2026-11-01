<# Fish delivery caches only. Default preflight; no recursive deletion. #>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Plan,[switch]$Apply)
$ErrorActionPreference = 'Stop'
$planPath = [IO.Path]::GetFullPath($Plan)
$p = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
$root = [IO.Path]::GetFullPath($p.workspace).TrimEnd('\')
if (-not $planPath.StartsWith($root + '\output\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Plan outside workspace output.' }
if ($p.kind -ne 'reviewed_fish_delivery_cache_cleanup') { throw 'Wrong plan kind.' }
$scope = [IO.Path]::GetFullPath($p.scope_root).TrimEnd('\')
if (-not $scope.StartsWith($root + '\projects\fishing-2d\experiments\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid experiment scope.' }
$script:CheckedAncestors = @{}
function Check-Path([string]$path) {
    $full = [IO.Path]::GetFullPath($path)
    if (-not $full.StartsWith($root + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Path outside workspace.' }
    if ((Test-Path -LiteralPath $full) -and ((Get-Item -LiteralPath $full -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Reparse target.' }
    $cursor = [IO.Path]::GetDirectoryName($full)
    while ($cursor.Length -gt $root.Length) {
        if ($script:CheckedAncestors.ContainsKey($cursor)) { break }
        if ((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Reparse point in path.' }
        $script:CheckedAncestors[$cursor]=$true
        $cursor = [IO.Path]::GetDirectoryName($cursor)
    }
    return $full
}
function Check-Ref($entry) {
    $full = Check-Path $entry.path
    if ((Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Changed input: $full" }
}
foreach ($inputRef in $p.inputs) { Check-Ref $inputRef }
$archive = Get-Content -LiteralPath $p.retention_report -Raw | ConvertFrom-Json
if (-not $archive.ok) { throw 'Retention not verified.' }
$archiveRef = @{path=$archive.archive; sha256=$archive.archive_sha256}; Check-Ref $archiveRef
$protected = @{}
foreach ($entry in $archive.files) { $protected[[IO.Path]::GetFullPath((Join-Path $root $entry.path))] = $true }
foreach ($entry in $p.retained) { Check-Ref $entry; $protected[[IO.Path]::GetFullPath($entry.path)] = $true }
$deliveryRoots = @()
foreach ($delivery in $p.deliveries) {
    $folder = Check-Path $delivery.path
    if (-not $folder.StartsWith($scope + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Delivery outside scope.' }
    $manifest = Get-Content -LiteralPath (Join-Path $folder 'manifest.json') -Raw | ConvertFrom-Json
    if (-not $manifest.ok -or $manifest.status -ne 'done') { throw 'Delivery has not passed.' }
    Check-Ref @{path=$manifest.model;sha256=$manifest.model_sha256}
    foreach ($stage in $manifest.stages) {
        if (-not $stage.ok -or $stage.status -ne 'done') { throw 'Incomplete stage.' }
        Check-Ref @{path=$stage.report;sha256=$stage.report_sha256}
    }
    $deliveryRoots += $folder.TrimEnd('\')
}
$active = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(Godot|blender)' -and $_.CommandLine -and $_.CommandLine.Contains($scope) })
if ($active.Count -gt 0) { throw 'An engine process is using this experiment.' }
$repo = Join-Path $root 'projects\fishing-2d'
$relativeScope = [IO.Path]::GetRelativePath($repo,$scope).Replace('\','/')
$tracked = @(& git -C $repo ls-files -- $relativeScope)
if ($LASTEXITCODE -ne 0) { throw 'Git tracking check failed.' }
$trackedSet = @{}
foreach ($path in $tracked) { $trackedSet[[IO.Path]::GetFullPath((Join-Path $repo $path))]=$true }
$relativeTargets = @($p.files | ForEach-Object { $checkedTarget=Check-Path $_.path; [IO.Path]::GetRelativePath($repo,$checkedTarget).Replace('\','/') })
# Git --stdin on this Windows build treats CR from PowerShell's CRLF pipe as
# part of the pathname. Feed explicit LF bytes; do not weaken the ignore guard.
$gitInfo = [Diagnostics.ProcessStartInfo]::new('git')
$gitInfo.UseShellExecute=$false; $gitInfo.CreateNoWindow=$true
$gitInfo.RedirectStandardInput=$true; $gitInfo.RedirectStandardOutput=$true; $gitInfo.RedirectStandardError=$true
foreach ($arg in @('-c','core.quotepath=false','-C',$repo,'check-ignore','--stdin')) { $gitInfo.ArgumentList.Add($arg) }
$gitProcess = [Diagnostics.Process]::Start($gitInfo)
$ignoreOutputTask=$gitProcess.StandardOutput.ReadToEndAsync(); $ignoreErrorTask=$gitProcess.StandardError.ReadToEndAsync()
$gitProcess.StandardInput.Write(($relativeTargets -join "`n")+"`n"); $gitProcess.StandardInput.Close()
$gitProcess.WaitForExit(); $ignoreOutput=$ignoreOutputTask.GetAwaiter().GetResult(); $ignoreError=$ignoreErrorTask.GetAwaiter().GetResult()
if ($gitProcess.ExitCode -notin @(0,1)) { throw "Git ignore check failed: $ignoreError" }
$ignored = @($ignoreOutput -split "`n" | Where-Object { $_.Length -gt 0 })
$ignoredSet = @{}
foreach ($path in $ignored) { $ignoredSet[[IO.Path]::GetFullPath((Join-Path $repo $path))]=$true }
$eligible = @(); $seen = @{}; $missing = @()
foreach ($entry in $p.files) {
    $full = Check-Path $entry.path
    if ($seen.ContainsKey($full)) { throw 'Duplicate target.' }; $seen[$full]=$true
    if ($protected.ContainsKey($full)) { throw 'Target is required retained evidence.' }
    $owners = @($deliveryRoots | Where-Object { $full.StartsWith($_ + '\',[StringComparison]::OrdinalIgnoreCase) })
    if ($owners.Count -ne 1) { throw 'Target outside a single verified delivery.' }
    $relative = $full.Substring($owners[0].Length + 1)
    if ($relative -notmatch '^fin490\\[a-z_]+\\sample-\d{3}\.json$' -and $relative -notmatch '^review\\frames\\frame-\d{4}\.jpg$') { throw 'Target is not a reproducible pose/frame cache.' }
    if ($trackedSet.ContainsKey($full)) { throw 'Tracked target.' }
    if (-not $ignoredSet.ContainsKey($full)) { throw "Target is not ignored: $full" }
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { $missing += $full; continue }
    if ((Get-Item -LiteralPath $full).Length -ne $entry.bytes) { throw 'Changed target size.' }
    Check-Ref $entry; $eligible += $entry
}
$out = Join-Path ([IO.Path]::GetDirectoryName($planPath)) $(if ($Apply) {'execution.validation.json'} else {'preflight.validation.json'})
if (Test-Path -LiteralPath $out) { throw 'Preserve previous receipt; choose a fresh plan directory.' }
$report = [ordered]@{ok=$false;apply=[bool]$Apply;plan=$planPath;plan_sha256=(Get-FileHash -LiteralPath $planPath -Algorithm SHA256).Hash.ToLowerInvariant();executor_sha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant();eligible_files=$eligible.Count;eligible_bytes=[long](($eligible|Measure-Object bytes -Sum).Sum);already_missing=$missing;deleted_files=0;deleted_bytes=0;errors=@()}
try {
    if ($Apply) {
        $script:CheckedAncestors.Clear()
        foreach ($entry in $eligible) {
            Check-Path $entry.path | Out-Null; Check-Ref $entry
            Remove-Item -LiteralPath $entry.path -Force
            $report.deleted_files++; $report.deleted_bytes += [long]$entry.bytes
        }
    }
    foreach ($entry in $p.retained) { Check-Ref $entry }
    $report.ok=$true
} catch { $report.errors += $_.Exception.Message; throw }
finally { $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $out -Encoding utf8 }
$report | ConvertTo-Json -Depth 4
