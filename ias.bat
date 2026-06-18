@echo off
REM =============================================================================
REM SIMMOON — IAS (Intelligent Agent System) Launcher for Windows
REM Lanzador unificado para TODAS las IAs desde Windows (usa WSL2 internamente)
REM
REM Uso:
REM   ias                  Modo menu interactivo
REM   ias start            Inicia todos los backends
REM   ias start ollama     Inicia solo Ollama
REM   ias stop             Detiene todo
REM   ias status           Estado de todos los servicios
REM   ias restart          Reinicia todo
REM   ias backup           Backup PostgreSQL
REM   ias models           Lista modelos Ollama
REM =============================================================================

setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
set "DISTRO=Ubuntu"
set "SCRIPT_DIR=%~dp0"

REM ── ANSI Colors (define ESC character for Windows 10+ conhost) ──────────
for /f "delims=" %%a in ('echo prompt $E^| cmd') do set "ESC=%%a"
set "GREEN=%ESC%[92m"
set "RED=%ESC%[91m"
set "YELLOW=%ESC%[93m"
set "CYAN=%ESC%[96m"
set "MAGENTA=%ESC%[95m"
set "DIM=%ESC%[90m"
set "BOLD=%ESC%[1m"
set "NC=%ESC%[0m"

REM ── Temp file for service checks ────────────────────────────────────────
set "TMPFILE=%TEMP%\ias_svc_%RANDOM%.tmp"

REM ═══════════════════════════════════════════════════════════════════════════
REM  STATUS
REM ═══════════════════════════════════════════════════════════════════════════
:status
echo.
echo %CYAN%╔══════════════════════════════════════════════════════════╗%NC%
echo %CYAN%║%NC%       %BOLD%☾  SIMMOON  —  IAS Launcher (Windows)%NC%                %CYAN%║%NC%
echo %CYAN%╚══════════════════════════════════════════════════════════╝%NC%
echo.
echo %BOLD%📊 Estado de Servicios:%NC%
echo.

call :test_svc "🧠 Ollama       " 11434 "/api/tags"
call :test_svc "🖌️  InvokeAI     " 9090 "/api/v1/app/version"
call :test_svc "🤖 OpenHuman    " 7788 "/health"
call :test_svc "📊 Dashboard    " 5000 "/api/health"
call :test_svc_postgres
call :test_svc_telegram
call :test_svc_agatha
call :test_svc_openhuman_desktop

echo.
echo %CYAN%──────────────────────────────────────────────────────────%NC%
echo   %BOLD%[a]%NC% Start ALL       %BOLD%[s]%NC% Stop ALL        %BOLD%[r]%NC% Restart ALL
echo   %BOLD%[1]%NC% Ollama          %BOLD%[2]%NC% InvokeAI         %BOLD%[3]%NC% PostgreSQL
echo   %BOLD%[4]%NC% OpenHuman       %BOLD%[5]%NC% Dashboard        %BOLD%[6]%NC% Telegram Bot
echo   %BOLD%[7]%NC% Agatha Actas    %BOLD%[8]%NC% All Bots         %BOLD%[m]%NC% Models
echo   %BOLD%[b]%NC% Backup DB       %BOLD%[q]%NC% Quit
echo %CYAN%──────────────────────────────────────────────────────────%NC%
echo.
goto :eof

:test_svc
set "label=%~1"
set "port=%~2"
set "path=%~3"
wsl -d %DISTRO% -- bash -c "curl -sf --max-time 2 http://localhost:%port%%path% >/dev/null 2>&1 && echo YES || echo NO" 2>nul > "%TMPFILE%"
set /p SVC_RESULT=<"%TMPFILE%"
if "%SVC_RESULT%"=="YES" (
    echo   %GREEN%🟢%NC% %label% %DIM%→ :%port%%NC%
) else (
    echo   %RED%⚫%NC% %label%
)
goto :eof

:test_svc_postgres
wsl -d %DISTRO% -- bash -c "pg_isready -q -h localhost -p 5432 2>/dev/null && echo YES || echo NO" 2>nul > "%TMPFILE%"
set /p PG_RESULT=<"%TMPFILE%"
if "%PG_RESULT%"=="YES" (
    echo   %GREEN%🟢%NC% 🗄️  PostgreSQL   %DIM%→ :5432%NC%
) else (
    echo   %RED%⚫%NC% 🗄️  PostgreSQL
)
goto :eof

:test_svc_telegram
wsl -d %DISTRO% -- bash -c "tmux has-session -t telegram-bot 2>/dev/null && echo YES || echo NO" 2>nul > "%TMPFILE%"
set /p TG_RESULT=<"%TMPFILE%"
if "%TG_RESULT%"=="YES" (
    echo   %GREEN%🟢%NC% 🤖 Telegram Bot %DIM%→ tmux%NC%
) else (
    echo   %RED%⚫%NC% 🤖 Telegram Bot
)
goto :eof

:test_svc_agatha
wsl -d %DISTRO% -- bash -c "tmux has-session -t agatha-actas 2>/dev/null && echo YES || echo NO" 2>nul > "%TMPFILE%"
set /p AG_RESULT=<"%TMPFILE%"
if "%AG_RESULT%"=="YES" (
    echo   %GREEN%🟢%NC% 📋 Agatha Actas %DIM%→ tmux%NC%
) else (
    echo   %RED%⚫%NC% 📋 Agatha Actas
)
goto :eof

:test_svc_openhuman_desktop
wsl -d %DISTRO% -- bash -c "command -v openhuman-core >/dev/null 2>&1 && echo YES || echo NO" 2>nul > "%TMPFILE%"
set /p OH_RESULT=<"%TMPFILE%"
if "%OH_RESULT%"=="YES" (
    echo   %GREEN%🟢%NC% 🖥️  OpenHuman Desk %DIM%→ WSL bin%NC%
) else (
    echo   %DIM%⚫%NC% 🖥️  OpenHuman Desk %DIM%(no instalado)%NC%
)
goto :eof

REM ═══════════════════════════════════════════════════════════════════════════
REM  START
REM ═══════════════════════════════════════════════════════════════════════════
:start
if "%~2"=="" (
    call :start_all
) else (
    call :start_one %2
)
goto :eof

:start_all
echo.
echo %CYAN%╔══════════════════════════════════════════════════════════╗%NC%
echo %CYAN%║%NC%       %BOLD%☾  SIMMOON  —  Launching ALL IAs%NC%                    %CYAN%║%NC%
echo %CYAN%╚══════════════════════════════════════════════════════════╝%NC%
echo.

echo %BOLD%[1/6] 🧠 Ollama...%NC%
wsl -d %DISTRO% -- bash -c "nohup ollama serve > /dev/null 2>&1 & sleep 3; curl -sf --max-time 2 http://localhost:11434/api/tags >/dev/null && echo 'OK' || echo 'WAIT'" 2>nul
echo   %GREEN%✅ Iniciado%NC%

echo.
echo %BOLD%[2/6] 🗄️  PostgreSQL...%NC%
wsl -d %DISTRO% -- bash -c "sudo systemctl start postgresql 2>/dev/null || sudo service postgresql start 2>/dev/null; pg_isready -q -h localhost && echo 'OK' || echo 'FAIL'" 2>nul
echo   %GREEN%✅ Iniciado%NC%

echo.
echo %BOLD%[3/6] 📊 Dashboard...%NC%
wsl -d %DISTRO% -- bash -c "cd ~/Simmoon_arc && nohup python3 dashboard.py > /dev/null 2>&1 & sleep 2" 2>nul
echo   %GREEN%✅ http://localhost:5000%NC%

echo.
echo %BOLD%[4/6] 🤖 Telegram Bot...%NC%
wsl -d %DISTRO% -- bash -c "cd ~/Simmoon_arc && tmux kill-session -t telegram-bot 2>/dev/null; tmux new-session -d -s telegram-bot 'python3 telegram_bot.py 2>&1 | tee ~/.simmoon-logs/telegram_bot.log; bash'" 2>nul
echo   %GREEN%✅ Iniciado (sesion: telegram-bot)%NC%

echo.
echo %BOLD%[5/6] 📋 Agatha Actas...%NC%
wsl -d %DISTRO% -- bash -c "cd ~/Simmoon_arc && tmux kill-session -t agatha-actas 2>/dev/null; tmux new-session -d -s agatha-actas 'python3 agatha_actas.py --daemon 2>&1 | tee ~/.simmoon-logs/agatha_actas.log; bash'" 2>nul
echo   %GREEN%✅ Iniciado (sesion: agatha-actas)%NC%

echo.
echo %BOLD%[6/6] 🤖 Coding Agents...%NC%
where goose >nul 2>nul && echo   🪿 goose      %GREEN%✅ disponible%NC% || echo   🪿 goose      %YELLOW%⚠️  no en PATH%NC%
where aider >nul 2>nul && echo   🧑‍✈️ Aider      %GREEN%✅ disponible%NC% || echo   🧑‍✈️ Aider      %YELLOW%⚠️  no en PATH%NC%
where devin >nul 2>nul && echo   🧑‍💻 Devin      %GREEN%✅ disponible%NC% || echo   🧑‍💻 Devin      %YELLOW%⚠️  no en PATH%NC%
where amp >nul 2>nul && echo   ⚡ Amp         %GREEN%✅ disponible%NC% || echo   ⚡ Amp         %YELLOW%⚠️  no en PATH%NC%

echo.
echo %CYAN%╔══════════════════════════════════════════════════════════╗%NC%
echo %CYAN%║%NC%              %GREEN%✅  STACK ACTIVO%NC%                              %CYAN%║%NC%
echo %CYAN%╠══════════════════════════════════════════════════════════╣%NC%
echo %CYAN%║%NC%  🧠 Ollama       → http://localhost:11434                %CYAN%║%NC%
echo %CYAN%║%NC%  🗄️  PostgreSQL   → localhost:5432                        %CYAN%║%NC%
echo %CYAN%║%NC%  📊 Dashboard    → http://localhost:5000                 %CYAN%║%NC%
echo %CYAN%║%NC%  🤖 Telegram Bot → tmux attach -t telegram-bot            %CYAN%║%NC%
echo %CYAN%║%NC%  📋 Agatha Actas → tmux attach -t agatha-actas            %CYAN%║%NC%
echo %CYAN%║%NC%  🪿 goose        → CLI (Block's open-source agent)        %CYAN%║%NC%
echo %CYAN%║%NC%  🧑‍✈️ Aider        → CLI (AI pair-programmer)                 %CYAN%║%NC%
echo %CYAN%║%NC%                                                          %CYAN%║%NC%
echo %CYAN%║%NC%  🛑 Detener: ias stop                                   %CYAN%║%NC%
echo %CYAN%║%NC%  📊 Estado:  ias status                                 %CYAN%║%NC%
echo %CYAN%╚══════════════════════════════════════════════════════════════╝%NC%
echo.
goto :eof

:start_one
set "svc=%~1"
if "%svc%"=="ollama" (
    echo 🧠 Iniciando Ollama...
    wsl -d %DISTRO% -- bash -c "nohup ollama serve > /dev/null 2>&1 &"
    echo %GREEN%✅ Ollama iniciado en :11434%NC%
) else if "%svc%"=="postgres" (
    echo 🗄️  Iniciando PostgreSQL...
    wsl -d %DISTRO% -- bash -c "sudo systemctl start postgresql 2>/dev/null || sudo service postgresql start 2>/dev/null"
    echo %GREEN%✅ PostgreSQL iniciado%NC%
) else if "%svc%"=="invokeai" (
    echo 🖌️  Iniciando InvokeAI...
    wsl -d %DISTRO% -- bash -c "cd ~/invokeai 2>/dev/null && nohup invokeai-web --host 0.0.0.0 --port 9090 > /dev/null 2>&1 &" 2>nul
    echo %GREEN%✅ InvokeAI → http://localhost:9090%NC%
) else if "%svc%"=="openhuman" (
    echo 🤖 Iniciando OpenHuman...
    wsl -d %DISTRO% -- bash -c "cd ~/openhuman 2>/dev/null && export LD_LIBRARY_PATH=.:\$LD_LIBRARY_PATH && nohup ./openhuman-core run --jsonrpc-only --host 0.0.0.0 --port 7788 > /dev/null 2>&1 &" 2>nul
    echo %GREEN%✅ OpenHuman → http://localhost:7788%NC%
) else if "%svc%"=="telegram" (
    echo 🤖 Iniciando Telegram Bot...
    wsl -d %DISTRO% -- bash -c "cd ~/Simmoon_arc && tmux kill-session -t telegram-bot 2>/dev/null; tmux new-session -d -s telegram-bot 'python3 telegram_bot.py 2>&1 | tee ~/.simmoon-logs/telegram_bot.log; bash'"
    echo %GREEN%✅ Telegram Bot iniciado (sesion: telegram-bot)%NC%
) else if "%svc%"=="agatha" (
    echo 📋 Iniciando Agatha Actas (reportes horarios)...
    wsl -d %DISTRO% -- bash -c "cd ~/Simmoon_arc && tmux kill-session -t agatha-actas 2>/dev/null; tmux new-session -d -s agatha-actas 'python3 agatha_actas.py --daemon 2>&1 | tee ~/.simmoon-logs/agatha_actas.log; bash'"
    echo %GREEN%✅ Agatha Actas iniciado (sesion: agatha-actas)%NC%
) else if "%svc%"=="dashboard" (
    echo 📊 Iniciando Dashboard...
    wsl -d %DISTRO% -- bash -c "cd ~/Simmoon_arc && nohup python3 dashboard.py > /dev/null 2>&1 &"
    echo %GREEN%✅ Dashboard → http://localhost:5000%NC%
) else if "%svc%"=="bot" (
    call :start_one telegram
    call :start_one agatha
    goto :eof
) else if "%svc%"=="coding" (
    call :start_coding_agents
) else (
    echo %YELLOW%Servicio desconocido: %svc%%NC%
    echo   Opciones: ollama, invokeai, postgres, openhuman, dashboard, telegram, agatha, bot, coding
)

:start_coding_agents
echo %CYAN%🤖 Iniciando Coding Agents (verificación en PATH)...%NC%
where goose >nul 2>nul && (echo   🪿 goose    %GREEN%✅ disponible%NC%) || (echo   🪿 goose    %YELLOW%⚠️  no instalado%NC%)
where aider >nul 2>nul && (echo   🧑‍✈️ Aider    %GREEN%✅ disponible%NC%) || (echo   🧑‍✈️ Aider    %YELLOW%⚠️  no instalado%NC%)
where devin >nul 2>nul && (echo   🧑‍💻 Devin    %GREEN%✅ disponible%NC%) || (echo   🧑‍💻 Devin    %YELLOW%⚠️  no instalado%NC%)
where amp >nul 2>nul && (echo   ⚡ Amp       %GREEN%✅ disponible%NC%) || (echo   ⚡ Amp       %YELLOW%⚠️  no instalado%NC%)
echo.
echo %DIM%Nota: Coding Agents son CLI/Desktop; este script solo verifica PATH.%NC%
echo %DIM%Para invocar: 'aider', 'goose', etc. desde terminal.%NC%
goto :eof
goto :eof

REM ═══════════════════════════════════════════════════════════════════════════
REM  STOP
REM ═══════════════════════════════════════════════════════════════════════════
:stop
if "%~2"=="" (
    echo %YELLOW%🛑 Deteniendo TODOS los servicios...%NC%
    wsl -d %DISTRO% -- bash -c "pkill -f 'ollama serve' 2>/dev/null; pkill -f 'dashboard.py' 2>/dev/null; sudo systemctl stop postgresql 2>/dev/null || sudo service postgresql stop 2>/dev/null; echo DONE"
    wsl -d %DISTRO% -- bash -c "tmux kill-session -t telegram-bot 2>/dev/null; tmux kill-session -t agatha-actas 2>/dev/null; echo OK"
    echo %GREEN%✅ Servicios backend detenidos (coding agents son CLI/Desktop, gestionar manualmente si necesario)%NC%
) else (
    call :stop_one %2
)
goto :eof

:stop_one
echo Deteniendo %1...
if "%~1"=="ollama"    wsl -d %DISTRO% -- bash -c "pkill -f 'ollama serve' 2>/dev/null || true"
if "%~1"=="invokeai"  wsl -d %DISTRO% -- bash -c "pkill -f 'invokeai-web' 2>/dev/null || true"
if "%~1"=="openhuman" wsl -d %DISTRO% -- bash -c "pkill -f 'openhuman-core' 2>/dev/null || true"
if "%~1"=="postgres"  wsl -d %DISTRO% -- bash -c "sudo service postgresql stop 2>/dev/null || true"
if "%~1"=="telegram"  wsl -d %DISTRO% -- bash -c "tmux kill-session -t telegram-bot 2>/dev/null; pkill -f 'telegram_bot.py' 2>/dev/null || true"
if "%~1"=="agatha"    wsl -d %DISTRO% -- bash -c "tmux kill-session -t agatha-actas 2>/dev/null; pkill -f 'agatha_actas.py' 2>/dev/null || true"
if "%~1"=="dashboard" wsl -d %DISTRO% -- bash -c "pkill -f 'dashboard.py' 2>/dev/null || true"
if "%~1"=="bot" (
    call :stop_one telegram
    call :stop_one agatha
    goto :eof
)
if "%~1"=="coding" (
    echo %DIM%Los Coding Agents (goose/aider/devin/amp) son procesos CLI/Desktop interactivos. Detener manualmente desde su terminal.%NC%
    goto :eof
)
echo ✅ Detenido
goto :eof

REM ═══════════════════════════════════════════════════════════════════════════
REM  TOOLS
REM ═══════════════════════════════════════════════════════════════════════════
:models
echo %BOLD%📦 Modelos Ollama:%NC%
wsl -d %DISTRO% -- bash -c "curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); [print(f'  • {m[chr(39)+chr(39).join(['name',''])]}') for m in d.get(chr(39)+chr(39).join(['models','']),[])]\" 2>/dev/null || echo '  (Ollama no responde o no hay modelos)'"
echo.
goto :eof

:backup
echo 🗄️  Ejecutando backup PostgreSQL...
wsl -d %DISTRO% -- bash -c "bash ~/backup_postgres.sh"
goto :eof

REM ═══════════════════════════════════════════════════════════════════════════
REM  MAIN
REM ═══════════════════════════════════════════════════════════════════════════
if "%~1"=="" (
    call :status
    set /p CHOICE="  > "
    if /i "!CHOICE!"=="q" goto :eof
    if /i "!CHOICE!"=="a" call :start all
    if /i "!CHOICE!"=="s" call :stop all
    if /i "!CHOICE!"=="r" ( call :stop all & timeout /t 2 >nul & call :start all )
if /i "!CHOICE!"=="1" call :start_one ollama
if /i "!CHOICE!"=="2" call :start_one invokeai
if /i "!CHOICE!"=="3" call :start_one postgres
if /i "!CHOICE!"=="4" call :start_one openhuman
if /i "!CHOICE!"=="5" call :start_one dashboard
if /i "!CHOICE!"=="6" call :start_one telegram
if /i "!CHOICE!"=="7" call :start_one agatha
if /i "!CHOICE!"=="8" call :start_one bot
if /i "!CHOICE!"=="m" call :models
if /i "!CHOICE!"=="b" call :backup
goto :eof
)

if /i "%~1"=="start"   ( call :start %* & goto :eof )
if /i "%~1"=="stop"    ( call :stop %* & goto :eof )
if /i "%~1"=="status"  ( call :status & goto :eof )
if /i "%~1"=="restart" ( call :stop all & timeout /t 2 >nul & call :start all & goto :eof )
if /i "%~1"=="models"  ( call :models & goto :eof )
if /i "%~1"=="backup"  ( call :backup & goto :eof )
if /i "%~1"=="help"    ( echo ias [start^|stop^|status^|restart^|models^|backup] [servicio] & goto :eof )

echo %YELLOW%Comando no reconocido: %1%NC%
echo Uso: ias [start^|stop^|status^|restart^|models^|backup^|help]
goto :eof
