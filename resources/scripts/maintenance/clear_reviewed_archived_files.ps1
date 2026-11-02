[CmdletBinding()]
param([Parameter(Mandatory)][string]$Plan,[switch]$Apply)
$ErrorActionPreference='Stop'
$review=Get-Content -LiteralPath $Plan -Raw | ConvertFrom-Json
$root=[IO.Path]::GetFullPath($review.workspace).TrimEnd('\')
$game=Join-Path $root 'projects\fishing-2d'
$planPath=[IO.Path]::GetFullPath($Plan)
if (-not $planPath.StartsWith($root+'\output\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Plan outside workspace output' }
$allowed=@('experiments\five-fish-head-evidence-20261101','experiments\five-fish-side-top-video-20261101','experiments\five-fish-version-compare-20261101','experiments\four-fish-current-standard-20261101','output\imagegen','game\assets\models\fish') | ForEach-Object { Join-Path $game $_ }
function Assert-Archive($a) {
 $p=[IO.Path]::GetFullPath($a.path)
 if (-not $p.StartsWith($game+'\plans\reviews\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Archive outside review tree'}
 if ((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $a.sha256) {throw 'Archive changed'}
}
Assert-Archive $review.archive
$indexPath=Join-Path ([IO.Path]::GetDirectoryName($review.archive.path)) 'archive-index.json'
$index=Get-Content -LiteralPath $indexPath -Raw | ConvertFrom-Json
if (-not $index.ok -or -not $index.archive.stream_verified -or $index.archive.sha256 -ne $review.archive.sha256) {throw 'Archive not verified'}
foreach ($a in $index.existing_archives) {Assert-Archive $a}
$untracked=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
git -C $game ls-files --others --exclude-standard | ForEach-Object {[void]$untracked.Add(($_ -replace '/','\'))}
if ($LASTEXITCODE -ne 0) {throw 'Git inventory failed'}
git -C $game ls-files --others --ignored --exclude-standard | ForEach-Object {[void]$untracked.Add(($_ -replace '/','\'))}
if ($LASTEXITCODE -ne 0) {throw 'Ignored-file inventory failed'}
$targets=@($review.targets)
foreach ($e in $targets) {
 $p=[IO.Path]::GetFullPath($e.path)
 if (-not ($allowed | Where-Object {$p.StartsWith($_+'\',[StringComparison]::OrdinalIgnoreCase)})) {throw "Outside reviewed scope: $p"}
 if (-not $untracked.Contains($p.Substring($game.Length+1))) {throw "Target is no longer untracked: $p"}
 $ancestor=$p
 while ($ancestor.Length -ge $root.Length) {
  if ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {throw "Reparse path: $ancestor"}
  if ($ancestor -eq $root) {break};$ancestor=[IO.Path]::GetDirectoryName($ancestor)
 }
 if ((Get-Item -LiteralPath $p).Length -ne $e.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) {throw "Changed input: $p"}
}
$count=0;$bytes=0
if ($Apply) {
 foreach ($e in $targets) {
  if ((Get-FileHash -LiteralPath $e.path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $e.sha256) {throw 'Changed during execution'}
  Remove-Item -LiteralPath $e.path -Force
  $count++;$bytes+=$e.bytes
 }
 # Only empty directories within the explicit reviewed experimental roots.
 foreach ($dir in $allowed | Select-Object -First 5) {
  if (-not (Test-Path -LiteralPath $dir)) {continue}
  $dirs=@(Get-ChildItem -LiteralPath $dir -Directory -Recurse -Force | Sort-Object {$_.FullName.Length} -Descending)
  foreach ($d in $dirs) {if (-not (Get-ChildItem -LiteralPath $d.FullName -Force | Select-Object -First 1)) {Remove-Item -LiteralPath $d.FullName -Force}}
 }
}
$report=@{ok=$true;apply=[bool]$Apply;eligible_files=$targets.Count;eligible_bytes=$review.delete_bytes;deleted_files=$count;deleted_bytes=$bytes;archive_sha256=$review.archive.sha256;plan_sha256=(Get-FileHash -LiteralPath $planPath -Algorithm SHA256).Hash.ToLowerInvariant()}
$name=if($Apply){'cleanup-execution.json'}else{'cleanup-preflight.json'}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path ([IO.Path]::GetDirectoryName($planPath)) $name) -Encoding utf8
$report | ConvertTo-Json -Compress
