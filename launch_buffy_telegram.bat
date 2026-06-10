@echo off
REM =============================================================================
REM  SIMMOON — Buffy Telegram Bridge — Launch Script (Windows)
REM  Lanza el bridge Buffy↔Telegram en WSL2.
REM
REM  Uso:
REM    launch_buffy_telegram.bat          # Iniciar
REM    launch_buffy_telegram.bat status   # Estado
REM    launch_buffy_telegram.bat stop     # Detener
REM    launch_buffy_telegram.bat logs     # Ver logs
REM =============================================================================

title SIMMOON — Buffy Telegram 🤖

setlocal enabledelayedexpansion
set DISTRO=Ubuntu
set SIMMOON_DIR=~/Simmoon_arc
set LOG_FILE=~/.simmoon-logs/buffy_telegram.log
set SESSION=buffy-telegram

if /i "%~1"=="status" goto :status
if /i "%~1"=="stop" goto :stop
if /i "%~1"=="logs" goto :logs
if /i "%~1"=="attach" goto :attach
goto :start

:status
echo.
wsl -d %DISTRO% -- bash -c "tmux has-session -t %SESSION% 2>/dev/null && echo '  🟢 Buffy Telegram ACTIVA' || echo '  ⚫ Buffy Telegram DETENIDA'"
echo.
wsl -d %DISTRO% -- bash -c "tmux has-session -t %SESSION% 2>/dev/null && tmux capture-pane -t %SESSION% -p | tail -5"
goto :end

:stop
echo.
echo   ⏹ Deteniendo Buffy Telegram...
wsl -d %DISTRO% -- bash -c "tmux kill-session -t %SESSION% 2>/dev/null; pkill -f buffy_telegram.py 2>/dev/null || true"
echo   ✅ Detenida
goto :end

:logs
echo.
echo   📋 Ultimos logs de Buffy:
echo   ----------------------------------------
wsl -d %DISTRO% -- bash -c "tail -40 %LOG_FILE% 2>/dev/null || echo '   (sin logs)'"
goto :end

:attach
echo.
echo   🖥️  Conectando a sesion Buffy Telegram...
wsl -d %DISTRO% -- bash -c "tmux attach -t %SESSION%"
goto :end

:start
echo.
echo   ===========================================
echo     🤖 SIMMOON — Buffy Telegram Bridge
echo     📱 Bot: @Jeremi_Hermes_bot
echo   ===========================================
echo.

REM Verificar si ya está corriendo
wsl -d %DISTRO% -- bash -c "tmux has-session -t %SESSION% 2>/dev/null" 2>nul
if %errorlevel%==0 (
    echo   ⚠️  Buffy Telegram ya esta activa
    echo   Usa 'launch_buffy_telegram.bat attach' para conectarte
    goto :end
)

echo   🤖 Iniciando Buffy Telegram...
wsl -d %DISTRO% -- bash -c "mkdir -p ~/.simmoon-logs"
wsl -d %DISTRO% -- bash -c "tmux kill-session -t %SESSION% 2>/dev/null || true"
wsl -d %DISTRO% -- bash -c "cd %SIMMOON_DIR% && tmux new-session -d -s %SESSION% 'python3 buffy_telegram.py --daemon 2>&1 | tee %LOG_FILE%; bash'"

timeout /t 2 >nul
wsl -d %DISTRO% -- bash -c "tmux has-session -t %SESSION% 2>/dev/null && echo '  ✅ Buffy Telegram INICIADA' || echo '  ❌ Error al iniciar'"

echo.
echo   Para ver logs: launch_buffy_telegram.bat logs
echo   Para conectar: launch_buffy_telegram.bat attach
echo   Para detener:  launch_buffy_telegram.bat stop
echo.

:end
endlocal
