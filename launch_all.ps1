<#
.SYNOPSIS
    SIMMOON Launch All — Windows
    Arranca WSL2 + Ollama + ComfyUI + viewer.html + Voice Bridge de un solo comando.
.DESCRIPTION
    1. Verifica WSL2 y lo inicia si está detenido
    2. Inicia Ollama (systemd)
    3. Inicia ComfyUI (puerto 8188)
    4. Abre viewer.html en Chrome
    5. Lanza Voice Bridge (hotkey mode)
    6. Muestra URLs de acceso a cada servicio
.PARAMETER NoWait
    Lanza servicios en background sin esperar.
.PARAMETER Quiet
    Suprime salida detallada.
.PARAMETER NoViewer
    No abre el navegador automáticamente.
.PARAMETER NoVoice
    No lanza el Voice Bridge.
.EXAMPLE
    .\launch_all.ps1
    .\launch_all.ps1 -NoWait -NoViewer -NoVoice
#>

param(
    [switch]$NoWait,
    [switch]$Quiet,
    [switch]$NoViewer,
    [switch]$NoVoice
)

$ErrorActionPreference = "Stop"
try { $Host.UI.RawUI.WindowTitle = "SIMMOON -- Launch All" } catch {}

function Write-Color {
    param([string]$Text, [string]$Color = "White")
    if (-not $Quiet) { Write-Host $Text -ForegroundColor $Color }
}

# ── Banner ──
try { Clear-Host } catch {}
Write-Color @"
  +==================================================+
  |       SIMMOON -- LAUNCH ALL                      |
  |                                                  |
  |  Windows -> WSL2 -> Ollama + ComfyUI + viewer    |
  |  A1111 removed — ComfyUI replaced it successfully |
  +==================================================+

"@ -Color Cyan

# ── Step 1: Check & Start WSL2 ──
Write-Color "[1] Checking WSL2..." -Color Green

$distroName = "Ubuntu"
$distros = wsl -l -v 2>$null | Out-String
if ($distros -notmatch $distroName) {
    Write-Color "[ERROR] Ubuntu distro not found. Install: wsl --install -d Ubuntu" -Color Red
    exit 1
}

$isRunning = $distros -match "$distroName\s+Running"
if (-not $isRunning) {
    Write-Color "  Starting WSL2..."
    wsl -d $distroName -- bash -c "echo WSL2_READY" | Out-Null
    Write-Color "  [OK] WSL2 started" -Color Green
} else {
    Write-Color "  [OK] WSL2 already running" -Color Green
}

# ── Step 2: Start Ollama ──
Write-Color "`n[2] Starting Ollama..." -Color Green
$ollamaRunning = wsl -d $distroName -- bash -c "pgrep -a ollama >/dev/null && echo YES || echo NO" 2>$null
if ($ollamaRunning -eq "YES") {
    Write-Color "  [OK] Ollama already running" -Color Green
} else {
    Write-Color "  Starting Ollama..."
    if ($NoWait) {
        wsl -d $distroName -- bash -c "nohup ollama serve > /dev/null 2>&1 &" 2>$null
        Write-Color "  [OK] Ollama starting in background" -Color Green
    } else {
        wsl -d $distroName -- bash -c "ollama serve &" 2>$null
        Start-Sleep -Seconds 3
        Write-Color "  [OK] Ollama started" -Color Green
    }
}
Write-Color "  URL: http://localhost:11434" -Color Cyan

# ── Step 3: Start ComfyUI ──
Write-Color "`n[3] Starting ComfyUI..." -Color Green
$comfyRunning = wsl -d $distroName -- bash -c "curl -s -o /dev/null -w '%{http_code}' http://localhost:8188 2>/dev/null || echo '000'" 2>$null
if ($comfyRunning -eq "200") {
    Write-Color "  [OK] ComfyUI already running" -Color Green
} else {
    Write-Color "  Starting ComfyUI..."
    if ($NoWait) {
        wsl -d $distroName -- bash -c "cd ~/ComfyUI && nohup ./venv/bin/python main.py --listen --port 8188 > /dev/null 2>&1 &" 2>$null
        Write-Color "  [OK] ComfyUI starting in background" -Color Green
    } else {
        wsl -d $distroName -- bash -c "cd ~/ComfyUI && nohup ./venv/bin/python main.py --listen --port 8188 > /dev/null 2>&1 &" 2>$null
        Start-Sleep -Seconds 5
        Write-Color "  [OK] ComfyUI started" -Color Green
    }
}
Write-Color "  URL: http://localhost:8188" -Color Cyan

# ── Step 4: Copy agent scripts to WSL2 ──
Write-Color "`n[5] Syncing agent scripts to WSL2..." -Color Green
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$agents = @("simmoon_agent.py", "simmoon_pipeline.py", "simmoon_autogen.py")
foreach ($agent in $agents) {
    $localPath = Join-Path $scriptDir "Simmoon_arc\$agent"
    if (Test-Path $localPath) {
        $driveLetter = $localPath[0].ToString().ToLower()
        $restOfPath = $localPath.Substring(3) -replace '\\', '/'
        $wslPath = "/mnt/$driveLetter/$restOfPath"
        wsl -d $distroName -- bash -c "cp '$wslPath' ~/Simmoon_arc/ 2>/dev/null && echo COPY_OK || echo COPY_FAIL" 2>$null | Out-Null
    }
}
Write-Color "  [OK] Agent scripts synced" -Color Green

# ── Step 5: Open viewer.html ──
if (-not $NoViewer) {
    Write-Color "`n[6] Opening viewer.html in Chrome..." -Color Green
    $viewerRel = Join-Path $scriptDir "Simmoon_arc\viewer.html"
    $viewerFull = Resolve-Path $viewerRel -ErrorAction SilentlyContinue
    if ($viewerFull) {
        $viewerUri = "file:///$($viewerFull.Path -replace '\\', '/' -replace ' ', '%20')"
        Start-Process "chrome" -ArgumentList $viewerUri -ErrorAction SilentlyContinue
        Write-Color "  [OK] Viewer opened" -Color Green
    } else {
        Write-Color "  [WARN] viewer.html not found at $viewerRel" -Color Yellow
    }
} else {
    Write-Color "  [SKIP] Viewer omitido (-NoViewer)" -Color Yellow
}

# ── Step 6: Launch Voice Bridge (hotkey mode) ──
if (-not $NoVoice) {
    Write-Color "`n[7] Launching Voice Bridge (hotkey mode)..." -Color Green
    $voiceBridge = Join-Path $scriptDir "Simmoon_arc\voice_bridge.py"
    if (Test-Path $voiceBridge) {
    $voiceCmd = "`$env:PYTHONIOENCODING='utf-8'; `$env:PYTHONUTF8='1'; & python -X utf8 '$voiceBridge' --hotkey"
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", $voiceCmd -WindowStyle Normal
    Write-Color "  [OK] Voice Bridge launched (hotkey mode in new window)" -Color Green
    Write-Color "  F4 = 🎤 Grabar y transcribir" -Color Cyan
    Write-Color "  F5 = 🔈 Leer seleccion" -Color Cyan
    Write-Color "  F6 = 📋 Leer portapapeles" -Color Cyan
        Write-Color "  ⚠️  Hotkeys globales requieren Admin. Si no responden, ejecutar pwsh como Administrador." -Color Yellow
    } else {
        Write-Color "  [WARN] voice_bridge.py not found (Voice Bridge skipped)" -Color Yellow
    }
} else {
    Write-Color "  [SKIP] Voice Bridge omitido (-NoVoice)" -Color Yellow
}

# ── Summary ──
Write-Color @"

+==================================================+
  ACCESS URLs
+==================================================+
  Ollama API    -> http://localhost:11434
  ComfyUI       -> http://localhost:8188
  Viewer        -> Simmoon_arc/viewer.html
  Voice Bridge   -> python Simmoon_arc/voice_bridge.py  (hotkeys: F4/F5/F6)

  Agent:
    python Simmoon_arc/simmoon_agent.py --advise
    python Simmoon_arc/simmoon_pipeline.py

+==================================================+
"@ -Color Cyan

Write-Color "To stop: wsl -d $distroName -- bash -c 'pkill -f main.py; pkill -f ollama'" -Color Yellow
Write-Color ""
