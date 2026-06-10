<#
.SYNOPSIS
    SIMMOON — Ollama Launcher
    Start / Stop / Status del servicio Ollama en WSL2
.DESCRIPTION
    Ollama es el servidor LLM local (puerto 11434).
    Modelos: gemma3-tools-64k, qwen3-14b-64k, qwen25-coder-14b-64k, nomic-embed-text
.PARAMETER Action
    start   — Inicia Ollama en WSL2
    stop    — Detiene Ollama
    status  — Muestra estado y modelos disponibles
    restart — Reinicia Ollama
.EXAMPLE
    .\launch_ollama.ps1
    .\launch_ollama.ps1 start
    .\launch_ollama.ps1 status
#>

param(
    [ValidateSet("start", "stop", "status", "restart")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
$Distro = "Ubuntu"
$OllamaPort = 11434

function Write-Color { param([string]$T, [string]$C="White") Write-Host $T -ForegroundColor $C }
function Test-Ollama { wsl -d $Distro -- bash -c "curl -sf --max-time 2 http://localhost:$OllamaPort/api/tags >/dev/null && echo YES || echo NO" 2>$null }

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
