@echo off
chcp 65001 >nul
title SIMMOON — Dashboard 📊
cd /d "%~dp0Simmoon_arc"

set PORT=5002
set HOST=127.0.0.1

:parse_args
if "%1"=="" goto run
if /i "%1"=="--port" set PORT=%2& shift
if /i "%1"=="--host" set HOST=%2& shift
shift
goto parse_args

:run
echo.
echo  ════════════════════════════════════════
echo   📊 SIMMOON Dashboard de Control Agenico
echo  ════════════════════════════════════════
echo.
echo  Iniciando dashboard en http://%HOST%:%PORT%
echo  Presiona Ctrl+C para detener.
echo.

python dashboard.py --port %PORT% --host %HOST%

echo.
echo  Dashboard detenido.
pause
