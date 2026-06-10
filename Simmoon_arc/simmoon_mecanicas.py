#!/usr/bin/env python3
"""
SIMMOON Mechanics Module v1.4
Adds save/load, random lunar events, and achievements.
"""
import json
import random
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# These are imported from juego_simmoon at runtime to avoid circular imports issues
# when this module is imported before juego_simmoon


# ─── A. Save / Load System ───────────────────────────────────────────────

class GestorGuardado:
    """Serializa y restaura el estado completo de la colonia."""

    @staticmethod
    def _get_save_dir() -> Path:
        home = Path.home()
        save_dir = home / "Documents" / "SIMMOON" / "saves"
        save_dir.mkdir(parents=True, exist_ok=True)
        return save_dir

    @staticmethod
    def guardar_juego(nombre: str, recursos: Any, mapa: Any, turno: int) -> str:
        """
        Guarda el estado actual en un archivo JSON.
        Returns the path to the saved file.
        """
        save_dir = GestorGuardado._get_save_dir()
        ruta = save_dir / f"{nombre}.json"

        # Serializar recursos (vars() convierte atributos a dict)
        estado_recursos = {
            "creditos": recursos.creditos,
            "energia": recursos.energia,
            "oxigeno": recursos.oxigeno,
            "agua": recursos.agua,
            "presion": recursos.presion,
            "energia_total": recursos.energia_total,
            "oxigeno_total": recursos.oxigeno_total,
            "agua_total": recursos.agua_total,
            "presion_total": recursos.presion_total,
            "poblacion": recursos.poblacion,
            "turno": recursos.turno,
            "felicidad": recursos.felicidad,
            "bono_produccion": recursos.bono_produccion,
        }

        # Serializar mapa: solo guardar edificios (sin sprites pygame)
        edificios_guardados = []
        for e in mapa.edificios:
            edificios_guardados.append({
                "tipo_id": e.tipo.id,
                "x": e.x,
                "y": e.y,
                "activo": e.activo,
            })

        # Serializar zonas
        zonas_guardadas = mapa.zonas

        estado = {
            "version": "1.4.0",
            "nombre": nombre,
            "turno_global": turno,
            "recursos": estado_recursos,
            "edificios": edificios_guardados,
            "zonas": zonas_guardadas,
        }

        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=2, ensure_ascii=False)

        return str(ruta)

    @staticmethod
    def listar_partidas() -> List[Tuple[str, str, int]]:
        """
        Retorna lista de partidas guardadas como (nombre, ruta, turno).
        """
        save_dir = GestorGuardado._get_save_dir()
        partidas = []
        for f in sorted(save_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    datos = json.load(fp)
                partidas.append((datos.get("nombre", f.stem), str(f), datos.get("turno_global", 0)))
            except Exception:
                continue
        return partidas

    @staticmethod
    def cargar_juego(ruta: str, juego: Any) -> bool:
        """
        Restaura el estado desde un archivo JSON.
        Returns True if successful.
        """
        from juego_simmoon import CATALOGO_EDIFICIOS

        if not os.path.exists(ruta):
            return False

        with open(ruta, "r", encoding="utf-8") as f:
            estado = json.load(f)

        # Restaurar recursos
        r = estado["recursos"]
        rec = juego.recursos
        rec.creditos = r["creditos"]
        rec.energia = r["energia"]
        rec.oxigeno = r["oxigeno"]
        rec.agua = r["agua"]
        rec.presion = r["presion"]
        rec.energia_total = r["energia_total"]
        rec.oxigeno_total = r["oxigeno_total"]
        rec.agua_total = r["agua_total"]
        rec.presion_total = r["presion_total"]
        rec.poblacion = r["poblacion"]
        rec.turno = r["turno"]
        rec.felicidad = r["felicidad"]
        rec.bono_produccion = r["bono_produccion"]

        # Reconstruir mapa
        juego.mapa.grid = [
            [None for _ in range(juego.mapa.tamanio)] for _ in range(juego.mapa.tamanio)
        ]
        juego.mapa.edificios = []
        juego.mapa.zonas = estado.get("zonas", [
            [None for _ in range(juego.mapa.tamanio)] for _ in range(juego.mapa.tamanio)
        ])

        for e_datos in estado["edificios"]:
            tipo_id = e_datos["tipo_id"]
            if tipo_id not in CATALOGO_EDIFICIOS:
                continue
            tipo = CATALOGO_EDIFICIOS[tipo_id]
            # Cargar sprite usando el renderizador del juego
            sprite = juego.renderizador.cargar_sprite(tipo.ruta_sprite)
            juego.mapa.colocar_edificio(e_datos["x"], e_datos["y"], tipo, sprite)
            # Restaurar estado activo/inactivo
            if juego.mapa.edificios:
                juego.mapa.edificios[-1].activo = e_datos.get("activo", True)

        # Actualizar balance
        juego.recursos.actualizar_balance(juego.mapa.edificios)

        print(f"  ✅ Partida cargada: {estado.get('nombre', 'save')} (Turno {estado.get('turno_global', 0)})")
        return True


# ─── B. Random Lunar Events ──────────────────────────────────────────────

@dataclass
class EventoLunar:
    titulo: str
    descripcion: str
    color_ui: Tuple[int, int, int]
    duracion_turnos: int = 1  # Cuántos turnos dura el efecto negativo


class SistemaEventos:
    """Genera eventos aleatorios lunares que afectan la colonia."""

    PROBABILIDAD_EVENTO = 0.12  # 12% por turno

    EVENTOS = [
        {
            "id": "meteorito",
            "titulo": "☄️ Lluvia de Meteoritos",
            "descripcion": "Impactos aleatorios dañan 1-2 edificios.",
            "color": (255, 80, 80),
            "duracion": 0,
        },
        {
            "id": "fallo_energia",
            "titulo": "⚡ Fallo de Energía",
            "descripcion": "La red eléctrica sufre una sobrecarga. -40 energía.",
            "color": (255, 200, 50),
            "duracion": 2,
        },
        {
            "id": "erupcion_solar",
            "titulo": "☀️ Erupción Solar",
            "descripcion": "Radiación intensa. +80 energía solar, -20 oxígeno.",
            "color": (255, 140, 0),
            "duracion": 1,
        },
        {
            "id": "inmigracion",
            "titulo": "🚀 Inmigración Repentina",
            "descripcion": "Una nave traumática trae +15 colonos.",
            "color": (50, 200, 100),
            "duracion": 0,
        },
        {
            "id": "fuga_oxigeno",
            "titulo": "💨 Fuga de Oxígeno",
            "descripcion": "Un sello se rompe. -30 oxígeno, -10 felicidad.",
            "color": (100, 180, 255),
            "duracion": 2,
        },
        {
            "id": "descubrimiento",
            "titulo": "🔬 Descubrimiento Científico",
            "descripcion": "Los investigadores hallan recursos. +200 créditos.",
            "color": (150, 100, 255),
            "duracion": 0,
        },
        {
            "id": "marcha_colonos",
            "titulo": "😠 Protesta de Colonos",
            "descripcion": "Baja producción por 1 turno. -15 felicidad.",
            "color": (200, 50, 50),
            "duracion": 1,
        },
    ]

    @classmethod
    def procesar_turno(cls, recursos: Any, mapa: Any) -> Optional[EventoLunar]:
        if random.random() > cls.PROBABILIDAD_EVENTO:
            return None

        evt = random.choice(cls.EVENTOS)

        if evt["id"] == "meteorito":
            if mapa.edificios:
                victima = random.choice(mapa.edificios)
                victima.activo = False

        elif evt["id"] == "fallo_energia":
            recursos.energia_total = max(0, recursos.energia_total - 40)
            recursos.felicidad = max(0, recursos.felicidad - 5)

        elif evt["id"] == "erupcion_solar":
            recursos.energia_total += 80
            recursos.oxigeno_total = max(0, recursos.oxigeno_total - 20)

        elif evt["id"] == "inmigracion":
            recursos.poblacion += 15
            recursos.felicidad = max(0, recursos.felicidad - 5)

        elif evt["id"] == "fuga_oxigeno":
            recursos.oxigeno_total = max(0, recursos.oxigeno_total - 30)
            recursos.felicidad = max(0, recursos.felicidad - 10)

        elif evt["id"] == "descubrimiento":
            recursos.creditos += 200
            recursos.felicidad = min(100, recursos.felicidad + 5)

        elif evt["id"] == "marcha_colonos":
            # El efecto de bono reducido se aplica en el hook por duracion_turnos
            recursos.bono_produccion = 0.5
            recursos.felicidad = max(0, recursos.felicidad - 15)

        return EventoLunar(
            titulo=evt["titulo"],
            descripcion=evt["descripcion"],
            color_ui=evt["color"],
            duracion_turnos=evt["duracion"],
        )


# ─── C. Achievement System ───────────────────────────────────────────────

@dataclass
class Logro:
    id: str
    nombre: str
    descripcion: str
    icono: str
    condicion_tipo: str  # "construir", "poblacion", "turno", "credito", "edificios_categoria"
    condicion_valor: int
    condicion_extra: Optional[str] = None  # e.g. category name
    desbloqueado: bool = False
    turno_desbloqueo: int = 0


class GestorLogros:
    """Gestiona los logros y evalúa si se cumplen las condiciones."""

    def __init__(self):
        self.logros: List[Logro] = [
            Logro("primera_construccion", "Primeros Pasos", "Construye tu primer edificio.", "🏗️", "construir", 1),
            Logro("domos_10", "Pionero Verde", "Construye 10 estructuras de cualquier tipo.", "🌿", "construir", 10),
            Logro("domos_25", "Arquitecto Lunar", "Construye 25 edificios.", "🏛️", "construir", 25),
            Logro("pop_50", "Villa Lunar", "Alcanza 50 colonos.", "👥", "poblacion", 50),
            Logro("pop_100", "Metrópolis Lunar", "Alcanza 100 colonos.", "🏙️", "poblacion", 100),
            Logro("pop_200", "Megaciudad", "Alcanza 200 colonos.", "🌆", "poblacion", 200),
            Logro("turno_10", "Superviviente", "Sobrevive 10 turnos.", "🛡️", "turno", 10),
            Logro("turno_50", "Veterano", "Sobrevive 50 turnos.", "⭐", "turno", 50),
            Logro("turno_100", "Leyenda Lunar", "Sobrevive 100 turnos.", "👑", "turno", 100),
            Logro("rico_1k", "Emprendedor", "Acumula 1,000 créditos.", "💰", "credito", 1000),
            Logro("rico_5k", "Magnate", "Acumula 5,000 créditos.", "💎", "credito", 5000),
            Logro("rico_10k", "Tycoon Lunar", "Acumula 10,000 créditos.", "🏦", "credito", 10000),
            Logro("eco_10", "Eco-Colonia", "Construye 10 invernaderos.", "🌱", "edificios_categoria", 10, "greenhouses"),
            Logro("industria_10", "Fábrica Lunar", "Construye 10 plantas industriales.", "🏭", "edificios_categoria", 10, "industry"),
            Logro("sin_eventos_20", "Paz Lunar", "Sobrevive 20 turnos sin eventos negativos.", "🕊️", "sin_eventos", 20),
        ]

    def evaluar_logros(self, recursos: Any, mapa: Any, turno: int, turnos_sin_evento_negativo: int) -> List[Logro]:
        """
        Evalúa condiciones de logros no desbloqueados.
        Retorna lista de logros recién desbloqueados en este turno.
        """
        nuevos = []
        for logro in self.logros:
            if logro.desbloqueado:
                continue

            cumple = False
            if logro.condicion_tipo == "construir":
                cumple = len(mapa.edificios) >= logro.condicion_valor
            elif logro.condicion_tipo == "poblacion":
                cumple = recursos.poblacion >= logro.condicion_valor
            elif logro.condicion_tipo == "turno":
                cumple = turno >= logro.condicion_valor
            elif logro.condicion_tipo == "credito":
                cumple = recursos.creditos >= logro.condicion_valor
            elif logro.condicion_tipo == "edificios_categoria":
                cat = logro.condicion_extra or ""
                cuenta = sum(1 for e in mapa.edificios if e.tipo.categoria == cat)
                cumple = cuenta >= logro.condicion_valor
            elif logro.condicion_tipo == "sin_eventos":
                cumple = turnos_sin_evento_negativo >= logro.condicion_valor

            if cumple:
                logro.desbloqueado = True
                logro.turno_desbloqueo = turno
                nuevos.append(logro)

        return nuevos

    def a_serializable(self) -> List[Dict[str, Any]]:
        """Retorna lista de logros para guardar en JSON."""
        return [
            {
                "id": l.id,
                "desbloqueado": l.desbloqueado,
                "turno_desbloqueo": l.turno_desbloqueo,
            }
            for l in self.logros
        ]

    def desde_serializable(self, datos: List[Dict[str, Any]]):
        """Restaura estado de logros desde JSON."""
        por_id = {l.id: l for l in self.logros}
        for d in datos:
            if d["id"] in por_id:
                por_id[d["id"]].desbloqueado = d.get("desbloqueado", False)
                por_id[d["id"]].turno_desbloqueo = d.get("turno_desbloqueo", 0)
