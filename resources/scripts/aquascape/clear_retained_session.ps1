param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$Plan
)
$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath($Root).TrimEnd('\')
$receipt = Get-Content -LiteralPath $Plan -Raw -Encoding UTF8 | ConvertFrom-Json
if ($receipt.root -ne $workspace) { throw 'Plan/workspace mismatch' }
$allowed = @($receipt.allowed_source_roots)
$allowed += @(
    "$workspace\projects\fishing-2d\game\assets\aquascape-v5\plant-static",
    "$workspace\projects\fishing-2d\game\assets\aquascape-v7\plant-static",
    "$workspace\projects\fishing-2d\game\assets\aquascape-v5\plants",
    "$workspace\projects\fishing-2d\game\assets\aquascape-v6\plants"
)
$reviewRoot = "$workspace\projects\fishing-2d\plans\reviews"
$allowed += @(Get-ChildItem -LiteralPath $reviewRoot -Directory | Where-Object {
    $_.Name.StartsWith('aquascape-') -or $_.Name.StartsWith('aquarium-hall-')
} | ForEach-Object { $_.FullName })

function Assert-BoundedPath([string]$Path) {
    $absolute = [IO.Path]::GetFullPath($Path)
    if (-not $absolute.StartsWith($workspace + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Outside workspace: $absolute"
    }
    $inside = $false
    foreach ($directory in $allowed) {
        $boundary = [IO.Path]::GetFullPath($directory).TrimEnd('\')
        if ($absolute.StartsWith($boundary + '\', [StringComparison]::OrdinalIgnoreCase)) { $inside = $true; break }
    }
    if (-not $inside) { throw "Outside aquascape cleanup roots: $absolute" }
    return $absolute
}

# Recheck every resolved path and byte hash before deleting any file.
foreach ($row in $receipt.remove) {
    $absolute = Assert-BoundedPath $row.path
    $item = Get-Item -LiteralPath $absolute -Force
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Not an ordinary file: $absolute"
    }
    if ((Get-FileHash -LiteralPath $absolute -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) {
        throw "File changed after planning: $absolute"
    }
}
foreach ($row in $receipt.remove) { Remove-Item -LiteralPath (Assert-BoundedPath $row.path) -Force }
Write-Output "Deleted $($receipt.remove.Count) bounded files. Run retain_session.py --verify for the final receipt."
