#!/usr/bin/env python3
"""
Blender 3D models for SIMMOON buildings (batch 5).
5 low-poly isometric: Parque Recreativo, Gestion Residuos, Estacion Bomberos,
Laboratorio Helio-3, Puerto Exportacion.
Run: blender.exe --background --python blender_render_buildings5.py
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


def make_mat(name, color=(0.5, 0.5, 0.5), rough=0.7):
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
    kb = os.path.getsize(out) / 1024 if os.path.exists(out) else 0
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


def build_parque():
    """Parque Recreativo: dome + trees + pond + paths + benches."""
    # Main dome
    box("Par_Base", (0, 0, 0.15), (0.9, 0.7, 0.3), "ParBase", (0.55, 0.58, 0.6))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.7, location=(0, 0, 0.5))
    dome = bpy.context.active_object
    dome.name = "Par_Dome"
    dome.scale = (0.9, 0.7, 0.35)
    dome.data.materials.append(make_mat("ParDome", (0.5, 0.75, 0.85), 0.12))
    # Trees (cones)
    for i, (x, y) in enumerate([(-0.25, 0.0), (0.2, -0.1), (0.0, 0.2), (-0.15, -0.2)]):
        cyl(f"Par_Trunk{i}", (x, y, 0.3), 0.03, 0.25, "ParTrunk", (0.4, 0.3, 0.2))
        cyl(f"Par_Tree{i}", (x, y, 0.5), 0.1, 0.25, "ParTree", (0.15, 0.55, 0.2), 0.5)
    # Pond
    box("Par_Pond", (0.3, 0.2, 0.16), (0.2, 0.15, 0.02), "ParPond", (0.3, 0.55, 0.7), 0.05)
    # Paths
    box("Par_Path1", (-0.1, -0.25, 0.05), (0.5, 0.06, 0.02), "ParPath", (0.75, 0.7, 0.6))
    box("Par_Path2", (-0.25, 0.0, 0.05), (0.06, 0.4, 0.02), "ParPath2", (0.75, 0.7, 0.6))
    # Bench
    box("Par_Bench", (0.1, -0.3, 0.15), (0.15, 0.04, 0.08), "ParBench", (0.5, 0.35, 0.25))
    print("  Parque Recreativo built")


def build_residuos():
    """Gestion de Residuos: plant + conveyor + sorting + compactor + chimney."""
    # Main plant
    box("Res_Body", (0, 0, 0.4), (0.9, 0.55, 0.8), "ResBody", (0.55, 0.58, 0.6))
    box("Res_Roof", (0, 0, 0.82), (0.85, 0.5, 0.05), "ResRoof", (0.45, 0.48, 0.5))
    # Chimney
    cyl("Res_Chimney", (0.25, -0.1, 1.0), 0.06, 0.5, "ResChim", (0.45, 0.42, 0.4))
    # Conveyor belt
    box("Res_Conv", (-0.45, -0.3, 0.2), (0.4, 0.06, 0.08), "ResConv", (0.4, 0.38, 0.35))
    for i, x in enumerate([-0.55, -0.45, -0.35]):
        cyl(f"Res_Roll{i}", (x, -0.3, 0.24), 0.03, 0.08, "ResRoll", (0.35, 0.33, 0.3))
        r = bpy.data.objects.get(f"Res_Roll{i}")
        if r:
            r.rotation_euler = (radians(90), 0, 0)
    # Sorting bins
    for i, (x, y) in enumerate([(-0.25, 0.3), (0.0, 0.3), (0.25, 0.3)]):
        box(f"Res_Bin{i}", (x, y, 0.15), (0.1, 0.1, 0.3), f"ResBin{i}", (0.5, 0.6, 0.65), 0.3)
    # Compactor
    box("Res_Comp", (0.35, 0.05, 0.25), (0.2, 0.2, 0.5), "ResComp", (0.6, 0.55, 0.5))
    print("  Gestion de Residuos built")


def build_bomberos():
    """Estacion de Bomberos: station + garage + siren tower + bay."""
    # Main station
    box("Bom_Body", (0, 0, 0.4), (0.8, 0.55, 0.8), "BomBody", (0.85, 0.3, 0.2))
    box("Bom_Roof", (0, 0, 0.82), (0.75, 0.5, 0.05), "BomRoof", (0.7, 0.22, 0.15))
    # Garage door
    box("Bom_Door", (0.35, 0, 0.35), (0.25, 0.04, 0.55), "BomDoor", (0.3, 0.32, 0.35), 0.2)
    # Siren tower
    cyl("Bom_Tower", (-0.3, 0.1, 0.65), 0.06, 0.5, "BomTower", (0.85, 0.3, 0.2))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(-0.3, 0.1, 0.93))
    siren = bpy.context.active_object
    siren.name = "Bom_Siren"
    siren.data.materials.append(make_mat("BomSiren", (0.95, 0.2, 0.1), 0.1))
    # Fire truck in bay
    box("Bom_Truck", (0.35, 0, 0.2), (0.2, 0.12, 0.2), "BomTruck", (0.9, 0.1, 0.1))
    # Truck ladder
    box("Bom_Ladder", (0.45, 0, 0.35), (0.03, 0.03, 0.3), "BomLadder", (0.7, 0.7, 0.75))
    # Windows
    box("Bom_Win", (-0.1, 0.3, 0.5), (0.3, 0.03, 0.2), "BomWin", (0.5, 0.7, 0.85), 0.1)
    print("  Estacion de Bomberos built")


def build_helio3():
    """Laboratorio Helio-3: facility + cryo tanks + chamber + cooling towers."""
    # Main facility
    box("He3_Body", (0, 0, 0.45), (0.85, 0.6, 0.9), "He3Body", (0.78, 0.8, 0.85))
    box("He3_Roof", (0, 0, 0.92), (0.8, 0.55, 0.05), "He3Roof", (0.65, 0.68, 0.72))
    # Cryo storage tanks
    for i, (x, y) in enumerate([(-0.3, 0.25), (0.15, 0.3)]):
        cyl(f"He3_Tank{i}", (x, y, 0.2), 0.07, 0.35, f"He3Tank{i}", (0.6, 0.7, 0.8), 0.15)
    # Processing chamber (sphere)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(0.3, -0.2, 0.35))
    chamber = bpy.context.active_object
    chamber.name = "He3_Chamber"
    chamber.data.materials.append(make_mat("He3Chamber", (0.7, 0.75, 0.8), 0.1))
    # Cooling towers
    for i, x in enumerate([-0.3, -0.1]):
        cyl(f"He3_Cool{i}", (x, -0.2, 0.3), 0.06, 0.45, f"He3Cool{i}", (0.55, 0.6, 0.65))
        # Tower top rim
        bpy.ops.mesh.primitive_torus_add(major_radius=0.065, minor_radius=0.01, location=(x, -0.2, 0.54))
        rim = bpy.context.active_object
        rim.name = f"He3_CoolRim{i}"
        rim.data.materials.append(make_mat(f"He3Rim{i}", (0.5, 0.55, 0.6)))
    # Connection pipes
    cyl("He3_Pipe1", (0.0, 0.1, 0.35), 0.02, 0.5, "He3Pipe", (0.5, 0.6, 0.7))
    p = bpy.data.objects.get("He3_Pipe1")
    if p:
        p.rotation_euler = (0, radians(60), 0)
    # Warning stripes
    box("He3_Stripe", (0, 0.32, 0.08), (0.7, 0.02, 0.02), "He3Stripe", (0.9, 0.85, 0.1))
    print("  Laboratorio Helio-3 built")


def build_puerto_export():
    """Puerto de Exportacion: launch pad + crane + silos + control tower."""
    # Launch pad platform
    box("Exp_Pad", (0, 0, 0.1), (0.9, 0.6, 0.2), "ExpPad", (0.45, 0.48, 0.5))
    # Pad markings
    box("Exp_Mark", (0, 0, 0.22), (0.6, 0.35, 0.02), "ExpMark", (0.35, 0.38, 0.4))
    # Cargo crane
    cyl("Exp_CranePole", (0.35, -0.2, 0.3), 0.04, 0.6, "ExpCrane", (0.9, 0.85, 0.1))
    box("Exp_CraneArm", (0.35, -0.2, 0.62), (0.03, 0.25, 0.04), "ExpCraneA", (0.85, 0.8, 0.1))
    # Storage silos
    for i, (x, y) in enumerate([(-0.3, 0.2), (-0.15, 0.25), (0.0, 0.2)]):
        cyl(f"Exp_Silo{i}", (x, y, 0.2), 0.06, 0.35, f"ExpSilo{i}", (0.6, 0.62, 0.65))
    # Control tower
    box("Exp_Tower", (0.25, 0.25, 0.3), (0.15, 0.15, 0.5), "ExpTower", (0.7, 0.72, 0.75))
    # Tower windows
    box("Exp_TowWin", (0.25, 0.33, 0.45), (0.1, 0.02, 0.15), "ExpTowWin", (0.5, 0.7, 0.85), 0.1)
    # Antenna on tower
    cyl("Exp_Ant", (0.25, 0.25, 0.6), 0.015, 0.2, "ExpAnt", (0.75, 0.75, 0.8))
    # Loading ramp
    box("Exp_Ramp", (-0.45, -0.25, 0.15), (0.2, 0.15, 0.08), "ExpRamp", (0.5, 0.52, 0.55))
    print("  Puerto Exportacion built")


def main():
    print("=" * 50)
    print("  SIMMOON Blender Buildings v5")
    print("=" * 50)
    models = [
        ("misc_parque_recreativo", build_parque),
        ("misc_gestion_residuos", build_residuos),
        ("misc_estacion_bomberos", build_bomberos),
        ("ind_laboratorio_helio3", build_helio3),
        ("ind_puerto_exportacion", build_puerto_export),
    ]
    for name, builder in models:
        try:
            clear_scene()
            setup_scene()
            builder()
            render_model(name)
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")

    print(f"\nAll done: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
