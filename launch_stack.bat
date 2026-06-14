@echo off
REM =============================================================================
REM SIMMOON — Launch Full Stack (One-Click)
REM Inicia Ollama + ComfyUI en WSL (tmux persistente) + Telegram Bot
REM
REM Doble-click en este archivo o ejecutalo desde terminal.
REM Los servicios sobreviven aunque cierres esta ventana (tmux en WSL).
REM =============================================================================

echo.
echo ============================================
echo   SIMMOON — Full Stack Launcher
echo ============================================
echo.

REM ── 1. Ensure WSL is running ──────────────────────────────────────────
echo [1/3] Verificando WSL...
set WSL_RETRIES=0
:check_wsl
wsl ~ -- bash -c "echo OK" >nul 2>&1
if %ERRORLEVEL% EQU 0 goto wsl_ok
set /a WSL_RETRIES+=1
if %WSL_RETRIES% LSS 3 (
    echo   WSL no listo aun, reintentando en 2s... (%WSL_RETRIES%/3)
    timeout /t 2 >nul
    goto check_wsl
)
echo   [ERROR] WSL no responde tras 3 intentos.
pause
exit /b 1
:wsl_ok
echo   [OK] WSL activo

REM ── 2. Start services in persistent tmux ──────────────────────────────
echo.
echo [2/3] Iniciando servicios en WSL (tmux persistente)...
cd /d "%~dp0Simmoon_arc"
python wsl_service_manager.py ensure
if %ERRORLEVEL% NEQ 0 (
    echo   [WARN] Algunos servicios no iniciaron. Revisa la salida.
) else (
    echo   [OK] Servicios listos
)

REM ── 3. Start Telegram Bot ─────────────────────────────────────────────
echo.
echo [3/3] Iniciando Telegram Bot...
echo   Presiona Ctrl+C para detener el bot.
echo   Los servicios WSL seguiran corriendo en tmux.
echo.
python telegram_bot.py

REM ── Bot stopped ───────────────────────────────────────────────────────
echo.
echo ============================================
echo   Bot detenido.
echo   Servicios WSL siguen en tmux.
echo   Para detenerlos: python wsl_service_manager.py stop
echo ============================================
pause
