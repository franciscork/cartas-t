#!/usr/bin/env bash
# ============================================
# Script de Configuración OpenHuman + Ollama
# Para Ubuntu (WSL o nativo)
# ============================================

set -euo pipefail

echo "============================================"
echo "  INSTALACIÓN DE OPENHUMAN + OLLAMA"
echo "============================================"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# 1. Verificar Ollama
echo -e "${YELLOW}[1/5] Verificando Ollama...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓ Ollama instalado:${NC}"
    ollama list 2>/dev/null || echo "  (sin modelos o error de conexion)"
    echo ""
    echo -e "${GREEN}✓ Servicio Ollama activo:${NC}"
    ps aux | grep -i ollama | grep -v grep || echo "Ollama no está corriendo"
else
    echo -e "${YELLOW}⚠ Ollama no encontrado. Instálalo primero:${NC}"
    echo "   curl -fsSL https://ollama.com/install.sh | sh"
fi

echo ""

# 2. Instalar OpenHuman (si no existe)
echo -e "${YELLOW}[2/5] Verificando OpenHuman...${NC}"
if [ -f "$HOME/bin/openhuman-core" ]; then
    echo -e "${GREEN}✓ OpenHuman ya instalado en ~/bin/openhuman-core${NC}"
else
    echo -e "${YELLOW}⚠ Instalando OpenHuman...${NC}"
    mkdir -p ~/openhuman_install
    cd ~/openhuman_install
    echo "   Descargando OpenHuman v0.57.18..."
    curl -LO https://github.com/tinyhumansai/openhuman/releases/download/v0.57.18/openhuman-core-0.57.18-x86_64-unknown-linux-gnu.tar.gz
    tar -xzf openhuman-core-0.57.18-x86_64-unknown-linux-gnu.tar.gz
    mkdir -p ~/bin
    mv openhuman-core ~/bin/
    chmod +x ~/bin/openhuman-core
    echo -e "${GREEN}✓ OpenHuman instalado${NC}"
fi

echo ""

# 3. Configurar variables de entorno
echo -e "${YELLOW}[3/5] Configurando variables de entorno...${NC}"

# Agregar al PATH
if ! grep -q "export PATH=\"\\$HOME/bin" ~/.bashrc 2>/dev/null; then
    echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
    echo -e "${GREEN}✓ PATH configurado${NC}"
fi

# Configurar Ollama
if ! grep -q "OLLAMA_BASE_URL" ~/.bashrc 2>/dev/null; then
    echo 'export OLLAMA_BASE_URL=http://localhost:11434' >> ~/.bashrc
    echo -e "${GREEN}✓ OLLAMA_BASE_URL configurado${NC}"
fi

# Configurar Puerto OpenHuman
if ! grep -q "OPENHUMAN_CORE_PORT" ~/.bashrc 2>/dev/null; then
    echo 'export OPENHUMAN_CORE_PORT=7788' >> ~/.bashrc
    echo -e "${GREEN}✓ OPENHUMAN_CORE_PORT configurado${NC}"
fi

# Configurar idioma español
if ! grep -q "LANG=es_ES" ~/.bashrc 2>/dev/null; then
    echo 'export LANG=es_ES.UTF-8' >> ~/.bashrc
    echo 'export LC_ALL=es_ES.UTF-8' >> ~/.bashrc
    echo -e "${GREEN}✓ Idioma español configurado${NC}"
fi

echo ""
echo -e "${YELLOW}[4/5] Cargando configuración...${NC}"
source ~/.bashrc 2>/dev/null || true

echo ""

# 5. Verificación final
echo -e "${YELLOW}[5/5] Verificación final...${NC}"
echo ""
echo "=== Variables de entorno ==="
echo "PATH: $HOME/bin"
echo "OLLAMA_BASE_URL: $OLLAMA_BASE_URL"
echo "OPENHUMAN_CORE_PORT: $OPENHUMAN_CORE_PORT"
echo "LANG: $LANG"
echo ""
echo "=== Binarios ==="
echo "OpenHuman: $(which openhuman-core 2>/dev/null || echo 'No encontrado')"
echo "Ollama: $(which ollama 2>/dev/null || echo 'No encontrado')"
echo ""

echo "============================================"
echo -e "${GREEN}  CONFIGURACIÓN COMPLETADA${NC}"
echo "============================================"
echo ""
echo "Para ejecutar OpenHuman:"
echo ""
echo "  1. En Ubuntu con escritorio gráfico (X11):"
echo "     openhuman-core"
echo ""
echo "  2. En WSL, necesitas un servidor X:"
echo "     - Instala VcXsrv o X410 en Windows"
echo "     - Ejecuta: export DISPLAY=:0"
echo "     - Luego: openhuman-core"
echo ""
echo "  3. Para usar solo Ollama local:"
echo "     Configura en la GUI de OpenHuman:"
echo "     Settings > Model Provider > Ollama (Local)"
echo ""
echo "Modelos Ollama disponibles:"
ollama list 2>/dev/null || echo "No hay modelos"
echo ""