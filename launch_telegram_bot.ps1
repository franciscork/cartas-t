<#
.SYNOPSIS
    SIMMOON Telegram Bot — Launch Script (Windows)
.DESCRIPTION
    Lanza el bot multi-agente de Telegram en WSL2.
.PARAMETER Action
    Acción: start, stop, status, logs
.EXAMPLE
    .\launch_telegram_bot.ps1          # Iniciar
    .\launch_telegram_bot.ps1 status   # Estado
    .\launch_telegram_bot.ps1 stop     # Detener
#>

param(
    [ValidateSet("start", "stop", "status", "logs", "restart")]
    [string]$Action = "start"
)

$Distro = "Ubuntu"
$SessionName = "telegram-bot"
$LogFile = "~/.simmoon-logs/telegram_bot.log"

function Write-Color {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Status-Bot {
    $result = wsl -d $Distro -- bash -c "tmux has-session -t $SessionName 2>/dev/null && echo YES || echo NO" 2>$null
    if ($result -eq "YES") {
        Write-Color "  🟢 Telegram Bot activo (sesión: $SessionName)" -Color Green
        return $true
    } else {
        Write-Color "  ⚫ Telegram Bot detenido" -Color Red
        return $false
    }
}

function Start-Bot {
    if (Status-Bot) {
        Write-Color "  ⚠️  El bot ya está corriendo. Detenlo primero:" -Color Yellow
        Write-Color "     .\launch_telegram_bot.ps1 stop" -Color Yellow
        return
    }

    Write-Color "  🤖 Iniciando Telegram Bot..." -Color Cyan

    wsl -d $Distro -- bash -c @"
cd ~/Simmoon_arc
mkdir -p ~/.simmoon-logs
tmux new-session -d -s $SessionName "python3 telegram_bot.py 2>&1 | tee $LogFile; bash"
"@ 2>$null

    Start-Sleep -Seconds 3

    if (Status-Bot) {
        Write-Color "  ✅ Telegram Bot iniciado" -Color Green
        Write-Color "  📋 Logs: wsl tail -f $LogFile" -Color Cyan
        Write-Color "  🖥️  TUI:  wsl tmux attach -t $SessionName" -Color Cyan
    } else {
        Write-Color "  ❌ Error al iniciar" -Color Red
    }
}

function Stop-Bot {
    Write-Host -NoNewline "  ⏹ Deteniendo Telegram Bot... "
    wsl -d $Distro -- bash -c "tmux kill-session -t $SessionName 2>/dev/null; pkill -f telegram_bot.py 2>/dev/null || true" 2>$null
    Write-Color "OK" -Color Green
}

function Show-Logs {
    wsl -d $Distro -- bash -c "tail -f $LogFile" 2>$null
}

# ── Main ───────────────────────────────────────────────────────────────────
switch ($Action) {
    "start"   { Start-Bot }
    "stop"    { Stop-Bot }
    "status"  { Status-Bot }
    "logs"    { Show-Logs }
    "restart" { Stop-Bot; Start-Sleep 1; Start-Bot }
}
