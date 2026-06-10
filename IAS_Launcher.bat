@echo off
setlocal enabledelayedexpansion
title IAS Launcher

:: Si algo falla, mostrar error y pausar
if not exist "%SystemRoot%\System32\wsl.exe" (
    echo ERROR: WSL no encontrado. Instala WSL2 primero.
    pause
    exit /b 1
)

:: Detectar navegador
set "BROWSER=chrome"
where chrome >nul 2>&1
if !errorlevel! neq 0 set "BROWSER=msedge"

:menu
cls
echo.
echo   =============================================
echo          I A S   -   L A U N C H E R
echo        Todos los servicios de IA en un click
echo   =============================================
echo.
echo     [1] Ollama           - Modelos LLM locales
echo     [2] ComfyUI          - Generar imagenes (SD)
echo     [3] Jarvis           - Asistente IA (preguntar)
echo     [4] OpenHuman        - Asistente escritorio
echo     [5] Dashboard        - Monitor del sistema
echo     [6] Simmoon          - Juego + generador
echo     [7] Documentacion    - Guias en navegador
echo     [8] Estado           - Ver todos los servicios
echo     [9] Start All        - Iniciar TODOS los servicios
echo.
echo     [0] Salir
echo.
set "choice="
set /p "choice=  Elige [0-9]: "

if "%choice%"=="1" goto ollama
if "%choice%"=="2" goto comfyui
if "%choice%"=="3" goto jarvis
if "%choice%"=="4" goto openhuman
if "%choice%"=="5" goto dashboard
if "%choice%"=="6" goto simmoon
if "%choice%"=="7" goto docs
if "%choice%"=="8" goto status
if "%choice%"=="9" goto startall
if "%choice%"=="0" goto end
goto menu

:ollama
cls
echo.
echo   Ollama - Modelos LLM locales
echo   ------------------------------------------
echo.
echo   Verificando Ollama...
echo.
wsl -d Ubuntu -- bash -c "curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); [print('     '+m.get('name','?')) for m in d.get('models',[])]\" 2>/dev/null || echo '   Ollama NO esta corriendo'"
echo.
echo   ------------------------------------------
echo   Ollama: http://localhost:11434
echo.
pause
goto menu

:comfyui
cls
echo.
echo   Abriendo ComfyUI en el navegador...
echo   http://localhost:8188
echo.
start "" %BROWSER% "http://localhost:8188"
echo.
pause
goto menu

:jarvis
cls
echo.
echo   Jarvis - Asistente IA
echo   ------------------------------------------
echo.
echo   Escribe tu pregunta y pulsa Enter.
echo.
wsl -d Ubuntu -- bash -c "export PATH=\"\$HOME/.local/bin:\$PATH\"; echo ''; read -p '  Pregunta: ' q; echo ''; echo '   Pensando...'; echo ''; jarvis ask --model qwen3:14b \"\$q\" 2>&1"
echo.
echo   ------------------------------------------
echo.
pause
goto menu

:openhuman
cls
echo.
echo   OpenHuman - Asistente de escritorio
echo   ------------------------------------------
echo.
echo   Estado del servidor:
wsl -d Ubuntu -- bash -c "curl -s http://localhost:7788/health 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); print(f'   Estado: {d.get(chr(34)+chr(34).join([chr(111),chr(107)]), chr(34)+chr(34).join([chr(63),chr(63)]))}')\" 2>nul || echo '   No responde'"
echo.
echo   API JSON-RPC: http://localhost:7788/rpc
echo   Healthcheck: http://localhost:7788/health
echo.
echo   Para abrir la GUI de escritorio:
echo     wsl -d Ubuntu -- bash -c "export DISPLAY=:0 && openhuman-core"
echo.
pause
goto menu

:dashboard
cls
echo.
echo   Abriendo Dashboard en el navegador...
echo   http://localhost:5000
echo   GPU, RAM, Disco, Servicios, Alertas en tiempo real
echo.
start "" %BROWSER% "http://localhost:5000"
echo.
pause
goto menu

:simmoon
cls
echo.
echo   Abriendo Dashboard de Simmoon...
echo   http://localhost:5000
echo.
start "" %BROWSER% "http://localhost:5000"
echo   Para lanzar el juego:
echo   wsl -d Ubuntu -- bash -c "cd ~/Simmoon_arc && python3 launch_simmoon.py"
echo.
pause
goto menu

:docs
cls
echo.
echo   Abriendo documentacion...
echo.
start "" %BROWSER% "file:///C:/Users/docus/Desktop/documentacion/index.html"
echo   14 guias de referencia para todas las apps.
echo.
pause
goto menu

:status
cls
echo.
echo   Verificando todos los servicios...
echo   ------------------------------------------
echo.
wsl -d Ubuntu -- bash -c "
echo '   Ollama      :11434'  && curl -s -o /dev/null -w '   -> HTTP %%{http_code}' http://localhost:11434/api/tags 2>/dev/null && echo '' || echo '   -> DOWN'
echo '   ComfyUI     :8188 '  && curl -s -o /dev/null -w '   -> HTTP %%{http_code}' http://localhost:8188/queue 2>/dev/null && echo '' || echo '   -> DOWN'
echo '   Dashboard   :5000 '  && curl -s -o /dev/null -w '   -> HTTP %%{http_code}' http://localhost:5000 2>/dev/null && echo '' || echo '   -> DOWN'
echo '   OpenHuman   :7788 '  && curl -s -o /dev/null -w '   -> HTTP %%{http_code}' http://localhost:7788 2>/dev/null && echo '' || echo '   -> DOWN'
echo '   PostgreSQL  :5432 '  && (pg_isready -q -h localhost -p 5432 2>/dev/null && echo '   -> OK' || echo '   -> DOWN')
echo ''
echo '   Monitor del sistema:'
python3 ~/Simmoon_arc/monitor_sistema.py 2>/dev/null | head -12
"
echo.
echo   ------------------------------------------
echo.
pause
goto menu

:startall
cls
echo.
echo   Iniciando TODOS los servicios...
echo   Esto puede tardar 10-20 segundos.
echo   ------------------------------------------
echo.
wsl -d Ubuntu -- bash ~/ias.sh start 2>&1
echo.
echo   ------------------------------------------
echo   Todos los servicios iniciados.
echo   Verifica con opcion [8] Estado.
echo.
pause
goto menu

:end
cls
echo.
echo   Hasta luego.
timeout /t 2 >nul
exit /b 0
