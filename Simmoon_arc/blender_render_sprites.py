"""
blender_render_sprites.py — Genera 3 sprites low-poly isométricos con Blender

Conceptos del CreativoJuegos:
  1. Drone de Mantenimiento Adaptativo → characters
  2. Cultivo Bio-Luminescente → lunar_flora
  3. Sonocreador Resonante (Resonancia Estelar) → infrastructure

Ejecutar:
  blender --background --python blender_render_sprites.py
"""

import bpy
import os
import sys
from math import radians, pi

# ── Config ──────────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd(), 
                          "blender_renders")
os.makedirs(OUTPUT_DIR, exist_ok=True)

RENDER_SIZE = 512  # Alto y ancho del render (luego se escala a 64x64)
CAM_DIST = 8.0
CAM_ANGLE = radians(60)       # Ángulo de elevación (isométrico estándar)
CAM_AZIMUTH = radians(45)     # Rotación horizontal para vista 3/4

# ── Limpiar escena ──────────────────────────────────────────────────────
def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # Limpiar materiales y mallas sobrantes (list() evita bug de iteración)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

# ── Configurar cámara isométrica ────────────────────────────────────────
def setup_isometric_camera():
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.name = "IsoCamera"
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 6.0
    
    # Posición isométrica (45° azimuth, ~35° elevation para 2:1 dimetric)
    x = CAM_DIST * 0.707  # cos(45°)
    y = CAM_DIST * 0.707  # sin(45°)  
    z = CAM_DIST * 0.577  # tan(30°) para ~2:1 ratio
    cam.location = (x, y, z)
    cam.rotation_euler = (radians(60), 0, radians(45))
    
    bpy.context.scene.camera = cam
    return cam

# ── Configurar render ───────────────────────────────────────────────────
def setup_render():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.render.resolution_x = RENDER_SIZE
    scene.render.resolution_y = RENDER_SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    
    # Cycles: pocas samples, sin denoising para aspecto "flat/pixel"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    
    # Iluminación ambiente limpia
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Strength'].default_value = 1.5
        bg.inputs['Color'].default_value = (0.85, 0.88, 0.92, 1.0)

# ── Material flat (cel-shaded) ──────────────────────────────────────────
def make_flat_material(name, color_rgb, roughness=0.9):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (*color_rgb, 1.0)
        bsdf.inputs['Roughness'].default_value = roughness
        bsdf.inputs['Specular IOR Level'].default_value = 0.0
    return mat

# ── Crear malla con material ────────────────────────────────────────────
def create_mesh_object(name, verts, faces, material, location=(0, 0, 0)):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    
    if mesh.materials:
        mesh.materials[0] = material
    else:
        mesh.materials.append(material)
    
    obj.location = location
    return obj

# ── Luz solar direccional ───────────────────────────────────────────────
def add_sun_light():
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
    sun = bpy.context.object
    sun.data.energy = 4.0
    sun.data.angle = 0.02  # Sombras duras → estilo pixel
    sun.rotation_euler = (radians(50), 0, radians(-30))
    return sun

# ══════════════════════════════════════════════════════════════════════════
#  SPRITE 1: Drone de Mantenimiento (characters)
# ══════════════════════════════════════════════════════════════════════════
def build_maintenance_drone():
    """Construye un drone flotante low-poly estilo WALL-E/repair bot."""
    mat_body = make_flat_material("Drone_Body", (0.9, 0.85, 0.75))  # Crema/beige
    mat_metal = make_flat_material("Drone_Metal", (0.5, 0.5, 0.55))  # Gris metal
    mat_glow = make_flat_material("Drone_Glow", (0.2, 0.7, 1.0))     # Cyan glow
    mat_lens = make_flat_material("Drone_Lens", (0.1, 0.1, 0.15))    # Negro lente

    # Cuerpo principal (cilindro achatado ≈ octágono)
    # Usamos un cilindro de 8 lados
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.6, depth=0.35, 
                                         location=(0, 0, 0.8))
    body = bpy.context.object
    body.name = "Drone_Body"
    body.data.materials.append(mat_body)
    
    # "Ojo" / lente frontal
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.2, depth=0.15,
                                         location=(0.35, 0, 0.95))
    eye = bpy.context.object
    eye.name = "Drone_Eye"
    eye.data.materials.append(mat_lens)
    
    # Brillo del ojo
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.08, depth=0.05,
                                         location=(0.4, 0.03, 1.0))
    glow_eye = bpy.context.object
    glow_eye.name = "Drone_GlowEye"
    glow_eye.data.materials.append(mat_glow)
    
    # Antenas
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.03, depth=0.5,
                                         location=(0, 0.2, 1.1))
    ant1 = bpy.context.object
    ant1.name = "Drone_Antenna1"
    ant1.data.materials.append(mat_metal)
    
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.03, depth=0.35,
                                         location=(0.15, -0.15, 1.05))
    ant2 = bpy.context.object
    ant2.name = "Drone_Antenna2"
    ant2.data.materials.append(mat_metal)
    
    # Brazos/herramientas laterales
    for side in [-1, 1]:
        # Brazo
        bpy.ops.mesh.primitive_cube_add(size=0.08, 
                                         location=(side * 0.65, 0, 0.75))
        bpy.ops.transform.resize(value=(0.5, 0.5, 1.5))
        arm = bpy.context.object
        arm.name = f"Drone_Arm_{side}"
        arm.data.materials.append(mat_metal)
        
        # Garra
        bpy.ops.mesh.primitive_cube_add(size=0.1,
                                         location=(side * 0.68, 0, 0.5))
        bpy.ops.transform.resize(value=(1, 0.3, 0.5))
        claw = bpy.context.object
        claw.name = f"Drone_Claw_{side}"
        claw.data.materials.append(mat_body)
    
    return body

# ══════════════════════════════════════════════════════════════════════════
#  SPRITE 2: Planta Bio-Luminescente (lunar_flora)
# ══════════════════════════════════════════════════════════════════════════
def build_bioluminescent_plant():
    """Construye una planta alienígena con bulbos brillantes."""
    mat_stem = make_flat_material("Plant_Stem", (0.25, 0.55, 0.25))      # Verde tallo
    mat_bulb = make_flat_material("Plant_Bulb", (0.5, 0.2, 0.85))        # Púrpura bulbo
    mat_glow = make_flat_material("Plant_Glow", (0.4, 0.9, 0.9))         # Cyan glow
    mat_base = make_flat_material("Plant_Base", (0.4, 0.35, 0.3))        # Tierra/roca

    # Base de roca
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.5, depth=0.2,
                                         location=(0, 0, 0.1))
    base = bpy.context.object
    base.name = "Plant_Base"
    base.data.materials.append(mat_base)
    
    # 3 tallos en diferentes alturas
    stems = []
    for i, (h, angle, radius) in enumerate([
        (1.2, 0, 0.04), (0.9, 2.1, 0.035), (1.05, 4.2, 0.035)
    ]):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=radius, depth=h,
                                             location=(0.1 * (i-1), 0.05 * i, 0.2 + h/2))
        stem = bpy.context.object
        stem.name = f"Plant_Stem_{i}"
        stem.data.materials.append(mat_stem)
        # Curvar ligeramente
        stem.rotation_euler = (radians(5 * (i-1)), radians(8), 0)
        stems.append(stem)
    
    # Bulbos brillantes en las puntas
    for i, stem in enumerate(stems):
        h = float(stem.location.z) * 2 - 0.2
        x = float(stem.location.x)
        y = float(stem.location.y)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, 
                                              radius=0.12, location=(x, y, h + 0.05))
        bulb = bpy.context.object
        bulb.name = f"Plant_Bulb_{i}"
        bulb.data.materials.append(mat_bulb)
        
        # Glow interior más pequeño
        bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4,
                                              radius=0.06, location=(x, y, h + 0.05))
        glow = bpy.context.object
        glow.name = f"Plant_Glow_{i}"
        glow.data.materials.append(mat_glow)
    
    return base

# ══════════════════════════════════════════════════════════════════════════
#  SPRITE 3: Sonocreador Resonante (infrastructure)
# ══════════════════════════════════════════════════════════════════════════
def build_sonic_extractor():
    """Construye un extractor/minero sónico con ondas concéntricas."""
    mat_body = make_flat_material("Extractor_Body", (0.65, 0.6, 0.55))    # Gris cálido
    mat_core = make_flat_material("Extractor_Core", (0.9, 0.55, 0.1))     # Ámbar/naranja
    mat_ring = make_flat_material("Extractor_Ring", (0.3, 0.65, 0.85))    # Azul acero
    mat_base = make_flat_material("Extractor_Base", (0.35, 0.33, 0.3))    # Base oscura
    mat_wave = make_flat_material("Extractor_Wave", (0.2, 0.8, 0.95))     # Cyan onda

    # Base octagonal
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.8, depth=0.15,
                                         location=(0, 0, 0.08))
    base = bpy.context.object
    base.name = "Extractor_Base"
    base.data.materials.append(mat_base)
    
    # Cuerpo principal
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.5, depth=0.7,
                                         location=(0, 0, 0.5))
    body = bpy.context.object
    body.name = "Extractor_Body"
    body.data.materials.append(mat_body)
    
    # Núcleo brillante en el centro
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.2, depth=0.5,
                                         location=(0, 0, 0.65))
    core = bpy.context.object
    core.name = "Extractor_Core"
    core.data.materials.append(mat_core)
    
    # Anillos concéntricos (ondas sónicas) en diferentes alturas
    for z_offset, ring_r, ring_t in [
        (0.3, 0.65, 0.04), (0.45, 0.75, 0.03), (0.6, 0.85, 0.02)
    ]:
        bpy.ops.mesh.primitive_torus_add(
            major_radius=ring_r, minor_radius=ring_t,
            location=(0, 0, z_offset),
            major_segments=16, minor_segments=6
        )
        ring = bpy.context.object
        ring.name = f"Extractor_Ring_{z_offset}"
        ring.data.materials.append(mat_wave if ring_r > 0.7 else mat_ring)
    
    # Antena/sonda en la cima
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.05, depth=0.4,
                                         location=(0, 0, 1.05))
    antenna = bpy.context.object
    antenna.name = "Extractor_Antenna"
    antenna.data.materials.append(mat_ring)
    
    # Bola en la punta
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, radius=0.08,
                                          location=(0, 0, 1.28))
    tip = bpy.context.object
    tip.name = "Extractor_Tip"
    tip.data.materials.append(mat_core)
    
    return base

# ══════════════════════════════════════════════════════════════════════════
#  RENDER & SAVE
# ══════════════════════════════════════════════════════════════════════════

def render_sprite(name, output_prefix):
    """Renderiza la escena actual y guarda el PNG."""
    filepath = os.path.join(OUTPUT_DIR, f"{output_prefix}.png")
    bpy.context.scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    size_kb = os.path.getsize(filepath) / 1024 if os.path.exists(filepath) else 0
    print(f"  ✅ {name}: {filepath} ({size_kb:.1f} KB)")
    return filepath

def build_and_render_all():
    """Construye y renderiza los 3 sprites secuencialmente."""
    print(f"\n{'='*60}")
    print(f"  🧊 BLENDER — Generando 3 sprites low-poly isométricos")
    print(f"  Basado en conceptos del CreativoJuegos")
    print(f"  Salida: {OUTPUT_DIR}")
    print(f"{'='*60}\n")
    
    # Setup compartido
    setup_render()
    cam = setup_isometric_camera()
    sun = add_sun_light()
    
    # ── Sprite 1: Drone (characters) ──
    clear_scene()
    setup_render()
    setup_isometric_camera()
    add_sun_light()
    build_maintenance_drone()
    render_sprite("Drone de Mantenimiento (characters)", "char_drone_maintenance")
    
    # ── Sprite 2: Planta (lunar_flora) ──
    clear_scene()
    setup_render()
    setup_isometric_camera()
    add_sun_light()
    build_bioluminescent_plant()
    render_sprite("Planta Bio-Luminescente (lunar_flora)", "flora_bioluminescent")
    
    # ── Sprite 3: Extractor (infrastructure) ──
    clear_scene()
    setup_render()
    setup_isometric_camera()
    add_sun_light()
    build_sonic_extractor()
    render_sprite("Sonocreador Resonante (infrastructure)", "infra_sonic_extractor")
    
    print(f"\n{'='*60}")
    print(f"  ✅ 3 sprites generados exitosamente")
    print(f"  📁 {OUTPUT_DIR}")
    print(f"{'='*60}")
    return True

# ── Entry point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    build_and_render_all()
