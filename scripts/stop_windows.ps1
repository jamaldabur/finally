# Idempotent stopper for FinAlly (PLAN.md section 11, DEPLOY-03).
#
# Never removes, prunes, moves, or truncates anything - stopping FinAlly
# must never be destructive to the user's portfolio (D-08).

param()

$ErrorActionPreference = "Stop"

$ContainerName = "finally"

# Resolve the repository root from this script's own location, not the
# caller's working directory - matches start_windows.ps1's constants exactly.
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

# Docker Desktop's WSL2 backend can print benign warnings to stderr; under
# $ErrorActionPreference = "Stop" that stderr text alone would otherwise be
# treated as a terminating error. Scope Continue to just the native call
# and check $LASTEXITCODE explicitly - matches start_windows.ps1 exactly,
# including always calling via the explicit -DockerArgs array (see that
# file's comment on the "-p"/-PipelineVariable collision this avoids).
function Invoke-Docker {
    param([Parameter(ValueFromRemainingArguments = $true)]$DockerArgs)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        docker @DockerArgs
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

# 2. If the daemon isn't reachable, FinAlly definitionally is not running.
Invoke-Docker -DockerArgs @("info") *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "FinAlly is not running (Docker does not appear to be running)."
    exit 0
}

# 3. Query the same anchored running filter used by start_windows.ps1 (D-07).
$running = Invoke-Docker -DockerArgs @("ps", "--filter", "name=^$ContainerName$", "--filter", "status=running", "-q")
if (-not $running) {
    Write-Host "FinAlly is not running."
    exit 0
}

# 4. Stop it. The data in db/ is left untouched.
Invoke-Docker -DockerArgs @("stop", $ContainerName) *> $null
Write-Host "FinAlly is stopped. The data in $RepoRoot\db has been left untouched."
exit 0
