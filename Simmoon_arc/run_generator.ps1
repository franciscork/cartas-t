<#
.SYNOPSIS
    SIMMOON Image Generator - PowerShell launcher
.DESCRIPTION
    Launches the SIMMOON image generator with specified backend and categories.
.PARAMETER Backend
    Image generation backend: comfyui or huggingface
.PARAMETER Category
    Specific categories to generate (space-separated). Default: all.
.PARAMETER DryRun
    Preview all prompts without generating.
.EXAMPLE
    .\run_generator.ps1 -Backend comfyui
    .\run_generator.ps1 -Backend comfyui -Category businesses vehicles
    .\run_generator.ps1 -Backend huggingface -DryRun
#>

param(
    [ValidateSet("comfyui", "huggingface")]
    [string]$Backend = "comfyui",

    [string[]]$Category,

    [switch]$DryRun,

    [switch]$ListCategories
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$GeneratorScript = Join-Path $ScriptDir "simmoon_generator.py"

if (-not (Test-Path $GeneratorScript)) {
    Write-Host "[ERROR] simmoon_generator.py not found in $ScriptDir" -ForegroundColor Red
    exit 1
}

# Ensure requests is installed
try {
    python -c "import requests" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[*] Installing requests package..." -ForegroundColor Yellow
        pip install requests
    }
} catch {
    Write-Host "[ERROR] Python is required. Install Python 3.8+ from python.org" -ForegroundColor Red
    exit 1
}

# Build command
$Args = @($GeneratorScript, "--backend", $Backend)

if ($ListCategories) {
    $Args += "--list-categories"
}

if ($Category) {
    $Args += "--category"
    $Args += $Category
}

if ($DryRun) {
    $Args += "--dry-run"
}

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║     SIMMOON Image Generator                  ║" -ForegroundColor Cyan
Write-Host "  ║     Backend: $($Backend.PadRight(32))║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN] Listing prompts only..." -ForegroundColor Yellow
}
if ($Category) {
    Write-Host "[Categories] $($Category -join ', ')" -ForegroundColor Green
}

python @Args

Write-Host ""
Write-Host "Done." -ForegroundColor Green
