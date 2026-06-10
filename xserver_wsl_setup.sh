#!/usr/bin/env bash
# ============================================
# Configurar Servidor X en WSL Ubuntu
# Compatible con WSLg (Windows 11/10)
# ============================================

set -euo pipefail

echo "============================================"
echo "  CONFIGURACIÓN DE SERVIDOR X EN WSL"
echo "============================================"
echo ""

# Colores (usar con echo -e)
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# 1. Verificar WSLg
echo -e "${YELLOW}[1/5] Verificando WSLg (Windows Subsystem for Linux GUI)...${NC}"
if [ -d "/mnt/wslg" ]; then
    echo -e "${GREEN}✓ WSLg está disponible y montado${NC}"
    echo "   Ubicación: /mnt/wslg"
    ls /mnt/wslg/
else
    echo -e "${YELLOW}⚠ WSLg no está montado. Usando configuración manual.${NC}"
fi

echo ""

# 2. Verificar DISPLAY
echo -e "${YELLOW}[2/5] Verificando variable DISPLAY...${NC}"
if [ -n "$DISPLAY" ]; then
    echo -e "${GREEN}✓ DISPLAY configurado: $DISPLAY${NC}"
else
    echo -e "${YELLOW}⚠ DISPLAY no configurado. Configurando...${NC}"
    # Intentar obtener IP de Windows
    export DISPLAY=$(grep nameserver /etc/resolv.conf | awk '{print $2; exit}'):0
    echo "   NUEVO DISPLAY: $DISPLAY"
fi

echo ""

# 3. Verificar libwebkit (necesario para OpenHuman)
echo -e "${YELLOW}[3/5] Verificando librerías GTK/WebKit...${NC}"
if ldconfig -p | grep -q "libwebkit2gtk"; then
    echo -e "${GREEN}✓ libwebkit2gtk disponible${NC}"
    ldconfig -p | grep "libwebkit2gtk" | head -1
else
    echo -e "${YELLOW}⚠ libwebkit2gtk no encontrada${NC}"
fi

echo ""

# 4. Verificar Ollama
echo -e "${YELLOW}[4/5] Verificando Ollama...${NC}"
if pgrep -x "ollama" > /dev/null; then
    echo -e "${GREEN}✓ Ollama está corriendo${NC}"
    curl -s http://localhost:11434/api/tags 2>/dev/null | head -1 || echo "   (Sin respuesta de API)"
else
    echo -e "${YELLOW}⚠ Ollama no está corriendo${NC}"
    echo "   Para iniciar: ollama serve"
fi

echo ""

# 5. Verificar OpenHuman en Ubuntu
echo -e "${YELLOW}[5/5] Verificando OpenHuman en Ubuntu...${NC}"
if [ -f "$HOME/bin/openhuman-core" ]; then
    echo -e "${GREEN}✓ OpenHuman instalado en $HOME/bin/openhuman-core${NC}"
    file $HOME/bin/openhuman-core | head -1
else
    echo -e "${YELLOW}⚠ OpenHuman no instalado en Ubuntu${NC}"
    echo "   (Ya está instalado en Windows: C:\\Program Files\\OpenHuman\\OpenHuman.exe)"
fi

echo ""
echo "============================================"
echo -e "${GREEN}  CONFIGURACIÓN LISTA${NC}"
echo "============================================"
echo ""
echo "INSTRUCCIONES:"
echo ""
echo "1. SI TIENES WSLg (Windows 11):"
echo "   - WSLg ya está configurado automáticamente"
echo "   - Solo ejecuta: openhuman-core"
echo "   - La GUI aparecerá en Windows"
echo ""
echo "2. SI NO TIENES WSLg (Windows 10 antiguo):"
echo "   - Instala VcXsrv en Windows:"
echo "     https://sourceforge.net/projects/vcxsrv/"
echo "   - Descarga e instala, luego ejecuta XLaunch"
echo "   - Selecciona 'Multiple windows', marca 'Disable access control'"
echo "   - En Ubuntu, ejecuta estos comandos:"
echo ""
echo "     echo 'export DISPLAY=\\$HOME/bin/wsl.x' >> ~/.bashrc"
echo "     echo 'export LIBGL_ALWAYS_INDIRECT=1' >> ~/.bashrc"
echo "     source ~/.bashrc"
echo ""
echo "3. PROBAR GUI:"
echo "   - Instala apps de prueba:"
echo "     sudo apt install x11-apps -y"
echo "   - Ejecuta: xeyes"
echo "   - Si aparecen ojos, la GUI funciona"
echo ""
echo "4. ABRIR OPENHUMAN EN WSL:"
echo "   - Configurar Ollama (verifica que esté corriendo):"
echo "     export OLLAMA_BASE_URL=http://localhost:11434"
echo "   - Ejecutar: openhuman-core"
echo ""

# Mostrar estado final
echo "=== RESUMEN DE CONFIGURACIÓN ==="
echo "WSLg: $([ -d '/mnt/wslg' ] && echo 'Activo' || echo 'No disponible')"
echo "DISPLAY: $DISPLAY"
echo "Ollama: $(pgrep -x ollama > /dev/null && echo 'Corriendo' || echo 'Detenido')"
echo "OpenHuman Ubuntu: $([ -f '$HOME/bin/openhuman-core' ] && echo 'Instalado' || echo 'No instalado')"
echo "OpenHuman Windows: $([ -f '/mnt/c/Program Files/OpenHuman/OpenHuman.exe' ] && echo 'Instalado' || echo 'No instalado')"
echo ""
echo "============================================"