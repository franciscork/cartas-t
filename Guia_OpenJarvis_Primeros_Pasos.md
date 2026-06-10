# Guía de Primeros Pasos - OpenJarvis

## ¿Qué es OpenJarvis?
OpenJarvis es un asistente de IA open-source con capacidades de voz (TTS/STT). Diseñado para funcionar completamente offline con modelos locales como Ollama.

## Características Principales
- 🎤 **Voz integrada** - Reconocimiento y síntesis de voz
- 🤖 **Modelos locales** - Compatible con Ollama
- 🔒 **Privacidad** - Todo el procesamiento en local
- ⚡ **Rápido** - Optimizado para ejecución local

## Instalación (Ya instalada en tu sistema)

OpenJarvis ya está instalado en `/home/docus/.local/bin/jarvis`

### Verificar instalación:
```bash
jarvis --version
jarvis doctor
```

## Configuración con Ollama

OpenJarvis usa Ollama para el procesamiento de lenguaje natural. Asegúrate de que Ollama esté corriendo:

```bash
# En otra terminal, iniciar Ollama
ollama serve

# Ver modelos disponibles
ollama list
```

## Uso con Voz

### Comandos de voz básicos:
- "Hey Jarvis" - Activar asistente
- "What can you do?" - Ver capacidades
- "Search for..." - Buscar información

### Comandos de texto:
```bash
jarvis "tu pregunta aquí"
```

## Configuración de Idioma
El idioma por defecto es inglés. Para configurar español, edita el archivo de configuración en `~/.openjarvis/config.yaml`:

```yaml
language: es
tts_language: es-ES
stt_language: es-ES
```

## Integraciones
- Ollama (modelos locales)
- VAD (Voice Activity Detection)
- TTS (Text-to-Speech) local
- STT (Speech-to-Text) local

## Archivos de Configuración
- Config: `~/.openjarvis/config.yaml`
- Logs: `~/.openjarvis/logs/`
- Modelos: `~/.openjarvis/models/`

## Solución de Problemas
- Si no responde a voz: Verificar que el micrófono esté configurado
- Si no conecta a Ollama: Verificar que `ollama serve` esté corriendo
- Para ver logs: `tail -f ~/.openjarvis/logs/jarvis.log`