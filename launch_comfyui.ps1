<#
.SYNOPSIS
    SIMMOON — ComfyUI Launcher
    Start / Stop / Status del servicio ComfyUI en WSL2
.DESCRIPTION
    ComfyUI es el backend de generación de imágenes (puerto 8188).
    Checkpoints: dreamshaper_8, revAnimated_v122, counterfeit_v30, pixelArtSprite, v1-5
.PARAMETER Action
    start   — Inicia ComfyUI en WSL2
    stop    — Detiene ComfyUI
    status  — Muestra estado
    restart — Reinicia ComfyUI
.PARAMETER Port
    Puerto (default: 8188)
.EXAMPLE
    .\launch_comfyui.ps1
    .\launch_comfyui.ps1 status
    .\launch_comfyui.ps1 stop
#>

param(
    [ValidateSet("start", "stop", "status", "restart")]
    [string]$Action = "start",
    [int]$Port = 8188
)

$ErrorActionPreference = "Stop"
$Distro = "Ubuntu"

function Write-Color { param([string]$T, [string]$C="White") Write-Host $T -ForegroundColor $C }
function Test-ComfyUI { wsl -d $Distro -- bash -c "curl -sf --max-time 2 http://localhost:$Port/queue >/dev/null && echo YES || echo NO" 2>$null }

switch ($Action) {
    "start" {
        Write-Color "🎨 ComfyUI — Iniciando..." -Color Green
        $running = Test-ComfyUI
        if ($running -eq "YES") {
            Write-Color "  ✅ Ya está corriendo en http://localhost:$Port" -Color Green
        } else {
            wsl -d $Distro -- bash -c "cd ~/ComfyUI && nohup ./venv/bin/python main.py --listen --port $Port > /dev/null 2>&1 &" 2>$null
            Write-Color "  ⏳ Esperando (puede tardar 20-40s)..." -Color Yellow
            for ($i=0; $i -lt 60; $i++) {
                Start-Sleep -Seconds 1
                if ((Test-ComfyUI) -eq "YES") {
                    Write-Color "  ✅ Iniciado en http://localhost:$Port" -Color Green
                    break
                }
                if ($i % 10 -eq 9) { Write-Host -NoNewline "  ." }
            }
            if ((Test-ComfyUI) -ne "YES") {
                Write-Color "  ⚠️ No respondió en 60s. Verifica: wsl -d Ubuntu -e bash -c 'tail -20 ~/.simmoon-logs/comfyui.log'" -Color Yellow
            }
        }
        # Show checkpoints
        $ckpts = wsl -d $Distro -- bash -c "ls ~/ComfyUI/models/checkpoints/*.safetensors 2>/dev/null | xargs -I{} basename {}" 2>$null
        if ($ckpts) {
            Write-Color "  Checkpoints:" -Color Cyan
            foreach ($c in ($ckpts -split "`n" | Where-Object { $_ })) { Write-Color "    • $c" -Color Cyan }
        }
    }
    "stop" {
        Write-Color "🎨 ComfyUI — Deteniendo..." -Color Yellow
        wsl -d $Distro -- bash -c "pkill -f 'main.py.*--port $Port' 2>/dev/null || true" 2>$null
        Write-Color "  ✅ Detenido" -Color Green
    }
    "status" {
        if ((Test-ComfyUI) -eq "YES") {
            Write-Color "🎨 ComfyUI — ACTIVO en http://localhost:$Port" -Color Green
        } else {
            Write-Color "🎨 ComfyUI — INACTIVO" -Color Red
        }
    }
    "restart" {
        & $PSCommandPath -Action stop -Port $Port
        Start-Sleep -Seconds 2
        & $PSCommandPath -Action start -Port $Port
    }
}
