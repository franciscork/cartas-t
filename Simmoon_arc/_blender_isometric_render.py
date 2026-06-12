"""
_blender_isometric_render.py — Script genérico de Blender para render isométrico

Importa cualquier modelo 3D (.blend o .obj), configura cámara isométrica
2:1 dimetric, aplica materiales flat/cel-shaded, y renderiza con Cycles.

Argumentos (vía --python-expr o variables de entorno):
  BLENDER_INPUT   — Ruta al archivo .blend o .obj
  BLENDER_OUTPUT  — Ruta del PNG de salida
  BLENDER_SIZE    — Resolución del render (default: 512)

Ejecutar:
  blender --background --python _blender_isometric_render.py
"""

import bpy
import os
import sys
from math import radians, cos, sin, tan
from pathlib import Path


# ── Config desde variables de entorno ──────────────────────────────────
INPUT_FILE = os.environ.get("BLENDER_INPUT", "")
OUTPUT_FILE = os.environ.get("BLENDER_OUTPUT", "render.png")
RENDER_SIZE = int(os.environ.get("BLENDER_SIZE", "512"))


# ── Constantes isométricas ─────────────────────────────────────────────
CAM_ELEVATION = radians(60)   # 60° desde vertical → 30° desde horizontal (ratio 2:1)
CAM_AZIMUTH = radians(45)     # Rotación 45° para vista 3/4
CAM_DISTANCE = 8.0
ORTHO_SCALE = 4.5


# ── Limpiar escena ─────────────────────────────────────────────────────
def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for light in list(bpy.data.lights):
        bpy.data.lights.remove(light)
    for cam in list(bpy.data.cameras):
        bpy.data.cameras.remove(cam)


# ── Importar modelo ────────────────────────────────────────────────────
def import_model(filepath: str):
    """Importa .blend (append) o .obj/.fbx (import)."""
    ext = Path(filepath).suffix.lower()
    
    try:
        if ext == '.blend':
            # Append all objects from the .blend file
            with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
                data_to.objects = data_from.objects
            for obj in data_to.objects:
                if obj is not None:
                    bpy.context.collection.objects.link(obj)
        
        elif ext == '.obj':
            bpy.ops.wm.obj_import(filepath=filepath)
        
        elif ext == '.fbx':
            bpy.ops.import_scene.fbx(filepath=filepath)
        
        elif ext in ('.glb', '.gltf'):
            bpy.ops.import_scene.gltf(filepath=filepath)
        
        else:
            raise ValueError(f"Formato no soportado: {ext}")
    except Exception as e:
        raise RuntimeError(f"Error importando {os.path.basename(filepath)}: {e}") from e


# ── Auto-centrar y escalar ─────────────────────────────────────────────
def auto_center_and_scale():
    """Centra todos los objetos en (0, 0, 0) y escala para que quepan
    en el encuadre isométrico (~3 unidades de ancho)."""
    objects = [obj for obj in bpy.context.scene.objects 
               if obj.type == 'MESH' and obj.visible_get()]
    
    if not objects:
        print("  ⚠️  No se encontraron objetos mesh para centrar")
        return
    
    # Calcular bounding box global
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    
    bpy.context.view_layer.update()
    
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')
    
    for obj in objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ bpy.mathutils.Vector(corner)
            min_x = min(min_x, world_corner.x)
            min_y = min(min_y, world_corner.y)
            min_z = min(min_z, world_corner.z)
            max_x = max(max_x, world_corner.x)
            max_y = max(max_y, world_corner.y)
            max_z = max(max_z, world_corner.z)
    
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    center_z = (min_z + max_z) / 2
    
    size_x = max_x - min_x
    size_y = max_y - min_y
    size_z = max_z - min_z
    max_dim = max(size_x, size_y, size_z)
    
    if max_dim < 0.001:
        max_dim = 1.0
    
    # Escala para que quepa en ~3 unidades
    target_size = 3.0
    scale_factor = target_size / max_dim
    
    # Mover todos al centro y escalar
    for obj in objects:
        obj.location.x -= center_x
        obj.location.y -= center_y
        obj.location.z -= min_z  # Poner sobre el suelo (z=0)
        
        # Escalar uniformemente
        obj.scale *= scale_factor
    
    bpy.ops.object.select_all(action='DESELECT')
    print(f"  📐 Auto-centrado: {len(objects)} objetos, escala ×{scale_factor:.2f}")
    print(f"     BBox original: {max_dim:.1f}u → escalado a ~{target_size:.1f}u")


# ── Aplicar materiales flat ────────────────────────────────────────────
def apply_flat_materials():
    """Aplica materiales planos (cel-shaded) a todos los objetos.
    Convierte todos los materiales a nodos y ajusta roughness vía Principled BSDF."""
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None:
                continue
            
            # Asegurar que el material usa nodos
            if not mat.use_nodes:
                mat.use_nodes = True
            
            nodes = mat.node_tree.nodes
            bsdf = nodes.get('Principled BSDF')
            if bsdf:
                bsdf.inputs['Roughness'].default_value = 0.85
                bsdf.inputs['Specular IOR Level'].default_value = 0.05
        
        # Si no tiene material, asignar uno gris flat
        if len(obj.material_slots) == 0:
            mat = bpy.data.materials.new(name=f"Flat_{obj.name}")
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            bsdf = nodes.get('Principled BSDF')
            if bsdf:
                bsdf.inputs['Base Color'].default_value = (0.7, 0.7, 0.75, 1.0)
                bsdf.inputs['Roughness'].default_value = 0.85
                bsdf.inputs['Specular IOR Level'].default_value = 0.05
            obj.data.materials.append(mat)


# ── Configurar cámara isométrica ───────────────────────────────────────
def setup_isometric_camera():
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.name = "SIMMOON_IsoCamera"
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = ORTHO_SCALE
    
    # Posición: 45° azimuth, elevación para ratio 2:1
    x = CAM_DISTANCE * cos(CAM_AZIMUTH)
    y = CAM_DISTANCE * sin(CAM_AZIMUTH)
    z = CAM_DISTANCE * tan(radians(30))
    cam.location = (x, y, z)
    
    # Apuntar al origen
    direction = bpy.mathutils.Vector((0, 0, 0.5)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    
    bpy.context.scene.camera = cam
    return cam


# ── Iluminación ────────────────────────────────────────────────────────
def setup_lighting():
    # Sol principal (sombras duras → estilo pixel)
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
    sun = bpy.context.object
    sun.name = "SIMMOON_Sun"
    sun.data.energy = 3.5
    sun.data.angle = 0.015
    sun.rotation_euler = (radians(55), 0, radians(-35))
    
    # Luz de relleno (ambiente)
    bpy.ops.object.light_add(type='SUN', location=(-3, 2, 4))
    fill = bpy.context.object
    fill.name = "SIMMOON_Fill"
    fill.data.energy = 1.2
    fill.data.angle = 0.05
    fill.rotation_euler = (radians(30), 0, radians(120))


# ── Configurar render ──────────────────────────────────────────────────
def setup_render():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.render.resolution_x = RENDER_SIZE
    scene.render.resolution_y = RENDER_SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    
    # Cycles: pocas samples, flat shading
    scene.cycles.samples = 32
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    
    # Fondo de mundo neutro
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Strength'].default_value = 1.8
        bg.inputs['Color'].default_value = (0.88, 0.90, 0.94, 1.0)


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{'='*60}")
    print(f"  🧊 SIMMOON — Render Isométrico Automático")
    print(f"  Input:  {INPUT_FILE}")
    print(f"  Output: {OUTPUT_FILE}")
    print(f"  Size:   {RENDER_SIZE}×{RENDER_SIZE}")
    print(f"{'='*60}\n")
    
    if not INPUT_FILE or not os.path.isfile(INPUT_FILE):
        print(f"  ❌ Archivo no encontrado: {INPUT_FILE}")
        print(f"     Define BLENDER_INPUT con la ruta al modelo")
        return
    
    # 1. Limpiar escena por defecto
    clear_scene()
    
    # 2. Importar modelo
    print(f"  📦 Importando: {os.path.basename(INPUT_FILE)}")
    import_model(INPUT_FILE)
    
    # 3. Auto-centrar y escalar
    auto_center_and_scale()
    
    # 4. Aplicar materiales flat
    apply_flat_materials()
    
    # 5. Configurar cámara, luces, render
    setup_isometric_camera()
    setup_lighting()
    setup_render()
    
    # 6. Renderizar
    print(f"\n  🎬 Renderizando...")
    bpy.context.scene.render.filepath = OUTPUT_FILE
    
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)
    
    bpy.ops.render.render(write_still=True)
    
    if os.path.isfile(OUTPUT_FILE):
        size_kb = os.path.getsize(OUTPUT_FILE) / 1024
        print(f"  ✅ Render guardado: {OUTPUT_FILE} ({size_kb:.1f} KB)")
    else:
        print(f"  ❌ Render no se generó")


if __name__ == "__main__":
    main()
