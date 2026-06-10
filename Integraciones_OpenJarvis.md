# Integraciones OpenJarvis

## Integración con Ollama

OpenJarvis usa Ollama como backend principal para procesamiento de lenguaje natural.

### Configuración
```bash
# Verificar conexión
curl http://localhost:11434/api/tags

# Configuración en ~/.openjarvis/config.yaml
ollama:
  base_url: http://localhost:11434
  default_model: qwen3:14b
```

## Modelos de Voz

### TTS (Text-to-Speech)
OpenJarvis incluye síntesis de voz local. Modelos compatibles:
- espeak-ng (instalado)
- piper (opcional)
- coqui-tts (opcional)

### STT (Speech-to-Text)
Reconocimiento de voz local:
- whisper (via Ollama)
- vosk (opcional)
- speech_recognition (Python)

## Wake Word (Palabra de Activación)
Configurar palabra de activación personalizada:
```yaml
wake_word: hey jarvis
sensitivity: 0.7
```

## Comandos de Voz

### Comandos Básicos
- "Hey Jarvis" → Activar asistente
- "What's the weather?" → Consulta clima
- "Set a reminder for 5pm" → Crear recordatorio
- "Play music" → Reproducir música

### Comandos de Control
- "Stop" → Detener
- "Pause" → Pausar
- "Resume" → Reanudar
- "Exit" → Salir

## Integración con Home Assistant
```yaml
home_assistant:
  url: http://localhost:8123
  token: YOUR_TOKEN
```

## Plugin System
OpenJarvis soporta plugins en:
```
~/.openjarvis/plugins/
```

## API de Voz
Endpoints disponibles:
- `/api/tts` - Síntesis de voz
- `/api/stt` - Reconocimiento de voz
- `/api/wake` - Detección de palabra de activación

## Variables de Entorno
```bash
# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Idioma
LANG=es_ES.UTF-8

# Directórios
OPENJARVIS_HOME=~/.openjarvis
OPENJARVIS_MODELS=~/.openjarvis/models
```

## Solución de Problemas de Voz
- Si no reconoce voz: Verificar permisos de micrófono
- Si TTS no funciona: Verificar que espeak-ng esté instalado
- Si Ollama no responde: Verificar que `ollama serve` esté corriendo