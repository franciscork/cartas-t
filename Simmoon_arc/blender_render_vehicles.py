#!/usr/bin/env python3
"""
Blender 3D models for SIMMOON vehicles (batch 1).
5 low-poly isometric: Camion Minero, Lanzadera Pasajeros, Carguero Pesado,
Vehiculo Emergencia, Dron Suministro.
Run: blender.exe --background --python blender_render_vehicles.py
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
    cam_data.ortho_scale = 6.0
    cam = bpy.data.objects.new("IsoCam", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    CAM_DIST = 7.0
    CAM_AZIMUTH = radians(45)
    cam.location = (CAM_DIST * cos(CAM_AZIMUTH), CAM_DIST * sin(CAM_AZIMUTH), CAM_DIST * tan(radians(30)))
    direction = mathutils.Vector((0, 0, 0.4)) - cam.location
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


def build_camion_minero():
    """Camion Minero: cab + dumper bed + wheels + exhaust."""
    # Cab
    box("Cam_Cab", (-0.3, 0, 0.3), (0.25, 0.22, 0.4), "CamCab", (0.85, 0.6, 0.2))
    # Cab window
    box("Cam_Win", (-0.3, 0.12, 0.4), (0.18, 0.04, 0.2), "CamWin", (0.5, 0.7, 0.85), 0.1)
    # Dumper bed
    box("Cam_Bed", (0.25, 0, 0.35), (0.35, 0.24, 0.2), "CamBed", (0.6, 0.55, 0.5))
    # Bed sides raised
    box("Cam_SideL", (0.25, 0.13, 0.45), (0.33, 0.02, 0.15), "CamSide", (0.55, 0.5, 0.45))
    box("Cam_SideR", (0.25, -0.13, 0.45), (0.33, 0.02, 0.15), "CamSide2", (0.55, 0.5, 0.45))
    # Wheels (4)
    for i, (x, y) in enumerate([(-0.2, 0.14), (-0.2, -0.14), (0.2, 0.14), (0.2, -0.14)]):
        cyl(f"Cam_Whl{i}", (x, y, 0.08), 0.06, 0.08, "CamWhl", (0.15, 0.12, 0.1))
    # Exhaust pipe
    cyl("Cam_Exh", (-0.3, -0.1, 0.55), 0.02, 0.25, "CamExh", (0.4, 0.38, 0.35))
    print("  Camion Minero built")


def build_lanzadera():
    """Lanzadera Pasajeros: fuselage + wings + engines + cockpit."""
    # Fuselage
    box("Lan_Body", (0, 0, 0.3), (0.7, 0.15, 0.18), "LanBody", (0.8, 0.82, 0.85))
    # Nose cone
    cyl("Lan_Nose", (0.4, 0, 0.3), 0.08, 0.25, "LanNose", (0.75, 0.78, 0.8))
    n = bpy.data.objects.get("Lan_Nose")
    if n:
        n.rotation_euler = (0, radians(90), 0)
    # Wings
    box("Lan_WingL", (0.05, 0.22, 0.28), (0.3, 0.04, 0.03), "LanWing", (0.6, 0.62, 0.65))
    box("Lan_WingR", (0.05, -0.22, 0.28), (0.3, 0.04, 0.03), "LanWing2", (0.6, 0.62, 0.65))
    # Tail fin
    box("Lan_TailV", (-0.35, 0, 0.4), (0.04, 0.02, 0.2), "LanTail", (0.7, 0.72, 0.75))
    # Engines (2 side pods)
    for i, y in enumerate([0.12, -0.12]):
        cyl(f"Lan_Eng{i}", (-0.15, y, 0.28), 0.04, 0.3, f"LanEng{i}", (0.5, 0.52, 0.55))
        e = bpy.data.objects.get(f"Lan_Eng{i}")
        if e:
            e.rotation_euler = (0, radians(90), 0)
    # Cockpit window
    box("Lan_Cockpit", (0.3, 0, 0.42), (0.1, 0.1, 0.06), "LanCockpit", (0.4, 0.7, 0.9), 0.08)
    print("  Lanzadera Pasajeros built")


def build_carguero():
    """Carguero Pesado: big body + cargo pods + engines + bridge."""
    # Main hull
    box("Car_Hull", (0, 0, 0.35), (0.65, 0.3, 0.25), "CarHull", (0.55, 0.58, 0.6))
    # Bridge (top)
    box("Car_Bridge", (-0.1, 0, 0.55), (0.15, 0.18, 0.2), "CarBridge", (0.7, 0.72, 0.75))
    box("Car_BridgeW", (-0.1, 0.1, 0.6), (0.1, 0.04, 0.12), "CarBridgeW", (0.5, 0.7, 0.85), 0.1)
    # Cargo pods (2 side)
    for i, y in enumerate([0.25, -0.25]):
        box(f"Car_Pod{i}", (0.1, y, 0.3), (0.2, 0.12, 0.2), f"CarPod{i}", (0.65, 0.62, 0.55))
    # Engines (rear)
    for i, (x, y) in enumerate([(0.35, 0.1), (0.35, -0.1)]):
        cyl(f"Car_Eng{i}", (x, y, 0.3), 0.05, 0.2, f"CarEng{i}", (0.4, 0.42, 0.45))
        e = bpy.data.objects.get(f"Car_Eng{i}")
        if e:
            e.rotation_euler = (0, radians(90), 0)
    # Cargo arms
    box("Car_ArmL", (0, 0.2, 0.2), (0.15, 0.03, 0.08), "CarArm", (0.5, 0.52, 0.55))
    print("  Carguero Pesado built")


def build_emergencia():
    """Vehiculo Emergencia: ambulance body + lights + siren bar."""
    # Body
    box("Emg_Body", (0, 0, 0.2), (0.4, 0.2, 0.2), "EmgBody", (0.9, 0.15, 0.15))
    # Cab
    box("Emg_Cab", (-0.25, 0, 0.3), (0.15, 0.18, 0.25), "EmgCab", (0.85, 0.1, 0.1))
    # Cab window
    box("Emg_CabW", (-0.25, 0.1, 0.42), (0.1, 0.04, 0.12), "EmgCabW", (0.5, 0.7, 0.85), 0.1)
    # Emergency lights (top bar)
    box("Emg_Light1", (-0.1, 0, 0.42), (0.06, 0.16, 0.03), "EmgLight", (0.95, 0.2, 0.1))
    box("Emg_Light2", (0.1, 0, 0.42), (0.06, 0.16, 0.03), "EmgLight2", (0.1, 0.2, 0.95))
    # Red cross
    box("Emg_CrossH", (0.1, 0, 0.33), (0.08, 0.02, 0.02), "EmgCross", (0.95, 0.95, 0.95))
    box("Emg_CrossV", (0.1, 0, 0.33), (0.02, 0.08, 0.02), "EmgCross2", (0.95, 0.95, 0.95))
    # Wheels
    for i, (x, y) in enumerate([(-0.15, 0.13), (-0.15, -0.13), (0.15, 0.13), (0.15, -0.13)]):
        cyl(f"Emg_Whl{i}", (x, y, 0.06), 0.05, 0.06, "EmgWhl", (0.1, 0.08, 0.07))
    print("  Vehiculo Emergencia built")


def build_dron():
    """Dron Suministro: central body + 4 rotors + cargo hook + camera."""
    # Central body
    box("Drn_Body", (0, 0, 0.25), (0.12, 0.1, 0.1), "DrnBody", (0.5, 0.55, 0.6))
    # Arms (4)
    for i, (x, y) in enumerate([(0.12, 0), (-0.12, 0), (0, 0.1), (0, -0.1)]):
        box(f"Drn_Arm{i}", (x/2, y/2, 0.3), (abs(x/2)+0.02, 0.015, 0.015), f"DrnArm{i}", (0.45, 0.48, 0.5))
    # Rotors (4 discs)
    for i, (x, y) in enumerate([(0.18, 0), (-0.18, 0), (0, 0.16), (0, -0.16)]):
        cyl(f"Drn_Rotor{i}", (x, y, 0.31), 0.06, 0.01, f"DrnRotor{i}", (0.3, 0.32, 0.35), 0.3)
    # Camera/sensor
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03, location=(0, 0, 0.18))
    cam = bpy.context.active_object
    cam.name = "Drn_Camera"
    cam.data.materials.append(make_mat("DrnCam", (0.1, 0.1, 0.15), 0.05))
    # Cargo hook
    box("Drn_Hook", (0, 0.06, 0.15), (0.015, 0.015, 0.08), "DrnHook", (0.4, 0.42, 0.45))
    # Cargo package
    box("Drn_Cargo", (0, 0.1, 0.08), (0.05, 0.05, 0.06), "DrnCargo", (0.7, 0.5, 0.2))
    # LED indicators
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.015, location=(0.05, 0, 0.32))
    led1 = bpy.context.active_object
    led1.name = "Drn_LED1"
    led1.data.materials.append(make_mat("DrnLED", (0.95, 0.2, 0.1), 0.05))
    print("  Dron Suministro built")


def main():
    print("=" * 50)
    print("  SIMMOON Blender Vehicles v1")
    print("=" * 50)
    models = [
        ("veh_camion_minero", build_camion_minero),
        ("veh_lanzadera_pasajeros", build_lanzadera),
        ("veh_carguero_pesado", build_carguero),
        ("veh_emergencia", build_emergencia),
        ("veh_dron_suministro", build_dron),
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
