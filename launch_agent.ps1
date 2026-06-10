<#
.SYNOPSIS
    SIMMOON — AI Agent Launcher
    Lanza el agente de IA que recomienda qué assets generar.
.DESCRIPTION
    simmoon_agent.py usa Ollama para analizar el estado de los assets y
    recomendar la próxima categoría y checkpoint a generar.
.PARAMETER Action
    advise   — Pide recomendación al AI director
    scan     — Escanea el filesystem y muestra el estado de assets
    list     — Lista modelos Ollama disponibles
    generate — Genera assets según la recomendación de la IA
.PARAMETER Category
    Categoría a generar (ej. businesses, vehicles)
.PARAMETER Checkpoint
    Checkpoint a usar (ej. dreamshaper_8.safetensors)
.PARAMETER Model
    Modelo Ollama (default: qwen3-coder)
.EXAMPLE
    .\launch_agent.ps1 advise
    .\launch_agent.ps1 scan
    .\launch_agent.ps1 generate -Category businesses -Checkpoint dreamshaper_8.safetensors
    .\launch_agent.ps1 list
#>

param(
    [ValidateSet("advise", "scan", "list", "generate")]
    [string]$Action = "advise",
    [string]$Category,
    [string]$Checkpoint,
    [string]$Suffix,
    [string]$Model = "qwen3-coder"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AgentScript = Join-Path $ScriptDir "Simmoon_arc\simmoon_agent.py"

if (-not (Test-Path $AgentScript)) {
    Write-Host "[ERROR] No se encuentra: $AgentScript" -ForegroundColor Red
    exit 1
}

$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
$PythonPath = if ($PythonCmd) { $PythonCmd.Source } else { "python" }

switch ($Action) {
    "advise" {
        Write-Host "🧠 Simmoon Agent — Consultando AI Director..." -ForegroundColor Cyan
        & $PythonPath $AgentScript --advise --model $Model
    }
    "scan" {
        Write-Host "📊 Simmoon Agent — Escaneando assets..." -ForegroundColor Cyan
        & $PythonPath $AgentScript --scan
    }
    "list" {
        Write-Host "📋 Modelos Ollama disponibles:" -ForegroundColor Cyan
        & $PythonPath $AgentScript --list-models
    }
    "generate" {
        if (-not $Category -or -not $Checkpoint) {
            Write-Host "[ERROR] --Category y --Checkpoint son requeridos para generate" -ForegroundColor Red
            exit 1
        }
        $cmdArgs = @($AgentScript, "--generate", "--category", $Category, "--checkpoint", $Checkpoint)
        if ($Suffix) { $cmdArgs += @("--suffix", $Suffix) }
        if ($Model) { $cmdArgs += @("--model", $Model) }
        Write-Host "🎨 Generando: $Category con $Checkpoint..." -ForegroundColor Cyan
        & $PythonPath @cmdArgs
    }
}
