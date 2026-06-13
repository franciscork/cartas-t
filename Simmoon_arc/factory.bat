@echo off
REM =============================================================================
REM  FACTORY GAMES — Windows Entry Point (BAT)
REM  Uso: double-click = menu interactivo
REM       factory status, factory agents, factory help, etc.
REM =============================================================================
setlocal enabledelayedexpansion

REM ── Resolver directorio ───────────────────────────────────────────────────
set "SCRIPT_DIR=%~dp0"
set "FACTORY_PY=%SCRIPT_DIR%factory.py"

REM ── Verificar ─────────────────────────────────────────────────────────────
if not exist "%FACTORY_PY%" (
    echo.
    echo   [ERROR] No se encuentra factory.py
    echo     Buscado en: %FACTORY_PY%
    echo.
    echo   Asegurate de ejecutar este .bat desde Simmoon_arc/
    pause
    exit /b 1
)

REM ── Cambiar al directorio del proyecto ────────────────────────────────────
cd /d "%SCRIPT_DIR%"

REM ── Ejecutar ──────────────────────────────────────────────────────────────
python factory.py %*
if ERRORLEVEL 1 (
    echo.
    echo   [ERROR] La factory termino con codigo: %ERRORLEVEL%
    pause
)
