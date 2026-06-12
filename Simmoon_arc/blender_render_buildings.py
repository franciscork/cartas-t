#!/usr/bin/env python3
"""
Blender 3D models for SIMMOON buildings.
4 low-poly isometric models: Hotel Lunar, Albergue Básico, Restaurante, Tienda Lunar.
Run: blender.exe --background --python blender_render_buildings.py
"""
import bpy
import mathutils
import os
from math import radians, cos, sin, tan
from pathlib import Path

OUTPUT_DIR = str(Path(__file__).parent / "blender_renders")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Scene setup ──────────────────────────────────────────────────────────

def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

def make_flat_material(name, color=(0.5, 0.5, 0.5), roughness=0.7):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    output = nodes.new(type="ShaderNodeOutputMaterial")
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    return mat

def setup_scene():
    # Camera
    cam_data = bpy.data.cameras.new("IsoCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 6.0
    cam = bpy.data.objects.new("IsoCam", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    
    CAM_DIST = 8.0
    CAM_AZIMUTH = radians(45)
    cam.location = (CAM_DIST * cos(CAM_AZIMUTH), CAM_DIST * sin(CAM_AZIMUTH), CAM_DIST * tan(radians(30)))
    direction = mathutils.Vector((0, 0, 0.5)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    
    # Sun light
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 5.0
    sun = bpy.data.objects.new("Sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.location = (8, -4, 10)
    sun.rotation_euler = (radians(45), radians(30), radians(15))
    
    # Fill light
    fill_data = bpy.data.lights.new("Fill", 'AREA')
    fill_data.energy = 80.0
    fill_data.size = 5.0
    fill = bpy.data.objects.new("Fill", fill_data)
    bpy.context.collection.objects.link(fill)
    fill.location = (-3, 5, 4)
    
    # Render settings
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.render.resolution_x = 512
    bpy.context.scene.render.resolution_y = 512
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.cycles.device = 'GPU'
    bpy.context.scene.view_layers[0].use_pass_object_index = False

def render_model(name):
    out = os.path.join(OUTPUT_DIR, f"{name}.png")
    bpy.context.scene.render.filepath = out
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)
    size_kb = os.path.getsize(out) / 1024 if os.path.exists(out) else 0
    print(f"  [OK] {out} ({size_kb:.0f} KB)")
    return out


# ── Building 1: Hotel Lunar ────────────────────────────────────────────────

def build_hotel():
    """Low-poly lunar hotel: main cylinder dome + entry arch + sign."""
    # Main dome (cylinder)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=1.0, depth=1.2, location=(0, 0, 0.6))
    body = bpy.context.active_object
    body.name = "Hotel_Body"
    body.data.materials.append(make_flat_material("HotelBody", (0.65, 0.55, 0.45), 0.5))
    
    # Dome roof (sphere cut)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1.05, location=(0, 0, 1.25))
    dome = bpy.context.active_object
    dome.name = "Hotel_Dome"
    dome.data.materials.append(make_flat_material("HotelDome", (0.4, 0.6, 0.75), 0.3))
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bisect(plane_co=(0, 0, 1.2), plane_no=(0, 0, -1), clear_inner=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Entry arch
    bpy.ops.mesh.primitive_cube_add(size=0.4, location=(0, 0.85, 0.6))
    entry = bpy.context.active_object
    entry.name = "Hotel_Entry"
    bpy.ops.transform.resize(value=(0.8, 0.3, 1.4))
    entry.data.materials.append(make_flat_material("HotelEntry", (0.5, 0.45, 0.4), 0.4))
    
    # Sign board
    bpy.ops.mesh.primitive_cube_add(size=0.2, location=(0, 1.05, 1.0))
    sign = bpy.context.active_object
    sign.name = "Hotel_Sign"
    bpy.ops.transform.resize(value=(1.5, 0.2, 0.8))
    sign.data.materials.append(make_flat_material("HotelSign", (0.9, 0.3, 0.2), 0.3))
    
    # Accent lights
    for angle in [0, 90, 180, 270]:
        rad = radians(angle)
        x = 1.05 * cos(rad)
        y = 1.05 * sin(rad)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(x, y, 1.15))
        light = bpy.context.active_object
        light.name = f"Hotel_Light_{angle}"
        light.data.materials.append(make_flat_material("HotelLight", (1.0, 0.9, 0.3), 0.2))
    
    print("  Hotel Lunar built")


# ── Building 2: Albergue Básico ────────────────────────────────────────────

def build_albergue():
    """Basic habitat module: rectangular box + airlock + solar panel."""
    # Main box
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.3))
    body = bpy.context.active_object
    body.name = "Albergue_Body"
    bpy.ops.transform.resize(value=(1.2, 0.7, 0.6))
    body.data.materials.append(make_flat_material("AlbBody", (0.7, 0.7, 0.72), 0.5))
    
    # Roof
    bpy.ops.mesh.primitive_cube_add(size=0.8, location=(0, 0, 0.65))
    roof = bpy.context.active_object
    roof.name = "Albergue_Roof"
    bpy.ops.transform.resize(value=(1.1, 0.6, 0.15))
    roof.data.materials.append(make_flat_material("AlbRoof", (0.55, 0.55, 0.6), 0.4))
    
    # Airlock (cylinder on side)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=0.4, location=(0.5, 0, 0.3))
    airlock = bpy.context.active_object
    airlock.name = "Albergue_Airlock"
    bpy.ops.transform.rotate(value=radians(90), orient_axis='X')
    airlock.data.materials.append(make_flat_material("AlbAirlock", (0.6, 0.6, 0.65), 0.3))
    
    # Solar panel on roof
    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(-0.15, 0.1, 0.78))
    panel = bpy.context.active_object
    panel.name = "Albergue_Panel"
    bpy.ops.transform.resize(value=(1.5, 1.2, 0.08))
    bpy.ops.transform.rotate(value=radians(15), orient_axis='X')
    panel.data.materials.append(make_flat_material("AlbPanel", (0.15, 0.25, 0.45), 0.2))
    
    # Window
    bpy.ops.mesh.primitive_cube_add(size=0.15, location=(0, 0.35, 0.5))
    window = bpy.context.active_object
    window.name = "Albergue_Window"
    bpy.ops.transform.resize(value=(1.5, 0.3, 0.6))
    window.data.materials.append(make_flat_material("AlbWindow", (0.6, 0.85, 1.0), 0.15))
    
    print("  Albergue Básico built")


# ── Building 3: Restaurante Lunar ──────────────────────────────────────────

def build_restaurante():
    """Lunar restaurant: main hall + kitchen cylinder + outdoor tables."""
    # Main hall
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.35))
    hall = bpy.context.active_object
    hall.name = "Rest_Hall"
    bpy.ops.transform.resize(value=(1.3, 0.8, 0.7))
    hall.data.materials.append(make_flat_material("RestHall", (0.8, 0.6, 0.4), 0.5))
    
    # Kitchen (cylinder extension)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.35, depth=0.6, location=(0.7, 0, 0.3))
    kitchen = bpy.context.active_object
    kitchen.name = "Rest_Kitchen"
    kitchen.data.materials.append(make_flat_material("RestKitchen", (0.7, 0.5, 0.35), 0.4))
    
    # Roof canopy
    bpy.ops.mesh.primitive_cube_add(size=0.8, location=(0, -0.1, 0.72))
    canopy = bpy.context.active_object
    canopy.name = "Rest_Canopy"
    bpy.ops.transform.resize(value=(1.1, 0.7, 0.1))
    canopy.data.materials.append(make_flat_material("RestCanopy", (0.9, 0.2, 0.15), 0.3))
    
    # Outdoor tables (4 small cubes)
    positions = [(-0.3, -0.55, 0.15), (0.1, -0.55, 0.15), (-0.1, 0.55, 0.15), (0.3, 0.55, 0.15)]
    for i, pos in enumerate(positions):
        bpy.ops.mesh.primitive_cube_add(size=0.15, location=pos)
        table = bpy.context.active_object
        table.name = f"Rest_Table_{i}"
        bpy.ops.transform.resize(value=(0.8, 0.8, 0.5))
        table.data.materials.append(make_flat_material("RestTable", (0.6, 0.5, 0.4), 0.3))
    
    # Sign
    bpy.ops.mesh.primitive_cube_add(size=0.15, location=(0, 0.55, 0.65))
    sign = bpy.context.active_object
    sign.name = "Rest_Sign"
    bpy.ops.transform.resize(value=(2.0, 0.15, 0.7))
    sign.data.materials.append(make_flat_material("RestSign", (0.9, 0.7, 0.2), 0.2))
    
    print("  Restaurante Lunar built")


# ── Building 4: Tienda Lunar ───────────────────────────────────────────────

def build_tienda():
    """Lunar shop: simple box + display window + awning + chimney."""
    # Main box
    bpy.ops.mesh.primitive_cube_add(size=0.8, location=(0, 0, 0.3))
    body = bpy.context.active_object
    body.name = "Tienda_Body"
    bpy.ops.transform.resize(value=(1.0, 0.7, 0.8))
    body.data.materials.append(make_flat_material("TiendaBody", (0.75, 0.7, 0.6), 0.5))
    
    # Roof
    bpy.ops.mesh.primitive_cube_add(size=0.6, location=(0, 0, 0.72))
    roof = bpy.context.active_object
    roof.name = "Tienda_Roof"
    bpy.ops.transform.resize(value=(1.0, 0.65, 0.1))
    roof.data.materials.append(make_flat_material("TiendaRoof", (0.5, 0.45, 0.4), 0.4))
    
    # Display window
    bpy.ops.mesh.primitive_cube_add(size=0.2, location=(0, 0.35, 0.4))
    window = bpy.context.active_object
    window.name = "Tienda_Window"
    bpy.ops.transform.resize(value=(2.0, 0.15, 0.8))
    window.data.materials.append(make_flat_material("TiendaWin", (0.5, 0.8, 0.9), 0.1))
    
    # Awning
    bpy.ops.mesh.primitive_cube_add(size=0.2, location=(0, 0.42, 0.62))
    awning = bpy.context.active_object
    awning.name = "Tienda_Awning"
    bpy.ops.transform.resize(value=(2.5, 0.2, 0.1))
    bpy.ops.transform.rotate(value=radians(10), orient_axis='X')
    awning.data.materials.append(make_flat_material("TiendaAwning", (0.85, 0.25, 0.2), 0.3))
    
    # Chimney
    bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.3, location=(-0.2, -0.2, 0.8))
    chimney = bpy.context.active_object
    chimney.name = "Tienda_Chimney"
    chimney.data.materials.append(make_flat_material("TiendaChimney", (0.4, 0.35, 0.3), 0.5))
    
    # Entrance step
    bpy.ops.mesh.primitive_cube_add(size=0.1, location=(0, 0.4, 0.08))
    step = bpy.context.active_object
    step.name = "Tienda_Step"
    bpy.ops.transform.resize(value=(2.5, 0.5, 0.3))
    step.data.materials.append(make_flat_material("TiendaStep", (0.55, 0.5, 0.45), 0.6))
    
    print("  Tienda Lunar built")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  SIMMOON Blender Buildings v1")
    print("=" * 50)
    
    models = [
        ("biz_hotel_lunar", build_hotel),
        ("hou_albergue_basico", build_albergue),
        ("biz_restaurante_lunar", build_restaurante),
        ("biz_tienda_lunar", build_tienda),
    ]
    
    for name, builder in models:
        clear_scene()
        setup_scene()
        builder()
        render_model(name)
    
    print(f"\nAll renders saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
