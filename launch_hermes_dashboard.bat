@echo off
chcp 65001 >nul
title Hermes Dashboard 📊

echo.
echo  ════════════════════════════════════════
echo   📊 Hermes Dashboard — Web UI
echo   Puerto :9120
echo  ════════════════════════════════════════
echo.
echo  Iniciando Hermes Dashboard...
echo  Abre http://localhost:9120 en tu navegador
echo  Presiona Ctrl+C para detener.
echo.

hermes dashboard --port 9120

echo.
echo  Dashboard detenido.
pause
