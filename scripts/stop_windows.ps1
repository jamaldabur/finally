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

# 1. Accept zero arguments only. An empty param() rejects nothing by
# itself, because unbound tokens land in $args, so the check is explicit
# (see step 1 of start_windows.ps1). $args alone also misses a
# colon-suffixed token the -File parser drops before this script runs, so
# the host command line is cross-checked too - see step 1 of
# start_windows.ps1 for the rationale. If the cross-check cannot find
# this script's own path in the host command line, the invocation is
# rejected (fail closed) - see step 1 of start_windows.ps1.
# BEGIN host-argv cross-check: keep this block identical in start_windows.ps1 and stop_windows.ps1
$ScriptArgs = @($args)
$RawArgs = $null
$ArgsIntact = $true
if ([string]::IsNullOrEmpty($MyInvocation.Line)) {
    $HostArgs = [Environment]::GetCommandLineArgs()
    for ($i = 1; $i -lt $HostArgs.Count; $i++) {
        $candidate = $null
        try {
            $candidate = [System.IO.Path]::GetFullPath($HostArgs[$i])
        } catch {
            $candidate = $null
        }
        if ($candidate -and ($candidate -eq $PSCommandPath)) {
            $RawArgs = @($HostArgs | Select-Object -Skip ($i + 1))
            break
        }
    }
    if ($null -eq $RawArgs) {
        # No host argv token names this script's own path, so the
        # caller's raw tokens cannot be recovered. Fail closed instead of
        # trusting $args alone (05-REVIEW.md CR-01, 2026-09-27 pass).
        $ArgsIntact = $false
    } elseif ($RawArgs.Count -ne $ScriptArgs.Count) {
        $ArgsIntact = $false
    } else {
        foreach ($token in $RawArgs) {
            if ($token.EndsWith(":", [System.StringComparison]::Ordinal)) {
                $ArgsIntact = $false
            }
        }
    }
}
# END host-argv cross-check
if (-not $ArgsIntact -or $ScriptArgs.Count -gt 0) {
    [Console]::Error.WriteLine("Usage: stop_windows.ps1")
    exit 1
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
