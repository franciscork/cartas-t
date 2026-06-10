<#
.SYNOPSIS
    SIMMOON — Pipeline Launcher
    Lanza el pipeline LangGraph: ComfyUI → Pixel Art → PostgreSQL
.DESCRIPTION
    simmoon_pipeline.py ejecuta el workflow completo de generación de assets.
    Requiere ComfyUI corriendo en WSL2 (puerto 8188).
.PARAMETER Categories
    Categorías a procesar (si se omite, todas)
.PARAMETER RunSuffix
    Sufijo para nombres de archivo
.PARAMETER Checkpoint
    Checkpoint de ComfyUI
.PARAMETER NoLoras
    Desactiva LoRAs
.PARAMETER Lora
    Especificación LoRA (nombre:strength_model:strength_clip)
.PARAMETER SkipGeneration
    Salta el paso de generación con ComfyUI
.PARAMETER SkipPixel
    Salta la conversión a pixel art
.PARAMETER SkipDb
    Salta la inserción en PostgreSQL
.EXAMPLE
    .\launch_pipeline.ps1 -Categories businesses,vehicles
    .\launch_pipeline.ps1 -RunSuffix dream_v8 -Checkpoint dreamshaper_8.safetensors -NoLoras
    .\launch_pipeline.ps1 -SkipGeneration  # Solo pixel + DB
    .\launch_pipeline.ps1 -SkipPixel        # Solo generate + DB
#>

param(
    [string[]]$Categories,
    [string]$RunSuffix = "",
    [string]$Checkpoint = "",
    [switch]$NoLoras,
    [string]$Lora = "",
    [switch]$SkipGeneration,
    [switch]$SkipPixel,
    [switch]$SkipDb
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PipelineScript = Join-Path $ScriptDir "Simmoon_arc\simmoon_pipeline.py"

if (-not (Test-Path $PipelineScript)) {
    Write-Host "[ERROR] No se encuentra: $PipelineScript" -ForegroundColor Red
    exit 1
}

$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
$PythonPath = if ($PythonCmd) { $PythonCmd.Source } else { "python" }

Write-Host "🔄 SIMMOON Pipeline — LangGraph Workflow" -ForegroundColor Cyan
Write-Host "   ComfyUI → Pixel Art → PostgreSQL" -ForegroundColor Cyan

$cmdArgs = @($PipelineScript)

if ($Categories) {
    $cmdArgs += @("--category")
    $cmdArgs += $Categories
}

if ($RunSuffix) { $cmdArgs += @("--run-suffix", $RunSuffix) }
if ($Checkpoint) { $cmdArgs += @("--checkpoint", $Checkpoint) }
if ($NoLoras)   { $cmdArgs += @("--no-loras") }
if ($Lora)       { $cmdArgs += @("--lora", $Lora) }
if ($SkipGeneration) { $cmdArgs += @("--skip-generation") }
if ($SkipPixel)      { $cmdArgs += @("--skip-pixel") }
if ($SkipDb)         { $cmdArgs += @("--skip-db") }

Write-Host "  Cmd: python $($cmdArgs -join ' ')" -ForegroundColor DarkGray
& $PythonPath @cmdArgs
