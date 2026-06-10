#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buffy_ollama.py — 🦙 Comando rápido para ejecutar tareas con Ollama desde terminal

Usa el cliente OllamaAnthropicClient (Anthropic Messages API) para ejecutar
tareas de código directamente desde la terminal, sin escribir Python.

Uso:
    buffy-ollama "Tu tarea de codigo aqui"
    buffy-ollama "Refactoriza esto" --file simmoon_pipeline.py
    buffy-ollama --models
    buffy-ollama --interactive

Alias rapido (si prefieres):
    cc "Tu tarea de codigo aqui"
    cc "Analiza este archivo" -f apply_happiness.py

Ejemplos:
    cc "Explica que hace este codigo" -f simmoon_pipeline.py
    cc "Agrega logging a este modulo" -f generator_factory.py --context "Usa logging de Python"
    cc "Crea una funcion que valide JSON" --output-mode raw
    cc --models                          # Listar modelos disponibles
    cc --interactive                     # Chat interactivo
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()

# ── Import OllamaAnthropicClient ──────────────────────────────────────────
try:
    from claude_code_bridge import OllamaAnthropicClient, ClaudeCodeResult
except ImportError as e:
    print(f"❌ Error: No se pudo importar OllamaAnthropicClient: {e}")
    print("   Asegurate de que claude_code_bridge.py existe en el mismo directorio.")
    sys.exit(1)


# ── Colores para terminal ─────────────────────────────────────────────────
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'
    # Advertencia: en Windows cmd.exe clasico no hay soporte ANSI
    # En PowerShell, Terminal Windows, o bash si hay soporte
    SUPPORTS_COLOR = (
        hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        and os.environ.get('TERM') not in ('', 'dumb')
    )

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        if cls.SUPPORTS_COLOR:
            return f"{color}{text}{cls.RESET}"
        return text


def print_banner():
    """Print banner al iniciar."""
    banner = rf"""{Colors.colorize("  ╔══════════════════════════════════════╗", Colors.CYAN)}
{Colors.colorize("  ║     🦙  B U F F Y   O L L A M A    ║", Colors.CYAN)}
{Colors.colorize("  ║     Codigo local y gratuito         ║", Colors.CYAN)}
{Colors.colorize("  ╚══════════════════════════════════════╝", Colors.CYAN)}
"""
    print(banner)


def format_time(seconds: float) -> str:
    """Formatear segundos a formato legible."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}m{secs}s"


def print_result(result: ClaudeCodeResult, output_mode: str = "smart",
                 show_banner: bool = True):
    """Mostrar resultado de forma bonita."""
    if show_banner:
        print_banner()

    # Status header
    if result.success:
        status = Colors.colorize("✅ COMPLETADO", Colors.GREEN)
    else:
        status = Colors.colorize("❌ ERROR", Colors.RED)

    duration_str = format_time(result.duration)

    print(f"  {status}  |  {Colors.colorize('⏱', Colors.DIM)} {duration_str}")
    print()

    # Output
    output = result.output.strip()
    if not output:
        print(f"  {Colors.colorize('(sin output)', Colors.DIM)}")
        print()
        return

    if output_mode == "raw":
        # Modo raw: output sin adornos
        print(output)
        return

    # Modo smart: output procesado
    print(f"  {Colors.colorize('─' * 50, Colors.DIM)}")
    print(f"  {Colors.colorize('📄 SALIDA', Colors.BOLD)}")
    print(f"  {Colors.colorize('─' * 50, Colors.DIM)}")
    print()

    # Si es demasiado largo, truncar con aviso
    max_chars = 5000 if output_mode == "smart" else 100000
    if len(output) > max_chars:
        print(output[:max_chars])
        print()
        print(f"  {Colors.colorize(f'... ({len(output) - max_chars} chars mas, usa --output-mode raw para completo)', Colors.DIM)}")
    else:
        print(output)

    print()
    print(f"  {Colors.colorize('─' * 50, Colors.DIM)}")

    # Summary
    if result.summary and output_mode == "smart":
        print(f"  {Colors.colorize('📋 RESUMEN:', Colors.BOLD)} {result.summary[:200]}")

    print(f"  {Colors.colorize('─' * 50, Colors.DIM)}")
    print()


def list_models(client: OllamaAnthropicClient):
    """Listar modelos disponibles en Ollama."""
    print_banner()
    print(f"  {Colors.colorize('🔍 Modelos disponibles en Ollama', Colors.BOLD)}")
    print(f"  {Colors.colorize('─' * 50, Colors.DIM)}")

    models = client.list_models()
    if not models:
        print(f"  {Colors.colorize('❌ No se pudo conectar con Ollama.', Colors.RED)}")
        print(f"  Asegurate de que 'ollama serve' este corriendo.")
        return

    # Separar modelos de codigo
    coder_models = [m for m in models if 'coder' in m.lower()]
    other_models = [m for m in models if 'coder' not in m.lower()]

    if coder_models:
        print(f"\n  {Colors.colorize('🧠 Modelos recomendados para codigo:', Colors.GREEN)}")
        for m in sorted(coder_models):
            print(f"    • {Colors.colorize(m, Colors.BOLD)}{Colors.colorize('  ← recomendado', Colors.GREEN)}")

    print(f"\n  {Colors.colorize('📦 Otros modelos disponibles:', Colors.DIM)}")
    for m in sorted(other_models):
        print(f"    • {m}")

    # Modelo activo
    print(f"\n  {Colors.colorize('─' * 50, Colors.DIM)}")
    print(f"  Modelo activo: {Colors.colorize(client.model, Colors.CYAN)}")
    print(f"  Para cambiar:  cc --model <nombre> \"tu tarea\"")
    print()


def interactive_chat(client: OllamaAnthropicClient):
    """Modo interactivo: chat continuo."""
    print_banner()
    print(f"  {Colors.colorize('💬 Modo interactivo', Colors.BOLD)}")
    print(f"  {Colors.colorize(f'  Modelo: {client.model}', Colors.DIM)}")
    print(f"  {Colors.colorize('  Escribe \"exit\" o Ctrl+C para salir', Colors.DIM)}")
    print(f"  {Colors.colorize('─' * 50, Colors.DIM)}")

    history = []
    try:
        while True:
            # Prompt del usuario
            try:
                prompt = input(f"\n  {Colors.colorize('🧑 Tú:', Colors.BLUE)} ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not prompt:
                continue
            if prompt.lower() in ('exit', 'quit', 'salir', ':q', 'q'):
                break

            history.append({"role": "user", "content": prompt})

            # Mostrar spinner
            sys.stdout.write(f"  {Colors.colorize('🤖 Buffy:', Colors.CYAN)} ")
            sys.stdout.flush()

            start = time.time()
            response = client.chat(prompt, timeout=300)
            duration = time.time() - start

            # Borrar el placeholder y mostrar respuesta
            sys.stdout.write("\r\033[K")  # Limpiar linea
            if response.startswith("[ERROR]"):
                print(f"  {Colors.colorize(f'❌ {response}', Colors.RED)}")
            else:
                print(f"  {Colors.colorize('🤖 Buffy:', Colors.CYAN)} {response}")
                print(f"  {Colors.colorize(f'  ⏱ {format_time(duration)}', Colors.DIM)}")
                history.append({"role": "assistant", "content": response})

    except KeyboardInterrupt:
        print(f"\n\n  {Colors.colorize('👋 Hasta luego!', Colors.YELLOW)}")
    finally:
        print()


def main():
    parser = argparse.ArgumentParser(
        description="🦙 Buffy Ollama — Ejecuta tareas de codigo con Ollama desde la terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ejemplos:
  cc "Explica que hace este codigo"
  cc "Refactoriza esta funcion" -f simmoon_pipeline.py
  cc "Crea un test" -f app.py -c "Usa pytest"
  cc --models
  cc --interactive
  cc --model qwen2.5-coder:14b "Hazme un resumen"
        """,
    )

    parser.add_argument("task", nargs="?", default="",
                        help="Tarea a ejecutar (omitir para ver ayuda)")
    parser.add_argument("-f", "--file", "--files", nargs="+", default=[],
                        help="Archivos relevantes para la tarea")
    parser.add_argument("-c", "--context", default="",
                        help="Contexto adicional sobre la tarea")
    parser.add_argument("-m", "--model", default="qwen2.5-coder:14b",
                        help="Modelo Ollama (default: qwen2.5-coder:14b)")
    parser.add_argument("--output-mode", choices=["smart", "raw"], default="smart",
                        help="Modo de salida (smart: truncado + resumen, raw: completo)")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Timeout en segundos (default: 300)")
    parser.add_argument("--temperature", type=float, default=0.3,
                        help="Temperatura del modelo (default: 0.3)")
    parser.add_argument("--max-tokens", type=int, default=4096,
                        help="Max tokens de respuesta (default: 4096)")
    parser.add_argument("--models", action="store_true",
                        help="Listar modelos disponibles en Ollama")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="Modo interactivo (chat continuo)")
    parser.add_argument("--no-banner", action="store_true",
                        help="Omitir banner de inicio")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Modo silencioso (solo output, sin adornos)")

    args = parser.parse_args()

    # ── Modo listar modelos ──
    if args.models:
        client = OllamaAnthropicClient(verbose=False)
        list_models(client)
        return

    # ── Modo interactivo ──
    if args.interactive:
        client = OllamaAnthropicClient(model=args.model, verbose=False)
        interactive_chat(client)
        return

    # ── Sin tarea: mostrar ayuda ──
    if not args.task:
        parser.print_help()
        print()
        print(f"  💡 Tip: Prueba con {Colors.colorize('cc \"tu tarea aqui\"', Colors.CYAN)}")
        print()
        return

    # ── Modo silencioso ──
    if args.quiet:
        client = OllamaAnthropicClient(
            model=args.model,
            verbose=False,
        )
        if args.file:
            files = [str(SCRIPT_DIR / f) if not Path(f).is_absolute() else f for f in args.file]
        else:
            files = None

        result = client.run_task(
            task=args.task,
            files=files,
            context=args.context,
            timeout=args.timeout,
        )

        # En modo silencioso, solo el output puro
        print(result.output.strip())
        sys.exit(0 if result.success else 1)
        return

    # ── Modo normal ──
    show_banner = not args.no_banner
    if show_banner:
        print_banner()

    # Mostrar configuracion
    print(f"  {Colors.colorize('🧠 Modelo:', Colors.DIM)} {Colors.colorize(args.model, Colors.CYAN)}")
    if args.file:
        file_list = [Path(f).name for f in args.file]
        print(f"  {Colors.colorize('📁 Archivos:', Colors.DIM)} {', '.join(file_list)}")
    print(f"  {Colors.colorize('📋 Tarea:', Colors.DIM)} {args.task[:100]}{'...' if len(args.task) > 100 else ''}")
    print(f"  {Colors.colorize('⏱ Timeout:', Colors.DIM)} {format_time(args.timeout)}")
    print(f"  {Colors.colorize('─' * 50, Colors.DIM)}")
    print()

    # Resolver rutas de archivos (relativas al CWD del usuario)
    if args.file:
        files = []
        for f in args.file:
            path = Path(f)
            if not path.is_absolute():
                path = Path.cwd() / f
            if path.exists():
                files.append(str(path.resolve()))
            else:
                print(f"  {Colors.colorize(f'⚠️  Archivo no encontrado: {path}', Colors.YELLOW)}")
        if not files:
            files = None
    else:
        files = None

    # Crear cliente y ejecutar
    client = OllamaAnthropicClient(
        model=args.model,
        verbose=False,
    )

    result = None
    start = time.time()

    # Spinner mientras se ejecuta
    spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    spinner_idx = 0

    def spin():
        nonlocal spinner_idx
        if Colors.SUPPORTS_COLOR:
            sys.stdout.write(f"\r  {Colors.colorize(spinner_chars[spinner_idx], Colors.CYAN)} Ejecutando... ")
            sys.stdout.flush()
            spinner_idx = (spinner_idx + 1) % len(spinner_chars)

    # Hilo simple para spinner (no bloqueante)
    import threading
    stop_spinner = threading.Event()

    def spinner_thread():
        while not stop_spinner.is_set():
            spin()
            time.sleep(0.1)

    spinner_t = threading.Thread(target=spinner_thread, daemon=True)
    if Colors.SUPPORTS_COLOR and not args.quiet:
        spinner_t.start()

    try:
        result = client.run_task(
            task=args.task,
            files=files,
            context=args.context,
            timeout=args.timeout,
        )
    finally:
        stop_spinner.set()
        if Colors.SUPPORTS_COLOR:
            sys.stdout.write("\r\033[K")  # Limpiar linea del spinner
            sys.stdout.flush()

    duration = time.time() - start

    # Safety net: si result es None (excepción inesperada), crear resultado de error
    if result is None:
        result = ClaudeCodeResult(
            task=args.task, task_id="error",
            stdout="", stderr="[ERROR] La tarea fallo inesperadamente",
            exit_code=-1, duration=duration, success=False,
        )

    print()

    # Mostrar resultado
    if args.output_mode == "raw":
        output = result.output.strip()
        if not result.success:
            # Incluso en modo raw, indicar error
            print(f"[EXIT:{result.exit_code}] {output}" if output else f"[ERROR] exit code {result.exit_code}")
        else:
            print(output)
    else:
        print_result(result, output_mode=args.output_mode, show_banner=False)

    # Exit code
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
