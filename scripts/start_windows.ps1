# Build (if needed) and run the FinAlly Docker container.
# Safe to run multiple times: reuses an existing image unless -Build is
# passed, and replaces any existing container of the same name.
param(
    [switch]$Build
)

# Deliberately NOT using $ErrorActionPreference = "Stop": in Windows
# PowerShell 5.1, redirecting a native command's stderr (e.g. `2>$null`)
# wraps it in a terminating NativeCommandError under "Stop", turning
# ordinary docker CLI stderr output into an ugly stack trace instead of a
# clean message. Native command failures are instead checked explicitly via
# $LASTEXITCODE below.
$ErrorActionPreference = "Continue"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$ImageName = "finally"
$ContainerName = "finally"
$Port = 8000

docker version --format '{{.Server.Version}}' *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker does not appear to be running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host "No .env file found -- copying .env.example to .env."
    Write-Host "Edit .env and add your OPENROUTER_API_KEY before using AI chat."
    Copy-Item ".env.example" ".env"
}

$imageExists = docker images -q $ImageName
if ($Build -or -not $imageExists) {
    Write-Host "Building $ImageName image..."
    docker build -t $ImageName .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker build failed." -ForegroundColor Red
        exit 1
    }
}

$existing = docker ps -a --format '{{.Names}}' | Where-Object { $_ -eq $ContainerName }
if ($existing) {
    Write-Host "Removing existing $ContainerName container..."
    docker rm -f $ContainerName | Out-Null
}

Write-Host "Starting $ContainerName..."
docker run -d `
    --name $ContainerName `
    -p "${Port}:8000" `
    -v finally-data:/app/db `
    --env-file .env `
    $ImageName | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start the $ContainerName container." -ForegroundColor Red
    exit 1
}

$Url = "http://localhost:$Port"
Write-Host "FinAlly is running at $Url"

try {
    Start-Process $Url
} catch {}
