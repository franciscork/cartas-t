@echo off
chcp 65001 >nul
title IAS - Lanzador Unificado de IAs
color 0E

:: ─── IAS Launcher ───────────────────────────────────────────────
:: Abre una terminal WSL con el menú interactivo de ias.sh
:: Todos los servicios de IA en un solo lugar
:: ─────────────────────────────────────────────────────────────────

echo.
echo    ╔══════════════════════════════════════════════╗
echo    ║        🧠  I A S   L A U N C H E R          ║
echo    ║     Lanzador Unificado de Inteligencias      ║
echo    ╚══════════════════════════════════════════════╝
echo.
echo    Abriendo terminal WSL con el menú interactivo...
echo    (Si es la primera vez, puede tardar unos segundos)
echo.

:: Lanzar ias.sh en modo menú interactivo dentro de WSL
wsl -d Ubuntu -- bash -c "cd ~ && bash ias.sh menu"

echo.
echo    ──────────────────────────────────────────────
echo    Sesión IAS finalizada.
pause
