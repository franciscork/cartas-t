<#
.SYNOPSIS
    SIMMOON Telegram Bot — Launch Script (Windows)
.DESCRIPTION
    Lanza el bot multi-agente de Telegram. Usa TELEGRAM_BOT_TOKEN
    de variable de entorno o telegram_config.json.
.PARAMETER Action
    Acción: start, stop, status, logs, send
.PARAMETER Message
    Mensaje para enviar (solo con -Action send)
.EXAMPLE
    .\launch_telegram_bot.ps1                    # Iniciar bot
    .\launch_telegram_bot.ps1 status             # Estado
    .\launch_telegram_bot.ps1 stop               # Detener
    .\launch_telegram_bot.ps1 logs               # Ver logs
    .\launch_telegram_bot.ps1 send -Message "Hola"  # Enviar mensaje
#>

param(
    [ValidateSet("start", "stop", "status", "logs", "restart")]
    [string]$Action = "start"
)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SimmoonDir = Join-Path $ProjectRoot "Simmoon_arc"
$BotScript = Join-Path $SimmoonDir "telegram_bot.py"
$SessionName = "telegram-bot"
$LogDir = "$env:USERPROFILE\.simmoon-logs"
$LogFile = "$LogDir\telegram_bot.log"

# ── Colors ─────────────────────────────────────────────────────────────────
$Colors = @{
    Green  = "Green"
    Red    = "Red"
    Yellow = "Yellow"
    Cyan   = "Cyan"
}

function Write-Color {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Status-Bot {
    $result = wsl -d Ubuntu -- bash -c "tmux has-session -t $SessionName 2>/dev/null && echo YES || echo NO" 2>$null
    if ($result -eq "YES") {
        Write-Color "  🟢 Telegram Bot activo (sesión: $SessionName)" -Color $Colors.Green
        return $true
    } else {
        Write-Color "  ⚫ Telegram Bot detenido" -Color $Colors.Red
        return $false
    }
}

function Start-Bot {
    if (-not (Test-Path $BotScript)) {
        Write-Color "  ❌ No se encuentra $BotScript" -Color $Colors.Red
        return
    }

    # Verificar que hay token
    $token = [Environment]::GetEnvironmentVariable("TELEGRAM_BOT_TOKEN")
    if (-not $token) {
        # Revisar config file
        $cfgPath = Join-Path $SimmoonDir "telegram_config.json"
        if (Test-Path $cfgPath) {
            $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
            $token = $cfg.telegram_token
        }
    }
    if (-not $token) {
        Write-Color "  ⚠️  No hay token configurado." -Color $Colors.Yellow
        Write-Color "  Configura TELEGRAM_BOT_TOKEN como variable de entorno" -Color $Colors.Yellow
        Write-Color "  o edita Simmoon_arc/telegram_config.json" -Color $Colors.Yellow
        return
    }

    if (Status-Bot) {
        Write-Color "  ⚠️  El bot ya está corriendo." -Color $Colors.Yellow
        Write-Color "     .\launch_telegram_bot.ps1 stop" -Color $Colors.Yellow
        return
    }

    Write-Color "  🤖 Iniciando Telegram Bot..." -Color $Colors.Cyan
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

    # Iniciar en WSL2 via tmux
    wsl -d Ubuntu -- bash -c @"
cd '$SimmoonDir'
mkdir -p '$LogDir'
TELEGRAM_BOT_TOKEN='$token' tmux new-session -d -s $SessionName \
    "python3 telegram_bot.py 2>&1 | tee '$LogFile'; bash"
"@ 2>$null

    Start-Sleep -Seconds 4

    if (Status-Bot) {
        Write-Color "  ✅ Telegram Bot iniciado" -Color $Colors.Green
        Write-Color "  🧠 Bot: @Jeremi_Hermes_bot" -Color $Colors.Cyan
        Write-Color "  📋 Logs: Get-Content '$LogFile' -Tail 20" -Color $Colors.Cyan
        Write-Color "  🖥️  TUI:  wsl tmux attach -t $SessionName" -Color $Colors.Cyan
    } else {
        Write-Color "  ❌ Error al iniciar. Logs:" -Color $Colors.Red
        if (Test-Path $LogFile) { Get-Content $LogFile -Tail 10 }
    }
}

function Stop-Bot {
    Write-Host -NoNewline "  ⏹ Deteniendo Telegram Bot... "
    wsl -d Ubuntu -- bash -c "tmux kill-session -t $SessionName 2>/dev/null; pkill -f telegram_bot.py 2>/dev/null || true" 2>$null
    # También matar procesos Python en Windows
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "telegram_bot" } | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Color "OK" -Color $Colors.Green
}

function Show-Logs {
    if (Test-Path $LogFile) {
        Get-Content $LogFile -Tail 30
    } else {
        Write-Color "  📭 No hay logs aún." -Color $Colors.Yellow
    }
}

# ── Main ───────────────────────────────────────────────────────────────────
switch ($Action) {
    "start"   { Start-Bot }
    "stop"    { Stop-Bot }
    "status"  { Status-Bot }
    "logs"    { Show-Logs }
    "restart" { Stop-Bot; Start-Sleep 2; Start-Bot }
}
