<#
.SYNOPSIS
    Agatha Actas — Launch Script (Windows)
.DESCRIPTION
    Lanza el agente de reportes horarios en WSL2.
.PARAMETER Action
    Acción: start, stop, status, setup, test, logs
.EXAMPLE
    .\launch_agatha.ps1          # Iniciar demonio
    .\launch_agatha.ps1 status   # Estado
    .\launch_agatha.ps1 stop     # Detener
    .\launch_agatha.ps1 setup    # Configurar chat ID
    .\launch_agatha.ps1 test     # Reporte de prueba
#>

param(
    [ValidateSet("start", "stop", "status", "setup", "test", "logs", "restart")]
    [string]$Action = "start"
)

$Distro = "Ubuntu"
$SessionName = "agatha-actas"
$LogFile = "~/.simmoon-logs/agatha_actas.log"

function Write-Color {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Status-Bot {
    $result = wsl -d $Distro -- bash -c "tmux has-session -t $SessionName 2>/dev/null && echo YES || echo NO" 2>$null
    if ($result -eq "YES") {
        Write-Color "  🟢 Agatha Actas activo (sesión: $SessionName)" -Color Green
        return $true
    } else {
        Write-Color "  ⚫ Agatha Actas detenido" -Color Red
        return $false
    }
}

function Start-Bot {
    if (Status-Bot) { Write-Color "  ⚠️  Ya está corriendo" -Color Yellow; return }
    Write-Color "  📋 Iniciando Agatha Actas (demonio)..." -Color Cyan
    wsl -d $Distro -- bash -c @"
cd ~/Simmoon_arc
mkdir -p ~/.simmoon-logs
tmux new-session -d -s $SessionName "python3 agatha_actas.py --daemon 2>&1 | tee $LogFile; bash"
"@ 2>$null
    Start-Sleep -Seconds 3
    if (Status-Bot) {
        Write-Color "  ✅ Agatha Actas iniciado" -Color Green
    } else {
        Write-Color "  ❌ Error al iniciar" -Color Red
    }
}

function Stop-Bot {
    Write-Host -NoNewline "  ⏹ Deteniendo Agatha Actas... "
    wsl -d $Distro -- bash -c "tmux kill-session -t $SessionName 2>/dev/null; pkill -f agatha_actas.py 2>/dev/null || true" 2>$null
    Write-Color "OK" -Color Green
}

function Run-Setup {
    wsl -d $Distro -- bash -c "cd ~/Simmoon_arc && python3 agatha_actas.py --setup"
}

function Run-Test {
    wsl -d $Distro -- bash -c "cd ~/Simmoon_arc && python3 agatha_actas.py --test"
}

function Show-Logs {
    wsl -d $Distro -- bash -c "tail -f $LogFile" 2>$null
}

# ── Main ───────────────────────────────────────────────────────────────────
switch ($Action) {
    "start"   { Start-Bot }
    "stop"    { Stop-Bot }
    "status"  { Status-Bot }
    "setup"   { Run-Setup }
    "test"    { Run-Test }
    "logs"    { Show-Logs }
    "restart" { Stop-Bot; Start-Sleep 1; Start-Bot }
}
