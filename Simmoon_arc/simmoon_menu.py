#!/usr/bin/env python3
"""
SIMMOON Launcher v1.4 — Menú Principal con Pantalla de Título
Entry point que muestra menú antes de iniciar juego_simmoon.py
"""
import os
import sys

# Redirect stdout/stderr to a log file in PyInstaller windowed builds to avoid cp1252 crashes
if getattr(sys, "frozen", False):
    try:
        import atexit
        _log_path = os.path.expanduser("~/Documents/SIMMoon/runtime.log")
        os.makedirs(os.path.dirname(_log_path), exist_ok=True)
        _log_file = open(_log_path, "w", encoding="utf-8", errors="replace")
        sys.stdout = _log_file
        sys.stderr = _log_file
        atexit.register(_log_file.close)
    except Exception:
        class _SafeOut:
            encoding = 'utf-8'
            def write(self, s): pass
            def flush(self): pass
        sys.stdout = _SafeOut()
        sys.stderr = _SafeOut()

import math
import random
import pygame
import types
from pathlib import Path
from typing import Optional, Dict, Tuple, List

# Import game module (triggers pygame.init() and class definitions)
import juego_simmoon

# New mechanics module
from simmoon_mecanicas import GestorGuardado, SistemaEventos, GestorLogros

# Reuse game classes directly
Config = juego_simmoon.Config
SonidoProcedural = juego_simmoon.SonidoProcedural
JuegoSimmoon = juego_simmoon.JuegoSimmoon
cargar_votos = juego_simmoon.cargar_votos


def _get_base_dir() -> Path:
    """Return the directory containing assets, handling PyInstaller frozen mode."""
    if getattr(sys, "frozen", False):
        # PyInstaller onefile extracts to sys._MEIPASS
        return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return Path(__file__).parent

# ─── Menú Principal ────────────────────────────────────────────────────────

class MenuPrincipal:
    """Pantalla de título con opciones de inicio."""

    def __init__(self):
        self.pantalla = pygame.display.set_mode((Config.ANCHO_VENTANA, Config.ALTO_VENTANA), pygame.RESIZABLE)
        self.reloj = pygame.time.Clock()
        self.ejecutando = True
        self.estrellas = [(random.randint(0, Config.ANCHO_VENTANA), random.randint(0, Config.ALTO_VENTANA // 2), random.random()) for _ in range(120)]
        self.tiempo = 0.0
        self._precargar_fuentes()

    def _precargar_fuentes(self):
        self.fuente_titulo = pygame.font.Font(None, 72)
        self.fuente_sub = pygame.font.Font(None, 36)
        self.fuente_boton = pygame.font.Font(None, 32)
        self.fuente_peq = pygame.font.Font(None, 20)

    def _renderizar_estrellas(self):
        for x, y, fase in self.estrellas:
            brillo = max(0, min(255, int(128 + 127 * math.sin(self.tiempo * 2 + fase * 6.28))))
            tamano = max(1, int(1 + 1.5 * (0.5 + 0.5 * math.sin(self.tiempo * 3 + fase * 6.28))))
            pygame.draw.circle(self.pantalla, (brillo, brillo, min(255, brillo + 20)), (int(x), int(y)), tamano)

    def _renderizar_boton(self, rect, texto, hover, seleccionado, color_base=(40, 40, 70)):
        if seleccionado:
            color = (100, 80, 200)
        elif hover:
            color = (70, 60, 120)
        else:
            color = color_base
        pygame.draw.rect(self.pantalla, color, rect, border_radius=10)
        pygame.draw.rect(self.pantalla, (100, 100, 150), rect, 2, border_radius=10)
        txt = self.fuente_boton.render(texto, True, Config.COLOR_TEXTO)
        tx = rect.centerx - txt.get_width() // 2
        ty = rect.centery - txt.get_height() // 2
        self.pantalla.blit(txt, (tx, ty))

    def ejecutar(self) -> Optional[str]:
        botones = [
            ("☾  Nueva Partida", "nueva"),
            ("📂 Cargar Partida", "cargar"),
            ("⚙️  Opciones", "opciones"),
            ("🚪 Salir", "salir"),
        ]
        btn_ancho, btn_alto = 340, 50
        btn_x = Config.ANCHO_VENTANA // 2 - btn_ancho // 2
        btn_inicio_y = 340
        gap = 16

        while self.ejecutando:
            dt = self.reloj.tick(Config.FPS) / 1000.0
            self.tiempo += dt
            mouse_pos = pygame.mouse.get_pos()
            mouse_click = False

            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    self.ejecutando = False
                    return None
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE:
                        self.ejecutando = False
                        return None
                    if evento.key == pygame.K_n:
                        SonidoProcedural.sonido_construir()
                        return "nueva"
                    if evento.key == pygame.K_c:
                        SonidoProcedural.sonido_construir()
                        return "cargar"
                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    mouse_click = True

            self.pantalla.fill(Config.COLOR_FONDO)
            self._renderizar_estrellas()

            # Luna decorativa
            pygame.draw.circle(self.pantalla, (180, 180, 200), (Config.ANCHO_VENTANA // 2, 160), 80)
            pygame.draw.circle(self.pantalla, (140, 140, 160), (Config.ANCHO_VENTANA // 2 - 20, 140), 12)
            pygame.draw.circle(self.pantalla, (140, 140, 160), (Config.ANCHO_VENTANA // 2 + 30, 170), 18)
            pygame.draw.circle(self.pantalla, (140, 140, 160), (Config.ANCHO_VENTANA // 2 - 10, 190), 10)

            txt_titulo = self.fuente_titulo.render("☾ SIMMOON", True, (220, 220, 240))
            self.pantalla.blit(txt_titulo, (Config.ANCHO_VENTANA // 2 - txt_titulo.get_width() // 2, 60))
            txt_sub = self.fuente_sub.render("Constructor de Colonia Lunar", True, (180, 180, 210))
            self.pantalla.blit(txt_sub, (Config.ANCHO_VENTANA // 2 - txt_sub.get_width() // 2, 130))

            txt_ver = self.fuente_peq.render("v1.4.0 — Pygame Edition", True, (120, 120, 140))
            self.pantalla.blit(txt_ver, (Config.ANCHO_VENTANA // 2 - txt_ver.get_width() // 2, 260))

            for i, (label, accion) in enumerate(botones):
                rect = pygame.Rect(btn_x, btn_inicio_y + i * (btn_alto + gap), btn_ancho, btn_alto)
                hover = rect.collidepoint(mouse_pos)
                if hover and mouse_click:
                    SonidoProcedural.sonido_construir()
                    if accion == "salir":
                        self.ejecutando = False
                        return None
                    return accion
                self._renderizar_boton(rect, label, hover, False)

            txt_atajo = self.fuente_peq.render("N: Nueva  |  C: Cargar  |  ESC: Salir", True, (100, 100, 120))
            self.pantalla.blit(txt_atajo, (Config.ANCHO_VENTANA // 2 - txt_atajo.get_width() // 2, Config.ALTO_VENTANA - 40))

            pygame.display.flip()

        return None


class OpcionesMenu:
    """Menú de opciones simple."""

    def __init__(self, pantalla):
        self.pantalla = pantalla
        self.reloj = pygame.time.Clock()
        self.ejecutando = True
        self.fuente_titulo = pygame.font.Font(None, 48)
        self.fuente_boton = pygame.font.Font(None, 28)
        self.fuente_peq = pygame.font.Font(None, 20)

    def ejecutar(self) -> bool:
        btn_volver = pygame.Rect(Config.ANCHO_VENTANA // 2 - 100, 500, 200, 45)
        while self.ejecutando:
            self.reloj.tick(Config.FPS)
            mouse_pos = pygame.mouse.get_pos()
            mouse_click = False

            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    return False
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    return True
                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    mouse_click = True

            self.pantalla.fill(Config.COLOR_FONDO)
            txt = self.fuente_titulo.render("⚙️  Opciones", True, Config.COLOR_TEXTO_AMARILLO)
            self.pantalla.blit(txt, (Config.ANCHO_VENTANA // 2 - txt.get_width() // 2, 60))

            info_lines = [
                "Resolución: 1280×720 (ajustable con ventana)",
                "Controles: Mouse + Teclado",
                "B: Construir  |  V: Vender  |  Z: Zonificar",
                "F5: Guardar  |  F9: Cargar  |  ESPACIO: Siguiente turno",
                "T: Investigación  |  C: Comercio  |  P: Profesiones",
                "L: Logros  |  I: Inmigración  |  H: Ayuda",
                "WASD/Flechas: Mover cámara  |  Rueda: Zoom",
            ]
            y = 160
            for line in info_lines:
                txt_line = self.fuente_peq.render(line, True, Config.COLOR_TEXTO)
                self.pantalla.blit(txt_line, (Config.ANCHO_VENTANA // 2 - txt_line.get_width() // 2, y))
                y += 28

            hover = btn_volver.collidepoint(mouse_pos)
            color = Config.COLOR_BOTON_HOVER if hover else Config.COLOR_BOTON
            pygame.draw.rect(self.pantalla, color, btn_volver, border_radius=8)
            txt_volver = self.fuente_boton.render("← Volver", True, Config.COLOR_TEXTO)
            self.pantalla.blit(txt_volver, (btn_volver.centerx - txt_volver.get_width() // 2, btn_volver.centery - txt_volver.get_height() // 2))
            if hover and mouse_click:
                SonidoProcedural.sonido_vender()
                return True

            pygame.display.flip()
        return True


class PantallaCarga:
    """Pantalla de carga con barra de progreso."""

    def __init__(self, pantalla):
        self.pantalla = pantalla
        self.fuente = pygame.font.Font(None, 28)
        self.fuente_peq = pygame.font.Font(None, 20)

    def mostrar(self, texto="Cargando colonia lunar..."):
        self.pantalla.fill(Config.COLOR_FONDO)
        txt = self.fuente.render(texto, True, Config.COLOR_TEXTO)
        self.pantalla.blit(txt, (Config.ANCHO_VENTANA // 2 - txt.get_width() // 2, Config.ALTO_VENTANA // 2 - 20))

        bar_w, bar_h = 400, 18
        bar_x = Config.ANCHO_VENTANA // 2 - bar_w // 2
        bar_y = Config.ALTO_VENTANA // 2 + 20
        for i in range(21):
            pygame.draw.rect(self.pantalla, (30, 30, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
            fill_w = int(bar_w * i / 20)
            if fill_w > 0:
                pygame.draw.rect(self.pantalla, (0, 200, 150), (bar_x, bar_y, fill_w, bar_h), border_radius=6)
            txt_pct = self.fuente_peq.render(f"{i * 5}%", True, Config.COLOR_TEXTO)
            self.pantalla.blit(txt_pct, (bar_x + bar_w + 12, bar_y))
            pygame.display.flip()
            pygame.event.pump()
            pygame.time.delay(30)


# ─── Entry Point ───────────────────────────────────────────────────────────

def main():
    print("+========================================+")
    print("|   SIMMOON - Constructor de Colonia     |")
    print("|   Motor: Pygame | Estilo: SimCity    |")
    print("+========================================+")
    print()
    print("  Cargando votos...")

    dir_assets = str(_get_base_dir())
    votos = cargar_votos(dir_assets)

    print(f"  Edificios disponibles: {len(juego_simmoon.filtrar_catalogo_por_votos(votos))}")
    print()

    SonidoProcedural._init_mixer()

    while True:
        menu = MenuPrincipal()
        seleccion = menu.ejecutar()

        if seleccion is None:
            break
        elif seleccion == "nueva":
            carga = PantallaCarga(menu.pantalla)
            carga.mostrar("Iniciando nueva colonia lunar...")
            juego = JuegoSimmoon(votos=votos)
            _setup_mecanicas(juego)
            juego.ejecutar()
        elif seleccion == "cargar":
            selector = PantallaCargarPartida(menu.pantalla)
            ruta_partida = selector.ejecutar()
            if ruta_partida:
                carga = PantallaCarga(menu.pantalla)
                carga.mostrar("Cargando partida guardada...")
                juego = JuegoSimmoon(votos=votos)
                _setup_mecanicas(juego)
                try:
                    GestorGuardado.cargar_juego(ruta_partida, juego)
                except Exception as e:
                    print(f"  [WARN] No se pudo cargar la partida: {e}")
                juego.ejecutar()
        elif seleccion == "opciones":
            opciones = OpcionesMenu(menu.pantalla)
            if not opciones.ejecutar():
                break

    sys.stdout.flush()
    pygame.quit()


# ─── Integración de Mecánicas ──────────────────────────────────────────────

def _setup_mecanicas(juego: JuegoSimmoon) -> None:
    """Inyecta guardado, eventos y logros en una instancia de JuegoSimmoon."""
    juego.gestor_guardado = GestorGuardado()
    juego.sistema_eventos = SistemaEventos()
    juego.gestor_logros = GestorLogros()
    juego._turnos_para_autoguardado = 0
    juego._evento_activo = None
    juego._turnos_sin_evento_negativo = 0
    juego._turnos_bono_persistente = 0

    # Hook procesar_siguiente_turno
    _orig_turno = juego.procesar_siguiente_turno

    def _turno_hook(self):
        # Procesar evento aleatorio
        evento = self.sistema_eventos.procesar_turno(self.recursos, self.mapa)
        evento_negativo = False
        notificaciones = []
        if evento:
            self._evento_activo = evento
            evento_negativo = evento.duracion_turnos > 0
            notificaciones.append(f"{evento.titulo}: {evento.descripcion}")
            if evento.duracion_turnos > 0:
                self._turnos_bono_persistente = evento.duracion_turnos

        # Llamar turno original
        _orig_turno()

        # Aplicar duración de efectos negativos (ej. marcha de colonos)
        if self._turnos_bono_persistente > 0:
            self._turnos_bono_persistente -= 1
        else:
            self.recursos.bono_produccion = 1.0

        # Tracking turnos sin evento negativo
        if evento_negativo:
            self._turnos_sin_evento_negativo = 0
        else:
            self._turnos_sin_evento_negativo += 1

        # Evaluar logros
        nuevos = self.gestor_logros.evaluar_logros(
            self.recursos, self.mapa, self.recursos.turno,
            self._turnos_sin_evento_negativo
        )
        for logro in nuevos:
            notificaciones.append(f"🏆 {logro.icono} Logro: {logro.nombre}")

        # Mostrar notificaciones concatenadas
        if notificaciones and hasattr(self, 'mostrar_mensaje_error'):
            self.mostrar_mensaje_error("  |  ".join(notificaciones[:3]))

        # Auto-guardado cada 5 turnos
        self._turnos_para_autoguardado += 1
        if self._turnos_para_autoguardado >= 5:
            self._turnos_para_autoguardado = 0
            try:
                ruta = self.gestor_guardado.guardar_juego("autosave", self.recursos, self.mapa, self.recursos.turno)
                print(f"  💾 Auto-guardado: {ruta}")
            except Exception as e:
                print(f"  [WARN] Auto-guardado falló: {e}")

    juego.procesar_siguiente_turno = types.MethodType(_turno_hook, juego)


class PantallaCargarPartida:
    """Pantalla de selección de partidas guardadas."""

    def __init__(self, pantalla):
        self.pantalla = pantalla
        self.reloj = pygame.time.Clock()
        self.fuente_titulo = pygame.font.Font(None, 48)
        self.fuente_item = pygame.font.Font(None, 28)
        self.fuente_peq = pygame.font.Font(None, 20)

    def ejecutar(self) -> Optional[str]:
        partidas = GestorGuardado.listar_partidas()
        seleccion = 0
        while True:
            self.reloj.tick(Config.FPS)
            mouse_pos = pygame.mouse.get_pos()
            click = False

            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    return None
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE:
                        return None
                    if evento.key == pygame.K_UP:
                        seleccion = max(0, seleccion - 1)
                    if evento.key == pygame.K_DOWN:
                        seleccion = min(len(partidas) - 1, seleccion + 1)
                    if evento.key == pygame.K_RETURN and partidas:
                        return partidas[seleccion][1]
                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    click = True

            self.pantalla.fill(Config.COLOR_FONDO)
            txt = self.fuente_titulo.render("📂 Partidas Guardadas", True, Config.COLOR_TEXTO_AMARILLO)
            self.pantalla.blit(txt, (Config.ANCHO_VENTANA // 2 - txt.get_width() // 2, 60))

            if not partidas:
                txt_vacio = self.fuente_item.render("No hay partidas guardadas.", True, Config.COLOR_TEXTO)
                self.pantalla.blit(txt_vacio, (Config.ANCHO_VENTANA // 2 - txt_vacio.get_width() // 2, 300))
            else:
                for i, (nombre, ruta, turno) in enumerate(partidas[:10]):
                    rect = pygame.Rect(Config.ANCHO_VENTANA // 2 - 250, 160 + i * 50, 500, 42)
                    hover = rect.collidepoint(mouse_pos)
                    sel = i == seleccion
                    color = Config.COLOR_BOTON_SELECCIONADO if sel else (Config.COLOR_BOTON_HOVER if hover else Config.COLOR_BOTON)
                    pygame.draw.rect(self.pantalla, color, rect, border_radius=8)
                    pygame.draw.rect(self.pantalla, Config.COLOR_PANEL_BORDE, rect, 2, border_radius=8)
                    txt_n = self.fuente_item.render(f"{nombre} — Turno {turno}", True, Config.COLOR_TEXTO)
                    self.pantalla.blit(txt_n, (rect.x + 12, rect.y + 8))
                    if (hover and click) or (sel and click):
                        return ruta

            txt_atajo = self.fuente_peq.render("↑↓: Navegar | ENTER: Cargar | ESC: Volver", True, (100, 100, 120))
            self.pantalla.blit(txt_atajo, (Config.ANCHO_VENTANA // 2 - txt_atajo.get_width() // 2, Config.ALTO_VENTANA - 40))
            pygame.display.flip()


# ─── Entry Point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
