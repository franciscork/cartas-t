# 🚀 Guía Rápida - IAS (Lanzador Unificado de IAs)

## ¿Qué es?
**IAS** (Inteligencias Artificiales Simplificadas) es el lanzador unificado que reemplaza 9 scripts dispersos. Un solo comando para gestionar todos los servicios de IA.

## Acceso Rápido
| Plataforma | Comando / Archivo |
|------------|-------------------|
| **Escritorio** | Doble clic en `ias_desktop.bat` |
| **WSL2/Linux** | `bash ~/ias.sh <comando>` |
| **Windows cmd** | `ias.bat <comando>` (desde la raíz del proyecto) |

## Configurar alias (opcional, una sola vez)
```bash
# Añadir a ~/.bashrc para usar 'ias' directamente
echo "alias ias='bash ~/ias.sh'" >> ~/.bashrc
source ~/.bashrc
```

## Comandos Principales
```bash
# Menú interactivo (recomendado)
bash ~/ias.sh menu

# Iniciar todos los servicios
bash ~/ias.sh start

# Detener todos los servicios
bash ~/ias.sh stop

# Estado de todos los servicios
bash ~/ias.sh status

# Reiniciar todos
bash ~/ias.sh restart

# Backup de configuraciones
bash ~/ias.sh backup

# Listar modelos Ollama
bash ~/ias.sh models

# Ver ayuda
bash ~/ias.sh help
```

## Servicios Gestionados
| # | Servicio | Puerto | Tipo |
|---|----------|--------|------|
| 1 | Ollama | 11434 | Modelos LLM |
| 2 | PostgreSQL | 5432 | Base de datos |
| 3 | ComfyUI | 8188 | Imágenes (Stable Diffusion) |
| 4 | InvokeAI | 9090 | Imágenes (canvas) |
| 5 | Hermes | 9119 | Agente autónomo |
| 6 | OpenHuman | 7788 | Asistente escritorio |
| 7 | Jarvis | CLI | Asistente voz (CLI) |
| 8 | Dashboard | 5000 | Monitor web |

## Comandos por Servicio
```bash
# Iniciar servicio específico
bash ~/ias.sh start comfyui
bash ~/ias.sh start ollama
bash ~/ias.sh start hermes

# Detener servicio específico
bash ~/ias.sh stop postgres
bash ~/ias.sh stop dashboard

# Ver logs
tail -f /tmp/simmoon_*.log
```

## Orden de Inicio (start all)
1. Ollama (modelos LLM)
2. PostgreSQL (datos)
3. ComfyUI (imágenes principal)
4. InvokeAI (imágenes canvas)
5. Hermes (agente autónomo)
6. OpenHuman (asistente escritorio)
7. Dashboard (monitor web)

## Atajos de Escritorio
| Archivo | Función |
|---------|---------|
| `ias_desktop.bat` | Menú interactivo IAS |
| `SIMMOON_Launch.bat` | Verificar + abrir Dashboard + Viewer |

## Ubicaciones
- **Script Linux**: `~/ias.sh`
- **Script Windows**: `C:\Program Files\PowerShell\7\ias.bat`
- **Logs**: `/tmp/simmoon_*.log`

## Solución de Problemas
- **WSL no arranca**: `wsl -d Ubuntu` en PowerShell
- **Puerto ocupado**: `bash ~/ias.sh status` para ver qué está corriendo
- **sudo no funciona**: Ya configurado con passwordless para docus
