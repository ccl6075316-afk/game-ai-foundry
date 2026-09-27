# Repo-local launcher: prefer .venv, never Windows Store python stubs.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
$Launcher = Join-Path $Root "gamefactory.py"

if (-not (Test-Path $VenvPy)) {
    Write-Host "[gamefactory] .venv missing. Bootstrapping with setup ensure-python ..."
    $bootstrap = $null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $bootstrap = { & py -3 (Join-Path $Root "cli\gamefactory.py") setup ensure-python }
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $bootstrap = { & python (Join-Path $Root "cli\gamefactory.py") setup ensure-python }
    } else {
        throw "No usable Python found to bootstrap .venv. Install Python 3.11+ from python.org."
    }
    & $bootstrap
    if (-not (Test-Path $VenvPy)) {
        throw "Failed to create .venv. Run: py -3 cli\gamefactory.py setup ensure-python --json"
    }
}

& $VenvPy $Launcher @args
exit $LASTEXITCODE
