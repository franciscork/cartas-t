"""
renderizador.py — Renderizador isométrico para SIMMOON

Extraído de juego_simmoon.py. Usa imports locales (lazy) para
evitar dependencias circulares con juego_simmoon.
"""
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import pygame
from simmoon_terrain import generar_tiles_terreno

# ── Lazy import helper ────────────────────────────────────────────
def _from_game(name):
    """Importa un nombre desde juego_simmoon (lazy, evita circular)."""
    import juego_simmoon as _gs
    return getattr(_gs, name)


class Renderizador:

    """Renderiza el mapa isométrico, edificios, UI y cursores."""

    

    def __init__(self, directorio_assets: str):

        self.directorio_assets = Path(directorio_assets)

        self.fuente_pequenia: Optional[pygame.font.Font] = None

        self.fuente_mediana: Optional[pygame.font.Font] = None

        self.fuente_grande: Optional[pygame.font.Font] = None

        self.fuente_titulo: Optional[pygame.font.Font] = None

        self.tile_terreno: Optional[pygame.Surface] = None

        self.tile_terreno_base: Optional[pygame.Surface] = None

        self.sprites_cache: Dict[str, pygame.Surface] = {}

        # Ciclo lunar (actualizado externamente por JuegoSimmoon)
        self.es_de_noche: bool = False
        self.contador_lunar: int = 0

        self._inicializar_fuentes()

        self._generar_tiles_terreno()

        self._cargar_terreno()

    

    def _inicializar_fuentes(self) -> None:

        """Carga las fuentes del juego."""

        try:

            self.fuente_pequenia = pygame.font.Font(None, 18)

            self.fuente_mediana = pygame.font.Font(None, 24)

            self.fuente_grande = pygame.font.Font(None, 32)

            self.fuente_titulo = pygame.font.Font(None, 48)

        except Exception:

            # Fallback a fuente por defecto de pygame

            self.fuente_pequenia = pygame.font.Font(None, 18)

            self.fuente_mediana = pygame.font.Font(None, 24)

            self.fuente_grande = pygame.font.Font(None, 32)

            self.fuente_titulo = pygame.font.Font(None, 48)

    def _generar_tiles_terreno(self) -> None:
        """Genera tiles procedurales para todos los biomas del terreno."""
        self.tiles_terreno = generar_tiles_terreno(64)

        # Hornear borde de cuadricula isometrica en cada tile
        grid_overlay = pygame.Surface((64, 64), pygame.SRCALPHA)
        color_grid = _from_game('Config').COLOR_GRID
        puntos = [(32, 0), (64, 16), (32, 32), (0, 16)]
        pygame.draw.polygon(grid_overlay, color_grid, puntos, 1)
        for tile in self.tiles_terreno.values():
            tile.blit(grid_overlay, (0, 0))

        self.tile_terreno = self.tiles_terreno.get("regolith")
        self.tile_terreno_base = self._crear_tile_base()

    

    def _cargar_terreno(self) -> None:

        """Carga los tiles de terreno base (legacy: usa procedural)."""

        pass
    def _crear_tile_base(self) -> pygame.Surface:

        """Crea un tile base semitransparente para casillas vacías."""

        surf = pygame.Surface((64, 64), pygame.SRCALPHA)

        surf.fill((40, 38, 50, 180))

        pygame.draw.rect(surf, (55, 52, 65, 100), (3, 3, 58, 58), 1)

        return surf

    

    def cargar_sprite(self, ruta_relativa: str, escala: Optional[Tuple[int, int]] = None) -> pygame.Surface:

        """Carga un sprite desde el directorio de assets, con caché.

        Prioriza versiones post-procesadas en postproc/ (auto-contraste, borde,

        paleta indexada) si existen. Si no, cae al sprite original pixelado.

        """

        clave = f"{ruta_relativa}_{escala}"

        if clave in self.sprites_cache:

            return self.sprites_cache[clave]



        # Intentar 1: sprite post-procesado (postproc/{stem}_processed.png)

        ruta_original = self.directorio_assets / ruta_relativa

        ruta_p = Path(ruta_relativa)

        ruta_postproc = self.directorio_assets / ruta_p.parent / "postproc" / f"{ruta_p.stem}_processed.png"

        ruta = ruta_postproc if ruta_postproc.exists() else ruta_original



        if ruta.exists():

            try:

                sprite = pygame.image.load(str(ruta)).convert_alpha()

                if escala:

                    sprite = pygame.transform.scale(sprite, escala)

                self.sprites_cache[clave] = sprite

                return sprite

            except pygame.error:

                pass

        

        # Sprite por defecto (cuadrado de color)

        surf = pygame.Surface((64, 64), pygame.SRCALPHA)

        surf.fill((100, 100, 150))

        pygame.draw.rect(surf, (255, 255, 255), (5, 5, 54, 54), 2)

        if escala:

            surf = pygame.transform.scale(surf, escala)

        return surf

    

    def renderizar_mapa(self, pantalla: pygame.Surface, mapa: '_from_game("Mapa")', camara: '_from_game("Camara")') -> None:

        """Renderiza el mapa isométrico completo."""

        tam = int(_from_game('Config').TAMANIO_TILE * camara.zoom)

        

        # Orden de renderizado isométrico (back-to-front, top-to-bottom)

        for y in range(mapa.tamanio):

            for x in range(mapa.tamanio):

                px, py = camara.iso_a_pantalla(x, y)

                

                # Recorte de cámara (culling) - solo renderizar lo visible

                if px < -tam or px > camara.ancho_ventana + tam:

                    continue

                if py < -tam or py > camara.alto_ventana + tam:

                    continue

                

                # Renderizar tile de terreno (por bioma)

                tipo_terreno = "regolith"

                if hasattr(mapa, "terrain") and y < len(mapa.terrain) and x < len(mapa.terrain[y]):

                    tipo_terreno = mapa.terrain[y][x]

                tile = self.tiles_terreno.get(tipo_terreno, self.tile_terreno)

                if tile:

                    tile_escalado = pygame.transform.scale(tile, (tam, tam))

                elif self.tile_terreno:

                    tile_escalado = pygame.transform.scale(self.tile_terreno, (tam, tam))

                else:

                    tile_escalado = pygame.transform.scale(self.tile_terreno_base, (tam, tam))

                

                # Sombra de elevacion

                if hasattr(mapa, "height") and y < len(mapa.height) and x < len(mapa.height[y]):

                    h = mapa.height[y][x]

                    bright = int((h - 0.5) * 40)

                    if bright != 0:

                        overlay = pygame.Surface((tam, tam), pygame.SRCALPHA)

                        if bright > 0:

                            overlay.fill((bright, bright, bright, 30))

                        else:

                            overlay.fill((-bright, -bright, -bright, 20))

                        pantalla.blit(overlay, (px - tam // 2, py - tam // 4))

                

                pantalla.blit(tile_escalado, (px - tam // 2, py - tam // 4))



                # Overlay de zona (si existe)

                zona_id = mapa.zonas[y][x]

                if zona_id and zona_id in _from_game('CATALOGO_ZONAS'):

                    zona = _from_game('CATALOGO_ZONAS')[zona_id]

                    zona_overlay = pygame.Surface((tam, tam), pygame.SRCALPHA)

                    puntos = [

                        (tam // 2, 0), (tam, tam // 4), (tam // 2, tam // 2),

                        (0, tam // 4)

                    ]

                    pygame.draw.polygon(zona_overlay, (*zona.color, 70), puntos)

                    pantalla.blit(zona_overlay, (px - tam // 2, py - tam // 4))

                

                # Renderizar edificio si existe (solo en su esquina superior-izquierda)

                edificio = mapa.grid[y][x]

                if edificio and edificio.x == x and edificio.y == y and edificio.sprite:

                    ancho_px = int(tam * edificio.ancho)

                    alto_px = int(tam * edificio.alto)

                    sprite_esc = pygame.transform.scale(edificio.sprite, (ancho_px, alto_px))

                    # Centrar el sprite en el footprint (alineado con el tile Y)

                    off_x = (ancho_px - tam) // 2

                    off_y = (alto_px - tam) // 2

                    pantalla.blit(sprite_esc, (px - tam // 2 - off_x, py - tam // 4 - off_y))

    

    def renderizar_cursor(self, pantalla: pygame.Surface, camara: '_from_game("Camara")',

                          grid_x: int, grid_y: int, valido: bool, 

                          sprite_preview: Optional[pygame.Surface] = None,

                          ancho: int = 1, alto: int = 1) -> None:

        """Renderiza el cursor de construcción multi-tile sobre el footprint apuntado."""

        tam = int(_from_game('Config').TAMANIO_TILE * camara.zoom)

        px, py = camara.iso_a_pantalla(grid_x, grid_y)

        

        # Preview del sprite escalado al footprint

        if sprite_preview:

            ancho_px = int(tam * ancho)

            alto_px = int(tam * alto)

            sprite_esc = pygame.transform.scale(sprite_preview, (ancho_px, alto_px))

            sprite_esc.set_alpha(180)

            off_x = (ancho_px - tam) // 2

            off_y = (alto_px - tam) // 2

            pantalla.blit(sprite_esc, (px - tam // 2 - off_x, py - tam // 4 - off_y))

        

        # Dibujar cursor en cada tile del footprint

        color = _from_game('Config').COLOR_TILE_HOVER[:3] if valido else _from_game('Config').COLOR_TILE_INVALIDO[:3]

        for dy in range(alto):

            for dx in range(ancho):

                tx, ty = camara.iso_a_pantalla(grid_x + dx, grid_y + dy)

                alpha = 100 if valido else 140

                cursor_surf = pygame.Surface((tam, tam), pygame.SRCALPHA)

                puntos = [

                    (tam // 2, 0), (tam, tam // 4), (tam // 2, tam // 2),

                    (0, tam // 4)

                ]

                pygame.draw.polygon(cursor_surf, (*color, alpha), puntos)

                pygame.draw.polygon(cursor_surf, (*color, 200), puntos, 2)

                pantalla.blit(cursor_surf, (tx - tam // 2, ty - tam // 4))

    

    def renderizar_panel(self, pantalla: pygame.Surface, recursos: '_from_game("Recursos")',

                         edificio_seleccionado: Optional[TipoEdificio],

                         modo_construir: bool, modo_vender: bool,

                         categoria_actual: str,

                         catalogo: Dict[str, TipoEdificio],

                         votos: Dict[str, int],

                         mouse_pos: Tuple[int, int], mouse_click: bool) -> Tuple[Optional[str], str, bool]:

        """Renderiza el panel lateral derecho. Retorna (edificio_id, categoria, click_turno)."""

        panel_x = pantalla.get_width() - 320



        # Fondo del panel

        panel_surf = pygame.Surface((320, pantalla.get_height()), pygame.SRCALPHA)

        panel_surf.fill((*_from_game('Config').COLOR_PANEL, 240))

        pantalla.blit(panel_surf, (panel_x, 0))



        # Borde izquierdo

        pygame.draw.line(pantalla, _from_game('Config').COLOR_PANEL_BORDE, (panel_x, 0), (panel_x, pantalla.get_height()), 2)



        y_offset = 10

        margen = panel_x + 10



        # ── Título ──

        txt_titulo = self.fuente_grande.render("☾ SIMMOON", True, _from_game('Config').COLOR_TEXTO)

        pantalla.blit(txt_titulo, (margen, y_offset))

        y_offset += 40



        # ── Recursos HUD (compacto) ──

        recursos_data = [

            ("💰 Créditos", recursos.creditos, _from_game('Config').COLOR_TEXTO_AMARILLO),

            ("⚡ Energía", f"{recursos.energia}/{recursos.energia_total}",

             _from_game('Config').COLOR_TEXTO_VERDE if recursos.energia_total > 0 else _from_game('Config').COLOR_TEXTO_ROJO),

            ("🫁 Oxígeno", f"{recursos.oxigeno}/{recursos.oxigeno_total}",

             _from_game('Config').COLOR_TEXTO_VERDE if recursos.oxigeno_total > 0 else _from_game('Config').COLOR_TEXTO_ROJO),

            ("💧 Agua", f"{recursos.agua}/{recursos.agua_total}",

             _from_game('Config').COLOR_TEXTO_VERDE if recursos.agua_total > 0 else _from_game('Config').COLOR_TEXTO_ROJO),

            ("💨 Presión", f"{recursos.presion}/{recursos.presion_total}",

             _from_game('Config').COLOR_TEXTO_VERDE if recursos.presion_total > 0 else _from_game('Config').COLOR_TEXTO_ROJO),

            ("\U0001f60a Felicidad", f"{recursos.felicidad}%",
             _from_game('Config').COLOR_TEXTO_VERDE if recursos.felicidad >= 70 else (_from_game('Config').COLOR_TEXTO_AMARILLO if recursos.felicidad >= 35 else _from_game('Config').COLOR_TEXTO_ROJO)),
        ]



        for nombre, valor, color in recursos_data:

            txt = self.fuente_pequenia.render(f"{nombre}: {valor}", True, color)

            pantalla.blit(txt, (margen, y_offset))

            y_offset += 22



        # Indicador de ciclo lunar

        if hasattr(self, 'es_de_noche') and self.es_de_noche:

            ciclo_icon = "🌙"

            ciclo_txt = f"{ciclo_icon} Noche {self.contador_lunar}/{_from_game('Config').DIAS_NOCHE}"

            ciclo_color = (100, 100, 180)

        else:

            ciclo_icon = "☀️"

            ciclo_txt = f"{ciclo_icon} Día {self.contador_lunar}/{_from_game('Config').DIAS_LUZ}"

            ciclo_color = _from_game('Config').COLOR_TEXTO_AMARILLO

        txt_ciclo = self.fuente_pequenia.render(ciclo_txt, True, ciclo_color)

        pantalla.blit(txt_ciclo, (margen, y_offset))

        y_offset += 20

        txt_pob = self.fuente_pequenia.render(f"👨‍🚀 Pob: {recursos.poblacion}  |  🔄 Turno: {recursos.turno}", True, _from_game('Config').COLOR_TEXTO)
        pantalla.blit(txt_pob, (margen, y_offset))
        y_offset += 22


        # ── Indicador de economía dinámica ──

        try:
            eco_linea = recursos.mercado.linea_indicador() if hasattr(recursos, 'mercado') else "📊 Economía: —"
        except (AttributeError, ImportError):
            eco_linea = "📊 Economía: —"
        txt_eco = self.fuente_pequenia.render(eco_linea, True, _from_game('Config').COLOR_TEXTO_AMARILLO)
        pantalla.blit(txt_eco, (margen, y_offset))
        y_offset += 24



        pygame.draw.line(pantalla, _from_game('Config').COLOR_PANEL_BORDE, (margen, y_offset), (panel_x + 300, y_offset), 1)

        y_offset += 8



        # ── Modo actual ──

        if modo_construir:

            modo_txt = "🔨 CONSTRUIR"

            color_modo = _from_game('Config').COLOR_TEXTO_VERDE

        elif modo_vender:

            modo_txt = "💸 VENDER"

            color_modo = _from_game('Config').COLOR_TEXTO_ROJO

        else:

            modo_txt = "👆 Selecciona"

            color_modo = _from_game('Config').COLOR_TEXTO



        txt_modo = self.fuente_pequenia.render(modo_txt, True, color_modo)

        pantalla.blit(txt_modo, (margen, y_offset))

        y_offset += 28



        # ── Botones de categoría (2 columnas) ──

        categorias = [

            ("🏛️ Gobierno", "government"),

            ("🏠 Alojamiento", "housing"),

            ("⚡ Energía", "solar_energy"),

            ("💧 Recursos", "life_support"),

            ("🏭 Industria", "industry"),

            ("🚀 Transporte", "transport"),

            ("🏢 Negocios", "businesses"),

            ("🎓 Universidades", "universities"),

            ("🔬 Servicios", "civic"),

            ("⚠️ Riesgos", "risk_management"),

            ("🚗 Vehículos", "vehicles"),

            ("🛣️ Carreteras", "roads"),

            ("👤 Personajes", "characters"),

            ("🎨 Decoración", "decorations"),

            ("🌱 Invernadero", "greenhouses"),

            ("🌿 Flora Lunar", "lunar_flora"),

            ("🏗️ Edificios", "buildings_misc"),

            ("🔧 Infraestructura", "infrastructure"),

            ("🏛️ Sitios", "lunar_sites"),

            ("👤 Personajes", "characters"),

            ("🌿 Flora Lunar", "lunar_flora"),

            ("🔧 Infraestructura", "infrastructure"),

        ]



        cat_clickeada = categoria_actual

        mouse_rel_x = mouse_pos[0] - panel_x

        mouse_rel_y = mouse_pos[1]

        btn_w, btn_h = 144, 28

        col2_x = margen + btn_w + 4



        for i, (nombre, cat_key) in enumerate(categorias):

            col = i % 2

            fila = i // 2

            bx = margen if col == 0 else col2_x

            by = y_offset + fila * 32

            btn_rect = pygame.Rect(bx, by, btn_w, btn_h)



            color_btn = _from_game('Config').COLOR_BOTON_SELECCIONADO if categoria_actual == cat_key else _from_game('Config').COLOR_BOTON

            if btn_rect.collidepoint(mouse_rel_x, mouse_rel_y):

                color_btn = _from_game('Config').COLOR_BOTON_HOVER

                if mouse_click:

                    cat_clickeada = cat_key



            pygame.draw.rect(pantalla, color_btn, btn_rect, border_radius=5)

            txt_btn = self.fuente_pequenia.render(nombre, True, _from_game('Config').COLOR_TEXTO)

            txt_x = bx + (btn_w - txt_btn.get_width()) // 2

            pantalla.blit(txt_btn, (txt_x, by + 5))



        y_offset += (len(categorias) // 2 + 1) * 32 + 8



        pygame.draw.line(pantalla, _from_game('Config').COLOR_PANEL_BORDE, (margen, y_offset), (panel_x + 300, y_offset), 1)

        y_offset += 8



        # ── Lista de edificios publicos (solo los votados, sin privados) ──

        edificios_categoria = [e for e in catalogo.values() if e.categoria == categoria_actual and not _from_game('es_edificio_privado')(e.id)]

        edificio_clickeado = None



        if not edificios_categoria:

            if categoria_actual == "universities":

                txt_sin = self.fuente_pequenia.render("📋 Usa Zonificar > Académico", True, _from_game('Config').COLOR_TEXTO_AMARILLO)

                pantalla.blit(txt_sin, (margen, y_offset))

                y_offset += 18

                txt_sin2 = self.fuente_pequenia.render("   y avanza turno para construir", True, _from_game('Config').COLOR_TEXTO_AMARILLO)

                pantalla.blit(txt_sin2, (margen, y_offset))

                y_offset += 22

            elif categoria_actual in ("government", "housing", "life_support", "industry", "transport", "civic", "risk_management"):

                txt_sin = self.fuente_pequenia.render("📋 Edificios privados — usa zonificar", True, _from_game('Config').COLOR_TEXTO_AMARILLO)

                pantalla.blit(txt_sin, (margen, y_offset))

                y_offset += 18

                txt_sin2 = self.fuente_pequenia.render("   y avanza turno para construirlos", True, _from_game('Config').COLOR_TEXTO_AMARILLO)

                pantalla.blit(txt_sin2, (margen, y_offset))

                y_offset += 22

            else:

                txt_sin = self.fuente_pequenia.render("🗳️ Sin edificios con votos", True, _from_game('Config').COLOR_TEXTO)

                pantalla.blit(txt_sin, (margen, y_offset))

                y_offset += 25



        # ── Grid visual de edificios (3 columnas) ──
        COLUMNAS = 3
        CELDA_W = 96
        CELDA_H = 96
        GAP_X = 4
        GAP_Y = 6

        total = len(edificios_categoria)
        renderizados = 0

        for i, tipo in enumerate(edificios_categoria):
            fila = i // COLUMNAS
            col = i % COLUMNAS

            celda_x = margen + col * (CELDA_W + GAP_X)
            celda_y = y_offset + fila * (CELDA_H + GAP_Y)

            # Si se sale del panel, cortar
            if celda_y + CELDA_H > pantalla.get_height() - 60:
                break

            renderizados += 1
            rect_celda = pygame.Rect(celda_x, celda_y, CELDA_W, CELDA_H)

            # Color de fondo
            seleccionado = edificio_seleccionado and edificio_seleccionado.id == tipo.id
            if seleccionado:
                color_fondo = _from_game('Config').COLOR_BOTON_SELECCIONADO
            elif rect_celda.collidepoint(mouse_rel_x, mouse_rel_y):
                color_fondo = _from_game('Config').COLOR_BOTON_HOVER
                if mouse_click:
                    edificio_clickeado = tipo.id
            else:
                color_fondo = _from_game('Config').COLOR_BOTON

            pygame.draw.rect(pantalla, color_fondo, rect_celda, border_radius=6)

            # Sprite 64x64 centrado
            sprite = self.cargar_sprite(tipo.ruta_sprite, (64, 64))
            sprite_x = celda_x + (CELDA_W - 64) // 2
            sprite_y = celda_y + 4
            pantalla.blit(sprite, (sprite_x, sprite_y))

            # Nombre
            nombre_mostrar = tipo.nombre if len(tipo.nombre) <= 14 else tipo.nombre[:13] + "…"
            txt_nombre = self.fuente_pequenia.render(nombre_mostrar, True, _from_game('Config').COLOR_TEXTO)
            txt_x = celda_x + (CELDA_W - txt_nombre.get_width()) // 2
            pantalla.blit(txt_nombre, (txt_x, sprite_y + 64 + 2))

            # Coste (mas estrellas si aplica)
            estrellas = votos.get(tipo.id, 0)
            if tipo.ancho_tiles > 1 or tipo.alto_tiles > 1:
                info_cost = f"💰{tipo.costo} {tipo.ancho_tiles}x{tipo.alto_tiles}" if estrellas == 0 else f"💰{tipo.costo} {tipo.ancho_tiles}x{tipo.alto_tiles} ⭐{estrellas}"
            else:
                info_cost = f"💰{tipo.costo}" if estrellas == 0 else f"💰{tipo.costo} ⭐{estrellas}"
            txt_coste = self.fuente_pequenia.render(info_cost, True, _from_game('Config').COLOR_TEXTO_AMARILLO)
            coste_x = celda_x + (CELDA_W - txt_coste.get_width()) // 2
            pantalla.blit(txt_coste, (coste_x, sprite_y + 64 + 18))

            # Etiqueta privado (esquina superior derecha)
            if _from_game('es_edificio_privado')(tipo.id):
                txt_priv = self.fuente_pequenia.render("📋", True, (255, 180, 50))
                pantalla.blit(txt_priv, (celda_x + CELDA_W - 24, celda_y + 2))

        # ── Indicador de scroll si hay más ──
        if renderizados < total and renderizados > 0:
            restantes = total - renderizados
            txt_mas = self.fuente_pequenia.render(f"▼ {restantes} mas...", True, _from_game('Config').COLOR_TEXTO_AMARILLO)
            mas_x = margen + (300 - txt_mas.get_width()) // 2
            ult_fila = (renderizados - 1) // COLUMNAS
            mas_y = y_offset + (ult_fila + 1) * (CELDA_H + GAP_Y) + 4
            pantalla.blit(txt_mas, (mas_x, mas_y))
            y_offset = mas_y + 25
        elif renderizados > 0:
            total_filas = (total + COLUMNAS - 1) // COLUMNAS
            y_offset += total_filas * (CELDA_H + GAP_Y) + 10



        # ── Botón SIGUIENTE TURNO (siempre visible al fondo) ──

        btn_turno_y = pantalla.get_height() - 55

        btn_turno_rect = pygame.Rect(margen, btn_turno_y, 298, 42)

        color_turno = _from_game('Config').COLOR_BOTON

        click_turno = False



        if btn_turno_rect.collidepoint(mouse_rel_x, mouse_rel_y):

            color_turno = _from_game('Config').COLOR_BOTON_HOVER

            if mouse_click:

                click_turno = True



        pygame.draw.rect(pantalla, color_turno, btn_turno_rect, border_radius=8)

        txt_turno = self.fuente_mediana.render("⏩ SIGUIENTE TURNO", True, _from_game('Config').COLOR_TEXTO_VERDE)

        txt_tx = margen + (298 - txt_turno.get_width()) // 2

        pantalla.blit(txt_turno, (txt_tx, btn_turno_y + 8))



        return edificio_clickeado, cat_clickeada, click_turno



    def renderizar_panel_zonificar(self, pantalla: pygame.Surface, zona_actual: Optional[str],

                                    mouse_pos: Tuple[int, int], mouse_click: bool) -> Optional[str]:

        """Renderiza el panel de zonificacion. Retorna el ID de zona clickeada o None."""

        panel_x = pantalla.get_width() - 320

        margen = panel_x + 10

        mouse_rel_x = mouse_pos[0] - panel_x

        mouse_rel_y = mouse_pos[1]

        y_offset = 10



        # Fondo

        panel_surf = pygame.Surface((320, pantalla.get_height()), pygame.SRCALPHA)

        panel_surf.fill((*_from_game('Config').COLOR_PANEL, 240))

        pantalla.blit(panel_surf, (panel_x, 0))

        pygame.draw.line(pantalla, _from_game('Config').COLOR_PANEL_BORDE, (panel_x, 0), (panel_x, pantalla.get_height()), 2)



        txt_titulo = self.fuente_grande.render("🗺️ ZONIFICAR", True, _from_game('Config').COLOR_TEXTO_AMARILLO)

        pantalla.blit(txt_titulo, (margen, y_offset))

        y_offset += 40



        txt_info = self.fuente_pequenia.render("Click: pintar zona | Der: borrar", True, _from_game('Config').COLOR_TEXTO)

        pantalla.blit(txt_info, (margen, y_offset))

        y_offset += 28



        pygame.draw.line(pantalla, _from_game('Config').COLOR_PANEL_BORDE, (margen, y_offset), (panel_x + 300, y_offset), 1)

        y_offset += 8



        zona_clickeada = None

        btn_w, btn_h = 298, 36



        for zona in _from_game('CATALOGO_ZONAS').values():

            if y_offset > pantalla.get_height() - 70:

                break

            btn_rect = pygame.Rect(margen, y_offset, btn_w, btn_h)

            color_btn = _from_game('Config').COLOR_BOTON_SELECCIONADO if zona_actual == zona.id else _from_game('Config').COLOR_BOTON

            if btn_rect.collidepoint(mouse_rel_x, mouse_rel_y):

                color_btn = _from_game('Config').COLOR_BOTON_HOVER

                if mouse_click:

                    zona_clickeada = zona.id



            pygame.draw.rect(pantalla, color_btn, btn_rect, border_radius=6)

            # Barra de color de zona

            pygame.draw.rect(pantalla, zona.color, (margen + 4, y_offset + 4, 28, 28), border_radius=4)

            # Nombre y rango de alquiler

            txt_nombre = self.fuente_pequenia.render(f"{zona.icono} {zona.nombre}", True, _from_game('Config').COLOR_TEXTO)

            pantalla.blit(txt_nombre, (margen + 40, y_offset + 2))

            txt_rango = self.fuente_pequenia.render(f"Prima: {zona.prima_min}-{zona.prima_max}💰  Alq: {zona.alquiler_min}-{zona.alquiler_max}/t", True, _from_game('Config').COLOR_TEXTO_AMARILLO)

            pantalla.blit(txt_rango, (margen + 40, y_offset + 20))

            y_offset += btn_h + 4



        # Sugerencia

        y_bottom = pantalla.get_height() - 45

        txt_z = self.fuente_pequenia.render("Tecla Z: volver a Construir", True, _from_game('Config').COLOR_TEXTO)

        pantalla.blit(txt_z, (margen, y_bottom))



        return zona_clickeada



    def renderizar_minimapa(self, pantalla: pygame.Surface, mapa: '_from_game("Mapa")', camara: '_from_game("Camara")') -> None:

        """Renderiza un minimapa de navegación en la esquina inferior izquierda.

        Muestra el grid completo 40×40, los edificios colocados y el viewport de la cámara."""

        mm_tam = 156  # Tamaño del minimapa

        mm_x = 8

        mm_y = pantalla.get_height() - mm_tam - 8

        tile_mm = mm_tam / mapa.tamanio  # px por tile en el minimapa



        # Fondo del minimapa

        mm_surf = pygame.Surface((mm_tam, mm_tam), pygame.SRCALPHA)

        mm_surf.fill((0, 0, 0, 200))



        # Dibujar cada tile

        for gy in range(mapa.tamanio):

            for gx in range(mapa.tamanio):

                px = int(gx * tile_mm)

                py = int(gy * tile_mm)

                color = (40, 38, 50)

                edif = mapa.grid[gy][gx]

                zona_id = mapa.zonas[gy][gx]

                if edif:

                    # Colorear según categoría

                    cat = edif.tipo.categoria

                    if cat == "businesses":

                        color = (255, 180, 50)  # Naranja

                    elif cat == "solar_energy":

                        color = (0, 200, 200)  # Cian

                    elif cat == "vehicles":

                        color = (150, 120, 255)  # Violeta

                    elif cat == "roads":

                        color = (180, 180, 180)  # Gris

                    elif cat == "characters":

                        color = (200, 180, 100)  # Dorado personajes

                    elif cat == "decorations":

                        color = (100, 180, 100)  # Verde claro

                    elif cat == "greenhouses":

                        color = (0, 220, 100)  # Verde

                    elif cat == "lunar_flora":

                        color = (100, 220, 100)  # Verde flora

                    elif cat == "buildings_misc":

                        color = (200, 150, 100)  # Marrón

                    elif cat == "government":

                        color = (220, 180, 60)  # Dorado gobierno

                    elif cat == "housing":

                        color = (70, 130, 180)  # Azul vivienda

                    elif cat == "life_support":

                        color = (0, 200, 200)  # Cian recursos

                    elif cat == "industry":

                        color = (180, 120, 50)  # Marrón industria

                    elif cat == "infrastructure":

                        color = (180, 180, 200)  # Gris claro infraestructura

                    elif cat == "transport":

                        color = (200, 180, 100)  # Ocre transporte

                    elif cat == "civic":

                        color = (100, 200, 220)  # Turquesa servicios

                    elif cat == "risk_management":

                        color = (220, 100, 60)  # Naranja riesgos

                    elif cat == "universities":

                        color = (140, 80, 200)  # Púrpura académico

                    elif cat == "lunar_sites":

                        color = (255, 100, 100)  # Rojo

                    elif cat == "characters":

                        color = (200, 180, 100)  # Dorado personajes

                    elif cat == "lunar_flora":

                        color = (100, 220, 100)  # Verde flora

                    elif cat == "infrastructure":

                        color = (180, 180, 200)  # Gris claro infraestructura

                if edif and edif.x == gx and edif.y == gy:

                    # Dibujar el footprint completo del edificio

                    ancho_px = int(edif.ancho * tile_mm)

                    alto_px = int(edif.alto * tile_mm)

                    pygame.draw.rect(mm_surf, color, (px, py, ancho_px, alto_px))

                elif not edif:

                    # Mostrar color de zona si existe

                    if zona_id and zona_id in _from_game('CATALOGO_ZONAS'):

                        color = _from_game('CATALOGO_ZONAS')[zona_id].color

                    pygame.draw.rect(mm_surf, color, (px, py, int(tile_mm) + 1, int(tile_mm) + 1))



        # Viewport de la cámara (calculado desde la posición real de cámara)

        cam_centro_x, cam_centro_y = camara.pantalla_a_iso(camara.ancho_ventana // 2, camara.alto_ventana // 2)

        tam = int(_from_game('Config').TAMANIO_TILE * camara.zoom)

        vis_ancho = int(camara.ancho_ventana / tam * 2) + 2

        vis_alto = int(camara.alto_ventana / (tam / 2)) + 2

        # Posición del viewport centrada en lo que ve la cámara

        vp_x = mm_x + cam_centro_x * tile_mm - (vis_ancho // 2) * tile_mm

        vp_y = mm_y + cam_centro_y * tile_mm - (vis_alto // 2) * tile_mm

        vp_w = vis_ancho * tile_mm

        vp_h = vis_alto * tile_mm

        # Clampear al minimapa

        vp_x = max(mm_x, min(mm_x + mm_tam - vp_w, vp_x))

        vp_y = max(mm_y, min(mm_y + mm_tam - vp_h, vp_y))

        pygame.draw.rect(pantalla, (255, 255, 255, 140), (vp_x, vp_y, vp_w, vp_h), 1)



        # Borde del minimapa

        pantalla.blit(mm_surf, (mm_x, mm_y))

        pygame.draw.rect(pantalla, _from_game('Config').COLOR_PANEL_BORDE, (mm_x, mm_y, mm_tam, mm_tam), 2)



        # Etiqueta "MINIMAPA"

        txt_mm = self.fuente_pequenia.render("MAPA", True, _from_game('Config').COLOR_TEXTO)

        pantalla.blit(txt_mm, (mm_x + 4, mm_y - 16))



# ─── Motor Principal del Juego ────────────────────────────────────────────