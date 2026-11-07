param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$workspace = 'E:\game-ai-foundry'
$review = Join-Path $workspace 'projects\fishing-2d\plans\reviews\static-fish-release-20261108'
$planFile = Join-Path $review 'cleanup-plan.json'
$plan = Get-Content -LiteralPath $planFile -Raw | ConvertFrom-Json
$planHash = (Get-FileHash -LiteralPath $planFile -Algorithm SHA256).Hash
$allowed = @(
 'work\fish-expression-study-20261108', 'work\sailfish-shape-20261105',
 'work\whale-shark-mosi-study', 'work\whale-shark-reference-20261105',
 'work\static-fish-release-20261108',
 'projects\fishing-2d\experiments\atlantic-sailfish-static-merge',
 'projects\fishing-2d\plans\reviews\sailfish-whale-shape-20261105',
 'projects\fishing-2d\plans\reviews\nile-clean-pixel-20261108',
 'projects\fishing-2d\plans\reviews\whale-shark-20261026',
 'projects\fishing-2d\plans\reviews\whale-shark151',
 'projects\fishing-2d\plans\reviews\whale-shark152',
 'projects\fishing-2d\plans\reviews\whale-shark153',
 'projects\fishing-2d\plans\reviews\whale-shark154',
 'projects\fishing-2d\plans\reviews\whale-shark155',
 'projects\fishing-2d\plans\reviews\whale-shark156',
 'projects\fishing-2d\plans\reviews\whale-shark157',
 'projects\fishing-2d\plans\reviews\whale-shark158',
 'projects\fishing-2d\plans\reviews\whale-shark159'
) | ForEach-Object { [IO.Path]::GetFullPath((Join-Path $workspace $_)) }
function Assert-NativePath([string]$path) {
 $full = [IO.Path]::GetFullPath($path)
 if (-not $full.StartsWith($workspace + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "Outside workspace: $full" }
 $entry = Get-Item -LiteralPath $full -Force
 $cursor = $entry
 while ($null -ne $cursor -and $cursor.FullName.Length -ge $workspace.Length) {
  if (($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Link or junction is not allowed: $($cursor.FullName)" }
  $cursor = if ($cursor -is [IO.FileInfo]) { $cursor.Directory } else { $cursor.Parent }
 }
 return $entry
}
$protected = @{}
foreach ($entry in $plan.protected) {
 $item = Assert-NativePath $entry.path
 if ((Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Protected hash changed: $($entry.path)" }
 $protected[$item.FullName.ToLowerInvariant()] = $true
}
if ($protected.Count -lt 57) { throw 'Incomplete current asset protection list' }
$seen = @{}
$total = [long]0
foreach ($entry in $plan.files) {
 $item = Assert-NativePath $entry.path
 if ($item -isnot [IO.FileInfo]) { throw 'Only exact regular files may be retired' }
 if (-not ($allowed | Where-Object { $item.FullName.StartsWith($_ + '\', [StringComparison]::OrdinalIgnoreCase) })) { throw "Not in fixed historical scope: $($item.FullName)" }
 $key = $item.FullName.ToLowerInvariant()
 if ($seen.ContainsKey($key) -or $protected.ContainsKey($key)) { throw "Duplicate or protected target: $key" }
 $seen[$key] = $true
 if ($item.Length -ne $entry.bytes -or (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Target changed: $key" }
 $total += $item.Length
}
if ($total -ne $plan.deleted_bytes -or $seen.Count -ne $plan.deleted_files) { throw 'Plan totals mismatch' }
# Inspect both repositories once. Tracked historical files are intentionally
# retired by the user's explicit acceptance/cleanup request, not ignored blindly.
$tracked = @{}
$gitSnapshots = @()
foreach ($repo in @($workspace, (Join-Path $workspace 'projects\fishing-2d'))) {
 $names = & git -C $repo -c core.quotepath=false ls-files
 if ($LASTEXITCODE -ne 0) { throw 'Git inventory failed' }
 foreach ($name in $names) { $tracked[[IO.Path]::GetFullPath((Join-Path $repo $name)).ToLowerInvariant()] = $true }
 $status = & git -C $repo status --short
 if ($LASTEXITCODE -ne 0) { throw 'Git status failed' }
 $gitSnapshots += @{repo=$repo;status=@($status)}
}
$trackedTargets = @($plan.files | Where-Object { $tracked.ContainsKey($_.path.ToLowerInvariant()) }).Count
$active = @()
foreach ($process in Get-CimInstance Win32_Process) {
 if ($process.Name -notmatch '^(Godot.*|blender|python.*)\.exe$') { continue }
 foreach ($root in $allowed) {
  if ($process.CommandLine -and ($process.CommandLine.Replace('/', '\').IndexOf($root, [StringComparison]::OrdinalIgnoreCase) -ge 0)) { $active += $process.ProcessId; break }
 }
}
if ($active.Count) { throw "Historical workspace still in use: $($active -join ',')" }
$preflight = @{ok=$true;plan_sha256=$planHash;files=$seen.Count;bytes=$total;tracked_targets=$trackedTargets;protected_files=$protected.Count;native_paths_without_links=$true;active_processes=@();git=$gitSnapshots;scope='Exact accepted fish history only; shared references/current assets protected; no recursive directory deletion.'}
$preflight | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $review 'cleanup-preflight.json') -Encoding utf8
if (-not $Apply) { Write-Output "PREFLIGHT: $($seen.Count) files; $total bytes; $trackedTargets tracked historical files; $($protected.Count) protected."; exit 0 }
if ((Get-FileHash -LiteralPath $planFile -Algorithm SHA256).Hash -ne $planHash) { throw 'Plan changed during preflight' }
$removed = [long]0
foreach ($entry in $plan.files) {
 $item = Assert-NativePath $entry.path
 if ($item.Length -ne $entry.bytes -or (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Changed before removal: $($entry.path)" }
 Remove-Item -LiteralPath $item.FullName -Force
 $removed += $entry.bytes
}
foreach ($entry in $plan.protected) {
 if ((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Protection verification failed: $($entry.path)" }
}
# Empty directories only; exact verified absolute roots. Never recursive delete.
foreach ($root in $allowed) {
 if (-not (Test-Path -LiteralPath $root)) { continue }
 $null = Assert-NativePath $root
 $directories = @(Get-ChildItem -LiteralPath $root -Directory -Recurse -Force | Sort-Object { $_.FullName.Length } -Descending)
 foreach ($dir in $directories) { $null=Assert-NativePath $dir.FullName; if (-not (Get-ChildItem -LiteralPath $dir.FullName -Force | Select-Object -First 1)) { Remove-Item -LiteralPath $dir.FullName -Force } }
 if (-not (Get-ChildItem -LiteralPath $root -Force | Select-Object -First 1)) { Remove-Item -LiteralPath $root -Force }
}
$result = @{ok=$true;status='completed';plan_sha256=$planHash;deleted_files=$seen.Count;deleted_bytes=$removed;protected_files=$protected.Count;protected_hashes_unchanged=$true;tracked_history_files=$trackedTargets;scope=$preflight.scope;files=$plan.files}
$result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $review 'cleanup.validation.json') -Encoding utf8
Write-Output "COMPLETED: $($seen.Count) files, $removed bytes removed; all protected hashes retained."
