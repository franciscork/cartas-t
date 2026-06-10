# 🐳 Guía Rápida - Docker + NVIDIA Container Toolkit

## ¿Qué es?
Docker con aceleración GPU para contenedores que usan CUDA. Permite ejecutar ComfyUI, InvokeAI y otros servicios en contenedores con acceso directo a la RTX 4070.

## Versiones Instaladas
| Componente | Versión |
|------------|---------|
| Docker | 29.1.3 |
| NVIDIA Container Toolkit | 1.19.1 |
| CUDA | 12.4 |

## Comandos Básicos
```bash
# Verificar instalación
docker --version
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# Listar contenedores
docker ps
docker ps -a

# Listar imágenes
docker images

# Iniciar/detener
docker start <container>
docker stop <container>

# Limpiar
docker system prune -a
```

## Ejecutar con GPU
```bash
# Contenedor con acceso GPU
docker run --gpus all -it nvidia/cuda:12.4.0-base-ubuntu22.04 bash

# ComfyUI en Docker (ejemplo)
docker run --gpus all -p 8188:8188 \
  -v ~/ComfyUI/models:/ComfyUI/models \
  -v ~/ComfyUI/output:/ComfyUI/output \
  comfyui-docker
```

## Variables de Entorno
```bash
export NVIDIA_VISIBLE_DEVICES=all
export NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

## Ubicaciones
- **Docker config**: `/etc/docker/daemon.json`
- **Imágenes**: `/var/lib/docker/`
- **NVIDIA toolkit**: `/usr/share/nvidia-container-toolkit/`

## Solución de Problemas
- **GPU no detectada**: `sudo systemctl restart docker`
- **nvidia-smi no funciona en container**: Verificar toolkit instalado
- **Permisos**: Agregar usuario al grupo docker: `sudo usermod -aG docker $USER`
