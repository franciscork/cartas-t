#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix remaining failures from apply_happiness.py"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
base_dir = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(base_dir, 'juego_simmoon.py')

with open(filepath, 'rb') as f:
    raw = f.read()

lines = raw.replace(b'\r', b'').split(b'\n')
if lines and lines[-1] == b'':
    lines = lines[:-1]
text = [l.decode('utf-8') for l in lines]

changes = 0

def find_line(pattern, start=0):
    for i in range(start, len(text)):
        if pattern in text[i]:
            return i
    return -1

# Fix 1: actualizar_balance - the 4 assign lines have blank lines between them
# Find each line and fix them individually
idx_e = find_line('self.energia = self.energia_total')
idx_o = find_line('self.oxigeno = self.oxigeno_total')
idx_a = find_line('self.agua = self.agua_total')
idx_p = find_line('self.presion = self.presion_total')

if idx_e >= 0 and idx_p >= 0:
    # Check if these still need fixing (they were not already modified)
    if 'int(self.energia_total * self.bono_produccion)' not in text[idx_e]:
        text[idx_e] = '        # Aplicar bono/penalidad por felicidad'
        if idx_o >= 0:
            text[idx_o] = '        self.energia = int(self.energia_total * self.bono_produccion)'
            text[idx_o+1] = ''
        if idx_a >= 0:
            text[idx_a] = '        self.oxigeno = int(self.oxigeno_total * self.bono_produccion)'
            text[idx_a+1] = ''
        if idx_p >= 0:
            # p is the presion line
            text[idx_p] = '        self.agua = int(self.agua_total * self.bono_produccion)'
            if idx_p + 1 < len(text):
                text[idx_p+1] = '        self.presion = int(self.presion_total * self.bono_produccion)'
        changes += 1
        print("[OK] actualizar_balance bono")
    else:
        print("[SKIP] actualizar_balance already done")
else:
    print("[FAIL] actualizar_balance - lines not found")

# Fix 2: manifestantes init - check what's around mostrando_info_zona
idx = find_line('self.mostrando_info_zona = False')
if idx >= 0:
    print(f"  Context around line {idx}:")
    for j in range(max(0, idx-1), min(len(text), idx+8)):
        print(f"    {j}: {text[j][:80]}")
    
    # Check if already has manifestantes
    if any('manifestantes' in text[j] for j in range(idx, idx+8)):
        print("[SKIP] manifestantes already added")
    else:
        # Find the "Tutorial y ciclo lunar" line
        tut_idx = find_line('Tutorial y ciclo lunar', idx)
        if tut_idx >= 0 and tut_idx > idx:
            # Insert before tutorial line
            text[tut_idx:tut_idx] = [
                '',
                '        # Estado de manifestaciones',
                '        self.manifestantes: List[Dict] = []  # [{x, y, t_offset, mensaje, ...}]',
                '',
            ]
            changes += 1
            print("[OK] manifestantes init")
        else:
            print("[FAIL] manifestantes - tutorial not found after info_zona")
else:
    print("[FAIL] manifestantes init not found")

# Fix 3: Variables de depuracion - try different accent characters
# Try looking for "depuracion" without accent
idx = find_line('depurac')
if idx >= 0:
    print(f"  Found 'depurac' at line {idx}: {text[idx][:80]}")
    
    # Check if already has happiness code
    if any('Calculo de Felicidad' in text[j] for j in range(idx, min(len(text), idx+3))):
        print("[SKIP] happiness already in procesar_siguiente_turno")
    else:
        # Find the section: depuracion line + edificios_activos + noche sections
        # The exact line has an accent character we need to match
        dep_line = text[idx]
        print(f"  Full dep_line: {repr(dep_line[:60])}")
        
        # Find the end of this section (produccion_extra line)
        end = idx + 1
        while end < len(text) and 'produccion_extra' not in text[end]:
            end += 1
        if end < len(text):
            end += 1  # Include the produccion_extra line
        else:
            end = idx + 6
        
        old_section = text[idx:end]
        print(f"  Old section ({len(old_section)} lines):")
        for j, l in enumerate(old_section):
            print(f"    {j}: {l[:80]}")
        
        new_section = [
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
        ] + old_section
        text[idx:end] = new_section
        changes += 1
        print("[OK] procesar_siguiente_turno felicidad")
else:
    print("[FAIL] 'depurac' not found at all!")

# Fix 4: render call - add manifestantes render call after ayuda overlay
idx = find_line('self.renderizar_overlay_ayuda()')
if idx >= 0:
    # Check if already has manifestantes render
    if any('_renderizar_manifestantes' in text[j] for j in range(idx, min(len(text), idx+5))):
        print("[SKIP] render call already has manifestantes")
    else:
        # Find the empty line after ayuda call, before flip
        # The section is: ayuda() / empty / flip()
        found_flip = False
        for j in range(idx+1, min(len(text), idx+6)):
            if 'pygame.display.flip()' in text[j]:
                text[j:j] = [
                    '        if self.manifestantes and not self.mostrando_ayuda and not self.mostrando_resumen:',
                    '            self._renderizar_manifestantes()',
                    '',
                ]
                changes += 1
                found_flip = True
                print("[OK] render call")
                break
        if not found_flip:
            print("[FAIL] render call - flip not found after ayuda")
else:
    print("[FAIL] render call - ayuda not found")

# Fix 5: HUD felicidad - find presion line by different method
# Search for "Presi" with the unicode char or just text
for i, line in enumerate(text):
    if 'Presi' in line and 'recursos.presion' in line:
        print(f"  Found Presion at line {i}: {line[:50]}")
        # Check if felicidad already added
        if any('Felicidad' in text[j] for j in range(i, i+5)):
            print("[SKIP] HUD felicidad already added")
        else:
            # Find the closing ] 
            for j in range(i, min(len(text), i+10)):
                stripped = text[j].strip()
                if stripped == ']':  # End of recursos_data
                    text[j:j] = [
                        '            ("\\U0001f60a Felicidad", f"{recursos.felicidad}%",',
                        '             Config.COLOR_TEXTO_VERDE if recursos.felicidad >= 70 else (Config.COLOR_TEXTO_AMARILLO if recursos.felicidad >= 35 else Config.COLOR_TEXTO_ROJO)),',
                    ]
                    changes += 1
                    print("[OK] HUD felicidad")
                    break
        break
else:
    print("[FAIL] HUD - no presion line found")

# Fix 6: Resumen visual
idx = find_line('txt_pob2 = r.fuente_mediana.render')
if idx >= 0:
    # Find the blit line after it
    for j in range(idx, min(len(text), idx + 5)):
        if 'pantalla.blit(txt_pob2, (cx + 30, cy + 270))' in text[j]:
            # Check if already has felicidad
            if any('fel_color' in text[k] for k in range(j, min(len(text), j+15))):
                print("[SKIP] resumen visual already has felicidad")
            else:
                text[j+1:j+1] = [
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
                changes += 1
                print("[OK] resumen visual")
            break
    else:
        print("[FAIL] resumen visual - blit line not found")
else:
    print("[FAIL] resumen visual - txt_pob2 not found")

# Write back
out_lines = [l.encode('utf-8') for l in text]
raw_out = b'\r\n'.join(out_lines) + b'\r\n'
with open(filepath, 'wb') as f:
    f.write(raw_out)

print(f"\n[DONE] {changes} cambios adicionales")
