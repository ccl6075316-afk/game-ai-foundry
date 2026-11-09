<#
Only synthetic pilot duplicates or round-trip-verified snapshot staging files.
No arbitrary target input, recursive deletion, source asset or LFS cache removal.
Default is preflight. -Apply requires the same validation and hash checks again.
#>
[CmdletBinding()]
param([ValidateSet('pilot','snapshot','agent')][string]$Scope='pilot',[switch]$Apply)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..')).TrimEnd('\')
function Assert-File([string]$path) {
 $full=[IO.Path]::GetFullPath($path)
 if (-not $full.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Outside workspace'}
 $item=Get-Item -LiteralPath $full -Force
 if ($item -isnot [IO.FileInfo]) {throw 'Expected regular file'}
 $cursor=$item
 while ($null -ne $cursor -and $cursor.FullName.Length -ge $root.Length) {
  if ($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) {throw 'Links/junctions forbidden'}
  $cursor=if ($cursor -is [IO.FileInfo]) {$cursor.Directory} else {$cursor.Parent}
 }
 return $item
}
function Assert-Hash([string]$path,[string]$hash,[long]$bytes) {
 $item=Assert-File $path
 if ($item.Length -ne $bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hash) {throw "File changed: $path"}
}
$active=@(Get-CimInstance Win32_Process | Where-Object {
 $_.Name -eq 'bdpan.exe' -or ($_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match '(baidu_lfs_snapshot\.py (prepare|transfer|verify|publish)|baidu_lfs_agent\.py|pilot\.py run)')
})
if ($active.Count) {throw 'Storage transfer/verification is active'}
$targets=@();$protected=@()
if ($Scope -eq 'pilot') {
 $review=Join-Path $root 'plans/reviews/baidu-storage-pilot-20261108'
 $work=Join-Path $root 'work/baidu-storage-pilot-20261108'
 $validation=Get-Content -LiteralPath (Join-Path $review 'validation.json') -Raw | ConvertFrom-Json
 if (-not $validation.cloud_round_trip_passed -or $validation.files.Count -ne 3) {throw 'Pilot not verified'}
 foreach ($row in $validation.files) {
  if ($row.name -notin @('probe-v1.txt','probe-v2.txt','probe-32MiB.bin') -or -not $row.sha256_match) {throw 'Unexpected pilot input'}
  $targets+=@{path=(Join-Path $work ('receiver/'+$row.name));bytes=$row.bytes;sha256=$row.sha256}
  if ($row.name -eq 'probe-32MiB.bin') {$targets+=@{path=(Join-Path $work ('sender/'+$row.name));bytes=$row.bytes;sha256=$row.sha256}}
  else {$protected+=@{path=(Join-Path $work ('sender/'+$row.name));bytes=$row.bytes;sha256=$row.sha256}}
 }
} elseif ($Scope -eq 'agent') {
 $review=Join-Path $root 'docs/storage/baidu-lfs-20261109'
 $work=Join-Path $root 'work/baidu-lfs-agent'
 $manifestFile=Join-Path $review 'manifest.json'
 $manifest=Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json
 $publication=Get-Content -LiteralPath (Join-Path $review 'publication.json') -Raw | ConvertFrom-Json
 $manifestHash=(Get-FileHash -LiteralPath $manifestFile -Algorithm SHA256).Hash.ToLowerInvariant()
 if (-not $publication.ok -or $publication.sha256 -ne $manifestHash) {throw 'Published snapshot proof mismatch'}
 $known=@{}
 foreach ($pack in $manifest.packs) {$known[$pack.sha256]=$pack.bytes}
 $packFolder=Join-Path $work 'packs'
 if (Test-Path -LiteralPath $packFolder) {
  foreach ($file in Get-ChildItem -LiteralPath $packFolder -File -Force) {
   $oid=$file.BaseName
   if ($file.Extension -ne '.tar' -or -not $known.ContainsKey($oid)) {throw 'Unknown agent cache file'}
   $targets+=@{path=$file.FullName;bytes=$known[$oid];sha256=$oid}
  }
 }
} else {
 $review=Join-Path $root 'docs/storage/baidu-lfs-20261109'
 $work=Join-Path $root 'work/baidu-lfs-20261109'
 $manifestFile=Join-Path $review 'manifest.json'
 $manifest=Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json
 $validation=Get-Content -LiteralPath (Join-Path $review 'validation.json') -Raw | ConvertFrom-Json
 $publication=Get-Content -LiteralPath (Join-Path $review 'publication.json') -Raw | ConvertFrom-Json
 $manifestHash=(Get-FileHash -LiteralPath $manifestFile -Algorithm SHA256).Hash.ToLowerInvariant()
 if (-not $validation.ok -or -not $publication.ok -or $validation.manifest_sha256 -ne $manifestHash -or $publication.sha256 -ne $manifestHash) {throw 'Snapshot is not published and verified'}
 if ($validation.objects_reconstructed_sha256 -ne $manifest.unique_objects -or $validation.paths_covered -ne $manifest.path_count) {throw 'Incomplete coverage'}
 foreach ($pack in $manifest.packs) {
  if ($pack.index -lt 0 -or $pack.index -gt 9999 -or $pack.sha256 -notmatch '^[0-9a-f]{64}$') {throw 'Invalid pack'}
  foreach ($direction in @('send','receive')) {
   $targets+=@{path=(Join-Path $work ('{0}/{1:D4}.tar' -f $direction,[int]$pack.index));bytes=$pack.bytes;sha256=$pack.sha256}
  }
 }
 $targets+=@{path=(Join-Path $work 'manifest-roundtrip.json');bytes=$publication.bytes;sha256=$manifestHash}
 foreach ($repoName in @('foundry','fishing-2d')) {
  $repo=if($repoName -eq 'foundry'){$root}else{Join-Path $root 'projects/fishing-2d'}
  foreach ($file in $manifest.repositories.$repoName.files) {
   $source=[IO.Path]::GetFullPath((Join-Path $repo $file.path))
   if (-not $source.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Invalid protected source'}
   $protected+=@{path=$source;bytes=$file.bytes;sha256=$file.oid}
  }
 }
}
$proofs=@('validation.json')
if ($Scope -in @('snapshot','agent')) {$proofs+=@('manifest.json','publication.json')}
$proofHashes=@{}
foreach ($name in $proofs) {$proofHashes[$name]=(Get-FileHash -LiteralPath (Join-Path $review $name) -Algorithm SHA256).Hash}
$eligible=@();$missing=@();$seen=@{}
foreach ($entry in $targets) {
 $full=[IO.Path]::GetFullPath($entry.path)
 if (-not $full.StartsWith($work+'\',[StringComparison]::OrdinalIgnoreCase) -or $seen.ContainsKey($full)) {throw 'Invalid or duplicate target'}
 $seen[$full]=$true
 if (-not (Test-Path -LiteralPath $full)) {$missing+=$full;continue}
 Assert-Hash $full $entry.sha256 $entry.bytes
 $relative=[IO.Path]::GetRelativePath($root,$full).Replace('\','/')
 $tracked=@(& git -C $root ls-files -- $relative)
 if ($LASTEXITCODE -ne 0 -or $tracked.Count) {throw 'Tracked target forbidden'}
 & git -C $root check-ignore -q -- $relative
 if ($LASTEXITCODE -ne 0) {throw 'Target must be ignored staging data'}
 $eligible+=$entry
}
foreach ($entry in $protected) {Assert-Hash $entry.path $entry.sha256 $entry.bytes}
$report=[ordered]@{ok=$true;scope=$Scope;apply=[bool]$Apply;proof_hashes=$proofHashes;eligible_files=$eligible.Count;eligible_bytes=($eligible | Measure-Object bytes -Sum).Sum;protected_files=$protected.Count;already_missing=$missing;deleted_files=0;deleted_bytes=0;files=$eligible}
$prefix=if($Scope -eq 'agent'){'agent-cache-'}else{''}
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $review ($prefix+'cleanup-preflight.json')) -Encoding utf8
if ($Apply) {
 foreach ($name in $proofs) {if ((Get-FileHash -LiteralPath (Join-Path $review $name) -Algorithm SHA256).Hash -ne $proofHashes[$name]) {throw 'Proof changed'}}
 foreach ($entry in $eligible) {
  Assert-Hash $entry.path $entry.sha256 $entry.bytes
  Remove-Item -LiteralPath $entry.path -Force
  $report.deleted_files++;$report.deleted_bytes+=$entry.bytes
 }
 $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $review ($prefix+'cleanup-execution.json')) -Encoding utf8
}
[pscustomobject]@{ok=$true;apply=[bool]$Apply;eligible_files=$eligible.Count;deleted_files=$report.deleted_files;deleted_bytes=$report.deleted_bytes;protected_files=$protected.Count} | ConvertTo-Json -Compress
