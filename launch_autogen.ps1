<#
.SYNOPSIS
    SIMMOON — AutoGen Launcher
    Lanza el sistema multi-agente de diseño colaborativo.
.DESCRIPTION
    simmoon_autogen.py usa 3 agentes (Generator, Critic, Curator) para diseñar,
    refinar y aprobar prompts de assets para SIMMOON.
.PARAMETER Action
    design — Sesión de diseño para una categoría
    quick  — Sugerencia rápida (opcional: categoría)
    list   — Lista categorías disponibles
    chat   — Modo interactivo
.PARAMETER Category
    Categoría a diseñar (ej. businesses, vehicles)
.PARAMETER Model
    Modelo Ollama (default: qwen3-coder)
.EXAMPLE
    .\launch_autogen.ps1 design businesses
    .\launch_autogen.ps1 quick
    .\launch_autogen.ps1 quick lunar_sites
    .\launch_autogen.ps1 list
    .\launch_autogen.ps1 chat
#>

param(
    [ValidateSet("design", "quick", "list", "chat")]
    [string]$Action = "chat",
    [string]$Category,
    [string]$Model = "qwen3-coder"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AutoGenScript = Join-Path $ScriptDir "Simmoon_arc\simmoon_autogen.py"

if (-not (Test-Path $AutoGenScript)) {
    Write-Host "[ERROR] No se encuentra: $AutoGenScript" -ForegroundColor Red
    exit 1
}

$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
$PythonPath = if ($PythonCmd) { $PythonCmd.Source } else { "python" }

switch ($Action) {
    "design" {
        if (-not $Category) {
            Write-Host "[ERROR] --Category requerida para design. Ej: .\launch_autogen.ps1 design businesses" -ForegroundColor Red
            exit 1
        }
        Write-Host "🤖 AutoGen — Sesión de diseño: $Category" -ForegroundColor Magenta
        Write-Host "   Agentes: Generator + Critic + Curator" -ForegroundColor Cyan
        & $PythonPath $AutoGenScript --design $Category --model $Model
    }
    "quick" {
        if ($Category) {
            Write-Host "⚡ AutoGen — Sugerencia rápida: $Category" -ForegroundColor Magenta
            & $PythonPath $AutoGenScript --quick $Category --model $Model
        } else {
            Write-Host "⚡ AutoGen — Sugerencia rápida" -ForegroundColor Magenta
            & $PythonPath $AutoGenScript --quick --model $Model
        }
    }
    "list" {
        & $PythonPath $AutoGenScript --list-categories
    }
    "chat" {
        Write-Host "🤖 AutoGen — Modo interactivo" -ForegroundColor Magenta
        Write-Host "   Comandos: design <cat> | quick [cat] | list | quit" -ForegroundColor Cyan
        & $PythonPath $AutoGenScript --model $Model
    }
}
