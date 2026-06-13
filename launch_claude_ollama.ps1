<#
.SYNOPSIS
    Claude Code local + Ollama (un solo comando)
.DESCRIPTION
    1. Verifica que Ollama responde en http://localhost:11434
    2. Exporta las 3 env vars de Claude Code (ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN, ANTHROPIC_API_KEY)
    3. Invoca `claude` desde el directorio actual

    Requisitos:
      - Ollama >= 0.14.0 (soporte nativo de /v1/messages con formato Anthropic)
      - `claude` instalado via `npm install -g @anthropic-ai/claude-code`

    Si Ollama no esta corriendo, este script ABORTA con un mensaje claro.
    NO descarga modelos, NO persiste env vars — eso lo hacen los scripts
    especializados (install-claude-ollama-env.ps1, launch_ollama.ps1).

.PARAMETER OllamaPort
    Puerto donde escucha Ollama. Default: 11434.
.PARAMETER NoVerify
    Si se especifica, NO verifica que Ollama responda (asume que esta corriendo).
.EXAMPLE
    .\launch_claude_ollama.ps1
    .\launch_claude_ollama.ps1 -OllamaPort 11435
    cd C:\mi\proyecto && .\launch_claude_ollama.ps1   # claude arranca en ese dir
#>

[CmdletBinding()]
param(
    [int]$OllamaPort = 11434,
    [switch]$NoVerify
)

$ErrorActionPreference = "Stop"

function Write-Step { param([string]$T) Write-Host "" ; Write-Host $T -ForegroundColor Cyan }
function Write-Ok    { param([string]$T) Write-Host "  $T" -ForegroundColor Green }
function Write-Warn  { param([string]$T) Write-Host "  $T" -ForegroundColor Yellow }
function Write-Err   { param([string]$T) Write-Host "  $T" -ForegroundColor Red }

Write-Host "============================================" -ForegroundColor Magenta
Write-Host " launch_claude_ollama.ps1" -ForegroundColor Magenta
Write-Host " Claude Code local + Ollama (1 comando)" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  CWD:        $(Get-Location)"
Write-Host "  Ollama URL: http://localhost:$OllamaPort"
Write-Host ""

# ---------------------------------------------------------------------------
# Pre-flight: verificar que `claude` CLI esta instalado (cheapest check, fail-fast)
# ---------------------------------------------------------------------------
$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) {
    Write-Err "`claude` CLI no esta instalado."
    Write-Err "Instalalo con: npm install -g @anthropic-ai/claude-code"
    exit 1
}

# ---------------------------------------------------------------------------
# Paso 1/3: Verificar que Ollama responde en :11434
# ---------------------------------------------------------------------------
Write-Step "1/3  Verificar Ollama en :$OllamaPort"
if (-not $NoVerify) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$OllamaPort/api/version" -TimeoutSec 5
        Write-Ok "Ollama v$($response.version) respondiendo"
    } catch {
        Write-Err "Ollama no responde en http://localhost:$OllamaPort"
        Write-Err "Arrancalo primero con: .\launch_ollama.ps1 start"
        exit 1
    }
} else {
    Write-Warn "Verificacion omitida (-NoVerify)"
}

# ---------------------------------------------------------------------------
# Paso 2/3: Exportar las 3 env vars de Claude Code
# ---------------------------------------------------------------------------
Write-Step "2/3  Exportar env vars de Claude Code"
$env:ANTHROPIC_BASE_URL    = "http://localhost:$OllamaPort"
$env:ANTHROPIC_AUTH_TOKEN  = "ollama"
$env:ANTHROPIC_API_KEY     = ""
Write-Ok "ANTHROPIC_BASE_URL    = $env:ANTHROPIC_BASE_URL"
Write-Ok "ANTHROPIC_AUTH_TOKEN  = $env:ANTHROPIC_AUTH_TOKEN"
Write-Ok "ANTHROPIC_API_KEY     = (empty)"

# ---------------------------------------------------------------------------
# Paso 3/3: Invocar claude desde el directorio actual
# ---------------------------------------------------------------------------
Write-Step "3/3  Lanzar claude en $(Get-Location)"
Write-Ok "claude: $($claude.Source)"
Write-Host "  (Ctrl+C para salir de claude; Ollama seguira corriendo)" -ForegroundColor DarkGray
Write-Host ""
& claude @args
