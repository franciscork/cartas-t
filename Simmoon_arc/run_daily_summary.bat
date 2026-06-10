@echo off
REM run_daily_summary.bat - Ejecuta resumen diario de Agatha
REM Usado por Windows Task Scheduler para ejecutar a las 23:00

cd /d "%~dp0"
"C:\Python314\python.exe" agatha_actas.py --daily-summary

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Daily summary failed with exit code %ERRORLEVEL% >> agatha_errors.log
)