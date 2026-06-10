# -*- coding: utf-8 -*-
"""
Script v3: Aplica tutorial interactivo a juego_simmoon.py
Usa busqueda posicional (find) con contenido minimo, no compara whitespace exacto.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RUTA = "Simmoon_arc/juego_simmoon.py"

with open(RUTA, encoding="utf-8", newline='') as f:
    content = f.read()

changes = 0

def apply(old, new, label):
    """Replace exact old string with new, report result."""
    global changes
    if old in content:
        content.replace(old, new, 1)
        changes += 1
        print("+OK", label)
        return True
    else:
        print("-FAIL", label)
        return False

# Normalize line endings for easier searching
c = content.replace('\r\n', '\n')

def find_and_replace(search_for, replacement, label):
    """Find a substring and replace the surrounding line context."""
    global changes
    idx = c.find(search_for)
    if idx < 0:
        print("-FAIL", label, "(pattern not found)")
        return False
    # Find start of current line
    line_start = c.rfind('\n', 0, idx) + 1
    # Find end of what to replace
    replace_end = idx + len(search_for)
    old = c[line_start:replace_end]
    c = c[:line_start] + replacement + c[replace_end:]
    changes += 1
    print("+OK", label)
    return True

def replace_line_after(search_for, added_lines, label):
    """Find a line and insert text after it."""
    global changes
    idx = c.find(search_for)
    if idx < 0:
        print("-FAIL", label)
        return False
    line_end = c.find('\n', idx)
    # Insert after the newline
    insert_pos = line_end + 1
    c = c[:insert_pos] + added_lines + c[insert_pos:]
    changes += 1
    print("+OK", label)
    return True

# ─── 1. INIT section ─────────────────────────────────────────────
old_init = "# Tutorial y ciclo lunar\n\n        self.mostrando_ayuda = True"
new_init = ("# Tutorial interactivo paso a paso\n\n"
    "        self.tutorial_activo = True   # Tutorial al inicio\n"
    "        self.tutorial_paso = 0        # 0=bienvenida, 1-6=pasos, 7=final\n"
    "        self.tutorial_wasd_hecho = False\n"
    "        self.tutorial_zoom_hecho = False\n"
    "        self.tutorial_b_hecho = False\n"
    "        self.tutorial_click_hecho = False\n"
    "        self.tutorial_espacio_hecho = False\n"
    "        self.tutorial_z_hecho = False\n"
    "        self.mostrando_ayuda = False  # Ayuda estatica con tecla H")
if old_init in c:
    c = c.replace(old_init, new_init, 1)
    changes += 1
    print("+OK INIT section")
else:
    print("-FAIL INIT section")

# ─── 2. ESC handler ──────────────────────────────────────────────
old_esc = 'if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:\n\n                    if self.mostrando_ayuda:'
new_esc = ('if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:\n\n'
    '                    if self.tutorial_activo and self.tutorial_paso == 0:\n'
    '                        self.tutorial_paso = 1\n\n'
    '                    elif self.tutorial_activo and self.tutorial_paso >= 7:\n'
    '                        self.tutorial_activo = False\n'
    '                        self.tutorial_paso = 0\n\n'
    '                    elif self.mostrando_ayuda:')
if old_esc in c:
    c = c.replace(old_esc, new_esc, 1)
    changes += 1
    print("+OK ESC handler")
else:
    print("-FAIL ESC handler")

# ─── 3. H key handler ────────────────────────────────────────────
old_h = "# Alternar pantalla de ayuda\n\n                    self.mostrando_ayuda = not self.mostrando_ayuda"
new_h = ("# Alternar ayuda estatica (H)\n\n"
    "                    if self.tutorial_activo:\n"
    "                        self.tutorial_activo = False\n"
    "                        self.mostrando_ayuda = True\n"
    "                    else:\n"
    "                        self.mostrando_ayuda = not self.mostrando_ayuda")
if old_h in c:
    c = c.replace(old_h, new_h, 1)
    changes += 1
    print("+OK H key handler")
else:
    print("-FAIL H key handler")

# ─── 4. K_LEFT handler (step 1) ──────────────────────────────────
# Add tutorial detection after camara.mover(-1, 0)
left_marker = "self.camara.mover(-1, 0)"
left_extra = "\n                    if self.tutorial_activo and self.tutorial_paso == 1:\n                        self.tutorial_wasd_hecho = True\n                        self.tutorial_paso = 2"
# Find the line and replace it
idx_left = c.find(left_marker)
if idx_left >= 0:
    line_end = c.find('\n', idx_left)
    c = c[:line_end] + left_extra + c[line_end:]
    changes += 1
    print("+OK K_LEFT handler")
else:
    print("-FAIL K_LEFT handler")

# Also add to K_RIGHT
right_marker = "self.camara.mover(1, 0)"
idx_right = c.find(right_marker)
if idx_right >= 0 and idx_right != idx_left:  # Make sure it's a different occurrence
    line_end = c.find('\n', idx_right)
    c = c[:line_end] + left_extra + c[line_end:]  # Same logic
    changes += 1
    print("+OK K_RIGHT handler")
else:
    print("-FAIL K_RIGHT handler")

# ─── 5. MOUSEWHEEL handler (step 2) ──────────────────────────────
wheel_marker = "self.camara.acercar(evento.y * 0.15)"
wheel_extra = "\n                if self.tutorial_activo and self.tutorial_paso == 2:\n                    self.tutorial_zoom_hecho = True\n                    self.tutorial_paso = 3"
idx_wheel = c.find(wheel_marker)
if idx_wheel >= 0:
    line_end = c.find('\n', idx_wheel)
    c = c[:line_end] + wheel_extra + c[line_end:]
    changes += 1
    print("+OK MOUSEWHEEL handler")
else:
    print("-FAIL MOUSEWHEEL handler")

# ─── 6. SPACE handler (paso 0 + paso 5) ──────────────────────────
old_space = "elif evento.key == pygame.K_SPACE:\n\n                    self.procesar_siguiente_turno()"
new_space = ("elif evento.key == pygame.K_SPACE:\n\n"
    "                    if self.tutorial_activo and self.tutorial_paso == 0:\n"
    "                        self.tutorial_paso = 1\n"
    "                    elif self.tutorial_activo and self.tutorial_paso == 5:\n"
    "                        self.tutorial_espacio_hecho = True\n"
    "                        self.tutorial_paso = 6\n"
    "                    else:\n"
    "                        self.procesar_siguiente_turno()")
if old_space in c:
    c = c.replace(old_space, new_space, 1)
    changes += 1
    print("+OK SPACE handler")
else:
    print("-FAIL SPACE handler")

# ─── 7. B key handler (step 3) ───────────────────────────────────
b_marker = "self.edificio_seleccionado = None"
b_extra = "\n                    if self.tutorial_activo and self.tutorial_paso == 3:\n                        self.tutorial_b_hecho = True\n                        self.tutorial_paso = 4"
# Find the RIGHT occurrence of this marker (the one in B key handler, not in __init__)
idx_b = c.find(b_marker)
if idx_b >= 0:
    # Skip the first occurrence (in __init__), find the second (in B handler)
    idx_b2 = c.find(b_marker, idx_b + len(b_marker))
    if idx_b2 >= 0:
        b_line_end = c.find('\n', idx_b2)
        c = c[:b_line_end] + b_extra + c[b_line_end:]
        changes += 1
        print("+OK B key handler")
    else:
        print("-FAIL B key handler (only one occurrence found)")
else:
    print("-FAIL B key handler")

# ─── 8. Z key handler (step 6) ───────────────────────────────────
z_marker = "self.modo_vender = False"
z_extra = "\n                    if self.tutorial_activo and self.tutorial_paso == 6:\n                        self.tutorial_z_hecho = True\n                        self.tutorial_paso = 7"
# Find the Z occurrence (not the B occurrence)
idx_z = c.find(z_marker)
if idx_z >= 0:
    # Skip B handler's occurrence, find Z's
    idx_z2 = c.find(z_marker, idx_z + len(z_marker))
    if idx_z2 >= 0:
        z_line_end = c.find('\n', idx_z2)
        c = c[:z_line_end] + z_extra + c[z_line_end:]
        changes += 1
        print("+OK Z key handler")
    else:
        print("-FAIL Z key handler")
else:
    print("-FAIL Z key handler")

# ─── 9. BUILD placement handler (step 4) ─────────────────────────
# Find the message with unicode checkmark
construido_marker = f"construido"
# Look for the f-string with this text
idx_construido = c.find(construido_marker)
if idx_construido >= 0:
    # Find line start
    line_s = c.rfind('\n', 0, idx_construido) + 1
    line_e = c.find('\n', idx_construido)
    # Check it has the right context
    context = c[line_s:line_e]
    if 'nombre' in context:
        c = c[:line_e] + "\n                    if self.tutorial_activo and self.tutorial_paso == 4:\n                        self.tutorial_click_hecho = True\n                        self.tutorial_paso = 5" + c[line_e:]
        changes += 1
        print("+OK BUILD placement handler")
    else:
        print("-FAIL BUILD handler (wrong context for construido)")
else:
    print("-FAIL BUILD handler (construido not found)")

# ─── 10. Click skip button handler ───────────────────────────────
click_marker = "elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:"
idx_click = c.find(click_marker)
if idx_click >= 0:
    click_lines = ('\n                # Click en boton Saltar del tutorial\n'
        '                if self.tutorial_activo and 1 <= self.tutorial_paso <= 6:\n'
        '                    mx, my = evento.pos\n'
        '                    pant_h = self.pantalla.get_height()\n'
        '                    pant_w = self.pantalla.get_width()\n'
        '                    skip_y_top = pant_h - 130 + 8\n'
        '                    if mx > pant_w - 140 and skip_y_top <= my <= skip_y_top + 28:\n'
        '                        self.tutorial_activo = False\n'
        '                        self.tutorial_paso = 0\n')
    # Find the self.tile_hover_x line after the click handler
    hover_marker = "self.tile_hover_x, self.tile_hover_y = gx, gy"
    idx_hover = c.find(hover_marker, idx_click)
    if idx_hover >= 0:
        hover_end = c.find('\n', idx_hover)
        c = c[:hover_end] + click_lines + c[hover_end:]
        changes += 1
        print("+OK CLICK skip button")
    else:
        print("-FAIL CLICK skip button (hover not found)")
else:
    print("-FAIL CLICK skip button")

# ─── 11. Replace renderizar_overlay_ayuda method ─────────────────
idx_start = c.find("    def renderizar_overlay_ayuda(self) -> None:")
if idx_start >= 0:
    # Find next method at same indentation
    idx_next_method = c.find("\n    def ", idx_start + 10)
    if idx_next_method < 0:
        idx_next_method = len(c)
    old_method = c[idx_start:idx_next_method]
    
    new_code = '''    def renderizar_tutorial(self) -> None:
        """Renderiza el tutorial interactivo paso a paso."""
        if not self.tutorial_activo:
            return

        paso = self.tutorial_paso
        r = self.renderizador
        pant_w, pant_h = self.pantalla.get_width(), self.pantalla.get_height()

        pasos = [
            { "titulo": "SIMMOON - Colonia Lunar", "fullscreen": True,
              "texto": ["Eres el Comisionado de la primera colonia en la Luna.","","Tu mision: construir, gestionar recursos y hacer","prosperar este asentamiento fronterizo.","","Este tutorial te guiara en los primeros pasos.","Vamos alla, Comisionado!"] },
            { "titulo": "Paso 1/6 - CAMARA", "fullscreen": False,
              "texto": ["Usa WASD o las FLECHAS del teclado para mover","la camara por el mapa de la colonia.","","Explora un poco - veras la carretera central","que cruza el asentamiento de este a oeste."] },
            { "titulo": "Paso 2/6 - ZOOM", "fullscreen": False,
              "texto": ["Usa la RUEDA del raton para acercar y alejar.","","Acerkate para ver los detalles de los edificios,","alejate para tener una vista panoramica."] },
            { "titulo": "Paso 3/6 - MODO CONSTRUIR", "fullscreen": False,
              "texto": ["Presiona la tecla B para entrar en modo CONSTRUIR.","","Veras que el panel lateral se ilumina y aparecen","los edificios disponibles para construir."] },
            { "titulo": "Paso 4/6 - COLOCAR", "fullscreen": False,
              "texto": ["Selecciona un edificio publico del panel lateral","(ej: Paneles Solares en la categoria Energia)","y haz CLICK IZQUIERDO en el mapa para colocarlo.","","Los edificios publicos se colocan directamente.","Los privados necesitan zonificacion (Paso 6)."] },
            { "titulo": "Paso 5/6 - AVANZAR TURNO", "fullscreen": False,
              "texto": ["Presiona ESPACIO o haz click en SIGUIENTE TURNO","para avanzar un turno.","","Cada turno: colonos producen, pagan impuestos,","y la economia de la colonia evoluciona."] },
            { "titulo": "Paso 6/6 - ZONIFICAR", "fullscreen": False,
              "texto": ["Presiona la tecla Z para entrar en modo ZONIFICAR.","","Elige un rubro (Alojamiento, Comercial, Industrial,","Ecologico) y pinta areas en el mapa.","","Al avanzar turno, emprendedores construiran","edificios privados automaticamente en las zonas."] },
            { "titulo": "MISION CUMPLIDA, COMISIONADO!", "fullscreen": True,
              "texto": ["Has completado el tutorial basico.","","Recuerda: gestiona Energia, Oxigeno, Agua y Presion.","Construye servicios de emergencia contra meteoritos.","Exporta excedentes, importa lo que falte.","","Presiona ESC o H para mas ayuda en cualquier momento.","Buena suerte en la Luna!"] },
        ]

        p = pasos[min(paso, len(pasos) - 1)]

        if paso == 0 or paso >= 7:
            # Full-screen overlay
            fondo = pygame.Surface((pant_w, pant_h), pygame.SRCALPHA)
            fondo.fill((0, 0, 0, 200))
            self.pantalla.blit(fondo, (0, 0))

            ancho, alto = 500, 380
            cx, cy = (pant_w - ancho) // 2, (pant_h - alto) // 2
            rect_c = pygame.Rect(cx, cy, ancho, alto)
            pygame.draw.rect(self.pantalla, Config.COLOR_PANEL, rect_c, border_radius=14)
            pygame.draw.rect(self.pantalla, Config.COLOR_PANEL_BORDE, rect_c, 2, border_radius=14)

            x, y = cx + 30, cy + 25
            titulo = r.fuente_grande.render(p["titulo"], True, Config.COLOR_TEXTO_AMARILLO)
            self.pantalla.blit(titulo, (x, y))
            y += 50

            for linea in p["texto"]:
                if linea == "":
                    y += 8
                    continue
                color = Config.COLOR_TEXTO_VERDE if "Presiona" in linea else Config.COLOR_TEXTO
                txt = r.fuente_mediana.render(linea, True, color)
                self.pantalla.blit(txt, (x + 10, y))
                y += 28

            y = cy + alto - 35
            hint_text = "Presiona ESPACIO o ESC para continuar" if paso == 0 else "Presiona ESC para cerrar"
            hint = r.fuente_pequenia.render(hint_text, True, Config.COLOR_TEXTO)
            self.pantalla.blit(hint, (x, y))
        else:
            # Bottom instruction bar (no bloquea la interaccion)
            alto_barra = 120
            barra_y = pant_h - alto_barra - 10

            fondo = pygame.Surface((pant_w - 20, alto_barra), pygame.SRCALPHA)
            fondo.fill((*Config.COLOR_PANEL, 230))
            self.pantalla.blit(fondo, (10, barra_y))
            pygame.draw.rect(self.pantalla, (80, 60, 140), (10, barra_y, pant_w - 20, alto_barra), 2, border_radius=8)

            x, y = 25, barra_y + 12
            step_tag = r.fuente_pequenia.render(p["titulo"], True, Config.COLOR_TEXTO_VERDE)
            self.pantalla.blit(step_tag, (x, y))

            prog_w = pant_w - 80
            prog_y = barra_y + 30
            pygame.draw.rect(self.pantalla, (40, 40, 60), (x, prog_y, prog_w, 8), border_radius=4)
            fill_w = int(prog_w * (min(paso, 6) / 6))
            pygame.draw.rect(self.pantalla, (80, 200, 120), (x, prog_y, fill_w, 8), border_radius=4)

            y = barra_y + 48
            for linea in p["texto"]:
                if linea == "":
                    y += 4
                    continue
                color = Config.COLOR_TEXTO_AMARILLO if "Presiona" in linea else Config.COLOR_TEXTO
                txt = r.fuente_pequenia.render(linea, True, color)
                self.pantalla.blit(txt, (x, y))
                y += 20

            # Skip button
            btn_skip = pygame.Rect(pant_w - 130, barra_y + 8, 100, 24)
            pygame.draw.rect(self.pantalla, (60, 40, 40), btn_skip, border_radius=6)
            txt_skip = r.fuente_pequenia.render("Saltar", True, (255, 100, 100))
            self.pantalla.blit(txt_skip, (pant_w - 120, barra_y + 10))

    def renderizar_ayuda_estatica(self) -> None:
        """Renderiza la pantalla de ayuda estatica (tecla H)."""
        pant_w, pant_h = self.pantalla.get_width(), self.pantalla.get_height()
        fondo = pygame.Surface((pant_w, pant_h), pygame.SRCALPHA)
        fondo.fill((0, 0, 0, 220))
        self.pantalla.blit(fondo, (0, 0))

        r = self.renderizador
        cx, cy = 60, 30

        txt = r.fuente_titulo.render("SIMMOON - Guia del Comisionado", True, Config.COLOR_TEXTO_AMARILLO)
        self.pantalla.blit(txt, (cx, cy))
        cy += 55

        txt = r.fuente_grande.render("Controles", True, Config.COLOR_TEXTO_VERDE)
        self.pantalla.blit(txt, (cx, cy))
        cy += 32

        controles = [
            "WASD / Flechas:  Mover camara por la colonia",
            "Rueda raton:     Zoom (acercar/alejar)",
            "Click izquierdo:  Colocar edificio / pintar zona",
            "Click derecho:    Cancelar / borrar zona",
            "B:               Modo construir",
            "V:               Modo vender (click en edificio)",
            "Z:               Modo zonificar (pintar zonas)",
            "H:               Alternar esta ayuda",
            "F:               Panel de finanzas (ultimos 10 turnos)",
            "Espacio:         Siguiente turno",
            "ESC:             Salir / cerrar ventana",
        ]
        for ctrl in controles:
            txt = r.fuente_mediana.render(ctrl, True, Config.COLOR_TEXTO)
            self.pantalla.blit(txt, (cx, cy))
            cy += 26

        cy += 10
        pygame.draw.line(self.pantalla, Config.COLOR_PANEL_BORDE, (cx, cy), (pant_w - 60, cy), 1)
        cy += 15

        txt = r.fuente_grande.render("Como Jugar?", True, Config.COLOR_TEXTO_VERDE)
        self.pantalla.blit(txt, (cx, cy))
        cy += 32

        instrucciones = [
            "1. ZONIFICA: Presiona Z, elige un rubro y pinta areas en el mapa",
            "2. AVANZA: Presiona Espacio para avanzar un turno",
            "3. CONSTRUYE: Los edificios privados se auto-construyen en sus zonas",
            "4. GESTIONA: Manten Energia, Oxigeno, Agua y Presion en positivo",
            "5. RECAUDACION: Ganas creditos por impuestos, alquileres y exportaciones",
            "6. PROTEJE: Construye servicios de emergencia contra meteoritos y tormentas",
        ]
        for instr in instrucciones:
            txt = r.fuente_mediana.render(instr, True, Config.COLOR_TEXTO)
            self.pantalla.blit(txt, (cx, cy))
            cy += 26

        cy += 10
        pygame.draw.line(self.pantalla, Config.COLOR_PANEL_BORDE, (cx, cy), (pant_w - 60, cy), 1)
        cy += 15
        txt = r.fuente_pequenia.render("Presiona ESC para cerrar o H para alternar", True, Config.COLOR_TEXTO)
        self.pantalla.blit(txt, (cx, cy))

    def renderizar_overlay_ayuda(self) -> None:
        """Alias legacy: redirects to tutorial system."""
        if self.tutorial_activo:
            self.renderizar_tutorial()
        else:
            self.renderizar_ayuda_estatica()'''
    
    c = c[:idx_start] + new_code + c[idx_next_method:]
    changes += 1
    print("+OK RENDER method replaced")
else:
    print("-FAIL RENDER method")

# ─── 12. Update renderizar() call ────────────────────────────────
old_call = "if self.mostrando_ayuda:\n\n            self.renderizar_overlay_ayuda()"
new_call = ("if self.tutorial_activo:\n"
    "            self.renderizar_tutorial()\n\n"
    "        elif self.mostrando_ayuda:\n"
    "            self.renderizar_ayuda_estatica()")
if old_call in c:
    c = c.replace(old_call, new_call, 1)
    changes += 1
    print("+OK RENDER CALL")
else:
    print("-FAIL RENDER CALL")

# ─── 13. Manifestantes condition ─────────────────────────────────
old_manif = "if self.manifestantes and not self.mostrando_ayuda and not self.mostrando_resumen:"
new_manif = "if self.manifestantes and not self.tutorial_activo and not self.mostrando_ayuda and not self.mostrando_resumen:"
if old_manif in c:
    c = c.replace(old_manif, new_manif, 1)
    changes += 1
    print("+OK MANIFESTANTES condition")
else:
    print("-FAIL MANIFESTANTES condition")

# ─── Write back with \r\n ────────────────────────────────────────
with open(RUTA, "w", encoding="utf-8", newline='') as f:
    f.write(c.replace('\n', '\r\n'))

print("")
print("=" * 40)
print("Cambios aplicados: %d" % changes)
print("=" * 40)
