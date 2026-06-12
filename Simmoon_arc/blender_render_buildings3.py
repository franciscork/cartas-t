#!/usr/bin/env python3
"""
Blender 3D models for SIMMOON buildings (batch 3).
5 low-poly isometric: Banco Lunar, Almacen, Torre Comunicaciones, Academia, Planta Agua.
Run: blender.exe --background --python blender_render_buildings3.py
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


def build_banco():
    """Banco Lunar: imposing main block + columns + pediment + vault + sign."""
    # Main building body
    box("Ban_Body", (0, 0, 0.45), (0.85, 0.6, 0.9), "BanBody", (0.82, 0.78, 0.7))
    # Pediment / roof triangle
    box("Ban_Roof", (0, 0, 0.92), (0.8, 0.55, 0.08), "BanRoof", (0.6, 0.5, 0.38))
    # Columns (4 front pillars)
    for i, x_pos in enumerate([-0.25, -0.08, 0.08, 0.25]):
        cyl(f"Ban_Col{i}", (x_pos, 0.32, 0.45), 0.04, 0.9, "BanCol", (0.9, 0.88, 0.82), 0.3)
    # Vault (cylinder in back, represents secure storage)
    cyl("Ban_Vault", (0, -0.22, 0.4), 0.2, 0.55, "BanVault", (0.55, 0.5, 0.42), 0.2)
    # Vault door ring
    bpy.ops.mesh.primitive_torus_add(major_radius=0.15, minor_radius=0.03, location=(0, -0.22, 0.68))
    door_ring = bpy.context.active_object
    door_ring.name = "Ban_VaultRing"
    door_ring.data.materials.append(make_mat("BanRing", (0.4, 0.35, 0.3), 0.1))
    # Sign post
    box("Ban_Sign", (0, 0.35, 0.7), (0.25, 0.05, 0.15), "BanSign", (0.3, 0.35, 0.55), 0.1)
    print("  Banco Lunar built")


def build_almacen():
    """Almacen: long warehouse + roll-up door + loading dock + roof vents."""
    # Main long body (2x1 footprint)
    box("Alm_Body", (0, 0, 0.5), (1.1, 0.65, 1.0), "AlmBody", (0.6, 0.58, 0.55))
    box("Alm_Roof", (0, 0, 1.02), (1.05, 0.6, 0.06), "AlmRoof", (0.45, 0.43, 0.4))
    # Roll-up door (front)
    box("Alm_Door", (0, 0.34, 0.4), (0.3, 0.04, 0.6), "AlmDoor", (0.35, 0.38, 0.42), 0.15)
    # Door tracks
    box("Alm_TrackL", (-0.16, 0.34, 0.7), (0.03, 0.03, 0.55), "AlmTrack", (0.3, 0.3, 0.32))
    box("Alm_TrackR", (0.16, 0.34, 0.7), (0.03, 0.03, 0.55), "AlmTrack2", (0.3, 0.3, 0.32))
    # Loading dock
    box("Alm_Dock", (0.45, 0.34, 0.2), (0.35, 0.2, 0.4), "AlmDock", (0.5, 0.48, 0.45))
    box("Alm_DockRoof", (0.45, 0.34, 0.42), (0.3, 0.15, 0.04), "AlmDockR", (0.4, 0.38, 0.35))
    # Roof vents
    for i, x_pos in enumerate([-0.3, 0.0, 0.3]):
        cyl(f"Alm_Vent{i}", (x_pos, -0.15, 1.08), 0.06, 0.15, "AlmVent", (0.4, 0.38, 0.42))
    print("  Almacen built")


def build_torre_comms():
    """Torre de Comunicaciones: base building + tall tower + antenna + satellite dishes."""
    # Base building
    box("Tor_Base", (0, 0, 0.3), (0.5, 0.5, 0.6), "TorBase", (0.65, 0.63, 0.6))
    box("Tor_BaseRoof", (0, 0, 0.62), (0.45, 0.45, 0.04), "TorBaseR", (0.5, 0.48, 0.45))
    # Entry
    box("Tor_Entry", (0, 0.27, 0.2), (0.2, 0.05, 0.4), "TorEntry", (0.45, 0.48, 0.5))
    # Main tower (tall cylinder)
    cyl("Tor_Tower", (0, 0, 1.0), 0.12, 1.2, "TorTower", (0.55, 0.53, 0.5))
    # Tower segments (ring accents)
    for z_offset in [0.35, 0.7, 1.05]:
        bpy.ops.mesh.primitive_torus_add(major_radius=0.13, minor_radius=0.02, location=(0, 0, 0.3 + z_offset))
        ring = bpy.context.active_object
        ring.name = f"Tor_Ring_{int(z_offset*10)}"
        ring.data.materials.append(make_mat(f"TorRing{int(z_offset*10)}", (0.4, 0.42, 0.45)))
    # Antenna spire on top
    cyl("Tor_Spire", (0, 0, 1.7), 0.03, 0.5, "TorSpire", (0.75, 0.75, 0.8))
    # Red warning light
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.04, location=(0, 0, 1.98))
    light = bpy.context.active_object
    light.name = "Tor_Light"
    light.data.materials.append(make_mat("TorLight", (0.95, 0.15, 0.1), 0.1))
    # Satellite dishes
    for i, (x, y, z) in enumerate([(0.2, 0.15, 0.7), (-0.2, -0.15, 0.55)]):
        cyl(f"Tor_DishPole{i}", (x, y, z), 0.03, 0.25, "TorDishPole", (0.5, 0.5, 0.55))
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(x, y, z + 0.14))
        dish = bpy.context.active_object
        dish.name = f"Tor_Dish{i}"
        dish.scale = (1.0, 1.0, 0.25)
        dish.data.materials.append(make_mat(f"TorDish{i}", (0.8, 0.82, 0.85), 0.15))

    print("  Torre de Comunicaciones built")


def build_academia():
    """Academia Lunar: main hall + dome + courtyard + side wings."""
    # Main hall (center block)
    box("Aca_Main", (0, 0, 0.45), (0.9, 0.6, 0.9), "AcaBody", (0.85, 0.82, 0.75))
    box("Aca_MainRoof", (0, 0, 0.92), (0.85, 0.55, 0.06), "AcaRoof", (0.6, 0.55, 0.45))
    # Dome (observatory / planetarium)
    cyl("Aca_DomeBase", (0, -0.15, 0.6), 0.22, 0.3, "AcaDomeB", (0.7, 0.68, 0.65))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.23, location=(0, -0.15, 0.8))
    dome = bpy.context.active_object
    dome.name = "Aca_Dome"
    dome.scale = (1.0, 1.0, 0.45)
    dome.data.materials.append(make_mat("AcaDome", (0.5, 0.65, 0.8), 0.15))
    # Left wing (classrooms)
    box("Aca_WingL", (-0.55, 0.1, 0.35), (0.4, 0.5, 0.7), "AcaWingL", (0.8, 0.78, 0.72))
    box("Aca_WingLRoof", (-0.55, 0.1, 0.72), (0.35, 0.45, 0.05), "AcaWLR", (0.55, 0.52, 0.45))
    # Right wing (offices)
    box("Aca_WingR", (0.55, 0.1, 0.35), (0.4, 0.5, 0.7), "AcaWingR", (0.8, 0.78, 0.72))
    box("Aca_WingRRoof", (0.55, 0.1, 0.72), (0.35, 0.45, 0.05), "AcaWR", (0.55, 0.52, 0.45))
    # Courtyard (flat area in front)
    box("Aca_Court", (0, 0.35, 0.08), (0.55, 0.25, 0.16), "AcaCourt", (0.5, 0.48, 0.52))
    # Windows
    box("Aca_Win1", (0, 0.32, 0.55), (0.4, 0.04, 0.25), "AcaWin", (0.5, 0.7, 0.85), 0.1)
    # Flag pole
    cyl("Aca_FlagPole", (0.35, 0.25, 0.55), 0.02, 0.7, "AcaPole", (0.7, 0.7, 0.75))
    bpy.ops.mesh.primitive_plane_add(size=0.12, location=(0.35, 0.25, 0.92))
    flag = bpy.context.active_object
    flag.name = "Aca_Flag"
    flag.rotation_euler = (0, 0, radians(15))
    flag.data.materials.append(make_mat("AcaFlag", (0.2, 0.35, 0.7)))
    print("  Academia built")


def build_planta_agua():
    """Planta de Agua: treatment tanks + pipes + rectangular plant building."""
    # Main plant building
    box("Plt_Body", (0, 0, 0.35), (0.7, 0.5, 0.7), "PltBody", (0.7, 0.72, 0.75))
    box("Plt_Roof", (0, 0, 0.72), (0.65, 0.45, 0.05), "PltRoof", (0.55, 0.58, 0.62))
    # Water treatment tanks (3 large cylinders)
    for i, (x, y) in enumerate([(-0.25, 0.3), (0.0, 0.35), (0.25, 0.3)]):
        cyl(f"Plt_Tank{i}", (x, y, 0.25), 0.12, 0.4, f"PltTank{i}", (0.55, 0.7, 0.82), 0.2)
        # Tank rim
        bpy.ops.mesh.primitive_torus_add(major_radius=0.12, minor_radius=0.02, location=(x, y, 0.47))
        rim = bpy.context.active_object
        rim.name = f"Plt_TankRim{i}"
        rim.data.materials.append(make_mat(f"PltRim{i}", (0.45, 0.48, 0.5)))
    # Connecting pipes between tanks
    for i, (x1, x2) in enumerate([(-0.25, 0.0), (0.0, 0.25)]):
        cx = (x1 + x2) / 2
        cyl(f"Plt_Pipe{i}", (cx, 0.35, 0.47), 0.025, abs(x2 - x1), f"PltPipe{i}", (0.5, 0.55, 0.6))
        pipe = bpy.data.objects.get(f"Plt_Pipe{i}")
        if pipe:
            pipe.rotation_euler = (0, radians(90), 0)
    # Pump station (small building beside tanks)
    box("Plt_Pump", (0.35, -0.2, 0.25), (0.25, 0.25, 0.5), "PltPump", (0.65, 0.63, 0.6))
    box("Plt_PumpRoof", (0.35, -0.2, 0.52), (0.2, 0.2, 0.04), "PltPumpR", (0.5, 0.48, 0.45))
    # Output pipe
    cyl("Plt_OutPipe", (0.5, -0.05, 0.15), 0.03, 0.5, "PltOut", (0.45, 0.5, 0.55))
    out_pipe = bpy.data.objects.get("Plt_OutPipe")
    if out_pipe:
        out_pipe.rotation_euler = (0, radians(45), 0)
    # Valve wheel
    bpy.ops.mesh.primitive_torus_add(major_radius=0.05, minor_radius=0.01, location=(0.5, -0.05, 0.42))
    valve = bpy.context.active_object
    valve.name = "Plt_Valve"
    valve.data.materials.append(make_mat("PltValve", (0.9, 0.25, 0.15)))
    print("  Planta de Agua built")


def main():
    print("=" * 50)
    print("  SIMMOON Blender Buildings v3")
    print("=" * 50)
    models = [
        ("biz_banco_lunar", build_banco),
        ("biz_almacen", build_almacen),
        ("misc_torre_comunicaciones", build_torre_comms),
        ("misc_academia", build_academia),
        ("misc_planta_agua", build_planta_agua),
    ]
    for name, builder in models:
        clear_scene()
        setup_scene()
        builder()
        render_model(name)
    print(f"\nAll done: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
