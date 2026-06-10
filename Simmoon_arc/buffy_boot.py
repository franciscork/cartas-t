#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buffy_boot.py — Boot Loader para Buffy 🤖🚀

Ejecuta esto al INICIO de cada sesión para que Buffy recuerde todo
lo que pasó en sesiones anteriores. Lee la memoria compartida desde
PostgreSQL (tabla agent_memory) y presenta el contexto completo.

Uso:
    python buffy_boot.py                          # Contexto completo
    python buffy_boot.py --quick                  # Solo resumen rápido
    python buffy_boot.py --today                  # Solo lo de hoy
    python buffy_boot.py --readme                 # Ruta al README
"""

import sys
from datetime import datetime
from pathlib import Path

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()

# ── Cargar memoria desde PostgreSQL ────────────────────────────────────────

def load_memory():
    """Load all Buffy memories from PostgreSQL via agent_memory."""
    try:
        from agent_memory import AgentMemory
        memory = AgentMemory('buffy', project='SIMMOON')
        return memory
    except ImportError:
        print("[WARN] agent_memory.py no encontrado")
        return None
    except Exception as e:
        print(f"[WARN] Error conectando a memoria: {e}")
        return None


def print_banner():
    print()
    print("=" * 60)
    print("   🤖 BUFFY v2 — Boot Loader Activated")
    print("   SIMMOON Asset Factory")
    print("=" * 60)
    print()


def print_synthesis():
    """Print Agatha's latest synthesis from daily_summaries."""
    try:
        from agatha_actas import get_recent_summaries
        summaries = get_recent_summaries(days=3)
        if summaries:
            latest = summaries[0]
            print("=" * 60)
            print(f"📊 SINTESIS DE AGATHA ({latest['date']})")
            print("=" * 60)
            print(f"  {latest['title']}")
            print(f"  Assets totales: {latest['assets_total']}")
            print(f"  Servicios: {latest['services_active']}/{latest['services_total']}")
            print(f"  Agentes: {latest['agents_active']}/{latest['agents_total']}")
            print()
    except Exception:
        pass


def print_shared_context(days=7):
    """Print shared context from ALL agents (Hermes, OpenHuman, Agatha, etc)."""
    try:
        from agent_memory import get_shared_context
        shared = get_shared_context('SIMMOON', days=days, limit=15)
        if shared:
            print("=" * 60)
            print("🔄 MEMORIA COMPARTIDA (todos los agentes)")
            print("=" * 60)
            for m in shared:
                print(f"  [{m['agent_name']}] {m['key_name']}")
                print(f"     {m['content'][:120]}")
            print()
    except Exception:
        pass


def print_context(memory, days=7):
    """Print full context for Buffy."""
    print(f"📅 Contexto cargado: últimos {days} días")
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # ── Facts (importantes) ──
    print("=" * 60)
    print("📌 HECHOS IMPORTANTES (facts)")
    print("=" * 60)
    facts = memory.get_recent(days=days, memory_type='fact', limit=20)
    if facts:
        for f in facts:
            stars = "⭐" * f['importance']
            print(f"  [{f['key_name']}] {stars}")
            print(f"     {f['content'][:120]}")
            print()
    else:
        print("  (sin hechos registrados)")
        print()

    # ── Context ──
    print("=" * 60)
    print("📋 CONTEXTO DE SESIONES (context)")
    print("=" * 60)
    contexts = memory.get_recent(days=days, memory_type='context', limit=10)
    if contexts:
        for c in contexts:
            print(f"  [{c['key_name']}]")
            print(f"     {c['content'][:200]}")
            print()
    else:
        print("  (sin contexto registrado)")
        print()

    # ── Preferences ──
    print("=" * 60)
    print("🎯 PREFERENCIAS DEL USUARIO (preferences)")
    print("=" * 60)
    prefs = memory.get_recent(days=30, memory_type='preference', limit=10)
    if prefs:
        for p in prefs:
            print(f"  • {p['content'][:80]}")
        print()
    else:
        print("  (sin preferencias registradas)")
        print()

    # ── Tareas pendientes ──
    print("=" * 60)
    print("✅ TAREAS Y PRÓXIMOS PASOS (task)")
    print("=" * 60)
    tasks = memory.get_recent(days=days, memory_type='task', limit=10)
    if tasks:
        for t in tasks:
            print(f"  [{t['key_name']}] {t['content'][:100]}")
        print()
    else:
        # Try next_steps from context
        next_steps = memory.get('next_steps')
        if next_steps:
            print(f"  📋 Próximos pasos guardados:")
            print(f"     {next_steps['content'][:200]}")
        print()

    # ── Síntesis de Agatha ──
    print_synthesis()

    # ── Memoria compartida de otros agentes ──
    print_shared_context(days)

    # ── README ──
    readme_path = SCRIPT_DIR / "README.md"
    print("=" * 60)
    print("📖 DOCUMENTACIÓN")
    print("=" * 60)
    if readme_path.exists():
        print(f"  README: {readme_path}")
        print(f"  (Lectura recomendada: python -c \"print(open('{readme_path}').read())\")")
    print()

    print("=" * 60)
    print("🚀 ¡BUFFY LISTA! Recuerda: usuario prefiere ESPAÑOL.")
    print("=" * 60)


def print_quick(memory, days=1):
    """Quick summary for today."""
    print(f"\n📋 RESUMEN RÁPIDO (hoy, {datetime.now().strftime('%Y-%m-%d')})")
    print("-" * 50)

    facts = memory.get_recent(days=days, memory_type='fact', limit=5)
    if facts:
        for f in facts:
            print(f"  • [{f['key_name']}] {f['content'][:80]}")

    ctx = memory.get_recent(days=days, memory_type='context', limit=3)
    if ctx:
        for c in ctx:
            print(f"  • [{c['key_name']}] {c['content'][:80]}")

    # Quick synthesis from Agatha
    print_synthesis()
    print()


def print_today(memory):
    """Show today's session context (most recent context memory)."""
    today = datetime.now().strftime('%Y%m%d')
    # Try dynamic session key first
    session = memory.get(f'session_{today}')
    if not session:
        # Fallback: get most recent context
        recent = memory.get_recent(days=7, memory_type='context', limit=1)
        if recent:
            session = recent[0]
    if session:
        print(f"\n📅 ÚLTIMA SESIÓN ({session['key_name']})")
        print("-" * 50)
        print(f"  {session['content'][:200]}")
        print()
    else:
        print("\n📭 No hay sesiones registradas.\n")


def print_readme():
    readme = SCRIPT_DIR / "README.md"
    if readme.exists():
        print(readme)
    else:
        print("README.md no encontrado en Simmoon_arc/")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Buffy Boot Loader — Cargar memoria persistida")
    parser.add_argument('--quick', action='store_true', help='Solo resumen rápido')
    parser.add_argument('--today', action='store_true', help='Solo lo de hoy')
    parser.add_argument('--readme', action='store_true', help='Ruta al README')
    parser.add_argument('--days', type=int, default=7, help='Días de historial (default: 7)')
    args = parser.parse_args()

    print_banner()
    memory = load_memory()

    if not memory:
        print("❌ Memoria no disponible. ¿PostgreSQL está corriendo?")
        print("\nPara empezar sin memoria, ve al README:")
        print(f"   {SCRIPT_DIR / 'README.md'}")
        sys.exit(1)

    if args.readme:
        print_readme()
    elif args.today:
        print_today(memory)
    elif args.quick:
        print_quick(memory, args.days)
    else:
        print_context(memory, args.days)


if __name__ == "__main__":
    main()
