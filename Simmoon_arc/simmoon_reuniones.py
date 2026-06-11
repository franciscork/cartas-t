#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simmoon_reuniones.py — 🏢 Sistema de Reuniones Semanales

Organiza reuniones de brainstorming/estrategia del equipo FactoryGames,
guarda actas en Obsidian y gestiona el seguimiento de tareas.

Uso:
    python simmoon_reuniones.py --nueva           # Iniciar nueva reunión
    python simmoon_reuniones.py --ideas           # Tormenta de ideas
    python simmoon_reuniones.py --actas --ultima  # Ver última acta
    python simmoon_reuniones.py --status          # Estado de seguimiento
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# ── Soft imports ──────────────────────────────────────────────────────────
_OBSIDIAN_MEMORY = None
def _get_obsidian() -> Optional[Any]:
    """Obtener ObsidianMemory de forma lazy (con REST API si está disponible)."""
    global _OBSIDIAN_MEMORY
    if _OBSIDIAN_MEMORY is None:
        try:
            from obsidian_memory import ObsidianMemory
            # Intentar REST API desde config
            cfg_path = SCRIPT_DIR / "obsidian_rest_config.json"
            if cfg_path.exists():
                with open(cfg_path) as f:
                    rc = json.load(f)
                _OBSIDIAN_MEMORY = ObsidianMemory(
                    agent_name="Reuniones",
                    project="SIMMOON",
                    rest_port=int(rc.get("port", 27124)),
                    rest_api_key=rc.get("apiKey", rc.get("api_key", "")),
                    rest_https=rc.get("use_https", True),
                    rest_host=rc.get("host", "127.0.0.1"),
                )
            else:
                vault = SCRIPT_DIR / "factory_memoria"
                vault.mkdir(parents=True, exist_ok=True)
                _OBSIDIAN_MEMORY = ObsidianMemory(
                    vault_path=str(vault),
                    agent_name="Reuniones",
                    project="SIMMOON",
                )
        except Exception as e:
            _OBSIDIAN_MEMORY = False  # Marcamos como "no disponible"
    return _OBSIDIAN_MEMORY if _OBSIDIAN_MEMORY else None


# Configuración de reuniones
REUNIONES_CONFIG = {
    "tipo": "semanal",
    "dia": "viernes",         # Día sugerido para la reunión semanal
    "hora": "18:00",          # Hora sugerida
    "duracion_min": 45,       # Duración sugerida en minutos
    "participantes": [
        {"nombre": "Buffy", "rol": "CEO / Orquestador", "emoji": "🦙"},
        {"nombre": "Creativo de Juegos", "rol": "Dirección Creativa y Diseño", "emoji": "🎮"},
        {"nombre": "Guionista", "rol": "Narrativa y Diálogos", "emoji": "✍️"},
        {"nombre": "Agatha Actas", "rol": "Supervisora / Secretaria", "emoji": "📋"},
    ],
    "orden_del_dia": [
        "🔄 Seguimiento de tareas pendientes",
        "🎮 Brainstorming creativo (Creativo de Juegos)",
        "✍️ Desarrollo narrativo (Guionista)",
        "🏭 Estado de la fábrica (Agatha)",
        "📋 Plan de la semana",
        "🗳️ Votación de prioridades",
    ],
}


# ══════════════════════════════════════════════════════════════════════════
#  Sistema de Reuniones
# ══════════════════════════════════════════════════════════════════════════

class SistemaReuniones:
    """Sistema de reuniones semanales con actas en Obsidian."""

    def __init__(self):
        self.memory = _get_obsidian()

    # ── Iniciar reunión ─────────────────────────────────────────────────

    def nueva_reunion(self, tipo: str = "semanal") -> Dict[str, Any]:
        """Iniciar una nueva reunión y guardar acta inicial en Obsidian.

        Args:
            tipo: 'semanal', 'extraordinaria', 'brainstorming'

        Returns:
            Dict con datos de la reunión creada
        """
        ahora = datetime.now()
        reunion = {
            "id": ahora.strftime("reunion_%Y%m%d_%H%M"),
            "fecha": ahora.strftime("%Y-%m-%d %H:%M"),
            "tipo": tipo,
            "participantes": REUNIONES_CONFIG["participantes"],
            "orden_del_dia": REUNIONES_CONFIG["orden_del_dia"],
            "ideas": [],
            "decisiones": [],
            "tareas_pendientes": [],
            "estado": "en_curso",
            "proxima_reunion": self._calcular_proxima(),
        }

        # Guardar en Obsidian
        if self.memory:
            contenido = self._formatear_acta(reunion)
            self.memory.save_task(
                key_name=reunion["id"],
                content=contenido,
                tags=["reunion", tipo, "acta"],
                importance=5,
            )

        return reunion

    def _calcular_proxima(self) -> str:
        """Calcular fecha de la próxima reunión semanal."""
        dias_map = {
            "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
            "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5,
            "domingo": 6
        }
        hoy = datetime.now()
        dia_target = dias_map.get(REUNIONES_CONFIG["dia"], 4)  # Default viernes
        dias_hasta = (dia_target - hoy.weekday()) % 7
        if dias_hasta == 0:
            dias_hasta = 7  # Siempre la próxima semana
        proxima = hoy + timedelta(days=dias_hasta)
        return proxima.strftime("%Y-%m-%d") + f" {REUNIONES_CONFIG['hora']}"

    # ── Tormenta de ideas ───────────────────────────────────────────────

    def agregar_idea(self, reunion_id: str, autor: str, idea: str,
                     categoria: str = "general") -> bool:
        """Agregar una idea a la reunión actual.

        Args:
            reunion_id: ID de la reunión
            autor: Quién propone la idea
            idea: Descripción de la idea
            categoria: 'mecanica', 'narrativa', 'estrategia', 'produccion'

        Returns:
            True si se guardó correctamente
        """
        if not self.memory:
            print("[WARN] Obsidian no disponible. Idea no persistida.")
            return False

        entrada_idea = {
            "timestamp": datetime.now().isoformat(),
            "autor": autor,
            "idea": idea,
            "categoria": categoria,
            "votos": 0,
        }

        # Leer acta actual, agregar idea, guardar
        acta = self.memory.get(reunion_id, memory_type="task")
        if acta:
            contenido = acta.get("content", "")
            # Append idea al contenido
            nueva_linea = (
                f"\n- 💡 *[{categoria}]* _{autor}_: {idea}"
            )
            contenido += nueva_linea
            self.memory.save_task(
                key_name=reunion_id,
                content=contenido,
                tags=["reunion", "brainstorming"],
                importance=5,
            )
            return True
        return False

    # ── Decisiones ──────────────────────────────────────────────────────

    def registrar_decision(self, reunion_id: str, decision: str,
                           responsable: str = "") -> bool:
        """Registrar una decisión tomada en la reunión.

        Args:
            reunion_id: ID de la reunión
            decision: Descripción de la decisión
            responsable: Quién ejecutará (opcional)

        Returns:
            True si se guardó
        """
        if not self.memory:
            return False

        acta = self.memory.get(reunion_id, memory_type="task")
        if acta:
            contenido = acta.get("content", "")
            resp = f" → _{responsable}_" if responsable else ""
            contenido += f"\n- ✅ *Decisión*: {decision}{resp}"
            return self.memory.save_task(
                key_name=reunion_id, content=contenido,
                tags=["reunion", "decision"], importance=5,
            )
        return False

    # ── Progreso ────────────────────────────────────────────────────────

    def obtener_ultimas_reuniones(self, limit: int = 5) -> List[Dict]:
        """Obtener las últimas reuniones desde Obsidian."""
        if not self.memory:
            return []
        memories = self.memory.search_by_tag("reunion", limit=limit)
        return sorted(memories, key=lambda m: m.get("key_name", ""), reverse=True)

    def status_seguimiento(self) -> str:
        """Generar reporte de seguimiento de reuniones."""
        if not self.memory:
            return "❌ Obsidian no disponible para seguimiento."

        reuniones = self.obtener_ultimas_reuniones(10)
        lines = ["🏢 *SEGUIMIENTO DE REUNIONES*\n"]

        if not reuniones:
            lines.append("📭 No hay reuniones registradas aún.")
            lines.append("\n💡 *Sugerencia:* ¡Programa la primera!")
            lines.append("   `python simmoon_reuniones.py --nueva`")
            return "\n".join(lines)

        lines.append(f"📊 {len(reuniones)} reuniones registradas")
        lines.append("")

        for r in reuniones:
            key = r.get("key_name", "?")
            content = r.get("content", "")
            # Extraer primera línea como título
            titulo = content.split("\n")[0][:80] if content else "(sin contenido)"
            lines.append(f"  📅 *{key}*")
            lines.append(f"     {titulo}")

        lines.append("")
        lines.append(f"_Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
        return "\n".join(lines)

    # ── Formateo ────────────────────────────────────────────────────────

    def _formatear_acta(self, reunion: Dict) -> str:
        """Formatear acta de reunión como markdown."""
        lines = [
            f"# 🏢 Reunión {reunion['tipo'].title()}",
            f"**Fecha:** {reunion['fecha']}",
            f"**Próxima:** {reunion.get('proxima_reunion', 'Pendiente')}",
            "",
            "---",
            "",
            "## 👥 Participantes",
        ]
        for p in reunion["participantes"]:
            lines.append(f"- {p['emoji']} **{p['nombre']}** — {p['rol']}")

        lines.extend([
            "",
            "---",
            "",
            "## 📋 Orden del Día",
        ])
        for i, item in enumerate(reunion["orden_del_dia"], 1):
            lines.append(f"{i}. {item}")

        lines.extend([
            "",
            "---",
            "",
            "## 💡 Ideas Generadas",
            "",
            "_(Registra ideas aquí durante la reunión)_",
            "",
            "---",
            "",
            "## ✅ Decisiones",
            "",
            "_(Anota las decisiones aquí)_",
            "",
            "---",
            "",
            "## 📝 Tareas Pendientes",
            "",
            "_(Registra los action items aquí)_",
            "",
            "---",
            "",
            f"_Generado por Sistema de Reuniones · {datetime.now().strftime('%H:%M')}_",
        ])
        return "\n".join(lines)

    # ── Reporte para Telegram ───────────────────────────────────────────

    def formato_telegram(self, reunion: Dict) -> str:
        """Formatear resumen de reunión para Telegram."""
        lines = [
            f"🏢 *Reunión {reunion['tipo'].title()}*",
            f"📅 {reunion['fecha']}",
            "",
            "👥 *Participantes:*",
        ]
        for p in reunion["participantes"]:
            lines.append(f"  {p['emoji']} {p['nombre']}")

        lines.extend([
            "",
            "📋 *Orden del Día:*",
        ])
        for i, item in enumerate(reunion["orden_del_dia"], 1):
            lines.append(f"  {i}. {item}")

        lines.extend([
            "",
            "💡 *¿Cómo participar?*",
            "",
            "Cada quien presenta sus ideas y",
            "entre todos votamos las mejores.",
            "",
            f"📅 Próxima: {reunion.get('proxima_reunion', 'TBD')}",
        ])
        return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────────────────
REUNIONES_PATH = SCRIPT_DIR / "reunion_actual.json"


def cmd_nueva():
    """Iniciar nueva reunión."""
    sis = SistemaReuniones()
    reunion = sis.nueva_reunion()
    # Guardar estado local
    with open(REUNIONES_PATH, "w", encoding="utf-8") as f:
        json.dump(reunion, f, indent=2, ensure_ascii=False)
    print(f"\n  🏢 *NUEVA REUNIÓN INICIADA*")
    print(f"  {'='*50}")
    print(f"  📅 {reunion['fecha']}")
    print(f"  📋 ID: {reunion['id']}")
    print(f"\n  👥 Participantes:")
    for p in reunion["participantes"]:
        print(f"     {p['emoji']} {p['nombre']} — {p['rol']}")
    print(f"\n  📋 Orden del Día:")
    for i, item in enumerate(reunion["orden_del_dia"], 1):
        print(f"     {i}. {item}")
    print(f"\n  ✅ Acta guardada en Obsidian")
    print(f"\n  💡 Próximos pasos:")
    print(f"     python simmoon_reuniones.py --ideas       # Agregar ideas")
    print(f"     python simmoon_reuniones.py --decision    # Registrar decisión")
    print(f"     python simmoon_reuniones.py --actas       # Ver actas")
    print()


def cmd_ideas():
    """Agregar ideas a la reunión actual (tormenta de ideas)."""
    if not REUNIONES_PATH.exists():
        print("\n  ❌ No hay reunión activa. Inicia una con:\n")
        print("     python simmoon_reuniones.py --nueva\n")
        return

    with open(REUNIONES_PATH, "r", encoding="utf-8") as f:
        reunion = json.load(f)

    sis = SistemaReuniones()
    print(f"\n  💡 TORMENTA DE IDEAS — {reunion['id']}")
    print(f"  {'='*50}")
    print(f"  Escribe tus ideas (Enter vacío para terminar):")
    print()

    categorias = {"1": "mecanica", "2": "narrativa", "3": "estrategia", "4": "produccion"}
    while True:
        idea = input("  💡 Idea: ").strip()
        if not idea:
            break
        print("     Categoría: 1=mecánica  2=narrativa  3=estrategia  4=producción")
        cat_idx = input("     > ").strip() or "1"
        categoria = categorias.get(cat_idx, "general")
        autor = input("     Autor: ").strip() or "Anónimo"

        if sis.agregar_idea(reunion["id"], autor, idea, categoria):
            print(f"     ✅ Idea guardada!\n")
        else:
            print(f"     ❌ Error al guardar idea.\n")

    print("  ✅ Ideas registradas en el acta.\n")


def cmd_decision():
    """Registrar una decisión de la reunión actual."""
    if not REUNIONES_PATH.exists():
        print("\n  ❌ No hay reunión activa.\n")
        return

    with open(REUNIONES_PATH, "r", encoding="utf-8") as f:
        reunion = json.load(f)

    sis = SistemaReuniones()
    print(f"\n  ✅ REGISTRAR DECISIÓN — {reunion['id']}")
    print(f"  {'='*50}")
    decision = input("  Decisión: ").strip()
    if decision:
        responsable = input("  Responsable (opcional): ").strip()
        if sis.registrar_decision(reunion["id"], decision, responsable):
            print(f"  ✅ Decisión registrada!\n")


def cmd_actas():
    """Ver actas de reuniones."""
    import argparse
    # Simple parsing for --ultima flag
    solo_ultima = "--ultima" in sys.argv or "-u" in sys.argv

    sis = SistemaReuniones()
    reuniones = sis.obtener_ultimas_reuniones(limit=1 if solo_ultima else 10)

    if not reuniones:
        print("\n  📭 No hay reuniones registradas aún.\n")
        return

    print(f"\n  📋 ACTAS DE REUNIONES ({len(reuniones)})")
    print(f"  {'='*50}")
    for mem in reuniones:
        key = mem.get("key_name", "?")
        content = mem.get("content", "")
        print(f"\n  📅 *{key}*")
        print(f"  {'─'*50}")
        # Mostrar primeras líneas del contenido
        for line in content.split("\n")[:10]:
            if line.strip():
                print(f"  {line}")
        print()
    print()


def cmd_status():
    """Mostrar estado de seguimiento."""
    sis = SistemaReuniones()
    print()
    print(sis.status_seguimiento())
    print()


def cmd_config():
    """Mostrar configuración de reuniones."""
    print(f"\n  ⚙️  CONFIGURACIÓN DE REUNIONES")
    print(f"  {'='*50}")
    print(f"  📅 Tipo:     {REUNIONES_CONFIG['tipo']}")
    print(f"  🕐 Día:      {REUNIONES_CONFIG['dia'].title()}")
    print(f"  ⏰ Hora:     {REUNIONES_CONFIG['hora']}")
    print(f"  ⏱️  Duración: {REUNIONES_CONFIG['duracion_min']} min")
    print(f"\n  👥 Participantes:")
    for p in REUNIONES_CONFIG["participantes"]:
        print(f"     {p['emoji']} {p['nombre']:20s} {p['rol']}")
    print(f"\n  📋 Orden del Día:")
    for i, item in enumerate(REUNIONES_CONFIG["orden_del_dia"], 1):
        print(f"     {i}. {item}")
    print()
    print(f"  💡 Primera reunión:")
    print(f"     python simmoon_reuniones.py --nueva")
    print()


def main():
    """CLI principal."""
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd in ("--nueva", "-n"):
        cmd_nueva()
    elif cmd in ("--ideas", "-i"):
        cmd_ideas()
    elif cmd in ("--decision", "-d"):
        cmd_decision()
    elif cmd in ("--actas", "-a"):
        cmd_actas()
    elif cmd in ("--status", "-s"):
        cmd_status()
    elif cmd in ("--config", "-c"):
        cmd_config()
    else:
        print(f"  ❌ Comando desconocido: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
