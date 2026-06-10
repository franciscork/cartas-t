# 🎯 Guía Rápida - InvokeAI (Generación de Imágenes)

## ¿Qué es?
InvokeAI es una suite profesional de generación de imágenes con IA. Interfaz canvas unificada para Stable Diffusion. Corre localmente con tu GPU RTX 4070.

> ⚠️ **Estado actual**: No instalado/inactivo en el sistema. Para usar, instalar primero:
> ```bash
> pip install invokeai
> invokeai-configure
> ```

## Puertos y URLs
| Recurso | URL |
|----------|-----|
| Interfaz Web | `http://localhost:9090` |
| Documentación | https://invoke-ai.github.io/InvokeAI |

## Iniciar / Detener
```bash
# Desde el lanzador unificado (recomendado)
bash ~/ias.sh start invokeai

# Manualmente
cd ~/invokeai
invokeai-web --host 0.0.0.0 --port 9090

# Detener
bash ~/ias.sh stop invokeai
```

## Características Principales
- 🎨 **Canvas unificado** — Inpaint, outpaint, img2img en un solo lienzo
- 🖼️ **ControlNet** — Control preciso con poses, bordes, profundidad
- 🎭 **IP-Adapter** — Transferencia de estilo por imagen
- 📦 **Model Manager** — Descarga y gestiona modelos desde la UI
- 🔧 **Regional Prompting** — Diferentes prompts para zonas de la imagen

## Scripts del Proyecto
```bash
# Generar con InvokeAI desde Simmoon
cd ~/Simmoon_arc
python3 generate_invokeai.py

# Pipeline automatizado
python3 simmoon_pipeline.py
```

## Comandos CLI
```bash
# Iniciar interfaz web
invokeai-web

# Instalar modelos
invokeai-model-install

# Configurar
invokeai-configure

# Importar modelos existentes
invokeai-import-images
```

## Ubicaciones
- **Instalación**: `~/invokeai/`
- **Modelos**: `~/invokeai/models/`
- **Outputs**: `~/invokeai/outputs/`
- **Config**: `~/invokeai/invokeai.yaml`
- **Logs**: En interfaz web y terminal

## Modelos Recomendados para RTX 4070
- SDXL 1.0 (base + refiner)
- SD 1.5 (más rápido)
- ControlNet para SDXL y SD 1.5
- IP-Adapter para transferencia de estilo

## Solución de Problemas
- **No arranca**: `fuser 9090/tcp` verificar puerto
- **Instalación**: `pip install invokeai`
- **Modelos no aparecen**: Re-escanear en Model Manager
- **VRAM**: Usar `--precision fp16` para ahorrar memoria
