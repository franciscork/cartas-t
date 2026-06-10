# Guía de Primeros Pasos - OpenHuman

## ¿Qué es OpenHuman?
OpenHuman es un asistente de IA de código abierto (licencia GNU GPL-3.0) diseñado como aplicación de escritorio con enfoque "local-first". Permite trabajar con modelos de IA localmente usando Ollama.

## Instalación

### Windows
1. Descarga el .msi desde: https://github.com/tinyhumansai/openhuman/releases
2. Ejecuta el instalador como administrador
3. OpenHuman se instalará en `C:\files\files\files\files`

### Ubuntu/WSL
```bash
# Descargar desde GitHub releases
curl -LO https://github.com/tinyhumansai/openhuman/releases/download/v0.57.18/openhuman-core-0.57.18-x86_64-unknown-linux-gnu.tar.gz
tar -xzf openhuman-core-*.tar.gz
mv openhuman-core ~/bin/
chmod +x ~/bin/openhuman-core
```

## Configuración con Ollama

### Variables de Entorno
```bash
export OLLAMA_BASE_URL=http://localhost:11434
export OPENHUMAN_CORE_PORT=7788
```

### Modelos Ollama Disponibles
- qwen2.5-coder:14b (9GB) - Código
- qwen3:14b (9.3GB) - Chat general
- gemma3-tools-32k (7.3GB) - Herramientas
- deepseek-r1:7b (4.7GB) - Reasoning

## Uso en WSL con GUI
```bash
# Configurar servidor X (ya configurado con WSLg)
export DISPLAY=:0

# Ejecutar OpenHuman
openhuman-core
```

## Configurar Idioma Español
1. Abre OpenHuman
2. Ve a Settings (⚙️)
3. Busca "Language" o "General"
4. Selecciona "Español"

## Integraciones
- Gmail (configurable en Settings)
- Notion (configurable en Settings)
- Google Calendar (configurable en Settings)
- Repository local con Ollama

## Primeros Pasos
1. **Iniciar Ollama** en segundo plano: `ollama serve`
2. **Abrir OpenHuman** desde el menú de aplicaciones
3. **Seleccionar modelo local** en Settings > Model Provider > Ollama
4. **Comenzar a chatear** - todo queda en tu máquina

## Solución de Problemas
- Si no encuentra libxdo.so.3: `sudo apt-get install libxdo3 xdotool`
- Si la GUI no aparece: Verificar que DISPLAY=:0 esté configurado
- Para ver modelos disponibles: `curl http://localhost:11434/api/tags`