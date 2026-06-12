#!/usr/bin/env python3
"""
Blender 3D models for SIMMOON buildings (batch 2).
5 low-poly isometric: Oficina Minera, Laboratorio, Centro Medico, Terminal Espacial, Fabrica.
Run: blender.exe --background --python blender_render_buildings2.py
"""
import bpy
import mathutils
import os
from math import radians, cos, sin, tan
from pathlib import Path

OUTPUT_DIR = str(Path(__file__).parent / "blender_renders")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

def make_mat(name, color=(0.5,0.5,0.5), rough=0.7):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    out = nodes.new(type="ShaderNodeOutputMaterial")
    mat.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat

def setup_scene():
    cam_data = bpy.data.cameras.new("IsoCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 7.0
    cam = bpy.data.objects.new("IsoCam", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    CAM_DIST = 8.0
    CAM_AZIMUTH = radians(45)
    cam.location = (CAM_DIST * cos(CAM_AZIMUTH), CAM_DIST * sin(CAM_AZIMUTH), CAM_DIST * tan(radians(30)))
    direction = mathutils.Vector((0, 0, 0.5)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    bpy.context.collection.objects.link(sun)
    sun.data.energy = 5.0
    sun.location = (8, -4, 10)
    sun.rotation_euler = (radians(45), radians(30), radians(15))
    
    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", 'AREA'))
    bpy.context.collection.objects.link(fill)
    fill.data.energy = 80.0
    fill.data.size = 5.0
    fill.location = (-3, 5, 4)
    
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.render.resolution_x = 512
    bpy.context.scene.render.resolution_y = 512
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.cycles.samples = 64

def render_model(name):
    out = os.path.join(OUTPUT_DIR, f"{name}.png")
    bpy.context.scene.render.filepath = out
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)
    kb = os.path.getsize(out)/1024 if os.path.exists(out) else 0
    print(f"  [OK] {out} ({kb:.0f} KB)")

def box(name, loc, scale, mat_name, color, rough=0.5):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(make_mat(mat_name, color, rough))
    return obj

def cyl(name, loc, radius, depth, mat_name, color, rough=0.4):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc, vertices=16)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(make_mat(mat_name, color, rough))
    return obj


def build_oficina():
    """Mining office: L-shaped blocks + antenna + conveyor arm."""
    box("Off_Main", (0, 0, 0.35), (0.9, 0.6, 0.7), "OffBody", (0.65, 0.6, 0.55))
    box("Off_Wing", (-0.35, -0.4, 0.3), (0.5, 0.5, 0.6), "OffWing", (0.6, 0.55, 0.5))
    box("Off_Roof", (0, 0, 0.72), (0.85, 0.55, 0.08), "OffRoof", (0.45, 0.4, 0.38))
    box("Off_Antenna", (0.15, -0.1, 0.85), (0.06, 0.06, 0.25), "OffAnt", (0.7, 0.7, 0.75))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.5, location=(0.5, 0.2, 0.25))
    arm = bpy.context.active_object
    arm.name = "Off_Conveyor"
    arm.rotation_euler = (0, radians(30), 0)
    arm.data.materials.append(make_mat("OffConv", (0.5, 0.45, 0.4)))
    print("  Oficina Minera built")

def build_laboratorio():
    """Research lab: main cylinder + glass dome + satellite dish."""
    cyl("Lab_Main", (0, 0, 0.5), 0.8, 1.0, "LabBody", (0.7, 0.72, 0.75))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.85, location=(0, 0, 1.05))
    dome = bpy.context.active_object
    dome.name = "Lab_Dome"
    dome.scale = (1.0, 1.0, 0.5)
    dome.data.materials.append(make_mat("LabDome", (0.5, 0.7, 0.85), 0.15))
    box("Lab_Entry", (0, 0.65, 0.3), (0.4, 0.25, 0.6), "LabEntry", (0.55, 0.5, 0.45))
    cyl("Lab_DishBase", (0.3, -0.5, 0.7), 0.08, 0.4, "LabDishB", (0.6, 0.6, 0.65))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25, location=(0.3, -0.5, 0.95))
    dish = bpy.context.active_object
    dish.name = "Lab_Dish"
    dish.scale = (1.0, 1.0, 0.3)
    dish.data.materials.append(make_mat("LabDish", (0.8, 0.8, 0.85), 0.2))
    box("Lab_Panel", (-0.5, 0.1, 0.7), (0.15, 0.4, 0.25), "LabPanel", (0.2, 0.3, 0.5), 0.1)
    print("  Laboratorio built")

def build_centro_medico():
    """Medical center: main block + red cross + ambulance bay + helipad."""
    box("Med_Main", (0, 0, 0.4), (1.2, 0.7, 0.8), "MedBody", (0.9, 0.9, 0.88))
    box("Med_Roof", (0, 0, 0.82), (1.1, 0.6, 0.06), "MedRoof", (0.75, 0.75, 0.78))
    # Red cross on roof
    box("Med_CrossH", (0, 0, 0.9), (0.3, 0.08, 0.04), "MedCross", (0.9, 0.15, 0.15))
    box("Med_CrossV", (0, 0, 0.9), (0.08, 0.3, 0.04), "MedCrossV", (0.9, 0.15, 0.15))
    # Ambulance bay
    box("Med_Bay", (0.5, 0, 0.25), (0.5, 0.6, 0.5), "MedBay", (0.8, 0.82, 0.85))
    box("Med_BayRoof", (0.5, 0, 0.52), (0.45, 0.55, 0.05), "MedBayR", (0.7, 0.72, 0.75))
    # Helipad
    box("Med_Heli", (-0.5, 0, 0.05), (0.4, 0.4, 0.04), "MedHeli", (0.5, 0.5, 0.55))
    # Windows
    box("Med_Win1", (0, 0.36, 0.55), (0.5, 0.04, 0.25), "MedWin", (0.5, 0.7, 0.85), 0.1)
    box("Med_Win2", (0, -0.36, 0.55), (0.5, 0.04, 0.25), "MedWin2", (0.5, 0.7, 0.85), 0.1)
    print("  Centro Medico built")

def build_terminal():
    """Spaceport terminal: long hall + control tower + landing pad."""
    box("Ter_Hall", (0, 0, 0.5), (1.6, 0.7, 1.0), "TerBody", (0.7, 0.72, 0.78))
    box("Ter_Roof", (0, 0, 1.02), (1.5, 0.6, 0.06), "TerRoof", (0.55, 0.58, 0.62))
    # Control tower
    cyl("Ter_Tower", (0.65, 0, 0.9), 0.2, 0.9, "TerTower", (0.65, 0.68, 0.72))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, location=(0.65, 0, 1.4))
    tower_top = bpy.context.active_object
    tower_top.name = "Ter_TowerTop"
    tower_top.scale = (1.0, 1.0, 0.4)
    tower_top.data.materials.append(make_mat("TerTop", (0.4, 0.5, 0.6), 0.15))
    # Landing pads
    box("Ter_Pad1", (-0.5, 0.5, 0.05), (0.45, 0.45, 0.03), "TerPad", (0.4, 0.42, 0.45))
    box("Ter_Pad2", (-0.5, -0.5, 0.05), (0.45, 0.45, 0.03), "TerPad2", (0.4, 0.42, 0.45))
    # Antenna
    cyl("Ter_Ant", (0.3, 0.15, 0.85), 0.04, 0.5, "TerAnt", (0.75, 0.75, 0.8))
    print("  Terminal Espacial built")

def build_fabrica():
    """Manufacturing plant: large box + smokestacks + loading bay + pipes."""
    box("Fab_Main", (0, 0, 0.55), (1.3, 0.8, 1.1), "FabBody", (0.55, 0.52, 0.48))
    box("Fab_Roof", (0, 0, 1.12), (1.2, 0.7, 0.06), "FabRoof", (0.4, 0.38, 0.35))
    # Smokestacks
    cyl("Fab_Stack1", (-0.3, -0.2, 1.3), 0.08, 0.6, "FabStack", (0.45, 0.4, 0.38))
    cyl("Fab_Stack2", (0.1, 0.2, 1.4), 0.1, 0.7, "FabStack2", (0.48, 0.42, 0.4))
    # Loading bay
    box("Fab_Load", (0.55, 0, 0.3), (0.4, 0.6, 0.6), "FabLoad", (0.5, 0.48, 0.45))
    box("Fab_LoadRoof", (0.55, 0, 0.62), (0.35, 0.55, 0.05), "FabLoadR", (0.38, 0.35, 0.32))
    # Pipes
    cyl("Fab_Pipe1", (0.2, 0.3, 0.9), 0.04, 0.4, "FabPipe", (0.6, 0.55, 0.5))
    pipe1 = bpy.data.objects.get("Fab_Pipe1")
    if pipe1:
        pipe1.rotation_euler = (radians(90), 0, 0)
    cyl("Fab_Pipe2", (-0.2, -0.3, 0.85), 0.04, 0.35, "FabPipe2", (0.6, 0.55, 0.5))
    bpy.context.view_layer.update()
    bpy.data.objects["Fab_Pipe2"].rotation_euler = (0, radians(90), 0)
    # Warning light
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(0, 0.42, 1.2))
    light = bpy.context.active_object
    light.name = "Fab_Light"
    light.data.materials.append(make_mat("FabLight", (0.95, 0.25, 0.1), 0.1))
    print("  Fabrica built")


def main():
    print("=" * 50)
    print("  SIMMOON Blender Buildings v2")
    print("=" * 50)
    models = [
        ("biz_oficina_minera", build_oficina),
        ("biz_laboratorio", build_laboratorio),
        ("biz_centro_medico", build_centro_medico),
        ("biz_terminal_espacial", build_terminal),
        ("biz_fabrica", build_fabrica),
    ]
    for name, builder in models:
        clear_scene()
        setup_scene()
        builder()
        render_model(name)
    print(f"\nAll done: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
