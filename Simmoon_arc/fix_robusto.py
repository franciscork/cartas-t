#!/usr/bin/env python3
"""Patcher robusto: busca edificios por ID y modifica campos especificos."""
import sys, re
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RUTA = "juego_simmoon.py"
with open(RUTA, "r", encoding="utf-8") as f:
    lineas = f.readlines()

cambios = 0

def buscar_bloque(pid, lineas, start=0):
    """Busca un bloque TipoEdificio por ID y devuelve (inicio, fin)."""
    for i in range(start, len(lineas)):
        if f'"{pid}": TipoEdificio("' in lineas[i]:
            for j in range(i, min(i+20, len(lineas))):
                if lineas[j].rstrip().endswith('),'):
                    return i, j+1
            return i, min(i+20, len(lineas))
    return None, None

def reemplazar_en_bloque(pid, busqueda, reemplazo):
    """Reemplaza texto dentro del bloque de un edificio."""
    global cambios
    inicio, fin, _ = buscar_bloque(pid, lineas)
    if inicio is None:
        print(f"  FAIL: {pid} no encontrado")
        return
    encontrado = False
    for i in range(inicio, fin):
        if busqueda in lineas[i]:
            lineas[i] = lineas[i].replace(busqueda, reemplazo, 1)
            encontrado = True
            cambios += 1
            print(f"  OK: {pid} - {busqueda.strip()[:40]} -> {reemplazo.strip()[:40]}")
            break
    if not encontrado:
        print(f"  FAIL: {pid} - '{busqueda[:40]}' no encontrado en bloque")

def cambiar_nombre(pid, nuevo_nombre):
    """Cambia el nombre mostrado de un edificio."""
    global cambios
    inicio, fin, _ = buscar_bloque(pid, lineas)
    if inicio is None:
        print(f"  FAIL: {pid} no encontrado")
        return
    for i in range(inicio, fin):
        m = re.match(r'(\s*)"' + re.escape(pid) + r'": TipoEdificio\("' + re.escape(pid) + r'", "[^"]+", "', lineas[i])
        if m:
            old_line = lineas[i]
            # Replace the name between second and third quotes
            parts = old_line.split('"')
            # parts[0] = whitespace, parts[1] = pid, parts[2] = ": TipoEdificio(\""
            # Actually let me use a simpler regex approach
            lineas[i] = re.sub(
                rf'"{pid}": TipoEdificio\("{pid}", "[^"]+", "',
                f'"{pid}": TipoEdificio("{pid}", "{nuevo_nombre}", "',
                old_line
            )
            if lineas[i] != old_line:
                cambios += 1
                print(f"  OK: {pid} nombre -> {nuevo_nombre}")
            else:
                print(f"  FAIL: {pid} regex no matcheo")
            return

def cambiar_categoria(pid, nueva_cat):
    """Cambia la categoria de un edificio (3er parametro de TipoEdificio)."""
    global cambios
    inicio, fin, _ = buscar_bloque(pid, lineas)
    if inicio is None:
        return
    for i in range(inicio, fin):
        if f'"{pid}": TipoEdificio("' in lineas[i]:
            old_line = lineas[i]
            # Replace category (3rd quoted string after pid)
            parts = old_line.split('"')
            # parts[0]=whitespace, parts[1]=pid, parts[2]=: TipoEdificio(, parts[3]=pid
            # Actually it's: "pid": TipoEdificio("pid", "name", "category",
            # So parts[5] should be the category
            lineas[i] = re.sub(
                rf'TipoEdificio\("{pid}", "[^"]+", "[^"]+"',
                f'TipoEdificio("{pid}", "{extraer_nombre(pid)}", "{nueva_cat}"',
                old_line
            )
            if lineas[i] != old_line:
                cambios += 1
                print(f"  OK: {pid} categoria -> {nueva_cat}")
            return

def extraer_nombre(pid):
    """Extrae el nombre actual de un edificio."""
    inicio, fin, _ = buscar_bloque(pid, lineas)
    if inicio is None:
        return "???"
    for i in range(inicio, fin):
        m = re.search(rf'TipoEdificio\("{pid}", "([^"]+)"', lineas[i])
        if m:
            return m.group(1)
    return "???"

# --- Aplicar cambios ---

print("Aplicando cambios...")

# 1. hou_01 -> Albergue Basico
cambiar_nombre("hou_01", "Albergue Basico")
reemplazar_en_bloque("hou_01", "costo=400, produce_energia=-3,", "costo=300, produce_energia=-2,")
reemplazar_en_bloque("hou_01", "alquiler=20)", "alquiler=12)")
reemplazar_en_bloque("hou_01", "Capsula subterranea para 4-8 colonos. 1x1", "Capsula economica para 4-8 colonos. 1x1")

# 2. hou_02 -> description + alquiler
reemplazar_en_bloque("hou_02", "Tuneles de lava acondicionados. 2x2", "Albergue compartido en tuneles de lava. 2x2")
reemplazar_en_bloque("hou_02", "alquiler=35)", "alquiler=22)")

# 3. hou_03 -> Hotel Cupula de Lujo, businesses
cambiar_nombre("hou_03", "Hotel Cupula de Lujo")
cambiar_categoria("hou_03", "businesses")
reemplazar_en_bloque("hou_03", "alquiler=80)", "alquiler=120)")
reemplazar_en_bloque("hou_03", "Estructura geodesica con vistas al espacio. 2x2", "Hotel premium con vistas al espacio. 2x2")

# 4. hou_04 -> Albergue Subterraneo
cambiar_nombre("hou_04", "Albergue Subterraneo")
reemplazar_en_bloque("hou_04", "costo=1000, produce_energia=-8,", "costo=700, produce_energia=-6,")
reemplazar_en_bloque("hou_04", "alquiler=45)", "alquiler=30)")
reemplazar_en_bloque("hou_04", "Colonias excavadas bajo la superficie. 3x2", "Albergue excavado bajo la superficie. 3x2")

# 5. site_08 fix (corrupted)
reemplazar_en_bloque("site_08", "costo=700, produce_energia=-6, produce_oxigeno=-5, produce_agua=-3,", "costo=800, produce_energia=-6, produce_oxigeno=-3, produce_agua=-2,")

# 6. biz_02 fix (corrupted by first patcher)
reemplazar_en_bloque("biz_02", "costo=300, produce_energia=-2, produce_oxigeno=-1,", "costo=400, produce_energia=-3, produce_oxigeno=-1,")

# 7. Remove hou_03 from alojamiento zone
for i, linea in enumerate(lineas):
    if 'categorias_compatibles=["hou_01", "hou_02", "hou_03", "hou_04"' in linea:
        # Find the zone definition - check if this is alojamiento zone
        for j in range(max(0, i-5), i):
            if '"alojamiento"' in lineas[j] or 'TipoZona("alojamiento"' in lineas[j]:
                lineas[i] = linea.replace('"hou_02", "hou_03", "hou_04"', '"hou_02", "hou_04"')
                cambios += 1
                print("  OK: hou_03 quitado de alojamiento zone")
                break
        break

# 8. Panel button: Vivienda -> Alojamiento
for i, linea in enumerate(lineas):
    if '("Vivienda", "housing")' in linea:
        lineas[i] = linea.replace('("Vivienda", "housing")', '("Alojamiento", "housing")')
        cambios += 1
        print("  OK: Boton Vivienda -> Alojamiento")
        break

# 9. Minimap comment
for i, linea in enumerate(lineas):
    if 'Azul vivienda' in linea:
        lineas[i] = linea.replace('Azul vivienda', 'Azul alojamiento')
        cambios += 1
        print("  OK: Minimap comment -> alojamiento")
        break

# Guardar
with open(RUTA, "w", encoding="utf-8") as f:
    f.writelines(lineas)

print(f"\nRESULTADO: {cambios} cambios aplicados")
