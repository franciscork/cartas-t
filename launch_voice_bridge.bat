@echo off
chcp 65001 >nul
title SIMMOON — Voice Bridge Launcher 🎤

echo.
echo  ════════════════════════════════════════
echo   ☾  SIMMOON Voice Bridge  —  🎤🔈
echo  ════════════════════════════════════════
echo.
echo  Abriendo Voice Bridge en ventana aparte...
echo.

pushd "%~dp0Simmoon_arc"
start "Voice Bridge" cmd /c "title SIMMOON — Voice Bridge 🎤 && python voice_bridge.py && pause"
popd

echo  ✅ Voice Bridge lanzado en nueva ventana.
echo     Cierra la ventana del Voice Bridge cuando termines.
echo.
echo  Presiona cualquier tecla para cerrar este lanzador...
pause >nul
