#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
factory/cli.py — Interfaz CLI de FactoryGames 🏭

Comandos:
  factory status              — Estado completo del sistema
  factory agents              — Listar agentes registrados
  factory delegate coding     — Delegar tarea de código
  factory delegate image      — Generar imagen
  factory delegate llm        — Consultar LLM
  factory recover <svc>       — Recuperar servicio
  factory recover --all       — Recuperar todos los caídos
  factory session             — Resumen de la sesión
  factory monitor             — Iniciar health checks periódicos
  factory help                — Ayuda detallada
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))


# ══════════════════════════════════════════════════════════════════════════
#  Factory CLI
# ══════════════════════════════════════════════════════════════════════════

_ORCHESTRATOR = None

def get_factory(verbose: bool = True):
    """Obtener instancia singleton del orquestador."""
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        from factory.orchestrator import FactoryOrchestrator
        _ORCHESTRATOR = FactoryOrchestrator(verbose=verbose)
    return _ORCHESTRATOR


def cmd_boot(args):
    """Arrancar el orquestador y mostrar estado."""
    factory = get_factory(args.verbose)
    factory.boot()


def cmd_status(args):
    """Mostrar estado completo del sistema."""
    factory = get_factory(args.verbose)
    print(factory.status_text())


def cmd_agents(args):
    """Listar agentes registrados."""
    factory = get_factory(args.verbose)
    print(factory.agents_text())


def cmd_pipeline(args):
    """Ejecutar pipeline completo de generación de assets."""
    factory = get_factory(args.verbose)

    categories = " ".join(args.categories) if args.categories else ""
    if not categories:
        print("  ❌ Debes especificar al menos una categoría")
        print("     Ej: factory pipeline businesses vehicles")
        return

    result = factory.delegate(
        task_type="pipeline",
        task=categories,
        run_suffix=args.run_suffix or "",
        checkpoint=args.checkpoint or "",
        backend=args.backend or "factory",
        no_loras=args.no_loras,
        lora=args.lora or "",
        skip_generation=args.skip_generation,
        skip_pixel=args.skip_pixel,
        skip_db=args.skip_db,
    )

    print(f"\n  Resultado: {'✅' if result['success'] else '❌'}")
    print(f"  Agente: {result['agent']}")
    print(f"  Duración: {result['duration']/60:.1f}m")
    if result["output"]:
        print(f"  {result['output'][:500]}")
    if result["error"]:
        print(f"  ⚠️  {result['error'][:500]}")


def cmd_delegate(args):
    """Delegar tarea al agente adecuado."""
    factory = get_factory(args.verbose)

    if args.type == "coding":
        task = " ".join(args.task) if args.task else input("  📝 Describe la tarea de código: ")
        files = args.files or []
        context = args.context or ""
        effort = args.effort or "high"

        result = factory.delegate(
            task_type="coding",
            task=task,
            files=files,
            context=context,
            effort=effort,
        )

        print(f"\n  Resultado: {'✅' if result['success'] else '❌'}")
        print(f"  Agente: {result['agent']}")
        print(f"  Duración: {result['duration']}s")
        if result["files_modified"]:
            print(f"  Archivos: {', '.join(result['files_modified'][:5])}")
        if result["output"]:
            print(f"\n  Output:\n    {result['output'][:500]}")

    elif args.type == "image":
        prompt = " ".join(args.task) if args.task else input("  🖼️  Describe la imagen: ")
        output = args.output or ""
        width = args.width or 512
        height = args.height or 512

        result = factory.delegate(
            task_type="image",
            task=prompt,
            output_path=output,
            width=width,
            height=height,
        )

        print(f"\n  Resultado: {'✅' if result['success'] else '❌'}")
        if result["files_modified"]:
            print(f"  📄 {result['files_modified'][0]}")

    elif args.type == "llm":
        prompt = " ".join(args.task) if args.task else input("  💬 Pregunta: ")

        result = factory.delegate(
            task_type="llm",
            task=prompt,
        )

        print(f"\n  Respuesta:")
        print(f"  {result['output'][:1000]}")

    elif args.type == "pipeline":
        categories = " ".join(args.task) if args.task else ""
        if not categories:
            print("  ❌ Debes especificar categorías")
            print("     Ej: factory delegate pipeline 'businesses vehicles'")
            return

        result = factory.delegate(
            task_type="pipeline",
            task=categories,
        )

        print(f"\n  Resultado: {'✅' if result['success'] else '❌'}")
        print(f"  Agente: {result['agent']}")
        print(f"  Duración: {result['duration']/60:.1f}m")
        if result["output"]:
            print(f"  {result['output'][:500]}")
        if result["error"]:
            print(f"  ⚠️  {result['error'][:500]}")

    else:
        print(f"  ❌ Tipo de tarea no soportado: {args.type}")
        print(f"     Usa: coding, image, llm, o pipeline")


def cmd_recover(args):
    """Recuperar servicio(s)."""
    factory = get_factory(args.verbose)

    if args.service == "all":
        results = factory.recover()
        print(f"\n  Resultados de recuperación:")
        for name, ok in results.items():
            icon = "✅" if ok else "❌"
            print(f"     {icon} {name}")
    else:
        ok = factory.recover(args.service)
        print(f"\n  {'✅' if ok else '❌'} {args.service}: "
              f"{'recuperado' if ok else 'no se pudo recuperar'}")


def cmd_session(args):
    """Mostrar resumen de la sesión."""
    factory = get_factory(args.verbose)
    print(factory.session_summary())


def cmd_monitor(args):
    """Iniciar health checks periódicos."""
    factory = get_factory(args.verbose)
    factory.monitor.start_periodic_check(interval=args.interval)
    print(f"  🔍 Health Monitor: verificando cada {args.interval}s")
    print("  Presiona Ctrl+C para detener...")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        factory.monitor.stop_periodic_check()
        print("  ✅ Monitor detenido")


def cmd_interactive(args):
    """Modo interactivo (menú)."""
    factory = get_factory(verbose=True)

    while True:
        import os
        os.system("cls" if sys.platform == "win32" else "clear")

        # Cabecera
        print(f"\n  {'='*55}")
        print(f"  🏭  FACTORY GAMES — Orquestador")
        print(f"  {'='*55}")

        # Estado rápido de servicios
        factory.monitor.check_all()
        results = factory.monitor.get_results()
        healthy = sum(1 for h in results.values() if h)
        total = len(results)
        print(f"\n  📊 Servicios: {healthy}/{total} activos")

        for name, ok in results.items():
            icon = "✅" if ok else "⚫"
            print(f"     {icon} {name}")

        # Menú
        print(f"\n  {'─'*55}")
        print(f"  [s] Status    [a] Agents    [d] Delegate    [p] Pipeline")
        print(f"  [r] Recover   [m] Monitor   [v] Session     [q] Salir")
        print(f"  {'─'*55}")

        choice = input("  > ").strip().lower()

        if choice == "q":
            break
        elif choice == "s":
            print(factory.status_text())
            input("  Presiona Enter para continuar...")
        elif choice == "a":
            print(factory.agents_text())
            input("  Presiona Enter para continuar...")
        elif choice == "d":
            task_type = input("  Tipo (coding/image/llm/pipeline): ").strip()
            task = input("  Tarea: ").strip()
            if task_type and task:
                result = factory.delegate(task_type, task)
                print(f"\n  {'✅' if result['success'] else '❌'} Completado")
            input("  Presiona Enter para continuar...")
        elif choice == "p":
            cats = input("  Categorías (ej: businesses vehicles): ").strip()
            if cats:
                result = factory.delegate("pipeline", cats)
                print(f"\n  {'✅' if result['success'] else '❌'} Pipeline completado")
            input("  Presiona Enter para continuar...")
        elif choice == "r":
            svc = input("  Servicio a recuperar (o 'all'): ").strip()
            if svc:
                cmd_recover(argparse.Namespace(service=svc, verbose=True))
            input("  Presiona Enter para continuar...")
        elif choice == "m":
            print(factory.status_text())
            input("  Presiona Enter para continuar...")
        elif choice == "v":
            print(factory.session_summary())
            input("  Presiona Enter para continuar...")


# ══════════════════════════════════════════════════════════════════════════
#  Main CLI
# ══════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    """Construir parser de argumentos."""
    parser = argparse.ArgumentParser(
        description="🏭 FactoryGames — Sistema de Orquestación",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  factory status           Estado completo del sistema
  factory agents           Listar agentes registrados
  factory delegate coding "Refactoriza X" -f archivo.py
  factory delegate image "un robot" -o robot.png
  factory delegate llm "Hola"
  factory recover ollama   Recuperar Ollama
  factory recover --all    Recuperar todos
  factory session          Resumen de sesión
        """,
    )
    parser.add_argument("--verbose", "-v", action="store_true", default=True,
                        help="Modo verbose")
    parser.add_argument("--quiet", "-q", action="store_false", dest="verbose",
                        help="Modo silencioso")

    subparsers = parser.add_subparsers(dest="command", help="Comandos")

    # boot
    p_boot = subparsers.add_parser("boot", help="Inicializar el sistema")

    # status
    p_status = subparsers.add_parser("status", help="Estado completo del sistema")

    # agents
    subparsers.add_parser("agents", help="Listar agentes registrados")

    # delegate
    p_delegate = subparsers.add_parser("delegate", help="Delegar tarea")
    p_delegate.add_argument("type", choices=["coding", "image", "llm", "pipeline"],
                            help="Tipo de tarea")
    p_delegate.add_argument("task", nargs="*", help="Descripción de la tarea")
    p_delegate.add_argument("--files", "-f", nargs="*", help="Archivos relevantes")
    p_delegate.add_argument("--context", "-c", help="Contexto adicional")
    p_delegate.add_argument("--effort", "-e", choices=["low", "medium", "high"],
                            default="high", help="Nivel de esfuerzo")
    p_delegate.add_argument("--output", "-o", help="Archivo de salida (para image)")
    p_delegate.add_argument("--width", "-w", type=int, default=512, help="Ancho (image)")
    p_delegate.add_argument("--height", type=int, default=512, help="Alto (image)")

    # pipeline (dedicado)
    p_pipeline = subparsers.add_parser("pipeline", help="Ejecutar pipeline completo de assets")
    p_pipeline.add_argument("categories", nargs="+",
                            help="Categorías a procesar (ej: businesses vehicles)")
    p_pipeline.add_argument("--run-suffix", default="",
                            help="Sufijo para archivos generados")
    p_pipeline.add_argument("--checkpoint", default="",
                            help="Checkpoint de ComfyUI")
    p_pipeline.add_argument("--backend", "-b", default="factory",
                            choices=["factory", "diffusers", "comfyui"],
                            help="Backend de generación (default: factory)")
    p_pipeline.add_argument("--no-loras", action="store_true",
                            help="Deshabilitar LoRAs")
    p_pipeline.add_argument("--lora", default="",
                            help="LoRA spec: 'name:strength_model:strength_clip'")
    p_pipeline.add_argument("--skip-generation", action="store_true",
                            help="Saltar generación")
    p_pipeline.add_argument("--skip-pixel", action="store_true",
                            help="Saltar pixel art")
    p_pipeline.add_argument("--skip-db", action="store_true",
                            help="Saltar inserción en BD")

    # recover
    p_recover = subparsers.add_parser("recover", help="Recuperar servicio(s)")
    p_recover.add_argument("service", nargs="?", default="all",
                           help="Servicio a recuperar (default: all)")

    # session
    subparsers.add_parser("session", help="Resumen de la sesión")

    # monitor
    p_monitor = subparsers.add_parser("monitor", help="Health checks periódicos")
    p_monitor.add_argument("--interval", "-i", type=int, default=30,
                           help="Intervalo en segundos (default: 30)")

    # interactive menu
    subparsers.add_parser("menu", help="Modo interactivo")
    subparsers.add_parser("interactive", help="Modo interactivo")
    subparsers.add_parser("help", help="Ayuda detallada")

    return parser


def main():
    """Punto de entrada principal de la CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command in (None, "menu", "interactive"):
        cmd_interactive(args)
    elif args.command == "boot":
        cmd_boot(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "agents":
        cmd_agents(args)
    elif args.command == "delegate":
        cmd_delegate(args)
    elif args.command == "pipeline":
        cmd_pipeline(args)
    elif args.command == "recover":
        cmd_recover(args)
    elif args.command == "session":
        cmd_session(args)
    elif args.command == "monitor":
        cmd_monitor(args)
    elif args.command == "help":
        parser.print_help()
        print()
        print("  Comandos disponibles:")
        for name, sub in parser._subparsers._group_actions[0].choices.items():
            print(f"    {name:15s} — {sub.description}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
