# Stop and remove the FinAlly container. Does NOT remove the data volume --
# your portfolio/watchlist persist across restarts. Safe to run repeatedly.
# Deliberately NOT using $ErrorActionPreference = "Stop" -- see the comment
# in start_windows.ps1 about native stderr + "Stop" producing stack traces
# instead of clean messages.
$ErrorActionPreference = "Continue"

$ContainerName = "finally"

docker version --format '{{.Server.Version}}' *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker does not appear to be running -- nothing to stop." -ForegroundColor Yellow
    exit 0
}

$existing = docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $ContainerName }
if ($existing) {
    Write-Host "Stopping and removing $ContainerName..."
    docker rm -f $ContainerName | Out-Null
    Write-Host "Stopped."
} else {
    Write-Host "$ContainerName is not running."
}
