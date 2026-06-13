<#
.SYNOPSIS
    SIMMOON — Ollama Launcher
    Start / Stop / Status del servicio Ollama en WSL2
.DESCRIPTION
    Ollama es el servidor LLM local (puerto 11434).
    Modelos: gemma3-tools-64k, qwen3-14b-64k, qwen25-coder-14b-64k, nomic-embed-text

    Cuando arranca Ollama, exporta automaticamente las 3 env vars necesarias
    para que Claude Code (@anthropic-ai/claude-code) lo use como backend:
      $env:ANTHROPIC_BASE_URL   = "http://localhost:11434"
      $env:ANTHROPIC_AUTH_TOKEN = "ollama"
      $env:ANTHROPIC_API_KEY    = ""
    Ollama expone /v1/messages (compat con API Anthropic) desde v0.14.0 (ene-2026).
.PARAMETER Action
    start   — Inicia Ollama en WSL2 y exporta env vars de Claude Code
    stop    — Detiene Ollama
    status  — Muestra estado y modelos disponibles (re-exporta env vars si esta activo)
    restart — Reinicia Ollama
.PARAMETER Persistent
    Si se especifica, persiste las env vars en el registro de usuario (HKCU\Environment)
    para que esten disponibles en TODAS las sesiones futuras de PowerShell.
.EXAMPLE
    .\launch_ollama.ps1
    .\launch_ollama.ps1 start
    .\launch_ollama.ps1 status
    .\launch_ollama.ps1 start -Persistent
#>

param(
    [ValidateSet("start", "stop", "status", "restart")]
    [string]$Action = "start",
    [switch]$Persistent
)

$ErrorActionPreference = "Stop"
$Distro = "Ubuntu"
$OllamaPort = 11434

function Write-Color { param([string]$T, [string]$C="White") Write-Host $T -ForegroundColor $C }
function Test-Ollama { wsl -d $Distro -- bash -c "curl -sf --max-time 2 http://localhost:$OllamaPort/api/tags >/dev/null && echo YES || echo NO" 2>$null }

# Exporta las 3 env vars para que Claude Code use Ollama como backend (API Anthropic en /v1/messages).
# - Sesion actual: $env:ANTHROPIC_* (vive solo en este proceso de PowerShell).
# - Persistente (con -Persistent): HKCU\Environment via [System.Environment]::SetEnvironmentVariable.
function Set-ClaudeEnv {
    param([bool]$MakePersistent = $false)
    $env:ANTHROPIC_BASE_URL    = "http://localhost:$OllamaPort"
    $env:ANTHROPIC_AUTH_TOKEN  = "ollama"
    $env:ANTHROPIC_API_KEY     = ""
    if ($MakePersistent) {
        [System.Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL",   $env:ANTHROPIC_BASE_URL,   "User")
        [System.Environment]::SetEnvironmentVariable("ANTHROPIC_AUTH_TOKEN", $env:ANTHROPIC_AUTH_TOKEN, "User")
        [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY",    "",                       "User")
        Write-Color "  🔒 Env vars persistidas en HKCU\Environment (sobreviven al cerrar PowerShell)" -Color Magenta
    }
    Write-Color "  🔧 Env vars exportadas para Claude Code:" -Color Green
    Write-Color "     `$env:ANTHROPIC_BASE_URL    = '$env:ANTHROPIC_BASE_URL'" -Color Gray
    Write-Color "     `$env:ANTHROPIC_AUTH_TOKEN  = '$env:ANTHROPIC_AUTH_TOKEN'" -Color Gray
    Write-Color "     `$env:ANTHROPIC_API_KEY     = ''" -Color Gray
    Write-Color "  💡 Ahora puedes ejecutar: claude" -Color Cyan
}

switch ($Action) {
    "start" {
        Write-Color "🧠 Ollama — Iniciando..." -Color Green
        $running = Test-Ollama
        if ($running -eq "YES") {
            Write-Color "  ✅ Ya está corriendo en http://localhost:$OllamaPort" -Color Green
        } else {
            wsl -d $Distro -- bash -c "nohup ollama serve > /dev/null 2>&1 &" 2>$null
            Start-Sleep -Seconds 2
            $running = Test-Ollama
            if ($running -eq "YES") {
                Write-Color "  ✅ Iniciado en http://localhost:$OllamaPort" -Color Green
            } else {
                Write-Color "  ⚠️ No respondió. Prueba 'wsl -d Ubuntu' y ejecuta 'ollama serve' manualmente." -Color Yellow
            }
        }
        # Show models
        $models = wsl -d $Distro -- bash -c "curl -sf http://localhost:$OllamaPort/api/tags | python3 -c \"import sys,json; d=json.load(sys.stdin); [print('    '+m['name']) for m in d.get('models',[])]\" 2>/dev/null"
        if ($models) { Write-Color "  Modelos:`n$models" -Color Cyan }
        # Auto-export env vars de Claude Code ahora que Ollama esta corriendo
        Set-ClaudeEnv -MakePersistent $Persistent
    }
    "stop" {
        Write-Color "🧠 Ollama — Deteniendo..." -Color Yellow
        wsl -d $Distro -- bash -c "pkill -f 'ollama serve' 2>/dev/null || true" 2>$null
        Write-Color "  ✅ Detenido" -Color Green
    }
    "status" {
        $running = Test-Ollama
        if ($running -eq "YES") {
            Write-Color "🧠 Ollama — ACTIVO en http://localhost:$OllamaPort" -Color Green
            $models = wsl -d $Distro -- bash -c "curl -sf http://localhost:$OllamaPort/api/tags | python3 -c \"import sys,json; d=json.load(sys.stdin); [print('  • '+m['name']) for m in d.get('models',[])]\" 2>/dev/null" 2>$null
            if ($models) { Write-Color "  Modelos:`n$models" -Color Cyan }
            # Re-export env vars para que el usuario pueda correr 'claude' sin reconfigurar
            Set-ClaudeEnv -MakePersistent $Persistent
        } else {
            Write-Color "🧠 Ollama — INACTIVO" -Color Red
        }
    }
    "restart" {
        & $PSCommandPath -Action stop
        Start-Sleep -Seconds 1
        & $PSCommandPath -Action start
    }
}
