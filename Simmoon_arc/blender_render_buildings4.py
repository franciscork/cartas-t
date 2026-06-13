#!/usr/bin/env python3
"""
Blender 3D models for SIMMOON buildings (batch 4).
5 low-poly isometric: Procesador Atmosferico, Puesto Comercial, Base Ascensor Espacial,
Fundicion de Regolito, Fabrica de Impresion 3D.
Run: blender.exe --background --python blender_render_buildings4.py
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


def build_procesador():
    """Procesador Atmosferico: tall tower + intake vents + exhaust + pipes."""
    # Main processing tower
    cyl("Prc_Tower", (0, 0, 0.6), 0.35, 1.2, "PrcBody", (0.65, 0.7, 0.75))
    # Tower rings
    for z in [0.25, 0.65, 1.05]:
        bpy.ops.mesh.primitive_torus_add(major_radius=0.36, minor_radius=0.025, location=(0, 0, z))
        ring = bpy.context.active_object
        ring.name = f"Prc_Ring_{int(z*100)}"
        ring.data.materials.append(make_mat(f"PrcRing{int(z*100)}", (0.45, 0.5, 0.55)))
    # Intake vents (side scoops)
    for i, (x, y, angle) in enumerate([(0.3, 0, 0), (-0.3, 0, 180), (0, 0.3, 90), (0, -0.3, 270)]):
        box(f"Prc_Vent{i}", (x, y, 0.5), (0.15, 0.06, 0.3), f"PrcVent{i}", (0.5, 0.55, 0.6))
        vent = bpy.data.objects.get(f"Prc_Vent{i}")
        if vent:
            vent.rotation_euler = (0, 0, radians(angle))
    # Exhaust top
    cyl("Prc_Exhaust", (0, 0, 1.3), 0.12, 0.35, "PrcExh", (0.4, 0.42, 0.45))
    # Connecting pipes to base
    cyl("Prc_Pipe1", (0.25, 0.15, 0.15), 0.04, 0.6, "PrcPipe", (0.5, 0.55, 0.6))
    p1 = bpy.data.objects.get("Prc_Pipe1")
    if p1:
        p1.rotation_euler = (radians(30), 0, radians(45))
    cyl("Prc_Pipe2", (-0.2, -0.2, 0.15), 0.04, 0.6, "PrcPipe2", (0.5, 0.55, 0.6))
    p2 = bpy.data.objects.get("Prc_Pipe2")
    if p2:
        p2.rotation_euler = (radians(-30), 0, radians(-45))
    # Base platform
    box("Prc_Base", (0, 0, 0.08), (0.5, 0.5, 0.16), "PrcBase", (0.55, 0.58, 0.6))
    print("  Procesador Atmosferico built")


def build_puesto_comercial():
    """Puesto Comercial: market stall + canopy + crates + sign."""
    # Main stall body
    box("Pue_Body", (0, 0, 0.3), (0.6, 0.45, 0.6), "PueBody", (0.75, 0.65, 0.5))
    # Canopy (wide flat roof)
    box("Pue_Canopy", (0, 0, 0.62), (0.75, 0.55, 0.06), "PueCanopy", (0.85, 0.55, 0.2))
    # Canopy poles
    for i, (x, y) in enumerate([(-0.32, 0.22), (0.32, 0.22), (-0.32, -0.22), (0.32, -0.22)]):
        cyl(f"Pue_Pole{i}", (x, y, 0.45), 0.02, 0.4, "PuePole", (0.6, 0.45, 0.3))
    # Counter
    box("Pue_Counter", (0, 0.25, 0.4), (0.5, 0.06, 0.35), "PueCounter", (0.7, 0.6, 0.45))
    # Crates
    box("Pue_Crate1", (-0.2, -0.15, 0.15), (0.12, 0.12, 0.3), "PueCrate", (0.65, 0.5, 0.35))
    box("Pue_Crate2", (0.15, -0.2, 0.12), (0.1, 0.1, 0.24), "PueCrate2", (0.6, 0.45, 0.3))
    # Sign hanging from canopy
    box("Pue_Sign", (0, 0.28, 0.55), (0.2, 0.03, 0.12), "PueSign", (0.2, 0.4, 0.7))
    print("  Puesto Comercial built")


def build_ascensor():
    """Base Ascensor Espacial: massive platform + tower + cable + control building."""
    # Main platform (3x2 footprint)
    box("Asc_Platform", (0, 0, 0.1), (1.5, 1.0, 0.2), "AscPlat", (0.5, 0.52, 0.55))
    # Platform markings
    box("Asc_Mark1", (-0.4, 0, 0.22), (0.35, 0.6, 0.02), "AscMark", (0.35, 0.38, 0.4))
    box("Asc_Mark2", (0.4, 0, 0.22), (0.35, 0.6, 0.02), "AscMark2", (0.35, 0.38, 0.4))
    # Central tower
    cyl("Asc_Tower", (0, 0, 0.6), 0.2, 0.9, "AscTower", (0.6, 0.62, 0.65))
    # Tower taper (cone on top)
    cyl("Asc_Cone", (0, 0, 1.1), 0.15, 0.3, "AscCone", (0.5, 0.52, 0.55))
    # Cable/tether going up
    cyl("Asc_Cable", (0, 0, 1.4), 0.025, 0.7, "AscCable", (0.75, 0.75, 0.8))
    # Control building
    box("Asc_Control", (0.5, 0.3, 0.35), (0.35, 0.25, 0.5), "AscCtrl", (0.7, 0.72, 0.75))
    box("Asc_CtrlRoof", (0.5, 0.3, 0.62), (0.3, 0.2, 0.04), "AscCtrlR", (0.55, 0.58, 0.6))
    # Antenna on control building
    cyl("Asc_Ant", (0.65, 0.35, 0.76), 0.02, 0.35, "AscAnt", (0.75, 0.75, 0.8))
    # Light beacon on cable top
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.04, location=(0, 0, 1.78))
    beacon = bpy.context.active_object
    beacon.name = "Asc_Beacon"
    beacon.data.materials.append(make_mat("AscBeacon", (0.95, 0.25, 0.1), 0.1))
    print("  Base Ascensor Espacial built")


def build_fundicion():
    """Fundicion de Regolito: smelter + chimney + furnace + conveyor + slag pile."""
    # Main smelter building
    box("Fun_Body", (0, 0, 0.5), (0.9, 0.6, 1.0), "FunBody", (0.45, 0.42, 0.38))
    box("Fun_Roof", (0, 0, 1.02), (0.85, 0.55, 0.06), "FunRoof", (0.35, 0.32, 0.28))
    # Tall chimney
    cyl("Fun_Chimney", (-0.2, -0.1, 1.25), 0.08, 0.6, "FunChim", (0.4, 0.38, 0.35))
    # Chimney cap
    bpy.ops.mesh.primitive_torus_add(major_radius=0.09, minor_radius=0.015, location=(-0.2, -0.1, 1.57))
    cap = bpy.context.active_object
    cap.name = "Fun_ChimCap"
    cap.data.materials.append(make_mat("FunChimCap", (0.35, 0.32, 0.3)))
    # Furnace opening (glowing)
    box("Fun_Furnace", (0.3, 0.32, 0.4), (0.2, 0.06, 0.35), "FunFurnace", (0.9, 0.4, 0.1))
    # Conveyor belt
    box("Fun_Conveyor", (-0.35, -0.35, 0.25), (0.35, 0.08, 0.1), "FunConv", (0.5, 0.48, 0.45))
    # Conveyor rollers
    for i, x in enumerate([-0.45, -0.35, -0.25]):
        cyl(f"Fun_Roller{i}", (x, -0.35, 0.3), 0.04, 0.1, "FunRoller", (0.4, 0.38, 0.35))
        r = bpy.data.objects.get(f"Fun_Roller{i}")
        if r:
            r.rotation_euler = (radians(90), 0, 0)
    # Slag pile
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(0.3, -0.25, 0.12))
    slag = bpy.context.active_object
    slag.name = "Fun_Slag"
    slag.scale = (1.0, 0.8, 0.5)
    slag.data.materials.append(make_mat("FunSlag", (0.4, 0.35, 0.3), 0.9))
    # Warning stripes
    box("Fun_Stripe", (0, 0.32, 0.08), (0.8, 0.02, 0.02), "FunStripe", (0.9, 0.85, 0.1))
    print("  Fundicion built")


def build_fabrica3d():
    """Fabrica de Impresion 3D: modern building + printer arm + material tanks + platform."""
    # Main building
    box("Fab3_Body", (0, 0, 0.45), (0.85, 0.65, 0.9), "Fab3Body", (0.8, 0.82, 0.85))
    box("Fab3_Roof", (0, 0, 0.92), (0.8, 0.6, 0.06), "Fab3Roof", (0.65, 0.68, 0.7))
    # Glass facade (front)
    box("Fab3_Glass", (0, 0.34, 0.5), (0.55, 0.03, 0.5), "Fab3Glass", (0.5, 0.7, 0.85), 0.1)
    # Printer arm (gantry structure)
    box("Fab3_GantryL", (-0.3, 0, 0.7), (0.06, 0.5, 0.15), "Fab3Gantry", (0.55, 0.58, 0.6))
    box("Fab3_GantryR", (0.3, 0, 0.7), (0.06, 0.5, 0.15), "Fab3Gantry2", (0.55, 0.58, 0.6))
    # Printer head
    box("Fab3_Head", (0, 0, 0.85), (0.12, 0.12, 0.08), "Fab3Head", (0.4, 0.42, 0.45))
    # Print bed
    box("Fab3_Bed", (0, -0.25, 0.5), (0.3, 0.3, 0.06), "Fab3Bed", (0.7, 0.72, 0.75))
    # Material tanks
    for i, (x, y) in enumerate([(-0.3, 0.25), (0.3, 0.25)]):
        cyl(f"Fab3_Tank{i}", (x, y, 0.2), 0.08, 0.35, f"Fab3Tank{i}", (0.5, 0.6, 0.7), 0.2)
    # Output platform
    box("Fab3_Out", (0.4, -0.2, 0.15), (0.25, 0.2, 0.3), "Fab3Out", (0.6, 0.62, 0.65))
    # Finished part on platform
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(0.45, -0.15, 0.32))
    part = bpy.context.active_object
    part.name = "Fab3_Part"
    part.data.materials.append(make_mat("Fab3Part", (0.2, 0.6, 0.3), 0.1))
    print("  Fabrica 3D built")


def main():
    print("=" * 50)
    print("  SIMMOON Blender Buildings v4")
    print("=" * 50)
    models = [
        ("misc_procesador_atmosferico", build_procesador),
        ("biz_puesto_comercial", build_puesto_comercial),
        ("misc_base_ascensor", build_ascensor),
        ("ind_fundicion", build_fundicion),
        ("ind_fabrica_3d", build_fabrica3d),
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
