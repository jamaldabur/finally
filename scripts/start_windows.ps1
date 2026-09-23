# Idempotent launcher for FinAlly (PLAN.md section 11, DEPLOY-03).
#
# The same contract as scripts/start_mac.sh, in PowerShell: identical
# constants, identical step order, identical exit codes. See
# .planning/phases/05-docker-packaging-deployment/05-02-PLAN.md Task 2.

param([switch]$Build)

$ErrorActionPreference = "Stop"

$ImageTag = "finally:latest"
$ContainerName = "finally"
$HostPort = 8000
$AppUrl = "http://localhost:8000"

# Resolve the repository root from this script's own location, never the
# caller's working directory (D-02).
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

# Docker Desktop's WSL2 backend can print benign warnings to stderr (e.g.
# "WARNING: No blkio throttle.read_bps_device support"). Under
# $ErrorActionPreference = "Stop" any stderr text from a native command is
# treated as a terminating error, which would abort this script on those
# harmless warnings alone. Scope Continue to just the native call and check
# $LASTEXITCODE explicitly instead - the exit-code check the plan calls for.
#
# Callers always pass the argument list via the explicit -DockerArgs array
# (never as loose positional tokens): PowerShell's parameter binder treats
# a bare "-p" token as a partial match against this advanced function's
# implicit -PipelineVariable common parameter, which the docker CLI's own
# "-p" (publish port) flag collides with. A pre-built array bound to a
# single named parameter is never re-parsed that way.
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

# `docker rm -f` can return before the daemon has fully released the
# container name/port, particularly for a container with an in-flight
# HEALTHCHECK exec (this one has one, D-11) - a `docker run` reusing the
# same name immediately afterward can then race a "Conflict: container
# name already in use" that only reproduces with the real timing of a
# live invocation, never in an isolated one-off `docker rm` test. Block
# on the removal actually completing before any run/build step proceeds.
function Remove-FinallyContainer {
    param([string]$Name)
    Invoke-Docker -DockerArgs @("rm", "-f", $Name) *> $null
    for ($i = 0; $i -lt 20; $i++) {
        $stillPresent = Invoke-Docker -DockerArgs @("ps", "-a", "--filter", "name=^$Name$", "-q")
        if (-not $stillPresent) {
            return
        }
        Start-Sleep -Milliseconds 250
    }
}

# Under $ErrorActionPreference = "Stop", Write-Error raises a terminating
# error before the next line runs, so PowerShell prints its own error-record
# block (the script path, an At <file>:<line> position line, and a source
# excerpt) instead of the intended message, and the exit 1 after it never
# runs. Writing the line straight to the process's stderr handle is the
# PowerShell equivalent of the bash launcher's `echo ... >&2` and makes
# exit 1 reachable again (WR-03, 05-REVIEW.md). Write-Host was rejected
# because it writes to the information stream, not stderr, breaking parity
# with the bash script; saving/restoring $ErrorActionPreference still prints
# the full error record, just without terminating.
# 2. .env guard (D-09). Existence only - never Get-Content that file.
$EnvFile = Join-Path $RepoRoot ".env"
if (-not (Test-Path $EnvFile -PathType Leaf)) {
    [Console]::Error.WriteLine("Error: .env not found at $EnvFile`nCopy .env.example to .env and fill in OPENROUTER_API_KEY before starting FinAlly.")
    exit 1
}

# 3. Daemon reachability. A native command's failure does not raise a
# PowerShell exception, so the exit code must be checked explicitly.
Invoke-Docker -DockerArgs @("info") *> $null
if ($LASTEXITCODE -ne 0) {
    [Console]::Error.WriteLine("Error: Docker does not appear to be running. Start Docker Desktop (or the Docker daemon) and try again.")
    exit 1
}

# 4. Already-running check (D-07). The trailing $ inside the double-quoted
# string interpolates $ContainerName and then leaves a literal `$` anchor.
$running = Invoke-Docker -DockerArgs @("ps", "--filter", "name=^$ContainerName$", "--filter", "status=running", "-q")
if ($running) {
    if (-not $Build) {
        Write-Host "FinAlly is already running at $AppUrl"
        exit 0
    }
    # P-02: an explicit rebuild wins over "already running".
    Write-Host "Explicit rebuild requested - stopping the running container before rebuilding."
    Remove-FinallyContainer -Name $ContainerName
}

# 5. Remove any stopped container holding the name, using the same
# anchored filter against docker ps -a. The container holds no state.
$stopped = Invoke-Docker -DockerArgs @("ps", "-a", "--filter", "name=^$ContainerName$", "-q")
if ($stopped) {
    Remove-FinallyContainer -Name $ContainerName
}

# 6. Build when -Build was passed or when the image is missing (D-06).
Invoke-Docker -DockerArgs @("image", "inspect", $ImageTag) *> $null
$imageMissing = ($LASTEXITCODE -ne 0)
if ($Build -or $imageMissing) {
    Write-Host "Building $ImageTag - this may take several minutes on a first run."
    Invoke-Docker -DockerArgs @("build", "-t", $ImageTag, $RepoRoot)
    if ($LASTEXITCODE -ne 0) {
        [Console]::Error.WriteLine("Error: docker build failed.")
        exit 1
    }
}

# 7. Mount source, in this exact order - create before Resolve-Path, since
# Resolve-Path throws on a path that does not exist yet.
$DbDir = Join-Path $RepoRoot "db"
New-Item -ItemType Directory -Force -Path $DbDir | Out-Null
$DbDir = (Resolve-Path $DbDir).Path

# 8. Run. The volume argument is built by concatenation so a colon
# immediately after the interpolated variable can't be misread as part of
# the variable name.
$mountArg = $DbDir + ":/app/db"
$runArgs = @(
    "run", "-d", "--name", $ContainerName,
    "-p", "${HostPort}:8000",
    "--env-file", $EnvFile,
    "-v", $mountArg,
    $ImageTag
)
Invoke-Docker -DockerArgs $runArgs *> $null
if ($LASTEXITCODE -ne 0) {
    [Console]::Error.WriteLine("Error: docker run failed.")
    exit 1
}

# 9. Wait for readiness - roughly forty attempts, one second apart.
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri "$AppUrl/api/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        # Not ready yet - keep polling.
    }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    [Console]::Error.WriteLine("FinAlly's container started but never became healthy.`nCheck the logs with: docker logs $ContainerName")
    exit 1
}

# 10. Print the URL, then best-effort browser open (D-08). A failure to
# open a browser must never change the script's exit code.
Write-Host "FinAlly is running at $AppUrl"
try {
    Start-Process $AppUrl | Out-Null
} catch {
    # Best-effort only - a headless machine must not fail the script.
}

exit 0
