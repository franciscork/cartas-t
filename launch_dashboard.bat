@echo off
chcp 65001 >nul
title SIMMOON — Dashboard 📊
cd /d "%~dp0Simmoon_arc"

echo.
echo  ════════════════════════════════════════
echo   📊 SIMMOON Dashboard de Control Agenico
echo  ════════════════════════════════════════
echo.
echo  Iniciando dashboard en http://localhost:5000
echo  Presiona Ctrl+C para detener.
echo.

python dashboard.py --port 5002

echo.
echo  Dashboard detenido.
pause
