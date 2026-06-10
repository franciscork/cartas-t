@echo off
REM =============================================================================
REM SIMMOON — Desktop Launcher (doble clic en el escritorio)
REM Abre el dashboard en Chrome y muestra estado rápido de IAs
REM =============================================================================
chcp 65001 >nul 2>&1
set "DISTRO=Ubuntu"

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║       ☾  SIMMOON  —  Desktop Launcher                  ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

echo  [1/3] Verificando servicios...
wsl -d %DISTRO% -- bash -c "
echo '  Ollama:  ' && curl -s -o /dev/null -w '%%{http_code}' http://localhost:11434/api/tags && echo '' || echo '  DOWN'
echo '  ComfyUI: ' && curl -s -o /dev/null -w '%%{http_code}' http://localhost:8188/queue && echo '' || echo '  DOWN'
echo '  Dashboard:' && curl -s -o /dev/null -w '%%{http_code}' http://localhost:5000 && echo '' || echo '  DOWN'
echo '  PostgreSQL:' && pg_isready -q -h localhost && echo '  OK' || echo '  DOWN'
"

echo.
echo  [2/3] Abriendo Dashboard en Chrome...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:5000" 2>nul
if errorlevel 1 start chrome "http://localhost:5000" 2>nul
if errorlevel 1 start msedge "http://localhost:5000" 2>nul

echo.
echo  [3/3] Abriendo Viewer de assets...
set "VIEWER=C:\Program Files\PowerShell\7\Simmoon_arc\viewer.html"
if exist "%VIEWER%" (
    set "VIEWER_URL=file:///C:/Program%%20Files/PowerShell/7/Simmoon_arc/viewer.html"
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "!VIEWER_URL!" 2>nul
)

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  ✅  Dashboard → http://localhost:5000                  ║
echo  ║  🎮  ias status → abre terminal y ejecuta: ias status   ║
echo  ║  🛑  ias stop   → abre terminal y ejecuta: ias stop     ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
pause
