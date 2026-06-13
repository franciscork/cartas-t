@echo off
REM launch_agatha_daemon.bat - Inicia el daemon de Agatha Actas
REM Usado por Windows Task Scheduler para arrancar al iniciar sesion

cd /d "%~dp0"

REM Registrar inicio en log
echo [%date% %time%] Agatha Daemon iniciado por Task Scheduler >> agatha_daemon.log

REM Ejecutar daemon (bucle infinito, se detiene al cerrar sesion)
"C:\Python314\python.exe" agatha_actas.py --daemon >> agatha_daemon.log 2>&1

REM Si llega aqui, el daemon termino (posiblemente por Ctrl+C o error)
echo [%date% %time%] Agatha Daemon detenido (exit %ERRORLEVEL%) >> agatha_daemon.log
