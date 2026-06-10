<#
.SYNOPSIS
    SIMMOON — InvokeAI Launcher
    Start / Stop / Status del servicio InvokeAI en WSL2
.DESCRIPTION
    InvokeAI es un backend alternativo de generación de imágenes (puerto 9090).
    Usa symlinks a los checkpoints de ComfyUI para ahorrar espacio.
.PARAMETER Action
    start   — Inicia InvokeAI en WSL2
    stop    — Detiene InvokeAI
    status  — Muestra estado y modelos
    restart — Reinicia InvokeAI
.EXAMPLE
    .\launch_invokeai.ps1
    .\launch_invokeai.ps1 status
    .\launch_invokeai.ps1 stop
#>

param(
    [ValidateSet("start", "stop", "status", "restart")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
$Distro = "Ubuntu"
$InvokePort = 9090

function Write-Color { param([string]$T, [string]$C="White") Write-Host $T -ForegroundColor $C }
function Test-InvokeAI { wsl -d $Distro -- bash -c "curl -sf --max-time 2 http://localhost:$InvokePort/api/v1/app/version >/dev/null && echo YES || echo NO" 2>$null }

switch ($Action) {
    "start" {
        Write-Color "🖼️  InvokeAI — Iniciando..." -Color Green
        $running = Test-InvokeAI
        if ($running -eq "YES") {
            Write-Color "  ✅ Ya está corriendo en http://localhost:$InvokePort" -Color Green
        } else {
            wsl -d $Distro -- bash -c "source ~/invokeai-env/bin/activate 2>/dev/null && cd ~/invokeai && nohup invokeai-web --root ~/invokeai > /dev/null 2>&1 &" 2>$null
            Write-Color "  ⏳ Esperando (puede tardar 15-30s)..." -Color Yellow
            for ($i=0; $i -lt 45; $i++) {
                Start-Sleep -Seconds 1
                if ((Test-InvokeAI) -eq "YES") {
                    Write-Color "  ✅ Iniciado en http://localhost:$InvokePort" -Color Green
                    break
                }
                if ($i % 10 -eq 9) { Write-Host -NoNewline "  ." }
            }
            if ((Test-InvokeAI) -ne "YES") {
                Write-Color "  ⚠️ No respondió. Verifica: wsl -d Ubuntu -e bash -c 'source ~/invokeai-env/bin/activate && invokeai-web --version'" -Color Yellow
            }
        }
        Write-Color "  URL: http://localhost:$InvokePort" -Color Cyan
        Write-Color "  Checkpoints (symlinks a ComfyUI):" -Color Cyan
        wsl -d $Distro -- bash -c "ls -la ~/invokeai/models/checkpoints/*.safetensors 2>/dev/null | awk '{print \"    • \" \$NF}'" 2>$null
    }
    "stop" {
        Write-Color "🖼️  InvokeAI — Deteniendo..." -Color Yellow
        wsl -d $Distro -- bash -c "pkill -f 'invokeai-web' 2>/dev/null || true" 2>$null
        Write-Color "  ✅ Detenido" -Color Green
    }
    "status" {
        if ((Test-InvokeAI) -eq "YES") {
            Write-Color "🖼️  InvokeAI — ACTIVO en http://localhost:$InvokePort" -Color Green
        } else {
            Write-Color "🖼️  InvokeAI — INACTIVO" -Color Red
        }
    }
    "restart" {
        & $PSCommandPath -Action stop
        Start-Sleep -Seconds 2
        & $PSCommandPath -Action start
    }
}
