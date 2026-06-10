#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buffy_memory.py — Memoria de Proyecto para Buffy 🤖

Permite a Buffy leer resúmenes diarios, memorias de agentes y contexto
del proyecto SIMMOON desde PostgreSQL al iniciar sesión.

Uso:
    python buffy_memory.py                     # Resumen completo (últimos 7 días)
    python buffy_memory.py --days 14           # Ver últimas 2 semanas
    python buffy_memory.py --summaries         # Solo resúmenes diarios
    python buffy_memory.py --memory            # Solo memorias de agentes
    python buffy_memory.py --context           # Contexto formato Buffy (para context window)
    python buffy_memory.py --today             # Solo resumen de hoy
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# ── PostgreSQL Connection ──────────────────────────────────────────────────
def get_db_conn():
    """Get PostgreSQL connection."""
    try:
        try:
            import psycopg
            return psycopg.connect(host="localhost", port=5432, dbname="simmoon", user="postgres")
        except ImportError:
            import psycopg2
            return psycopg2.connect(host="localhost", port=5432, database="simmoon", user="postgres")
    except Exception as e:
        print(f"[WARN] PostgreSQL no disponible: {e}")
        return None


# ── Daily Summaries ────────────────────────────────────────────────────────
def get_recent_summaries(days: int = 7) -> list:
    """Get recent daily summaries from PostgreSQL.
    
    Reutiliza la función de agatha_actas para evitar duplicación.
    """
    try:
        from agatha_actas import get_recent_summaries as _get_summaries
        return _get_summaries(days)
    except ImportError:
        # Fallback si no se puede importar
        pass
    
    conn = get_db_conn()
    if not conn:
        return []


# ── Agent Memory ───────────────────────────────────────────────────────────
def get_shared_context(project: str = 'SIMMOON', days: int = 7, limit: int = 30) -> list:
    """Get shared context from all agents.
    
    Reutiliza la función de agent_memory para evitar duplicación.
    """
    try:
        from agent_memory import get_shared_context as _get_context
        return _get_context(project, days=days, limit=limit)
    except ImportError:
        pass
    
    conn = get_db_conn()
    if not conn:
        return []


# ── Formatters for Buffy ───────────────────────────────────────────────────
def format_summaries_for_buffy(summaries: list) -> str:
    """Format summaries for Buffy context window."""
    if not summaries:
        return "📭 No hay resúmenes diarios disponibles."
    
    lines = []
    lines.append("=" * 60)
    lines.append("📋 RESÚMENES DIARIOS DEL PROYECTO SIMMOON")
    lines.append("=" * 60)
    
    for s in summaries:
        date_str = s['date'].strftime('%Y-%m-%d') if hasattr(s['date'], 'strftime') else str(s['date'])
        lines.append(f"\n📅 {date_str}")
        lines.append(f"   Título: {s['title']}")
        lines.append(f"   📊 Actividad: {s['agents_active']}/{s['agents_total']} agentes, "
                    f"{s['services_active']}/{s['services_total']} servicios")
        if s.get('alerts_count', 0) > 0:
            lines.append(f"   🚨 Alertas: {s['alerts_count']}")
    
    return "\n".join(lines)


def format_memory_for_buffy(memories: list) -> str:
    """Format agent memories for Buffy context window."""
    if not memories:
        return "🧠 No hay memorias de agentes disponibles."
    
    # Group by agent
    by_agent = {}
    for m in memories:
        agent = m['agent_name']
        if agent not in by_agent:
            by_agent[agent] = []
        by_agent[agent].append(m)
    
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("🧠 MEMORIAS COMPARTIDAS DE AGENTES")
    lines.append("=" * 60)
    
    for agent, items in by_agent.items():
        lines.append(f"\n🤖 {agent.upper()}")
        for item in items[:5]:  # Max 5 items per agent
            mem_type = item['memory_type']
            key = item['key_name']
            content = item['content'][:80] + "..." if len(item['content']) > 80 else item['content']
            imp = "⭐" * item['importance']
            lines.append(f"   [{mem_type}] {key}: {content} {imp}")
    
    return "\n".join(lines)


def format_context_for_buffy(days: int = 7) -> str:
    """Format complete context for Buffy (for context window)."""
    summaries = get_recent_summaries(days)
    memories = get_shared_context('SIMMOON', days)
    
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("📚 CONTEXTO DEL PROYECTO — SIMMOON")
    lines.append("=" * 60)
    lines.append(f"📅 Período: últimos {days} días")
    lines.append(f"🕐 Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Summaries
    lines.append("")
    lines.append(format_summaries_for_buffy(summaries))
    
    # Agent Memory
    lines.append(format_memory_for_buffy(memories))
    
    lines.append("")
    lines.append("=" * 60)
    lines.append("FIN DEL CONTEXTO")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def get_today_summary() -> str:
    """Get today's summary if exists."""
    summaries = get_recent_summaries(1)
    if summaries and summaries[0].get('date'):
        today = datetime.now().strftime('%Y-%m-%d')
        if hasattr(summaries[0]['date'], 'strftime'):
            summary_date = summaries[0]['date'].strftime('%Y-%m-%d')
        else:
            summary_date = str(summaries[0]['date'])
        
        if summary_date == today:
            s = summaries[0]
            lines = []
            lines.append(f"📅 RESUMEN DE HOY ({today})")
            lines.append(f"   {s['title']}")
            lines.append(f"   🤖 Agentes: {s['agents_active']}/{s['agents_total']}")
            lines.append(f"   🔌 Servicios: {s['services_active']}/{s['services_total']}")
            lines.append(f"   🖼️  Assets: {s['assets_total']}")
            if s.get('alerts_count', 0) > 0:
                lines.append(f"   🚨 Alertas pendientes: {s['alerts_count']}")
            return "\n".join(lines)
    
    return "📭 No hay resumen de hoy disponible."


def get_project_status() -> str:
    """Get quick project status summary."""
    summaries = get_recent_summaries(1)
    
    if summaries:
        s = summaries[0]
        status = []
        status.append(f"📊 Estado del proyecto:")
        status.append(f"   Agentes activos: {s.get('agents_active', '?')}/{s.get('agents_total', '?')}")
        status.append(f"   Servicios: {s.get('services_active', '?')}/{s.get('services_total', '?')}")
        status.append(f"   Assets totales: {s.get('assets_total', '?')}")
        if s.get('alerts_count', 0) > 0:
            status.append(f"   🚨 Alertas: {s['alerts_count']}")
        return "\n".join(status)
    
    return "📭 Estado no disponible."


# ── CLI Interface ──────────────────────────────────────────────────────────
def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Buffy Memory — Leer contexto del proyecto al iniciar sesión"
    )
    parser.add_argument('--days', type=int, default=7, help='Días de historial (default: 7)')
    parser.add_argument('--summaries', action='store_true', help='Solo resúmenes diarios')
    parser.add_argument('--memory', action='store_true', help='Solo memorias de agentes')
    parser.add_argument('--context', action='store_true', help='Contexto completo para Buffy')
    parser.add_argument('--today', action='store_true', help='Solo resumen de hoy')
    parser.add_argument('--status', action='store_true', help='Estado rápido del proyecto')
    
    args = parser.parse_args()
    
    # Default: show complete context
    if args.summaries:
        summaries = get_recent_summaries(args.days)
        print(format_summaries_for_buffy(summaries))
    elif args.memory:
        memories = get_shared_context('SIMMOON', args.days)
        print(format_memory_for_buffy(memories))
    elif args.today:
        print(get_today_summary())
    elif args.status:
        print(get_project_status())
    elif args.context:
        print(format_context_for_buffy(args.days))
    else:
        # Default: complete context for Buffy
        print(format_context_for_buffy(args.days))


if __name__ == "__main__":
    main()