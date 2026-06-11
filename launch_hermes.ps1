<#
.SYNOPSIS
    SIMMOON — Hermes Agent Launcher (Windows)
    Lanza las 3 interfaces desktop de Hermes en WSL2
.DESCRIPTION
    Hermes es el framework de agentes de Nous Research corriendo con Ollama.
    3 interfaces:
      • Gateway   — Backend compartido (sesión tmux: hermes-gateway)
      • TUI       — Interfaz de terminal (sesión tmux: hermes-tui)
      • Dashboard — Interfaz web (puerto 9119)
.PARAMETER Action
    start   — Inicia Gateway + TUI + Dashboard
    stop    — Detiene todas las interfaces
    status  — Muestra estado
    restart — Reinicia todo
.PARAMETER DashboardPort
    Puerto del dashboard web (default: 9119)
.EXAMPLE
    .\launch_hermes.ps1
    .\launch_hermes.ps1 status
    .\launch_hermes.ps1 stop
    .\launch_hermes.ps1 restart
#>

param(
    [ValidateSet("start", "stop", "status", "restart")]
    [string]$Action = "start",
    [int]$DashboardPort = 9119
)

$ErrorActionPreference = "Stop"
$Distro = "Ubuntu"

function Write-Color { param([string]$T, [string]$C="White") Write-Host $T -ForegroundColor $C }

switch ($Action) {
    "start" {
        Write-Color @"
╔══════════════════════════════════════════════════╗
║  🧠 Hermes Agent — Launch Center (Windows)       ║
║  v0.16.0 · Nous Research · Ollama Local          ║
╚══════════════════════════════════════════════════╝
"@ -Color Magenta

        # Verify Ollama
        Write-Color "[1/6] Verificando Ollama..." -Color Yellow
        $ollamaOk = wsl -d $Distro -- bash -c "curl -sf --max-time 2 http://localhost:11434/api/tags >/dev/null && echo YES || echo NO" 2>$null
        if ($ollamaOk -eq "YES") {
            Write-Color "  ✅ Ollama activo" -Color Green
        } else {
            Write-Color "  ⚠️ Ollama no responde. Iniciando..." -Color Yellow
            wsl -d $Distro -- bash -c "nohup ollama serve > /dev/null 2>&1 &" 2>$null
            Start-Sleep -Seconds 3
        }

        # Stop existing sessions
        Write-Color "[2/6] Limpiando sesiones previas..." -Color Yellow
        wsl -d $Distro -- bash -c "tmux kill-session -t hermes-gateway 2>/dev/null; tmux kill-session -t hermes-tui 2>/dev/null; tmux kill-session -t hermes-dashboard 2>/dev/null; pkill -f 'hermes' 2>/dev/null; echo DONE" 2>$null
        netsh interface portproxy delete v4tov4 listenport=$DashboardPort listenaddress=127.0.0.1 2>$null
        Write-Color "  ✅ Limpieza completada" -Color Green

        # Launch Gateway
        Write-Color "[3/6] Iniciando Gateway..." -Color Yellow
        wsl -d $Distro -- bash -c "export PATH=`$HOME/.local/bin:`$PATH; mkdir -p `$HOME/.hermes/logs; tmux new-session -d -s hermes-gateway 'source ~/.bashrc 2>/dev/null; export PATH=/usr/local/bin:/usr/bin:/bin:`$HOME/.local/bin && hermes gateway run --replace 2>&1 | tee `$HOME/.hermes/logs/gateway.log; bash'" 2>$null
        Start-Sleep -Seconds 3
        Write-Color "  ✅ Gateway activo (sesión: hermes-gateway)" -Color Green

        # Launch TUI
        Write-Color "[4/6] Iniciando TUI (Terminal)..." -Color Yellow
        wsl -d $Distro -- bash -c "export PATH=`$HOME/.local/bin:`$PATH; mkdir -p `$HOME/.hermes/logs; tmux new-session -d -s hermes-tui 'source ~/.bashrc 2>/dev/null; export PATH=/usr/local/bin:/usr/bin:/bin:`$HOME/.local/bin && hermes --tui 2>&1 | tee `$HOME/.hermes/logs/tui.log; bash'" 2>$null
        Write-Color "  ✅ TUI activo (sesión: hermes-tui)" -Color Green
        Write-Color "     Acceder: wsl -d Ubuntu -e bash -c 'tmux attach -t hermes-tui'" -Color Cyan

        # Launch Dashboard
        Write-Color "[5/6] Iniciando Dashboard (Web)..." -Color Yellow
        wsl -d $Distro -- bash -c "export PATH=`$HOME/.local/bin:`$PATH; mkdir -p `$HOME/.hermes/logs; tmux new-session -d -s hermes-dashboard 'source ~/.bashrc 2>/dev/null; export PATH=/usr/local/bin:/usr/bin:/bin:`$HOME/.local/bin && hermes dashboard --port $DashboardPort --no-open 2>&1 | tee `$HOME/.hermes/logs/dashboard.log; bash'" 2>$null
        Start-Sleep -Seconds 3
        Write-Color "  ✅ Dashboard en http://localhost:$DashboardPort" -Color Green

        # Setup port forwarding from Windows to WSL
        Write-Color "[6/6] Configurando port forwarding Windows → WSL..." -Color Yellow
        $wslIp = wsl -d $Distro -- bash -c "ip addr show eth0 2>/dev/null | grep 'inet ' | awk '{print \$2}' | cut -d/ -f1" 2>$null
        if ($wslIp) {
            netsh interface portproxy delete v4tov4 listenport=$DashboardPort listenaddress=127.0.0.1 2>$null
            netsh interface portproxy add v4tov4 listenport=$DashboardPort listenaddress=127.0.0.1 connectport=$DashboardPort connectaddress=$wslIp 2>$null
            Write-Color "  ✅ Port forwarding: Windows:$DashboardPort → WSL:$DashboardPort ($wslIp)" -Color Green
        } else {
            Write-Color "  ⚠️ No se pudo detectar IP de WSL para port forwarding" -Color Yellow
        }

        # Summary
        Write-Color @"

═══════════════════════════════════════════════════
  🚀 Hermes Agent — Todas las interfaces activas
═══════════════════════════════════════════════════
  🖥️  TUI (Terminal):
     wsl -d Ubuntu -e bash -c 'tmux attach -t hermes-tui'

  🌐 Dashboard (Web):
     http://localhost:$DashboardPort

  ⚙️  Gateway (Backend):
     Sesión tmux: hermes-gateway

  📋 Logs (WSL2): ~/.hermes/logs/

  🛑 Detener: .\launch_hermes.ps1 stop
═══════════════════════════════════════════════════
"@ -Color Cyan
    }
    "stop" {
        Write-Color "🛑 Hermes — Deteniendo todas las interfaces..." -Color Yellow
        wsl -d $Distro -- bash -c "tmux kill-session -t hermes-gateway 2>/dev/null; tmux kill-session -t hermes-tui 2>/dev/null; tmux kill-session -t hermes-dashboard 2>/dev/null; pkill -f 'hermes (gateway|dashboard|--tui)' 2>/dev/null; echo DONE" 2>$null
        netsh interface portproxy delete v4tov4 listenport=$DashboardPort listenaddress=127.0.0.1 2>$null
        Write-Color "  ✅ Todas las interfaces detenidas" -Color Green
    }
    "status" {
        Write-Color "📊 Hermes Agent — Estado:" -Color Cyan
        $gw = wsl -d $Distro -- bash -c "tmux has-session -t hermes-gateway 2>/dev/null && echo ACTIVE || echo INACTIVE" 2>$null
        $tui = wsl -d $Distro -- bash -c "tmux has-session -t hermes-tui 2>/dev/null && echo ACTIVE || echo INACTIVE" 2>$null
        $dash = wsl -d $Distro -- bash -c "tmux has-session -t hermes-dashboard 2>/dev/null && echo ACTIVE || echo INACTIVE" 2>$null
        $web = wsl -d $Distro -- bash -c "curl -sf --max-time 2 http://localhost:$DashboardPort >/dev/null && echo YES || echo NO" 2>$null

        Write-Color "  Gateway:   $(if ($gw -eq 'ACTIVE'){'✅ Activo'}else{'❌ Inactivo'})" -Color $(if ($gw -eq 'ACTIVE'){'Green'}else{'Red'})
        Write-Color "  TUI:       $(if ($tui -eq 'ACTIVE'){'✅ Activo (tmux attach -t hermes-tui)'}else{'❌ Inactivo'})" -Color $(if ($tui -eq 'ACTIVE'){'Green'}else{'Red'})
        Write-Color "  Dashboard: $(if ($web -eq 'YES'){'✅ Activo (http://localhost:' + $DashboardPort + ')'}else{'❌ Inactivo'})" -Color $(if ($web -eq 'YES'){'Green'}else{'Red'})
    }
    "restart" {
        & $PSCommandPath -Action stop
        Start-Sleep -Seconds 2
        & $PSCommandPath -Action start -DashboardPort $DashboardPort
    }
}
