# 🎨 Guía Rápida - ComfyUI (Generación de Imágenes)

## ¿Qué es?
ComfyUI es un generador de imágenes con IA basado en **Stable Diffusion**, usando interfaz de nodos visual. Corre localmente con tu GPU NVIDIA RTX 4070.

## Puertos y URLs
| Recurso | URL |
|----------|-----|
| Interfaz Web | `http://localhost:8188` |
| API REST | `http://localhost:8188/api` |
| Documentación | https://docs.comfy.org |

## Iniciar / Detener
```bash
# Desde el lanzador unificado (recomendado)
bash ~/ias.sh start comfyui

# Manualmente
cd ~/ComfyUI
python3 main.py --listen 0.0.0.0 --port 8188

# Detener
bash ~/ias.sh stop comfyui
# o manual: fuser -k 8188/tcp
```

## Workflows (Flujos de Trabajo)
Los workflows de generación están en `~/Simmoon_arc/`:
- **`generate_comfyui.py`** → `build_workflow()` — constructor canónico de workflows
- **`generator_factory.py`** → `ComfyUIBackend` — backend de generación
- **`comfyui_workflow_template.json`** — plantilla de workflow

### Workflow txt2img básico:
```python
from generate_comfyui import build_workflow

workflow = build_workflow(
    prompt="un gato espacial en marte",
    negative="borroso, deforme, baja calidad",
    width=1024, height=1024,
    steps=25, cfg=7.5, seed=-1,
    model="sd_xl_base_1.0.safetensors",
    sampler_name="dpmpp_2m",
    loras=[]
)
```

## Modelos Compatibles
- **SDXL** (Stable Diffusion XL)
- **SD 1.5 / 2.1**
- **Flux** (≥8GB con optimizaciones, experimental en RTX 4070 Laptop)
- **SD3** (≥8GB con optimizaciones, puede necesitar `--lowvram`)

## Parámetros Clave
| Parámetro | Rango | Descripción |
|-----------|-------|-------------|
| `steps` | 15-50 | Más pasos = más calidad, más lento |
| `cfg` | 3-15 | Control creatividad (7-9 típico) |
| `seed` | -1 = aleatorio | Fijar para reproducir resultados |
| `width/height` | 512-2048 | Resolución de salida |

## Ubicaciones
- **Instalación**: `~/ComfyUI/`
- **Modelos**: `~/ComfyUI/models/checkpoints/`
- **Outputs**: `~/ComfyUI/output/`
- **Logs**: `/tmp/simmoon_comfyui.log`

## RTX 4070 (8GB VRAM)
- ✅ SDXL: ~8-15 seg por imagen
- ✅ SD 1.5: ~4-8 seg por imagen
- ⚠️ Flux: posible (con optimizaciones)
- ⚠️ SD3: puede necesitar `--lowvram`

## Solución de Problemas
- **No arranca**: Verificar puerto `fuser 8188/tcp`
- **CUDA error**: `nvidia-smi` verificar GPU accesible
- **VRAM llena**: `fuser -k 8188/tcp && sleep 2` y reiniciar
- **Modelo no encontrado**: Colocar en `~/ComfyUI/models/checkpoints/`
