@echo off
chcp 65001 >nul
title SIMMOON — Agatha Actas 📋
cd /d "%~dp0Simmoon_arc"

:MENU
cls
echo.
echo  ═══════════════════════════════════════════
echo   📋 Agatha Actas — Reportes Horarios
echo   Bot: @Jeremias_Hermesai_bot
echo  ═══════════════════════════════════════════
echo.
echo  1. 🚀 Iniciar demonio (reportes cada hora)
echo  2. 🔧 Setup configuracion (chat ID)
echo  3. 📤 Enviar reporte de prueba ahora
echo  4. ❌ Salir
echo.
set /p opcion="Selecciona una opcion (1-4): "

if "%opcion%"=="1" goto DAEMON
if "%opcion%"=="2" goto SETUP
if "%opcion%"=="3" goto TEST
if "%opcion%"=="4" goto EXIT
goto MENU

:SETUP
cls
echo.
echo  🔧 ANTES de continuar:
echo  1. Abre Telegram y busca @Jeremias_Hermesai_bot
echo  2. Enviale cualquier mensaje a @Jeremias_Hermesai_bot (/start, hola, etc.)
echo  3. Luego presiona cualquier tecla aqui para continuar
echo.
pause
python agatha_actas.py --setup
echo.
echo  ✅ Si todo salio bien, ya puedes usar la opcion 1 para iniciar el demonio.
pause
goto MENU

:DAEMON
cls
echo.
echo  🚀 Iniciando Agatha Actas en modo demonio...
echo  Reportes cada hora a @Jeremias_Hermesai_bot
echo  Presiona Ctrl+C para detener.
echo.
python agatha_actas.py --daemon
echo.
pause
goto MENU

:TEST
cls
echo.
echo  📤 Enviando reporte de prueba...
python agatha_actas.py --test
echo.
pause
goto MENU

:EXIT
exit /b 0
