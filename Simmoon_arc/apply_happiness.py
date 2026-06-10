#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply happiness system - line-by-line patching."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
base_dir = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(base_dir, 'juego_simmoon.py')

with open(filepath, 'rb') as f:
    raw = f.read()

# Work with lines split by \r\n
lines = raw.replace(b'\r', b'').split(b'\n')
# Remove trailing empty line
if lines and lines[-1] == b'':
    lines = lines[:-1]

text_lines = [l.decode('utf-8') for l in lines]
changes = 0

def find_line(pattern, start=0):
    """Find first line containing pattern."""
    for i in range(start, len(text_lines)):
        if pattern in text_lines[i]:
            return i
    return -1

def replace_lines(old_lines, new_lines, desc):
    """Replace a sequence of lines with new lines."""
    global changes
    old_len = len(old_lines)
    for i in range(len(text_lines) - old_len + 1):
        if text_lines[i:i+old_len] == old_lines:
            text_lines[i:i+old_len] = new_lines
            changes += 1
            print(f"[OK] {desc}")
            return True
    print(f"[FAIL] {desc}")
    return False

# 1. Config: add happiness constants
idx = find_line('DIAS_NOCHE: int = 14')
if idx >= 0:
    new_config = [
        '    # Felicidad de colonos',
        '    FELICIDAD_INICIAL: int = 65',
        '    FELICIDAD_MAX: int = 100',
        '    FELICIDAD_MIN: int = 0',
        '    FELICIDAD_UMBRAL_CONTENTO: int = 70',
        '    FELICIDAD_UMBRAL_ENOJADO: int = 35',
        '    BONUS_FELICIDAD: float = 1.25',
        '    PENALTY_FELICIDAD: float = 0.75',
    ]
    # Insert after the DIAS_NOCHE line, with a blank line
    text_lines[idx+1:idx+1] = [''] + new_config
    changes += 1
    print("[OK] Config constantes")
else:
    print("[FAIL] Config constantes")

# 2. TipoEdificio: add produce_felicidad
idx = find_line('produce_presion: int = 0')
if idx >= 0:
    text_lines.insert(idx + 1, '    produce_felicidad: int = 0      # Felicidad que aporta a los colonos')
    changes += 1
    print("[OK] TipoEdificio produce_felicidad")
else:
    print("[FAIL] TipoEdificio produce_felicidad")

# 3. Recursos.__init__: add felicidad
idx = find_line('self.turno = 0')
if idx >= 0:
    text_lines[idx+1:idx+1] = [
        '        self.felicidad = Config.FELICIDAD_INICIAL',
        '        self.bono_produccion = 1.0  # 1.0 = neutral, 1.25 = contentos, 0.75 = enojados',
    ]
    changes += 1
    print("[OK] Recursos felicidad")
else:
    print("[FAIL] Recursos felicidad")

# 4. actualizar_balance: apply happiness bonus
idx = find_line('self.energia = self.energia_total')
if idx >= 0 and find_line('self.presion = self.presion_total') == idx + 3:
    text_lines[idx] = '        # Aplicar bono/penalidad por felicidad'
    text_lines[idx+1] = '        self.energia = int(self.energia_total * self.bono_produccion)'
    text_lines[idx+2] = '        self.oxigeno = int(self.oxigeno_total * self.bono_produccion)'
    text_lines[idx+3] = '        self.agua = int(self.agua_total * self.bono_produccion)'
    text_lines[idx+4] = '        self.presion = int(self.presion_total * self.bono_produccion)'
    changes += 1
    print("[OK] actualizar_balance bono")
else:
    print("[FAIL] actualizar_balance bono")

# 5. manifestantes init
idx = find_line('self.mostrando_info_zona = False')
if idx >= 0:
    next_line = text_lines[idx+1] if idx+1 < len(text_lines) else ''
    if next_line.strip() == '' and idx+2 < len(text_lines) and 'Tutorial' in text_lines[idx+2]:
        text_lines[idx+1:idx+1] = [
            '',
            '        # Estado de manifestaciones',
            '        self.manifestantes: List[Dict] = []  # [{x, y, t_offset, mensaje, ...}]',
        ]
        changes += 1
        print("[OK] manifestantes init")
    else:
        print(f"[FAIL] manifestantes init - unexpected context: {next_line[:40]}")
else:
    print("[FAIL] manifestantes init")

# 6. procesar_siguiente_turno: add happiness calculation
o_chr = chr(243)  # ó
dep_line = f'# Variables de depuraci{o_chr}n'
idx = find_line(dep_line)
if idx >= 0:
    # Find the end of this section
    end_idx = idx + 6  # The section is 6 lines
    if end_idx <= len(text_lines) and 'produccion_extra' in text_lines[end_idx - 1]:
        old_section = text_lines[idx:end_idx]
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
        text_lines[idx:end_idx] = new_section
        changes += 1
        print("[OK] procesar_siguiente_turno felicidad")
    else:
        print(f"[FAIL] procesar_siguiente_turno - unexpected end")
else:
    print(f"[FAIL] procesar_siguiente_turno - dep_line not found")

# 7. Render call - add manifestantes render
idx = find_line('self.renderizar_overlay_ayuda()')
if idx >= 0:
    # Find the next line after the blank line before pygame.display.flip()
    if idx + 2 < len(text_lines) and 'pygame.display.flip()' in text_lines[idx+2]:
        text_lines[idx+1:idx+1] = [
            '',
            '        if self.manifestantes and not self.mostrando_ayuda and not self.mostrando_resumen:',
            '            self._renderizar_manifestantes()',
        ]
        changes += 1
        print("[OK] render call")
    else:
        print(f"[FAIL] render call - unexpected context")
else:
    print("[FAIL] render call")

# 8. Add method before renderizar_overlay_ayuda
idx = find_line('def renderizar_overlay_ayuda(self) -> None:')
if idx >= 0:
    method_lines = [
        '    def _renderizar_manifestantes(self) -> None:',
        '        """Renderiza colonos flotando con pancartas de protesta."""',
        '        try:',
        '            ahora = pygame.time.get_ticks() / 1000.0',
        '            tam = int(Config.TAMANIO_TILE * self.camara.zoom)',
        '            r = self.renderizador',
        '            for m in self.manifestantes:',
        '                px, py = self.camara.iso_a_pantalla(m["x"], m["y"])',
        '                if px < -tam or px > self.pantalla.get_width() + tam:',
        '                    continue',
        '                if py < -tam or py > self.pantalla.get_height() + tam:',
        '                    continue',
        '                flotar = math.sin(ahora * 1.5 + m["t_offset"]) * 12',
        '                balanceo = math.sin(ahora * 0.8 + m["t_offset"]) * 4',
        '                hue = m["color_hue"]',
        '                r_col = min(255, hue % 360 // 2 + 30)',
        '                g_col = min(255, (hue * 7) % 200 + 40)',
        '                b_col = min(255, (hue * 3) % 200 + 100)',
        '                cx_px = int(px + balanceo)',
        '                cy_px = int(py - tam // 4 + flotar - 10)',
        '                pygame.draw.ellipse(self.pantalla, (r_col, g_col, b_col), (cx_px - 8, cy_px - 20, 16, 24))',
        '                pygame.draw.circle(self.pantalla, (200, 210, 220), (cx_px, cy_px - 28), 8)',
        '                pygame.draw.circle(self.pantalla, (160, 180, 200), (cx_px, cy_px - 28), 8, 2)',
        '                pygame.draw.ellipse(self.pantalla, (120, 200, 255), (cx_px - 5, cy_px - 32, 10, 7))',
        '                cartel_x = cx_px + 14',
        '                cartel_y = cy_px - 32',
        '                pygame.draw.line(self.pantalla, (180, 150, 100), (cartel_x, cartel_y + 40), (cartel_x, cartel_y - 10), 2)',
        '                lineas = m["mensaje"].split("\\\\n")',
        '                alto_cartel = len(lineas) * 14 + 8',
        '                ancho_cartel = max((len(l) for l in lineas), default=10) * 7 + 8',
        '                cartel_surf = pygame.Surface((ancho_cartel, alto_cartel), pygame.SRCALPHA)',
        '                cartel_surf.fill((230, 80, 80, 220))',
        '                pygame.draw.rect(cartel_surf, (200, 50, 50), (0, 0, ancho_cartel, alto_cartel), 2)',
        '                for i, linea in enumerate(lineas):',
        '                    txt = r.fuente_pequenia.render(linea.strip(), True, (255, 255, 255))',
        '                    cartel_surf.blit(txt, (4, 4 + i * 14))',
        '                self.pantalla.blit(cartel_surf, (cartel_x - ancho_cartel // 2, cartel_y + flotar * 0.5 + 10))',
        '                exc_txt = r.fuente_grande.render(chr(9888), True, (255, 80, 80))',
        '                exc_alpha = int(abs(math.sin(ahora * 3 + m["t_offset"])) * 200 + 55)',
        '                exc_txt.set_alpha(exc_alpha)',
        '                self.pantalla.blit(exc_txt, (cx_px - 18, cy_px - 60 + flotar * 0.3))',
        '        except Exception:',
        '            pass',
        '',
    ]
    text_lines[idx:idx] = method_lines
    changes += 1
    print("[OK] renderizar_manifestantes method")
else:
    print("[FAIL] renderizar_manifestantes method")

# 9. HUD: add felicidad
idx = find_line('"\\U0001f4a8 Presi')
if idx >= 0:
    # Find the closing ] of the recursos_data list
    close_idx = find_line('        ]', idx)
    if close_idx > idx:
        new_hud_line = '            ("\\U0001f60a Felicidad", f"{recursos.felicidad}%",'
        new_hud_line2 = '             Config.COLOR_TEXTO_VERDE if recursos.felicidad >= 70 else (Config.COLOR_TEXTO_AMARILLO if recursos.felicidad >= 35 else Config.COLOR_TEXTO_ROJO)),'
        text_lines[close_idx:close_idx] = [new_hud_line, new_hud_line2]
        changes += 1
        print("[OK] HUD felicidad")
    else:
        print(f"[FAIL] HUD - close bracket not found")
else:
    print("[FAIL] HUD - no presion marker")

# 10. Resumen dict
idx = find_line('"es_noche": self.es_de_noche,')
if idx >= 0:
    text_lines[idx:idx] = [
        '            "felicidad": self.recursos.felicidad,',
        '            "bono": self.recursos.bono_produccion,',
    ]
    changes += 1
    print("[OK] resumen dict")
else:
    print("[FAIL] resumen dict")

# 11. Resumen visual
idx = find_line('pantalla.blit(txt_pob2, (cx + 30, cy + 270))')
if idx >= 0:
    text_lines[idx+1:idx+1] = [
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
else:
    print("[FAIL] resumen visual")

# 12. Asignar produce_felicidad a edificios
entries = {
    "misc_08": 18, "misc_07": 8, "biz_04": 8, "biz_06": 12,
    "site_03": 20, "site_09": 22, "site_10": 15, "dec_05": 5,
    "hou_03": 10, "oficio_04": 8, "oficio_05": 12, "oficio_08": 14,
    "oficio_11": 6, "civ_01": 5, "misc_10": 5, "misc_11": 5, "rsk_03": 10,
}
for bid, val in entries.items():
    idx = find_line('"' + bid + '"')
    if idx < 0:
        print(f"  SKIP {bid}")
        continue
    # Find descripcion= in the next few lines
    for j in range(idx, min(idx + 15, len(text_lines))):
        if text_lines[j].strip().startswith('descripcion='):
            indent = ' ' * (len(text_lines[j]) - len(text_lines[j].lstrip()))
            text_lines.insert(j, indent + 'produce_felicidad=' + str(val) + ',')
            print(f"  OK {bid} = {val}")
            break

# Write back with CRLF
out_lines = [l.encode('utf-8') for l in text_lines]
raw_out = b'\r\n'.join(out_lines) + b'\r\n'
with open(filepath, 'wb') as f:
    f.write(raw_out)

print(f"\n[DONE] {changes} modificaciones principales + edificios")
