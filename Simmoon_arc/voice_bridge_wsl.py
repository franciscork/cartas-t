#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  SIMMOON — Voice Bridge WSL (solo TTS)                     ║
║  🔈 Lee texto en voz alta usando edge-tts + ffplay          ║
║  🎤 Sin micrófono · Sin hotkeys · Solo lectura              ║
╚══════════════════════════════════════════════════════════════╝

USO:
  python voice_bridge_wsl.py --say "Hola"
  python voice_bridge_wsl.py --daemon        # Modo pipe (lee de ~/.simmoon-logs/voice_pipe)
  python voice_bridge_wsl.py --list-voices   # Listar voces español
  python voice_bridge_wsl.py --voice es-MX-DaliaNeural --say "Hola"
  echo "texto a leer" > ~/.simmoon-logs/voice_pipe   # Enviar al daemon
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Dependencia única ──────────────────────────────────────────────────────
try:
    import edge_tts
except ImportError:
    print("❌ edge_tts no instalado.", file=sys.stderr)
    print("   Ejecuta: pip install --break-system-packages edge_tts", file=sys.stderr)
    sys.exit(1)

# ── Config ─────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / ".voice_bridge_wsl_config.json"
PIPE_PATH = Path.home() / ".simmoon-logs" / "voice_pipe"

# Voces español por defecto (de mejor a peor)
DEFAULT_VOICE = os.environ.get("VOICE_BRIDGE_VOICE", "es-MX-DaliaNeural")
RATE = "+10%"
PITCH = "+5Hz"

C = {
    "cyan": "\033[96m",
    "magenta": "\033[95m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "green": "\033[92m",
    "reset": "\033[0m",
    "dim": "\033[2m",
    "bold": "\033[1m",
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


# ── TTS Core ──────────────────────────────────────────────────────────────

async def speak(text: str, voice: str = DEFAULT_VOICE):
    """Convertir texto a voz y reproducir con ffplay."""
    if not text or not text.strip():
        return False

    text = text.strip()
    # Limitar longitud (Telegram max 4096, pero TTS muy largo es molesto)
    if len(text) > 500:
        text = text[:500] + "..."
    # Limpiar markdown para TTS
    text = text.replace("*", "").replace("_", "").replace("`", "").replace("~", "")

    print(f"  {C['magenta']}🔈 {text[:80]}{'...' if len(text) > 80 else ''}{C['reset']}")

    tmp_path = None
    try:
        # Generar MP3 con edge-tts
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_path = tmp.name
        tmp.close()

        communicate = edge_tts.Communicate(text, voice, rate=RATE, pitch=PITCH)
        await communicate.save(tmp_path)

        # Reproducir con ffplay (disponible en WSL)
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp_path],
            timeout=60,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True

    except subprocess.TimeoutExpired:
        print(f"  {C['red']}⚠️  Timeout reproduciendo{C['reset']}")
        return False
    except Exception as e:
        print(f"  {C['red']}❌ Error TTS: {e}{C['reset']}")
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def speak_sync(text: str, voice: str = DEFAULT_VOICE):
    """Wrapper síncrono."""
    return asyncio.run(speak(text, voice))


# ── Pipe Daemon ───────────────────────────────────────────────────────────

def daemon_mode(voice: str = DEFAULT_VOICE):
    """Modo daemon: leer de un FIFO pipe y leer cada línea en voz alta."""
    # Crear directorio de logs si no existe
    PIPE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Crear named pipe si no existe
    if not PIPE_PATH.exists():
        try:
            os.mkfifo(str(PIPE_PATH))
            print(f"  {C['green']}📁 Pipe creado: {PIPE_PATH}{C['reset']}")
        except OSError as e:
            print(f"  {C['red']}❌ No se pudo crear pipe: {e}{C['reset']}")
            print(f"  {C['yellow']}💡 Alternativa: usa --say directamente{C['reset']}")
            sys.exit(1)

    if not PIPE_PATH.is_fifo():
        # Si ya existe pero no es FIFO, borrar y recrear
        PIPE_PATH.unlink()
        os.mkfifo(str(PIPE_PATH))

    print(f"\n{C['cyan']}╔══════════════════════════════════════╗")
    print(f"║  ☾ VOICE BRIDGE WSL — DAEMON       ║")
    print(f"║  🔈 TTS activo ({voice.split('-')[-1]})              ║")
    print(f"╚══════════════════════════════════════╝{C['reset']}\n")
    print(f"  {C['dim']}Esperando texto en: {PIPE_PATH}{C['reset']}")
    print(f"  {C['dim']}Envía texto con: echo \\\"texto\\\" > {PIPE_PATH}{C['reset']}")
    print(f"  {C['dim']}Ctrl+C para detener{C['reset']}\n")

    try:
        while True:
            with open(PIPE_PATH, "r") as pipe:
                for line in pipe:
                    line = line.strip()
                    if line:
                        print(f"  {C['cyan']}📥 {line[:100]}{'...' if len(line) > 100 else ''}{C['reset']}")
                        try:
                            asyncio.run(speak(line, voice))
                        except Exception as e:
                            print(f"  {C['red']}❌ {e}{C['reset']}")
    except KeyboardInterrupt:
        print(f"\n  {C['yellow']}👋 Voice Bridge detenido{C['reset']}")
    except Exception as e:
        print(f"\n  {C['red']}❌ Error en daemon: {e}{C['reset']}")
    finally:
        # Limpiar pipe
        if PIPE_PATH.exists():
            try:
                PIPE_PATH.unlink()
            except Exception:
                pass


# ── Listar voces ──────────────────────────────────────────────────────────

def list_voices():
    """Listar voces en español disponibles en edge-tts."""
    print(f"\n{C['cyan']}═══ Voces edge-tts (español) ═══{C['reset']}\n")

    async def _list():
        return await edge_tts.list_voices()

    try:
        all_voices = asyncio.run(_list())
        es_voices = [v for v in all_voices if v["Locale"].startswith("es-")]

        if not es_voices:
            print(f"  {C['yellow']}No se encontraron voces en español{C['reset']}")
            return

        # Agrupar por país
        by_locale = {}
        for v in es_voices:
            loc = v["Locale"]
            if loc not in by_locale:
                by_locale[loc] = []
            by_locale[loc].append(v)

        for loc in sorted(by_locale.keys()):
            print(f"  {C['yellow']}📍 {loc}{C['reset']}:")
            for v in by_locale[loc]:
                name = v["ShortName"]
                gender = "♀" if v["Gender"] == "Female" else "♂"
                marker = " ← actual" if name == DEFAULT_VOICE else ""
                print(f"    {gender}  {name}{C['green']}{marker}{C['reset']}")
            print()

        print(f"  {C['dim']}Voz actual: {DEFAULT_VOICE}{C['reset']}")
        print(f"  {C['dim']}Cambiar: --voice <ShortName>{C['reset']}")
        print(f"  {C['dim']}O variable: VOICE_BRIDGE_VOICE=es-ES-ElviraNeural{C['reset']}\n")

    except Exception as e:
        print(f"  {C['red']}❌ Error: {e}{C['reset']}")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SIMMOON Voice Bridge WSL — TTS only")
    parser.add_argument("--say", type=str, metavar="TEXTO", help="Leer texto en voz alta")
    parser.add_argument("--daemon", action="store_true", help="Modo daemon (pipe FIFO)")
    parser.add_argument("--list-voices", action="store_true", help="Listar voces en español")
    parser.add_argument("--voice", type=str, default=DEFAULT_VOICE,
                        help=f"Voz edge-tts (default: {DEFAULT_VOICE})")
    args = parser.parse_args()

    voice = args.voice or DEFAULT_VOICE

    if args.list_voices:
        list_voices()
        return

    if args.say:
        success = speak_sync(args.say, voice)
        sys.exit(0 if success else 1)

    if args.daemon:
        daemon_mode(voice)
        return

    # Sin argumentos: mostrar ayuda
    parser.print_help()
    print(f"\n  {C['cyan']}🚀 Comandos rápidos:{C['reset']}")
    print(f"     python voice_bridge_wsl.py --say \"Hola\"")
    print(f"     python voice_bridge_wsl.py --daemon")
    print(f"     python voice_bridge_wsl.py --list-voices")
    print(f"     echo \"texto\" > {PIPE_PATH}")


if __name__ == "__main__":
    main()
