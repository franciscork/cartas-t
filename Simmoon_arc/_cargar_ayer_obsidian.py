#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_cargar_ayer_obsidian.py — Carga el resumen de AYER en Obsidian

Lee los eventos del system_log.jsonl de ayer y los guarda en
Diarias/YYYY-MM-DD.md del vault Obsidian (filesystem o REST API).

No usa generate_daily_summary() porque esa función solo genera para HOY.
"""
import sys
import os
import re
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# ── Importar listas canónicas de servicios y agentes ──────────────────────
# Single source of truth: shared_services_agents.py
# Esto evita los magic numbers 4/3 hardcodeados.
try:
    from shared_services_agents import (
        SERVICE_DEFINITIONS,
        AGENT_DEFINITIONS,
        KNOWN_SERVICES_TOTAL,
        KNOWN_AGENTS_TOTAL,
    )
    _REAL_COUNTS_OK = True
except ImportError as e:
    print(f"  ⚠️  No se pudo importar shared_services_agents: {e}")
    _REAL_COUNTS_OK = False

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_yesterday_events(yesterday: str) -> list:
    """Carga todos los eventos del log de la fecha objetivo.

    Busca primero en el archivo diario system_log.YYYY-MM-DD.jsonl.
    Si no existe, cae en el archivo único system_log.jsonl (legacy)
    y filtra por timestamp.
    """
    events = []

    # ── Intentar archivo diario (nuevo formato) ──
    daily_file = SCRIPT_DIR / f"system_log.{yesterday}.jsonl"
    if daily_file.exists():
        try:
            with open(daily_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            print(f"  📂 Leídos {len(events)} eventos de {daily_file.name}")
            return events
        except Exception as e:
            print(f"  ⚠️  Error leyendo {daily_file.name}: {e}")

    # ── Fallback: archivo único legacy ──
    log_file = SCRIPT_DIR / "system_log.jsonl"
    if not log_file.exists():
        return []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                    if e.get("ts", "").startswith(yesterday):
                        events.append(e)
                except json.JSONDecodeError:
                    continue
        print(f"  📂 Leídos {len(events)} eventos de system_log.jsonl (legacy)")
    except Exception as e:
        print(f"  ⚠️  Error leyendo system_log: {e}")
    return events


def _count_services_active(events: list) -> int:
    """Cuenta cuántos servicios (de SERVICE_DEFINITIONS) tienen actividad
    registrada en `events`.

    Reglas de match (por servicio):
      1. `event["source"]` igual al `key` del servicio (case-insensitive), o
      2. word-boundary match del `key` en `event["message"]`
         (e.g. `\bollama\b` NO matchea dentro de "llamó al cliente").

    Cada servicio se cuenta como máximo una vez aunque tenga varios eventos.
    Si SERVICE_DEFINITIONS no se pudo importar, devuelve 0 (desconocido).

    Args:
        events: lista de dicts con al menos los campos "source" y/o "message".

    Returns:
        Número entero de servicios con actividad detectada (0..N).
    """
    if not _REAL_COUNTS_OK:
        return 0
    services_active = 0
    for key, _name, _url, _tipo in SERVICE_DEFINITIONS:
        # Word-boundary regex evita falsos positivos tipo "ollama" en "llamó"
        pattern = re.compile(rf"\b{re.escape(key)}\b", re.IGNORECASE)
        for e in events:
            src = (e.get("source", "") or "").lower()
            msg = (e.get("message", "") or "")
            if src == key or pattern.search(msg):
                services_active += 1
                break  # cuenta cada servicio solo una vez
    return services_active


def load_yesterday_metrics(yesterday: str) -> dict:
    """Intenta obtener métricas de ayer desde PostgreSQL o desde
    los datos de generación de assets en filesystem."""
    # Totales reales desde connect_agents_to_memory (no magic numbers)
    if _REAL_COUNTS_OK:
        real_services_total = KNOWN_SERVICES_TOTAL
        real_agents_total = KNOWN_AGENTS_TOTAL
    else:
        # Si no se pudo importar, 0 indica "desconocido" (no inventar)
        real_services_total = 0
        real_agents_total = 0

    metrics = {
        "assets_created": 0,
        "assets_total": 0,
        "services_active": 0,
        "services_total": real_services_total,
        "agents_active": 0,
        "agents_total": real_agents_total,
        "alerts_count": 0,
    }

    # ── Intentar PostgreSQL (si está disponible) ──
    try:
        import psycopg2
        conn = psycopg2.connect(dbname='simmoon', user='simmoon',
                                password='simmoon', host='localhost')
        cur = conn.cursor()
        # Assets creados ayer
        cur.execute("""
            SELECT COUNT(*) FROM assets
            WHERE DATE(created_at) = %s
        """, (yesterday,))
        row = cur.fetchone()
        if row:
            metrics["assets_created"] = row[0]
        # Total assets
        cur.execute("SELECT COUNT(*) FROM assets")
        metrics["assets_total"] = cur.fetchone()[0]
        conn.close()
        print(f"  📊 Métricas obtenidas de PostgreSQL")
    except Exception:
        # ── Fallback: filesystem assets ──
        assets_dir = SCRIPT_DIR / "simmoon_blender_assets"
        if assets_dir.exists():
            from datetime import datetime as _dt
            y_dt = _dt.strptime(yesterday, "%Y-%m-%d")
            count = 0
            for f in assets_dir.rglob("*.png"):
                try:
                    mtime = _dt.fromtimestamp(f.stat().st_mtime)
                    if mtime.date() == y_dt.date():
                        count += 1
                except Exception:
                    pass
            metrics["assets_created"] = count
            total = sum(1 for _ in assets_dir.rglob("*.png"))
            metrics["assets_total"] = total
        print(f"  📊 Métricas obtenidas de filesystem (PostgreSQL no disponible)")

    return metrics


def build_yesterday_summary(yesterday: str) -> dict:
    """Construye el resumen de ayer desde logs locales + métricas."""
    print(f"  📅 Construyendo resumen para {yesterday}...")

    # ── 1) Métricas ──
    metrics = load_yesterday_metrics(yesterday)

    # ── 2) Eventos del system_log.jsonl ──
    events = load_yesterday_events(yesterday)
    by_source: dict = {}
    alerts = []
    for e in events:
        src = e.get("source", "?")
        by_source.setdefault(src, []).append(e)
        # Detectar alertas (iconos comunes: ⚠️ ❌ 🚨)
        if e.get("icon") in ("⚠️", "❌", "🚨", "⛔"):
            alerts.append(e)

    # agents_active: número de fuentes distintas en system_log
    metrics["agents_active"] = len(by_source)
    metrics["alerts_count"] = len(alerts)

    # services_active: contar servicios con actividad registrada HOY en logs.
    # Usa coincidencia exacta de source + word-boundary en message para
    # evitar falsos positivos tipo "ollama" dentro de "llamó".
    # NO completar a total cuando no hay eventos:
    # cero eventos puede significar daemon caído, no servicios sanos.
    metrics["services_active"] = _count_services_active(events)

    # ── 3) Componer contenido markdown ──
    pretty_date = datetime.strptime(yesterday, "%Y-%m-%d").strftime("%d/%m/%Y")
    lines = [
        f"📊 *Resumen SIMMOON — {pretty_date}*",
        "",
        f"📅 Fecha: {yesterday}",
        f"🤖 Fuentes de actividad: {len(by_source)}",
        f"📋 Eventos totales: {len(events)}",
        "",
        "🔔 *Métricas:*",
        f"  • Assets creados: {metrics['assets_created']}",
        f"  • Assets totales en sistema: {metrics['assets_total']}",
        f"  • Agentes IA activos: {metrics['agents_active']}",
        f"  • Alertas detectadas: {len(alerts)}",
        "",
    ]

    if by_source:
        lines.append("🤖 *Actividad por agente:*")
        for source, evs in sorted(by_source.items(), key=lambda x: -len(x[1])):
            lines.append(f"  • *{source}* — {len(evs)} eventos")
        lines.append("")

    if alerts:
        lines.append(f"🚨 *Alertas ({len(alerts)}):*")
        for a in alerts[:5]:
            ts = a.get("ts", "")[11:16]
            msg = a.get("message", "")[:80]
            lines.append(f"  • `{ts}` {msg}")
        if len(alerts) > 5:
            lines.append(f"  _... y {len(alerts) - 5} más_")
        lines.append("")

    if events:
        lines.append(f"📋 *Eventos destacados del día:*")
        # Mostrar 1-2 eventos por fuente
        for source, evs in sorted(by_source.items()):
            for ev in evs[:3]:
                ts = ev.get("ts", "")[11:16]
                icon = ev.get("icon", "·")
                msg = ev.get("message", "")[:90]
                lines.append(f"  `{ts}` {icon} *{source}*: {msg}")
        lines.append("")

    lines.append(f"🏭 *FactoryGames — Contexto*")
    lines.append("  Estudio indie con 15 agentes IA open-source | "
                 "Ollama + Freebuff + Claude Code + Hermes")
    lines.append("  Pipeline: Concepto → Diseño → Arte → 3D → Código → QA → Marketing → Release")
    lines.append("")
    lines.append(f"_Cargado por Buffy · {datetime.now().strftime('%H:%M')} · "
                 f"fuente: system_log.jsonl + métricas locales_")

    content = "\n".join(lines)

    metadata = {
        "date": yesterday,
        "assets_created": metrics["assets_created"],
        "assets_total": metrics["assets_total"],
        "services_active": metrics["services_active"],
        "services_total": metrics["services_total"],
        "agents_active": metrics["agents_active"],
        "agents_total": metrics["agents_total"],
        "alerts_count": metrics["alerts_count"],
        "system_events": len(events),
        "system_sources": len(by_source),
        "tags": ["daily", "yesterday", "from_local_logs", "buffy"],
        "created_by": "Buffy · cargar ayer",
    }

    return {
        "date": yesterday,
        "title": f"Resumen SIMMOON {yesterday}",
        "content": content,
        "metadata": metadata,
    }


def save_to_obsidian(summary: dict, vault_path: str = None) -> bool:
    """Guarda el resumen en Obsidian (filesystem o REST API)."""
    from obsidian_memory import ObsidianMemory

    # REST API tiene prioridad si está configurada
    rest_api_key = os.environ.get("OBSIDIAN_REST_API_KEY", "")
    rest_port = None
    if rest_api_key:
        rest_port = int(os.environ.get("OBSIDIAN_REST_PORT", "27123"))

    obs = ObsidianMemory(
        vault_path=vault_path,  # None → ~/simmoon-memoria
        agent_name="Buffy",
        project="SIMMOON",
        rest_port=rest_port,
        rest_api_key=rest_api_key or None,
        rest_https=os.environ.get("OBSIDIAN_REST_HTTPS", "").lower() == "true",
    )

    mode = "REST" if obs.rest_available else "FS"
    vault_display = obs.vault_path
    target_date = summary["date"]
    new_events = summary["metadata"].get("system_events", 0)

    # ── Guard: no sobrescribir si la diaria existente tiene contenido ──
    # Si el nuevo resumen tiene 0 eventos, verificamos que no estemos
    # pisando una versión anterior con datos reales (ej: generada por
    # send_daily_summary o una carga previa con eventos del log).
    # Comprobamos múltiples indicadores porque send_daily_summary() usa
    # assets_created/agents_active, mientras cargar_ayer usa system_events.
    if new_events == 0:
        try:
            existing_diarias = obs.get_diarias(days=30, limit=10)
            for d in existing_diarias:
                if d.get("date", "")[:10] == target_date:
                    has_content = (
                        d.get("system_events", 0) > 0 or
                        d.get("assets_created", 0) > 0 or
                        d.get("agents_active", 0) > 0 or
                        d.get("services_active", 0) > 0
                    )
                    if has_content:
                        existing_events = d.get("system_events", 0) or "?"
                        existing_sources = d.get("system_sources", 0) or "?"
                        print(f"  ⚠️  Ya existe una diaria con contenido "
                              f"({existing_events} eventos, "
                              f"{existing_sources} fuentes). "
                              f"No se sobrescribe con versión vacía (0 eventos).")
                        return False
                    break
        except Exception as e:
            # Si falla la consulta (ej: REST API caída), continuamos
            # con el guardado normal para no bloquear el flujo.
            print(f"  ⚠️  No se pudo verificar diaria existente: {e}")

    print(f"  🪨 Guardando en Obsidian [{mode}]: {vault_display}/Diarias/{target_date}.md")

    ok = obs.save_diaria(
        summary["date"],
        summary["title"],
        summary["content"],
        summary["metadata"],
    )

    if ok:
        # Contexto por hora como referencia
        obs.save_context(
            f"yesterday_load_{summary['date']}",
            f"Resumen del {summary['date']} cargado en Obsidian. "
            f"{summary['metadata'].get('system_events', 0)} eventos "
            f"de {summary['metadata'].get('system_sources', 0)} fuentes.",
            tags=["yesterday", "load", "obsidian"],
            importance=2,
        )
        print(f"  ✅ Guardado exitoso")
    else:
        print(f"  ❌ Error al guardar")

    return ok


def main():
    parser = argparse.ArgumentParser(
        description="Carga el resumen de ayer en Obsidian desde logs locales"
    )
    parser.add_argument("--date", default=None,
                        help="Fecha a cargar (default: ayer). Formato YYYY-MM-DD")
    parser.add_argument("--vault", default=None,
                        help="Ruta al vault Obsidian (default: ~/simmoon-memoria)")
    args = parser.parse_args()

    # Fecha objetivo
    if args.date:
        yesterday = args.date
    else:
        yesterday_dt = datetime.now() - timedelta(days=1)
        yesterday = yesterday_dt.strftime("%Y-%m-%d")

    print(f"\n  🌙 Cargando resumen de AYER ({yesterday}) en Obsidian...")
    print(f"  {'='*60}")

    summary = build_yesterday_summary(yesterday)
    print(f"\n  📝 Resumen construido:")
    print(f"     Título: {summary['title']}")
    print(f"     Contenido: {len(summary['content'])} caracteres")
    print(f"     Eventos: {summary['metadata'].get('system_events', 0)}")
    print(f"     Fuentes: {summary['metadata'].get('system_sources', 0)}")

    ok = save_to_obsidian(summary, vault_path=args.vault)

    if not ok:
        print(f"\n  ⚠️  No se guardó. La diaria existente tiene más contenido.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
