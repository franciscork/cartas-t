<#
.SYNOPSIS
    SIMMOON — Launch ALL IAs (Windows)
    Lanzadera unificada para todos los servicios de IA.
.DESCRIPTION
    Controla todos los servicios de IA del ecosistema SIMMOON:
      🧠 Ollama       — LLM server (puerto 11434)
      🎨 ComfyUI      — Generación de imágenes (puerto 8188)
      🖼️  InvokeAI     — Generación alternativa (puerto 9090)
      🧠 Hermes       — Agente con 3 escritorios (puerto 9119)
      🤖 Simmoon Agent — AI director de assets
      🤖 AutoGen      — Diseño multi-agente
      🔄 Pipeline     — Workflow LangGraph
.PARAMETER Action
    all      — Inicia todos los servicios backend
    stop     — Detiene todos los servicios
    status   — Muestra estado de todos los servicios
    start    — Inicia un servicio específico (usar -Service)
.PARAMETER Service
    Servicio a controlar: ollama, comfyui, invokeai, hermes
.PARAMETER NoAgent
    No lanza los agentes Python (solo servicios backend)
.PARAMETER NoViewer
    No abre viewer.html en Chrome
.EXAMPLE
    .\launch_ias.ps1                  # Inicia todo
    .\launch_ias.ps1 status           # Estado de todo
    .\launch_ias.ps1 stop             # Detiene todo
    .\launch_ias.ps1 start -Service hermes  # Solo Hermes
    .\launch_ias.ps1 all -NoAgent     # Solo backends
#>

param(
    [ValidateSet("all", "stop", "status", "start")]
    [string]$Action = "all",
    [ValidateSet("ollama", "comfyui", "invokeai", "hermes")]
    [string]$Service,
    [switch]$NoAgent,
    [switch]$NoViewer
)

$ErrorActionPreference = "Stop"
$Distro = "Ubuntu"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Color { param([string]$T, [string]$C="White") Write-Host $T -ForegroundColor $C }
function Write-Banner { Write-Color $args[0] $args[1] }

$services = @{
    ollama   = @{ port=11434; label="🧠 Ollama (LLM)     "; testCmd="curl -sf --max-time 2 http://localhost:11434/api/tags >/dev/null && echo YES || echo NO" }
    comfyui  = @{ port=8188;  label="🎨 ComfyUI (Imagen) "; testCmd="curl -sf --max-time 2 http://localhost:8188/queue >/dev/null && echo YES || echo NO" }
    invokeai = @{ port=9090;  label="🖼️  InvokeAI (Imagen)"; testCmd="curl -sf --max-time 2 http://localhost:9090/api/v1/app/version >/dev/null && echo YES || echo NO" }
    hermes   = @{ port=9119;  label="🧠 Hermes (3 desk)  "; testCmd="curl -sf --max-time 2 http://localhost:9119 >/dev/null && echo YES || echo NO" }
}

function Test-Service([string]$name) {
    $svc = $services[$name]
    wsl -d $Distro -- bash -c "$($svc.testCmd)" 2>$null
}

function Get-Status([string]$name) {
    $svc = $services[$name]
    $status = Test-Service $name
    if ($status -eq "YES") { return @{active=$true; text="✅ ACTIVO  http://localhost:$($svc.port)"} }
    else { return @{active=$false; text="❌ INACTIVO"} }
}

# ═══════════════════════════════════════════════════════════════
#  STATUS
# ═══════════════════════════════════════════════════════════════
if ($Action -eq "status") {
    Write-Banner @"

╔══════════════════════════════════════════════════╗
║       ☾  SIMMOON  —  Estado de IAs               ║
╚══════════════════════════════════════════════════╝
"@ -Color Cyan

    foreach ($name in @("ollama", "comfyui", "invokeai", "hermes")) {
        $st = Get-Status $name
        $color = if ($st.active) { "Green" } else { "Red" }
        Write-Color "  $($services[$name].label) $($st.text)" -Color $color
    }

    # Python agents check
    Write-Color "`n  📋 Agentes Python:" -Color Cyan
    $agentPath = Join-Path $ScriptDir "Simmoon_arc\simmoon_agent.py"
    $autogenPath = Join-Path $ScriptDir "Simmoon_arc\simmoon_autogen.py"
    $pipelinePath = Join-Path $ScriptDir "Simmoon_arc\simmoon_pipeline.py"
    Write-Color "  🤖 Simmoon Agent: $(if (Test-Path $agentPath) {'✅ Listo'}else{'❌ No encontrado'})" -Color $(if (Test-Path $agentPath) {'Green'}else{'Red'})
    Write-Color "  🤖 AutoGen:       $(if (Test-Path $autogenPath) {'✅ Listo'}else{'❌ No encontrado'})" -Color $(if (Test-Path $autogenPath) {'Green'}else{'Red'})
    Write-Color "  🔄 Pipeline:      $(if (Test-Path $pipelinePath) {'✅ Listo'}else{'❌ No encontrado'})" -Color $(if (Test-Path $pipelinePath) {'Green'}else{'Red'})

    # Quick launch commands
    Write-Color "`n  🚀 Lanzaderas disponibles:" -Color Cyan
    Get-ChildItem -Path $ScriptDir -Filter "launch_*.ps1" | ForEach-Object {
        Write-Color "     .\$($_.Name)" -Color DarkGray
    }
    Write-Color ""
    return
}

# ═══════════════════════════════════════════════════════════════
#  STOP ALL
# ═══════════════════════════════════════════════════════════════
if ($Action -eq "stop") {
    Write-Banner "🛑 SIMMOON — Deteniendo todas las IAs..." -Color Yellow
    Write-Color ""

    $stopScripts = @(
        @{name="ComfyUI";  cmd="pkill -f 'main.py.*--port 8188' 2>/dev/null || true"},
        @{name="InvokeAI"; cmd="pkill -f 'invokeai-web' 2>/dev/null || true"},
        @{name="Hermes";   cmd="for s in hermes-gateway hermes-tui hermes-dashboard; do tmux kill-session -t `$s 2>/dev/null; done; pkill -f 'hermes dashboard' 2>/dev/null; pkill -f 'hermes gateway' 2>/dev/null; true"},
        @{name="Ollama";   cmd="pkill -f 'ollama serve' 2>/dev/null || true"}
    )

    foreach ($s in $stopScripts) {
        Write-Color "  ⏹ $($s.name)..." -Color Yellow
        wsl -d $Distro -- bash -c $s.cmd 2>$null
    }

    Write-Color "`n  ✅ Todos los servicios detenidos" -Color Green

    if (-not $NoViewer) {
        Write-Color "  🌐 Recuerda cerrar viewer.html manualmente en Chrome" -Color DarkGray
    }
    Write-Color ""
    return
}

# ═══════════════════════════════════════════════════════════════
#  START SINGLE SERVICE
# ═══════════════════════════════════════════════════════════════
if ($Action -eq "start" -and $Service) {
    $launcherMap = @{
        ollama   = "launch_ollama.ps1"
        comfyui  = "launch_comfyui.ps1"
        invokeai = "launch_invokeai.ps1"
        hermes   = "launch_hermes.ps1"
    }
    $launcher = Join-Path $ScriptDir $launcherMap[$Service]
    if (Test-Path $launcher) {
        & $launcher start
    } else {
        Write-Color "[ERROR] No se encuentra: $launcher" -Color Red
        exit 1
    }
    return
}

# ═══════════════════════════════════════════════════════════════
#  START ALL
# ═══════════════════════════════════════════════════════════════

Write-Banner @"
╔══════════════════════════════════════════════════════════╗
║          ☾  SIMMOON  —  Launch ALL IAs                  ║
║                                                          ║
║  🧠 Ollama  ·  🎨 ComfyUI  ·  🖼️ InvokeAI               ║
║  🧠 Hermes (3 desktop)  ·  🤖 Agent  ·  🔄 Pipeline     ║
╚══════════════════════════════════════════════════════════╝
"@ -Color Cyan

# ── Step 1: Verify WSL2 ──
Write-Color "[1/6] Verificando WSL2..." -Color Green
$wslOut = wsl -l -v 2>$null | Out-String
if ($wslOut -notmatch "Ubuntu\s+Running") {
    Write-Color "  Iniciando WSL2..." -Color Yellow
    wsl -d $Distro -- bash -c "echo WSL2_READY" | Out-Null
    Write-Color "  [OK] WSL2 iniciado" -Color Green
} else {
    Write-Color "  [OK] WSL2 ya corriendo" -Color Green
}

# ── Step 2: Ollama ──
Write-Color "`n[2/6] 🧠 Ollama..." -Color Green
if ((Test-Service "ollama") -eq "YES") {
    Write-Color "  [OK] Ya activo en http://localhost:11434" -Color Green
} else {
    wsl -d $Distro -- bash -c "nohup ollama serve > /dev/null 2>&1 &" 2>$null
    Start-Sleep -Seconds 3
    if ((Test-Service "ollama") -eq "YES") {
        Write-Color "  [OK] Iniciado" -Color Green
    } else {
        Write-Color "  [WARN] No respondió" -Color Yellow
    }
}

# ── Step 3: ComfyUI ──
Write-Color "`n[3/6] 🎨 ComfyUI..." -Color Green
if ((Test-Service "comfyui") -eq "YES") {
    Write-Color "  [OK] Ya activo en http://localhost:8188" -Color Green
} else {
    wsl -d $Distro -- bash -c "cd ~/ComfyUI && nohup ./venv/bin/python main.py --listen --port 8188 > /dev/null 2>&1 &" 2>$null
    Write-Color "  ⏳ Esperando (20-40s)..." -Color Yellow
    $started = $false
    for ($i=0; $i -lt 45; $i++) {
        Start-Sleep -Seconds 1
        if ((Test-Service "comfyui") -eq "YES") {
            Write-Color "  [OK] Iniciado" -Color Green
            $started = $true
            break
        }
    }
    if (-not $started) { Write-Color "  [WARN] Puede tardar más — verifica con .\launch_comfyui.ps1 status" -Color Yellow }
}

# ── Step 4: InvokeAI ──
Write-Color "`n[4/6] 🖼️  InvokeAI..." -Color Green
if ((Test-Service "invokeai") -eq "YES") {
    Write-Color "  [OK] Ya activo en http://localhost:9090" -Color Green
} else {
    wsl -d $Distro -- bash -c "source ~/invokeai-env/bin/activate 2>/dev/null && cd ~/invokeai && nohup invokeai-web --root ~/invokeai > /dev/null 2>&1 &" 2>$null
    Write-Color "  ⏳ Esperando..." -Color Yellow
    for ($i=0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        if ((Test-Service "invokeai") -eq "YES") {
            Write-Color "  [OK] Iniciado" -Color Green
            break
        }
    }
}

# ── Step 5: Hermes ──
Write-Color "`n[5/6] 🧠 Hermes Agent (3 desktop)..." -Color Green
if ((Test-Service "hermes") -eq "YES") {
    Write-Color "  [OK] Dashboard ya activo en http://localhost:9119" -Color Green
} else {
    $hermesLauncher = Join-Path $ScriptDir "launch_hermes.ps1"
    if (Test-Path $hermesLauncher) {
        & $hermesLauncher start
    }
    Start-Sleep -Seconds 2
    Write-Color "  [OK] 3 interfaces iniciadas" -Color Green
    Write-Color "       TUI: wsl -d Ubuntu -e bash -c 'tmux attach -t hermes-tui'" -Color Cyan
    Write-Color "       Web: http://localhost:9119" -Color Cyan
}

# ── Step 6: Viewer ──
if (-not $NoViewer) {
    Write-Color "`n[6/6] 🌐 Viewer..." -Color Green
    $viewerRel = Join-Path $ScriptDir "Simmoon_arc\viewer.html"
    $viewerFull = Resolve-Path $viewerRel -ErrorAction SilentlyContinue
    if ($viewerFull) {
        $viewerUri = "file:///$($viewerFull.Path -replace '\\', '/' -replace ' ', '%20')"
        Start-Process "chrome" -ArgumentList $viewerUri -ErrorAction SilentlyContinue
        Write-Color "  [OK] Abierto en Chrome" -Color Green
    } else {
        Write-Color "  [WARN] viewer.html no encontrado" -Color Yellow
    }
}

# ── Summary ──
Write-Color @"

╔══════════════════════════════════════════════════════════╗
║              ✅  TODAS LAS IAs ACTIVAS                   ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  🧠 Ollama       → http://localhost:11434                ║
║  🎨 ComfyUI      → http://localhost:8188                 ║
║  🖼️  InvokeAI     → http://localhost:9090                 ║
║  🧠 Hermes Dash  → http://localhost:9119                 ║
║  🧠 Hermes TUI   → tmux attach -t hermes-tui            ║
║                                                          ║
║  🤖 Agentes Python (bajo demanda):                       ║
║     .\launch_agent.ps1 advise                            ║
║     .\launch_autogen.ps1 design <cat>                    ║
║     .\launch_pipeline.ps1 -Categories <cats>             ║
║                                                          ║
║  🛑 Detener todo: .\launch_ias.ps1 stop                  ║
║  📊 Estado:      .\launch_ias.ps1 status                 ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"@ -Color Cyan

Write-Color "Ctrl+C en cada sesión tmux o usa .\launch_ias.ps1 stop para detener." -Color DarkGray
Write-Color ""
