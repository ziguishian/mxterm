$ErrorActionPreference = "Stop"

$PackageRef = if ($env:PACKAGE_REF) { $env:PACKAGE_REF } else { "mxterm" }
$TargetShell = if ($env:MXTERM_SHELL) { $env:MXTERM_SHELL } else { "auto" }

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is required to install MXTerm."
}

if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    Write-Host "pipx not found. Installing pipx..." -ForegroundColor Yellow
    python -m pip install --user pipx
}

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Warning: Ollama is not on PATH. MXTerm can install, but AI translation will not work until Ollama is installed and running." -ForegroundColor Yellow
}

pipx install $PackageRef --force
mxterm config init | Out-Null
mxterm install --shell $TargetShell
Write-Host "MXTerm installed. Restart PowerShell to activate the hook." -ForegroundColor Green
