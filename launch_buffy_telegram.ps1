#!/usr/bin/env pwsh
<#
.SYNOPSIS
    SIMMOON — Buffy Telegram Bridge — Launch Script (PowerShell/Windows)
.DESCRIPTION
    Lanza el bridge Buffy↔Telegram en WSL2.
.PARAMETER Action
    start, status, stop, logs, attach, restart
.EXAMPLE
    .\launch_buffy_telegram.ps1
    .\launch_buffy_telegram.ps1 status
    .\launch_buffy_telegram.ps1 stop
#>

param(
    [ValidateSet("start", "status", "stop", "logs", "attach", "restart")]
    [string]$Action = "start"
)

$Distro = "Ubuntu"
$SessionName = "buffy-telegram"
$LogFile = "~/.simmoon-logs/buffy_telegram.log"
$SimmoonDir = "~/Simmoon_arc"

function Write-Color {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Test-Session {
    $result = wsl -d $Distro -- bash -c "tmux has-session -t $SessionName 2>/dev/null && echo 'YES' || echo 'NO'" 2>$null
    return $result -match "YES"
}

function Show-Status {
    Write-Host ""
    if (Test-Session) {
        Write-Color "  🟢 Buffy Telegram ACTIVA (sesión: $SessionName)" -Color Green
        Write-Color "  📱 Bot: @Jeremi_Hermes_bot" -Color Cyan
        Write-Host ""
        # Mostrar últimas líneas
        wsl -d $Distro -- bash -c "tmux capture-pane -t $SessionName -p 2>/dev/null | tail -5"
    } else {
        Write-Color "  ⚫ Buffy Telegram DETENIDA" -Color Red
    }
    Write-Host ""
}

function Start-Bridge {
    if (Test-Session) {
        Write-Color "  ⚠️  Buffy Telegram ya está activa" -Color Yellow
        Show-Status
        return
    }

    Write-Color "  🤖 Iniciando Buffy Telegram..." -Color Cyan

    # Crear directorio de logs
    wsl -d $Distro -- bash -c "mkdir -p ~/.simmoon-logs" 2>$null

    # Matar sesión anterior
    wsl -d $Distro -- bash -c "tmux kill-session -t $SessionName 2>/dev/null || true" 2>$null

    # Iniciar nueva sesión
    wsl -d $Distro -- bash -c "cd $SimmoonDir && tmux new-session -d -s $SessionName 'python3 buffy_telegram.py --daemon 2>&1 | tee $LogFile; bash'" 2>$null

    Start-Sleep -Seconds 2

    if (Test-Session) {
        Write-Color "  ✅ Buffy Telegram INICIADA (sesión: $SessionName)" -Color Green
        Write-Color "  📋 Logs: tail -f $LogFile (en WSL)" -Color Cyan
        Write-Color "  🖥️  Conectar: tmux attach -t $SessionName (en WSL)" -Color Cyan
    } else {
        Write-Color "  ❌ Error al iniciar Buffy Telegram" -Color Red
        Write-Color "  Revisa logs: wsl -d $Distro -- bash -c 'cat $LogFile'" -Color Yellow
    }
    Write-Host ""
}

function Stop-Bridge {
    Write-Host -NoNewline "  ⏹ Deteniendo Buffy Telegram... "
    wsl -d $Distro -- bash -c "tmux kill-session -t $SessionName 2>/dev/null; pkill -f buffy_telegram.py 2>/dev/null || true" 2>$null
    Write-Color "✅" -Color Green
}

function Show-Logs {
    Write-Host ""
    Write-Color "  📋 Últimos logs de Buffy:" -Color Cyan
    Write-Host "  ----------------------------------------"
    wsl -d $Distro -- bash -c "tail -40 $LogFile 2>/dev/null || echo '   (sin logs)'"
    Write-Host ""
}

function Attach-Session {
    if (Test-Session) {
        Write-Color "  🖥️  Conectando a sesión Buffy Telegram... (Ctrl+B D para salir)" -Color Cyan
        wsl -d $Distro -- bash -c "tmux attach -t $SessionName"
    } else {
        Write-Color "  ❌ Sesión no activa. Iníciala primero." -Color Red
    }
}

# ── Main ───────────────────────────────────────────────────────────────────
switch ($Action) {
    "status"  { Show-Status }
    "stop"    { Stop-Bridge }
    "logs"    { Show-Logs }
    "attach"  { Attach-Session }
    "restart" { Stop-Bridge; Start-Sleep 1; Start-Bridge }
    default   { Start-Bridge }
}
