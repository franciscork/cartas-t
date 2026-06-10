#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix: Insert happiness calculation into procesar_siguiente_turno."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
base_dir = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(base_dir, 'juego_simmoon.py')

with open(filepath, 'rb') as f:
    raw = f.read()

# Normalize line endings
text = raw.replace(b'\r\n', b'\n').decode('utf-8')
lines = text.split('\n')

def find_line(pattern, start=0):
    for i in range(start, len(lines)):
        if pattern in lines[i]:
            return i
    return -1

# Find procesar_siguiente_turno method
method_start = find_line('def procesar_siguiente_turno')
if method_start < 0:
    print("[FAIL] Method not found!")
    sys.exit(1)

# Find the section around "if self.es_de_noche:" which has produccion_extra
# Look for the sequence: felicidad calculation (if already inserted), or the original debug vars section
fel_idx = find_line('# --- Calculo de Felicidad ---', method_start)
if fel_idx >= 0:
    print("[SKIP] Happiness calculation already present at line", fel_idx + 1)
    sys.exit(0)

# Find the es_de_noche section - this is the anchor
noche_idx = find_line('if self.es_de_noche:', method_start)
if noche_idx < 0:
    print("[FAIL] es_de_noche not found!")
    sys.exit(1)

# Find what's before it - we need to insert BEFORE the es_de_noche block
# but AFTER the evento/costo_evento section
# Look for "costo_evento = 0" or similar right before noche
print(f"Method start: line {method_start + 1}")
print(f"Noche idx: line {noche_idx + 1}")

# Show surrounding context
print("\nContext before noche:")
for i in range(max(0, noche_idx - 15), noche_idx + 5):
    print(f"  {i+1}: {lines[i][:100]}")

# Now find a good insertion point: after "ingresos =" and before "if self.es_de_noche:"
# Look for the ingresos line
ingresos_idx = find_line('ingresos =', method_start)
if ingresos_idx < 0:
    print("[FAIL] ingresos line not found")
    sys.exit(1)

print(f"\nIngresos at line {ingresos_idx + 1}")

# Show lines between ingresos and noche
print("\nLines between ingresos and noche:")
for i in range(ingresos_idx, noche_idx + 1):
    print(f"  {i+1}: {lines[i][:100]}")

# The insertion point should be right after the evento/costo_evento section
# and right before "if self.es_de_noche:"
# Let's find the blank line before noche
insert_point = noche_idx
# We want to insert just before the noche section
# Skip any blank lines before it
while insert_point > 0 and lines[insert_point - 1].strip() == '':
    insert_point -= 1

print(f"\nInsert point: before line {insert_point + 1}")

# Build the happiness calculation block
happiness_block = [
    '        # --- Calculo de Felicidad ---',
    '        felicidad = Config.FELICIDAD_INICIAL',
    '        suficiencia = 0',
    '        for r_actual, r_total in [',
    '            (self.recursos.energia_total, max(1, abs(self.recursos.energia_total))),',
    '            (self.recursos.oxigeno_total, max(1, abs(self.recursos.oxigeno_total))),',
    '            (self.recursos.agua_total, max(1, abs(self.recursos.agua_total))),',
    '            (self.recursos.presion_total, max(1, abs(self.recursos.presion_total))),',
    '        ]:',
    '            if r_total > 0:',
    '                suficiencia += min(7.5, (r_actual / r_total) * 5)',
    '            elif r_total < -5:',
    '                suficiencia -= 5',
    '            else:',
    '                suficiencia += 3',
    '        felicidad += max(-20, min(30, suficiencia))',
    '        fel_edificios = sum(e.tipo.produce_felicidad for e in self.mapa.edificios if e.activo)',
    '        felicidad += min(25, fel_edificios)',
    '        empleos_calc = sum(e.tipo.empleos for e in self.mapa.edificios if e.activo)',
    '        if self.recursos.poblacion > 0:',
    '            tasa_empleo = min(1.0, empleos_calc / max(1, self.recursos.poblacion * 0.6))',
    '        else:',
    '            tasa_empleo = 0.5',
    '        felicidad += tasa_empleo * 15',
    '        for r_total in [self.recursos.energia_total, self.recursos.oxigeno_total,',
    '                        self.recursos.agua_total, self.recursos.presion_total]:',
    '            if r_total < -10:',
    '                felicidad -= 5',
    '            elif r_total < 0:',
    '                felicidad -= 2',
    '        felicidad = max(Config.FELICIDAD_MIN, min(Config.FELICIDAD_MAX, felicidad))',
    '        self.recursos.felicidad = int(felicidad)',
    '        if felicidad >= Config.FELICIDAD_UMBRAL_CONTENTO:',
    '            self.recursos.bono_produccion = Config.BONUS_FELICIDAD',
    '        elif felicidad < Config.FELICIDAD_UMBRAL_ENOJADO:',
    '            self.recursos.bono_produccion = Config.PENALTY_FELICIDAD',
    '        else:',
    '            self.recursos.bono_produccion = 1.0',
    '',
    '        if felicidad < Config.FELICIDAD_UMBRAL_ENOJADO and self.recursos.poblacion >= 5:',
    '            tiles_libres = [(x, y) for y in range(self.mapa.tamanio) for x in range(self.mapa.tamanio) if self.mapa.grid[y][x] is None]',
    '            import random as rnd_h',
    '            rnd_h.shuffle(tiles_libres)',
    '            num_protestas = min(3 + self.recursos.poblacion // 20, len(tiles_libres))',
    '            mensajes_p = ["QUEREMOS AIRE!", "MAS OXIGENO!", "JUSTICIA LUNAR!", "AGUA YA!", "BAJEN IMPUESTOS!", "TRABAJO DIGNO!"]',
    '            self.manifestantes = []',
    '            for i in range(num_protestas):',
    '                tx, ty = tiles_libres[i % len(tiles_libres)]',
    '                self.manifestantes.append({',
    '                    "x": tx, "y": ty,',
    '                    "t_offset": rnd_h.uniform(0, 6.28),',
    '                    "mensaje": rnd_h.choice(mensajes_p),',
    '                    "color_hue": rnd_h.randint(0, 360),',
    '                })',
    '        elif felicidad >= Config.FELICIDAD_UMBRAL_CONTENTO:',
    '            self.manifestantes = []',
    '',
]

# Insert the block
lines[insert_point:insert_point] = happiness_block
changes = len(happiness_block)
print(f"\n[OK] Inserted {changes} lines at position {insert_point + 1}")

# Also fix the resumen visual
# Find the right insertion point
pob_idx = find_line('Poblaci')
if pob_idx >= 0:
    # Find the blit line for poblacion
    for j in range(pob_idx, min(len(lines), pob_idx + 5)):
        if 'pantalla.blit' in lines[j] and '270)' in lines[j]:
            # Check if felicidad already added
            if any('Felicidad' in lines[k] for k in range(j, min(len(lines), j + 15))):
                print("[SKIP] Resumen visual already has felicidad")
            else:
                lines[j+1:j+1] = [
                    '                fel_color = Config.COLOR_TEXTO_VERDE if self.recursos.felicidad >= 70 else (Config.COLOR_TEXTO_AMARILLO if self.recursos.felicidad >= 35 else Config.COLOR_TEXTO_ROJO)',
                    '                txt_fel = r.fuente_mediana.render("\\U0001f60a Felicidad: " + str(self.recursos.felicidad) + "%", True, fel_color)',
                    '                pantalla.blit(txt_fel, (cx + 30, cy + 300))',
                    '                if self.recursos.bono_produccion != 1.0:',
                    '                    if self.recursos.bono_produccion > 1.0:',
                    '                        bono_str = "\\U0001f4c8 +" + str(int((self.recursos.bono_produccion - 1) * 100)) + "% produccion"',
                    '                    else:',
                    '                        bono_str = "\\U0001f4c9 -" + str(int((1 - self.recursos.bono_produccion) * 100)) + "% produccion"',
                    '                    txt_bono = r.fuente_pequenia.render(bono_str, True, Config.COLOR_TEXTO_AMARILLO)',
                    '                    pantalla.blit(txt_bono, (cx + 30, cy + 325))',
                ]
                print("[OK] Resumen visual felicidad added")
            break

# Write back with CRLF
new_text = '\n'.join(lines)
new_raw = new_text.encode('utf-8').replace(b'\n', b'\r\n')
with open(filepath, 'wb') as f:
    f.write(new_raw)

print(f"\n[DONE] File size: {len(new_raw)} bytes")
