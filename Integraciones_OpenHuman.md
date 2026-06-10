# Integraciones OpenHuman

## Modelos Locales (Ollama)

### Configurar Ollama como Backend
```bash
export OLLAMA_BASE_URL=http://localhost:11434
```

### Modelos Recomendados
| Modelo | Tamaño | Uso |
|--------|--------|-----|
| qwen2.5-coder:14b | 9GB | Programación |
| qwen3:14b | 9.3GB | Chat general |
| gemma3:12b | 8.1GB | Análisis |
| deepseek-r1:8b | 5.2GB | Razonamiento |

## Integraciones Disponibles

### Gmail
1. Ve a Settings > Integrations > Gmail
2. Autoriza con tu cuenta Google
3. Usa "Read emails" o "Send email" comandos

### Notion
1. Settings > Integrations > Notion
2. Integra tu workspace
3. Busca y crea páginas con comandos de voz

### Google Calendar
1. Settings > Integrations > Calendar
2. Conecta tu cuenta Google
3. Crea eventos con comandos: "Schedule meeting tomorrow at 3pm"

### Repository Local
Permite hacer preguntas sobre código en tu computadora:
```bash
# Configurar carpeta de repository
export OPENHUMAN_REPO=/path/to/your/code
```

## Variables de Entorno

```bash
# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Puerto de OpenHuman
OPENHUMAN_CORE_PORT=7788

# Idioma
LANG=es_ES.UTF-8

# Display para GUI (WSL)
DISPLAY=:0
```

## WSLg (GUI en Windows)
OpenHuman funciona con WSLg automáticamente. No necesita servidor X adicional.

## Plugin System
OpenHuman soporta plugins personalizados. Directorio de plugins:
```
~/.config/openhuman/plugins/
```

## API REST
OpenHuman expone una API REST para integraciones externas:
```
http://localhost:7788/api/
```

## Model Routing
El sistema de "model routing" de OpenHuman routing automáticamente al modelo más apropiado según la tarea.