"""
blender_render_2sprites.py — Genera 2 sprites adicionales: torre de comunicaciones + rover minero

Ejecutar:
  blender --background --python blender_render_2sprites.py
"""

import bpy
import mathutils
import os
from math import radians, cos, sin, tan

OUTPUT_DIR = os.path.join(os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd(), "blender_renders")
os.makedirs(OUTPUT_DIR, exist_ok=True)

RENDER_SIZE = 512
CAM_DISTANCE = 8.0
CAM_AZIMUTH = radians(45)

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

def make_flat_material(name, color_rgb):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (*color_rgb, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.85
        bsdf.inputs['Specular IOR Level'].default_value = 0.05
    return mat

def setup_scene():
    # Camera
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.name = "IsoCam"
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 4.5
    cam.location = (CAM_DISTANCE * cos(CAM_AZIMUTH), CAM_DISTANCE * sin(CAM_AZIMUTH), CAM_DISTANCE * tan(radians(30)))
    direction = mathutils.Vector((0, 0, 0.5)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam

    # Sun
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
    bpy.context.object.data.energy = 3.5
    bpy.context.object.data.angle = 0.015

    # Fill
    bpy.ops.object.light_add(type='SUN', location=(-3, 2, 4))
    bpy.context.object.data.energy = 1.2

    # Render settings
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.render.resolution_x = RENDER_SIZE
    scene.render.resolution_y = RENDER_SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.cycles.samples = 32
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Strength'].default_value = 1.8
        bg.inputs['Color'].default_value = (0.88, 0.90, 0.94, 1.0)

def render_sprite(name, prefix):
    path = os.path.join(OUTPUT_DIR, f"{prefix}.png")
    bpy.context.scene.render.filepath = path
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)
    kb = os.path.getsize(path) / 1024
    print(f"  OK {name}: {path} ({kb:.1f} KB)")

# =====================================================================
# SPRITE 1: Torre de Comunicaciones (infrastructure)
# =====================================================================
def build_comm_tower():
    mat_tower = make_flat_material("Tower_Body", (0.55, 0.55, 0.6))
    mat_dish = make_flat_material("Tower_Dish", (0.9, 0.9, 0.95))
    mat_red = make_flat_material("Tower_Red", (0.9, 0.2, 0.15))
    mat_base = make_flat_material("Tower_Base", (0.35, 0.33, 0.3))

    # Base octagonal
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.5, depth=0.2, location=(0, 0, 0.1))
    bpy.context.object.data.materials.append(mat_base)

    # Torre principal (cono truncado con cilindros apilados)
    for i, (h, r, z) in enumerate([
        (0.6, 0.12, 0.45), (0.5, 0.09, 0.95), (0.4, 0.06, 1.35), (0.3, 0.04, 1.65)
    ]):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=r, depth=h, location=(0, 0, z))
        bpy.context.object.data.materials.append(mat_tower)

    # Plato satelital en la cima
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.18, location=(0.15, 0, 1.85))
    bpy.ops.transform.resize(value=(0.6, 0.6, 0.25))
    bpy.context.object.data.materials.append(mat_dish)

    # Antena vertical
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.02, depth=0.3, location=(0, 0, 2.05))
    bpy.context.object.data.materials.append(mat_red)

    # Luces de advertencia
    for z in [0.5, 1.05, 1.55]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4, radius=0.04, location=(0, 0.08, z))
        bpy.context.object.data.materials.append(mat_red)

    # Plato secundario lateral
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, radius=0.1, location=(-0.2, 0, 1.2))
    bpy.ops.transform.resize(value=(0.5, 0.5, 0.2))
    bpy.context.object.data.materials.append(mat_dish)

# =====================================================================
# SPRITE 2: Rover Minero (vehicles)
# =====================================================================
def build_mining_rover():
    mat_body = make_flat_material("Rover_Body", (0.85, 0.6, 0.2))
    mat_wheel = make_flat_material("Rover_Wheel", (0.2, 0.2, 0.22))
    mat_glass = make_flat_material("Rover_Glass", (0.3, 0.6, 0.85))
    mat_arm = make_flat_material("Rover_Arm", (0.65, 0.65, 0.3))
    mat_bucket = make_flat_material("Rover_Bucket", (0.75, 0.55, 0.15))

    # Chasis
    bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, 0.35))
    bpy.ops.transform.resize(value=(1.5, 0.8, 0.6))
    bpy.context.object.data.materials.append(mat_body)

    # Cabina
    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(-0.35, 0, 0.65))
    bpy.ops.transform.resize(value=(0.8, 0.55, 0.5))
    bpy.context.object.data.materials.append(mat_glass)

    # Ruedas (6 ruedas estilo rover)
    for x in [-0.5, 0, 0.5]:
        for y in [-0.45, 0.45]:
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.18, depth=0.12, location=(x, y, 0.18))
            bpy.ops.transform.rotate(value=radians(90), orient_axis='Y')
            bpy.context.object.data.materials.append(mat_wheel)

    # Brazo extractor
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.06, depth=0.5, location=(0.5, 0, 0.55))
    bpy.ops.transform.rotate(value=radians(-30), orient_axis='Y')
    bpy.context.object.data.materials.append(mat_arm)

    # Cuchara/pala
    bpy.ops.mesh.primitive_cube_add(size=0.15, location=(0.65, 0, 0.35))
    bpy.ops.transform.resize(value=(1.2, 0.6, 0.4))
    bpy.context.object.data.materials.append(mat_bucket)

    # Antena GPS
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.025, depth=0.2, location=(-0.25, 0.1, 0.8))
    bpy.context.object.data.materials.append(mat_arm)

    # Bola GPS
    bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4, radius=0.04, location=(-0.25, 0.1, 0.93))
    bpy.context.object.data.materials.append(mat_glass)

# =====================================================================
# MAIN
# =====================================================================
print("="*60)
print("  BLENDER - 2 sprites: Comms Tower + Mining Rover")
print("="*60)

clear_scene()
setup_scene()
build_comm_tower()
render_sprite("Torre de Comunicaciones (infrastructure)", "infra_comm_tower")

clear_scene()
setup_scene()
build_mining_rover()
render_sprite("Rover Minero (vehicles)", "veh_mining_rover")

print("="*60)
print("  2 sprites generados en:", OUTPUT_DIR)
print("="*60)
