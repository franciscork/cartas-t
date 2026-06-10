@echo off
cd /d "%~dp0dist"
start SIMMOON_1_4_0.exe
timeout /t 8 /nobreak >nul
tasklist | findstr SIMMOON_1_4_0 >nul
if %errorlevel%==0 (
    echo EXE_RUNNING
) else (
    echo EXE_NOT_RUNNING
)
