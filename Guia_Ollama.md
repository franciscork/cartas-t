# 🦙 Guía Rápida - Ollama (Modelos Locales de IA)

## ¿Qué es?
Ollama ejecuta modelos de lenguaje (LLMs) localmente en tu máquina. Sin nube, sin límites, 100% privado.

## Puertos y URLs
| Recurso | URL |
|----------|-----|
| API REST | `http://localhost:11434` |
| Listar modelos | `curl http://localhost:11434/api/tags` |
| Documentación | https://ollama.com/docs |

## Modelos Instalados
```
phi3:latest                  (~2.3 GB) - Microsoft, rápido
qwen2.5-coder:7b             (~4.7 GB) - Código
qwen2.5-coder:14b            (~9.0 GB) - Código (grande)
qwen3:14b                    (~9.3 GB) - Chat general
qwen3:0.6b                   (~0.5 GB) - Ultra-rápido
orieg/gemma3-tools:12b-ft    (~8.1 GB) - Herramientas
gemma3-tools-32k:latest      (~7.3 GB) - Contexto 32k
nomic-embed-text:latest      (~0.5 GB) - Embeddings
```

## Comandos Básicos
```bash
# Iniciar servidor
ollama serve

# Listar modelos
ollama list

# Descargar modelo nuevo
ollama pull llama3.2:3b

# Ejecutar modelo (chat)
ollama run qwen3:14b

# Eliminar modelo
ollama rm phi3:latest

# Ver info de modelo
ollama show qwen3:14b
```

## Uso desde Python
```python
import requests
response = requests.post("http://localhost:11434/api/generate", json={
    "model": "qwen3:14b",
    "prompt": "Explica la teoría de la relatividad",
    "stream": False
})
print(response.json()["response"])
```

## Ubicaciones
- **Modelos**: `~/.ollama/models/`
- **Logs**: `/tmp/ollama.log`
- **Binario**: `/usr/local/bin/ollama`

## Solución de Problemas
- **No arranca**: `pkill ollama && sleep 2 && ollama serve`
- **Puerto ocupado**: `fuser -k 11434/tcp`
- **Modelo no encontrado**: `ollama pull <nombre>`
- **Sin GPU**: Ollama funciona en CPU (más lento pero funcional)
