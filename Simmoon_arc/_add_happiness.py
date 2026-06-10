#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
base_dir = os.path.dirname(os.path.abspath(__file__))
filepath = os.path.join(base_dir, 'juego_simmoon.py')

with open(filepath, 'rb') as f:
    raw = f.read()

# Normalize \r\n to \n for consistent string matching
content = raw.replace(b'\r\n', b'\n').decode('utf-8')
changes = 0

def apply(old_str, new_str, desc):
    global content, changes
    if old_str in content:
        content = content.replace(old_str, new_str, 1)
        changes += 1
        print(f"[OK] {desc}")
    else:
        print(f"[FAIL] {desc}")

# 1. Config: constantes de felicidad
old = "    DIAS_LUZ: int = 14\n    DIAS_NOCHE: int = 14"
new = old + "\n\n    # Felicidad de colonos\n    FELICIDAD_INICIAL: int = 65\n    FELICIDAD_MAX: int = 100\n    FELICIDAD_MIN: int = 0\n    FELICIDAD_UMBRAL_CONTENTO: int = 70\n    FELICIDAD_UMBRAL_ENOJADO: int = 35\n    BONUS_FELICIDAD: float = 1.25\n    PENALTY_FELICIDAD: float = 0.75"
apply(old, new, "Config constantes")

# 2. TipoEdificio: produce_felicidad
old = "    produce_presion: int = 0        # Presi?n generada (positivo) o consumida (negativo)\n    mantenimiento: int = 5"
new = "    produce_presion: int = 0\n    produce_felicidad: int = 0\n    mantenimiento: int = 5"
apply(old, new, "TipoEdificio produce_felicidad")

# 3. Recursos.__init__
old = "        self.poblacion = 10\n        self.turno = 0"
new = "        self.poblacion = 10\n        self.turno = 0\n        self.felicidad = Config.FELICIDAD_INICIAL\n        self.bono_produccion = 1.0"
apply(old, new, "Recursos felicidad")

# 4. actualizar_balance
old = "        self.energia = self.energia_total\n        self.oxigeno = self.oxigeno_total\n        self.agua = self.agua_total\n        self.presion = self.presion_total"
new = "        # Aplicar bono/penalidad por felicidad\n        self.energia = int(self.energia_total * self.bono_produccion)\n        self.oxigeno = int(self.oxigeno_total * self.bono_produccion)\n        self.agua = int(self.agua_total * self.bono_produccion)\n        self.presion = int(self.presion_total * self.bono_produccion)"
apply(old, new, "actualizar_balance bono")

# 5. manifestantes init
old = "        self.mostrando_info_zona = False\n\n        # Tutorial y ciclo lunar"
new = "        self.mostrando_info_zona = False\n\n        # Estado de manifestaciones\n        self.manifestantes: List[Dict] = []\n\n        # Tutorial y ciclo lunar"
apply(old, new, "manifestantes init")

# 6. procesar_siguiente_turno
o_chr = chr(243)  # ó
old = f"        # Variables de depuraci{o_chr}n\n        edificios_activos = [e for e in self.mapa.edificios if e.activo]\n        if self.es_de_noche:\n            produccion_extra = -energia_solar\n        else:\n            produccion_extra = 0"
new = f"""        # --- Calculo de Felicidad ---
        felicidad = Config.FELICIDAD_INICIAL
        suficiencia = 0
        for r_actual, r_total in [
            (self.recursos.energia_total, max(1, abs(self.recursos.energia_total))),
            (self.recursos.oxigeno_total, max(1, abs(self.recursos.oxigeno_total))),
            (self.recursos.agua_total, max(1, abs(self.recursos.agua_total))),
            (self.recursos.presion_total, max(1, abs(self.recursos.presion_total))),
        ]:
            if r_total > 0:
                suficiencia += min(7.5, (r_actual / r_total) * 5)
            elif r_total < -5:
                suficiencia -= 5
            else:
                suficiencia += 3
        felicidad += max(-20, min(30, suficiencia))
        fel_edificios = sum(e.tipo.produce_felicidad for e in self.mapa.edificios if e.activo)
        felicidad += min(25, fel_edificios)
        empleos_calc = sum(e.tipo.empleos for e in self.mapa.edificios if e.activo)
        if self.recursos.poblacion > 0:
            tasa_empleo = min(1.0, empleos_calc / max(1, self.recursos.poblacion * 0.6))
        else:
            tasa_empleo = 0.5
        felicidad += tasa_empleo * 15
        for r_total in [self.recursos.energia_total, self.recursos.oxigeno_total,
                        self.recursos.agua_total, self.recursos.presion_total]:
            if r_total < -10:
                felicidad -= 5
            elif r_total < 0:
                felicidad -= 2
        felicidad = max(Config.FELICIDAD_MIN, min(Config.FELICIDAD_MAX, felicidad))
        self.recursos.felicidad = int(felicidad)
        if felicidad >= Config.FELICIDAD_UMBRAL_CONTENTO:
            self.recursos.bono_produccion = Config.BONUS_FELICIDAD
        elif felicidad < Config.FELICIDAD_UMBRAL_ENOJADO:
            self.recursos.bono_produccion = Config.PENALTY_FELICIDAD
        else:
            self.recursos.bono_produccion = 1.0

        if felicidad < Config.FELICIDAD_UMBRAL_ENOJADO and self.recursos.poblacion >= 5:
            tiles_libres = [(x, y) for y in range(self.mapa.tamanio) for x in range(self.mapa.tamanio) if self.mapa.grid[y][x] is None]
            import random as rnd_h
            rnd_h.shuffle(tiles_libres)
            num_protestas = min(3 + self.recursos.poblacion // 20, len(tiles_libres))
            mensajes_p = ["QUEREMOS AIRE!", "MAS OXIGENO!", "JUSTICIA LUNAR!", "AGUA YA!", "BAJEN IMPUESTOS!", "TRABAJO DIGNO!"]
            self.manifestantes = []
            for i in range(num_protestas):
                tx, ty = tiles_libres[i % len(tiles_libres)]
                self.manifestantes.append({{
                    "x": tx, "y": ty,
                    "t_offset": rnd_h.uniform(0, 6.28),
                    "mensaje": rnd_h.choice(mensajes_p),
                    "color_hue": rnd_h.randint(0, 360),
                }})
        elif felicidad >= Config.FELICIDAD_UMBRAL_CONTENTO:
            self.manifestantes = []

        # Variables de depuraci{o_chr}n
        edificios_activos = [e for e in self.mapa.edificios if e.activo]
        if self.es_de_noche:
            produccion_extra = -energia_solar
        else:
            produccion_extra = 0"""
apply(old, new, "procesar_siguiente_turno felicidad")

# 7. Render call
old = "        if self.mostrando_ayuda:\n            self.renderizar_overlay_ayuda()\n\n        pygame.display.flip()"
new = "        if self.mostrando_ayuda:\n            self.renderizar_overlay_ayuda()\n\n        if self.manifestantes and not self.mostrando_ayuda and not self.mostrando_resumen:\n            self._renderizar_manifestantes()\n\n        pygame.display.flip()"
apply(old, new, "render call")

# 8. Method
old = "    def renderizar_overlay_ayuda(self) -> None:"
method = """    def _renderizar_manifestantes(self) -> None:
        try:
            ahora = pygame.time.get_ticks() / 1000.0
            tam = int(Config.TAMANIO_TILE * self.camara.zoom)
            r = self.renderizador
            for m in self.manifestantes:
                px, py = self.camara.iso_a_pantalla(m["x"], m["y"])
                if px < -tam or px > self.pantalla.get_width() + tam:
                    continue
                if py < -tam or py > self.pantalla.get_height() + tam:
                    continue
                flotar = math.sin(ahora * 1.5 + m["t_offset"]) * 12
                balanceo = math.sin(ahora * 0.8 + m["t_offset"]) * 4
                hue = m["color_hue"]
                r_col = min(255, hue % 360 // 2 + 30)
                g_col = min(255, (hue * 7) % 200 + 40)
                b_col = min(255, (hue * 3) % 200 + 100)
                cx_px = int(px + balanceo)
                cy_px = int(py - tam // 4 + flotar - 10)
                pygame.draw.ellipse(self.pantalla, (r_col, g_col, b_col), (cx_px - 8, cy_px - 20, 16, 24))
                pygame.draw.circle(self.pantalla, (200, 210, 220), (cx_px, cy_px - 28), 8)
                pygame.draw.circle(self.pantalla, (160, 180, 200), (cx_px, cy_px - 28), 8, 2)
                pygame.draw.ellipse(self.pantalla, (120, 200, 255), (cx_px - 5, cy_px - 32, 10, 7))
                cartel_x = cx_px + 14
                cartel_y = cy_px - 32
                pygame.draw.line(self.pantalla, (180, 150, 100), (cartel_x, cartel_y + 40), (cartel_x, cartel_y - 10), 2)
                lineas = m["mensaje"].split("\\\\n")
                alto_cartel = len(lineas) * 14 + 8
                ancho_cartel = max((len(l) for l in lineas), default=10) * 7 + 8
                cartel_surf = pygame.Surface((ancho_cartel, alto_cartel), pygame.SRCALPHA)
                cartel_surf.fill((230, 80, 80, 220))
                pygame.draw.rect(cartel_surf, (200, 50, 50), (0, 0, ancho_cartel, alto_cartel), 2)
                for i, linea in enumerate(lineas):
                    txt = r.fuente_pequenia.render(linea.strip(), True, (255, 255, 255))
                    cartel_surf.blit(txt, (4, 4 + i * 14))
                self.pantalla.blit(cartel_surf, (cartel_x - ancho_cartel // 2, cartel_y + flotar * 0.5 + 10))
                exc_txt = r.fuente_grande.render(chr(9888), True, (255, 80, 80))
                exc_alpha = int(abs(math.sin(ahora * 3 + m["t_offset"])) * 200 + 55)
                exc_txt.set_alpha(exc_alpha)
                self.pantalla.blit(exc_txt, (cx_px - 18, cy_px - 60 + flotar * 0.3))
        except Exception:
            pass

    def renderizar_overlay_ayuda(self) -> None:"""
apply(old, method, "renderizar_manifestantes method")

# 9. HUD felicidad
idx = content.find('"\\U0001f4a8 Presi')
if idx >= 0:
    end_idx = content.find('        ]', idx)
    if end_idx >= 0:
        old_sect = content[idx:end_idx + 8]
        new_sect = old_sect.rstrip() + '\n            ("\\U0001f60a Felicidad", f"{recursos.felicidad}%",\n             Config.COLOR_TEXTO_VERDE if recursos.felicidad >= 70 else (Config.COLOR_TEXTO_AMARILLO if recursos.felicidad >= 35 else Config.COLOR_TEXTO_ROJO)),\n        '
        content = content.replace(old_sect, new_sect, 1)
        changes += 1
        print("[OK] HUD felicidad")
    else:
        print("[FAIL] HUD - no end marker")
else:
    print("[FAIL] HUD - no presion marker")

# 10. Resumen dict
old = '            "presion": self.recursos.presion_total,\n            "es_noche": self.es_de_noche,'
new = '            "presion": self.recursos.presion_total,\n            "felicidad": self.recursos.felicidad,\n            "bono": self.recursos.bono_produccion,\n            "es_noche": self.es_de_noche,'
apply(old, new, "resumen dict")

# 11. Resumen visual
idx = content.find('pantalla.blit(txt_pob2, (cx + 30, cy + 270))')
if idx >= 0:
    old_line = 'pantalla.blit(txt_pob2, (cx + 30, cy + 270))'
    new_lines = old_line + '\n                fel_color = Config.COLOR_TEXTO_VERDE if self.recursos.felicidad >= 70 else (Config.COLOR_TEXTO_AMARILLO if self.recursos.felicidad >= 35 else Config.COLOR_TEXTO_ROJO)\n                txt_fel = r.fuente_mediana.render("\\U0001f60a Felicidad: " + str(self.recursos.felicidad) + "%", True, fel_color)\n                pantalla.blit(txt_fel, (cx + 30, cy + 300))\n                if self.recursos.bono_produccion != 1.0:\n                    if self.recursos.bono_produccion > 1.0:\n                        bono_str = "\\U0001f4c8 +" + str(int((self.recursos.bono_produccion - 1) * 100)) + "% produccion"\n                    else:\n                        bono_str = "\\U0001f4c9 -" + str(int((1 - self.recursos.bono_produccion) * 100)) + "% produccion"\n                    txt_bono = r.fuente_pequenia.render(bono_str, True, Config.COLOR_TEXTO_AMARILLO)\n                    pantalla.blit(txt_bono, (cx + 30, cy + 325))'
    content = content.replace(old_line, new_lines, 1)
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
    i = content.find('"' + bid + '"')
    if i < 0:
        print(f"  SKIP {bid}")
        continue
    section = content[i:i + 600]
    for line in section.split('\n'):
        if line.strip().startswith('descripcion='):
            indent = line[:len(line) - len(line.lstrip())]
            fel_line = indent + 'produce_felicidad=' + str(val) + ',\n'
            content = content.replace(line, fel_line + line, 1)
            print(f"  OK {bid} = {val}")
            break

# Write back with \r\n line endings
raw_out = content.encode('utf-8').replace(b'\n', b'\r\n')
with open(filepath, 'wb') as f:
    f.write(raw_out)

print(f"\n[DONE] {changes} cambios principales")
print("File written with CRLF line endings")
