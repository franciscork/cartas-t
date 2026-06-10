#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  SIMMOON — Voice Bridge (Puente de Voz)                    ║
║  🎤 Habla → se transcribe → se escribe en Codebuff         ║
║  🔈 Mis respuestas → se leen en voz alta                   ║
╚══════════════════════════════════════════════════════════════╝

USO:
  python voice_bridge.py              # Modo interactivo (menú)
  python voice_bridge.py --listen     # Escuchar una vez y transcribir
  python voice_bridge.py --say "texto" # Leer texto en voz alta
  python voice_bridge.py --clipboard  # Leer el portapapeles en voz alta
  python voice_bridge.py --hotkey     # Modo hotkey (F4=escuchar, F5=leer)
"""

import argparse
import asyncio
import io
import json
import os
import sys
import tempfile
import time
import wave
from pathlib import Path

# ── Dependencias ───────────────────────────────────────────────────────────
try:
    import speech_recognition as sr
except ImportError:
    print("\n❌ SpeechRecognition no instalado.")
    print("   Ejecuta: pip install SpeechRecognition")
    sys.exit(1)

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    print("\n❌ sounddevice no instalado.")
    print("   Ejecuta: pip install sounddevice numpy")
    sys.exit(1)

try:
    import edge_tts
except ImportError:
    print("\n❌ edge-tts no instalado.")
    print("   Ejecuta: pip install edge-tts")
    sys.exit(1)

try:
    import keyboard
except ImportError:
    print("\n❌ keyboard no instalado.")
    print("   Ejecuta: pip install keyboard")
    sys.exit(1)

try:
    import pyperclip
except ImportError:
    print("\n⚠️  pyperclip no instalado. La función de portapapeles no funcionará.")
    print("   Ejecuta: pip install pyperclip")
    pyperclip = None

# ─── Configuración ─────────────────────────────────────────────────────────

RUTA_CONFIG = Path(__file__).parent / ".voice_bridge_config.json"

def cargar_config() -> dict:
    if RUTA_CONFIG.exists():
        try:
            return json.loads(RUTA_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def guardar_config(config: dict):
    try:
        RUTA_CONFIG.write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception:
        pass

config_data = cargar_config()
VOZ = config_data.get("voz", "es-ES-AlvaroNeural")
SAMPLE_RATE = 16000
DURACION_MAX = 10
SILENCIO_UMBRAL = 0.02
SILENCIO_SEGUNDOS = 1.5

# ─── Colores ───────────────────────────────────────────────────────────────

C = {
    "verde": "\033[92m",
    "cyan": "\033[96m",
    "amarillo": "\033[93m",
    "rojo": "\033[91m",
    "magenta": "\033[95m",
    "reset": "\033[0m",
    "negrita": "\033[1m",
    "dim": "\033[2m",
}


def logo():
    print(f"""
{C['cyan']}╔══════════════════════════════════════╗
║  ☾ SIMMOON — PUENTE DE VOZ          ║
║  {C['magenta']}🎤 Tú me hablas  →  🔈 Yo te respondo{C['cyan']}   ║
╚══════════════════════════════════════╝{C['reset']}
    """)


# ─── Grabación de Audio ────────────────────────────────────────────────────

def grabar_audio() -> bytes:
    """Graba audio desde el micrófono hasta silencio o duración máxima.
    Retorna datos WAV en memoria como bytes."""
    print(f"  {C['verde']}🎤 ESCUCHANDO...{C['reset']} (habla, silencio=fin, máx {DURACION_MAX}s)")
    print(f"  {C['dim']}   Presiona Ctrl+C para cancelar{C['reset']}")

    try:
        buffer = []
        silencio_frames = 0
        grabando = False
        inicio = time.time()

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32') as stream:
            while True:
                bloque, _ = stream.read(int(SAMPLE_RATE * 0.1))
                buffer.append(bloque.copy())

                volumen = np.abs(bloque).mean()

                if volumen > SILENCIO_UMBRAL and not grabando:
                    grabando = True
                    print(f"  {C['cyan']}   📢 Detectado...{C['reset']}")

                if grabando:
                    if volumen < SILENCIO_UMBRAL:
                        silencio_frames += 1
                    else:
                        silencio_frames = 0

                    barras = min(int(volumen * 100), 40)
                    bar = "█" * barras + "░" * (40 - barras)
                    sys.stdout.write(f"\r  {C['verde']}|{bar}|{C['reset']} ")
                    sys.stdout.flush()

                tiempo = time.time() - inicio
                if grabando and silencio_frames > int(SILENCIO_SEGUNDOS / 0.1):
                    print(f"\n  {C['amarillo']}   🤐 Silencio detectado{C['reset']}")
                    break
                if tiempo > DURACION_MAX:
                    print(f"\n  {C['amarillo']}   ⏰ Tiempo máximo{C['reset']}")
                    break

        if not grabando:
            print(f"\n  {C['rojo']}   ❌ No se detectó audio{C['reset']}")
            return b""

        audio = np.concatenate(buffer)
        audio_int16 = (audio * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

        duracion = len(audio) / SAMPLE_RATE
        print(f"  {C['cyan']}   📊 {duracion:.1f}s grabados{C['reset']}")
        return buf.getvalue()

    except KeyboardInterrupt:
        print(f"\n  {C['amarillo']}   ⏹ Cancelado{C['reset']}")
        return b""
    except Exception as e:
        print(f"\n  {C['rojo']}   ❌ Error grabando: {e}{C['reset']}")
        return b""


# ─── Transcripción (STT) ───────────────────────────────────────────────────

def transcribir(audio_wav: bytes) -> str:
    """Transcribe audio WAV a texto usando SpeechRecognition + Google."""
    if not audio_wav:
        return ""

    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_wav)) as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        print(f"  {C['cyan']}   🔄 Transcribiendo...{C['reset']}")
        try:
            audio_data = recognizer.record(source)
            texto = recognizer.recognize_google(audio_data, language="es-ES")
            print(f"  {C['verde']}   ✅ \"{texto}\"{C['reset']}")
            return texto
        except sr.UnknownValueError:
            print(f"  {C['rojo']}   ❌ No se entendió el audio{C['reset']}")
            return ""
        except sr.RequestError as e:
            print(f"  {C['rojo']}   ❌ Error de conexión: {e}{C['reset']}")
            return ""


# ─── Síntesis de Voz (TTS) ─────────────────────────────────────────────────

async def hablar(texto: str, voz: str = VOZ):
    """Convierte texto a voz usando edge-tts y lo reproduce (sin pygame)."""
    if not texto.strip():
        print(f"  {C['rojo']}   ❌ No hay texto para leer{C['reset']}")
        return

    print(f"  {C['magenta']}🔈 \"{texto[:80]}{'...' if len(texto) > 80 else ''}\"{C['reset']}")

    try:
        comunicado = edge_tts.Communicate(texto, voz, rate="+10%", pitch="+5Hz")

        if sys.platform == "win32":
            # Windows: guardar como WAV y usar winsound (no toca pygame)
            import winsound
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp_path = tmp.name
            tmp.close()
            comunicado_wav = edge_tts.Communicate(texto, voz, rate="+10%", pitch="+5Hz")
            await comunicado_wav.save(tmp_path)
            winsound.PlaySound(tmp_path, winsound.SND_FILENAME)
            os.unlink(tmp_path)
        else:
            # Linux/Mac: guardar como MP3 y reproducir con ffplay/aplay
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp_path = tmp.name
            tmp.close()
            await comunicado.save(tmp_path)
            os.system(f"ffplay -nodisp -autoexit \"{tmp_path}\" 2>/dev/null || "
                      f"aplay \"{tmp_path}\" 2>/dev/null || "
                      f"echo '  ⚠️  No hay reproductor disponible'")
            os.unlink(tmp_path)

        print(f"  {C['magenta']}   ✅ Listo{C['reset']}")

    except Exception as e:
        print(f"  {C['rojo']}   ❌ Error TTS: {e}{C['reset']}")


def hablar_sync(texto: str):
    """Wrapper síncrono para hablar()."""
    asyncio.run(hablar(texto))


# ─── Escribir en ventana activa ────────────────────────────────────────────

def escribir_en_activa(texto: str, auto_enter: bool = False):
    """Escribe el texto transcrito en la ventana activa (Codebuff)."""
    if not texto:
        return
    print(f"  {C['cyan']}   ✍️  Escribiendo en ventana activa...{C['reset']}")
    time.sleep(0.3)
    if auto_enter:
        keyboard.write(texto + "\n")
    else:
        keyboard.write(texto)
    print(f"  {C['verde']}   ✅ Texto enviado{C['reset']}")


# ─── Ciclo de Escucha ──────────────────────────────────────────────────────

def ciclo_escucha(auto_escribir: bool = True) -> str:
    """Graba, transcribe y opcionalmente escribe en la ventana activa."""
    audio = grabar_audio()
    if not audio:
        return ""
    texto = transcribir(audio)
    if texto and auto_escribir:
        escribir_en_activa(texto, auto_enter=False)
    return texto


# ─── Leer texto seleccionado (usando portapapeles) ─────────────────────────

def leer_seleccion():
    """Lee el texto seleccionado usando portapapeles (Ctrl+C simulado).

    ⚠️  IMPORTANTE: Asegúrate de que la ventana con el texto a leer
        esté ACTIVA (enfocada). Si Codebuff está enfocado, Ctrl+C
        enviará una interrupción en vez de copiar.
    """
    print(f"  {C['amarillo']}   ⚠️  Enfoca la ventana con el texto (NO Codebuff) y espera...{C['reset']}")
    if pyperclip is None:
        print(f"  {C['rojo']}   ❌ pyperclip no instalado (pip install pyperclip){C['reset']}")
        return
    try:
        # Guardar portapapeles actual
        portapapeles_anterior = pyperclip.paste()
        time.sleep(0.5)  # Tiempo para cambiar de ventana
        # Simular Ctrl+C para copiar selección
        keyboard.send('ctrl+c')
        time.sleep(0.3)
        texto = pyperclip.paste()
        if texto.strip():
            hablar_sync(texto)
            # Restaurar portapapeles original después de leer
            if portapapeles_anterior:
                pyperclip.copy(portapapeles_anterior)
        else:
            print(f"  {C['rojo']}   ❌ No hay texto seleccionado{C['reset']}")
            if portapapeles_anterior:
                pyperclip.copy(portapapeles_anterior)
    except Exception as e:
        print(f"  {C['rojo']}   ❌ Error: {e}{C['reset']}")
        print(f"  {C['amarillo']}   💡 Alternativa: selecciona el texto, copia (Ctrl+C) y usa F6 (portapapeles){C['reset']}")


# ─── Modo Hotkey ───────────────────────────────────────────────────────────

def modo_hotkey():
    """Modo background con hotkeys: F4=escuchar, F5=leer selección."""
    logo()
    print(f"  {C['amarillo']}🎯 Modo HOTKEY activo{C['reset']}")
    print(f"  {C['cyan']}  ┌─────────────────────────────────────────────┐")
    print(f"  │  {C['verde']} F4 {C['reset']}  →  🎤 Grabar y transcribir voz      {C['cyan']}│")
    print(f"  │  {C['verde']} F5 {C['reset']}  →  🔈 Leer texto seleccionado     {C['cyan']}│")
    print(f"  │  {C['verde']} F6 {C['reset']}  →  📋 Leer portapapeles           {C['cyan']}│")
    print(f"  │  {C['rojo']}  ESC {C['reset']} →  ⏹ Salir                       {C['cyan']}│")
    print(f"  └─────────────────────────────────────────────┘")
    print(f"  {C['dim']}   Abre esto en una terminal APARTE, junto a Codebuff{C['reset']}")
    print(f"  {C['dim']}   Si las hotkeys no responden, usa modo interactivo (sin --hotkey){C['reset']}")
    print(f"  {C['dim']}   ⚠️  F5 funciona en ventanas NO terminales (navegador, editor, etc.){C['reset']}")
    print()

    def on_f4():
        print(f"\n{C['cyan']}═══ F4: Grabando voz ═══{C['reset']}")
        ciclo_escucha(auto_escribir=True)

    def on_f5():
        print(f"\n{C['cyan']}═══ F5: Leyendo selección ═══{C['reset']}")
        leer_seleccion()

    def on_f6():
        print(f"\n{C['cyan']}═══ F6: Leyendo portapapeles ═══{C['reset']}")
        if pyperclip:
            texto = pyperclip.paste()
            if texto.strip():
                hablar_sync(texto)
            else:
                print(f"  {C['rojo']}   ❌ Portapapeles vacío{C['reset']}")
        else:
            print(f"  {C['rojo']}   ❌ pyperclip no instalado{C['reset']}")

    try:
        keyboard.add_hotkey('f4', on_f4)
        keyboard.add_hotkey('f5', on_f5)
        keyboard.add_hotkey('f6', on_f6)
        keyboard.wait('esc')
    except Exception as e:
        print(f"\n  {C['rojo']}❌ Error con hotkeys: {e}{C['reset']}")
        print(f"  {C['amarillo']}   💡 En Windows, ejecuta como Administrador para hotkeys globales{C['reset']}")
        print(f"  {C['amarillo']}   💡 O usa modo interactivo (sin --hotkey): python voice_bridge.py{C['reset']}")


# ─── Modo Interactivo (menú) ───────────────────────────────────────────────

def modo_interactivo():
    """Modo interactivo con menú, no necesita hotkeys globales."""
    logo()

    while True:
        print(f"\n{C['cyan']}─── Menú ───{C['reset']}")
        print(f"  {C['verde']}1{C['reset']}  🎤  Escuchar y transcribir (escribe en ventana activa)")
        print(f"  {C['verde']}2{C['reset']}  🔊  Leer un texto en voz alta")
        print(f"  {C['verde']}3{C['reset']}  📋  Leer portapapeles en voz alta")
        print(f"  {C['verde']}4{C['reset']}  🔥  Modo hotkey (F4/F5/F6)")
        print(f"  {C['verde']}5{C['reset']}  🎙️  Cambiar voz ({VOZ})")
        print(f"  {C['rojo']}0{C['reset']}  ❌  Salir")
        print()

        try:
            opcion = input(f"  {C['amarillo']}Opción:{C['reset']} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {C['amarillo']}👋 ¡Hasta luego!{C['reset']}")
            break

        if opcion == "1":
            ciclo_escucha(auto_escribir=True)
        elif opcion == "2":
            texto = input(f"  {C['cyan']}Texto a leer:{C['reset']} ")
            if texto.strip():
                hablar_sync(texto)
        elif opcion == "3":
            if pyperclip:
                texto = pyperclip.paste()
                if texto.strip():
                    print(f"  {C['cyan']}   📋 \"{texto[:100]}{'...' if len(texto) > 100 else ''}\"{C['reset']}")
                    hablar_sync(texto)
                else:
                    print(f"  {C['rojo']}   ❌ Portapapeles vacío{C['reset']}")
            else:
                print(f"  {C['rojo']}   ❌ pyperclip no instalado (pip install pyperclip){C['reset']}")
        elif opcion == "4":
            modo_hotkey()
        elif opcion == "5":
            seleccionar_voz_interactivo()
        elif opcion == "0":
            print(f"  {C['amarillo']}👋 ¡Hasta luego!{C['reset']}")
            break
        else:
            print(f"  {C['rojo']}❌ Opción inválida{C['reset']}")


# ─── Listar y Seleccionar Voz ────────────────────────────────────────────

def listar_voces_espanol() -> list:
    """Obtiene la lista de voces en español de edge-tts."""
    async def _listar():
        voices = await edge_tts.list_voices()
        return [v for v in voices if v['Locale'].startswith('es-')]
    try:
        return asyncio.run(_listar())
    except Exception as e:
        print(f"  {C['rojo']}❌ Error al listar voces: {e}{C['reset']}")
        return []


def mostrar_voces(voces: list) -> str:
    """Muestra las voces numeradas y deja al usuario elegir.
    Retorna el ShortName de la voz seleccionada, o None si cancela."""
    # Agrupar por país
    paises = {}
    for v in voces:
        pais = v['Locale'].split('-')[1] if '-' in v['Locale'] else v['Locale']
        if pais not in paises:
            paises[pais] = []
        paises[pais].append(v)

    idx = 1
    opciones = []
    print(f"\n{C['cyan']}─── Voces disponibles ({len(voces)} en español) ───{C['reset']}")
    print()

    for pais in sorted(paises.keys()):
        voces_pais = paises[pais]
        print(f"  {C['amarillo']}📍 {pais}{C['reset']}:")
        for v in voces_pais:
            name = v['ShortName']
            genero = "Femenina" if v['Gender'] == 'Female' else "Masculina"
            marca = " <<< ACTUAL" if name == VOZ else ""
            print(f"    {C['verde']}{idx:2d}{C['reset']}) {name:35s} {genero}{C['verde']}{marca}{C['reset']}")
            opciones.append(name)
            idx += 1
        print()

    print(f"  {C['rojo']}  0{C['reset']})  Cancelar")
    print()

    while True:
        try:
            eleccion = input(f"  {C['amarillo']}Elige una voz (0-{len(opciones)}):{C['reset']} ").strip()
            if eleccion == "0":
                return None
            num = int(eleccion)
            if 1 <= num <= len(opciones):
                seleccionada = opciones[num - 1]
                return seleccionada
            print(f"  {C['rojo']}❌ Número inválido (1-{len(opciones)}){C['reset']}")
        except ValueError:
            print(f"  {C['rojo']}❌ Ingresa un número{C['reset']}")
        except (EOFError, KeyboardInterrupt):
            return None


def seleccionar_voz_interactivo():
    """Menú interactivo de selección de voz."""
    global VOZ
    print(f"\n{C['cyan']}═══ Seleccionar Voz ═══{C['reset']}")
    print(f"  {C['dim']}   Cargando lista de voces...{C['reset']}")

    voces = listar_voces_espanol()
    if not voces:
        print(f"  {C['rojo']}❌ No se pudieron cargar las voces{C['reset']}")
        return

    seleccionada = mostrar_voces(voces)
    if seleccionada and seleccionada != VOZ:
        VOZ = seleccionada
        guardar_config({"voz": VOZ})
        config_data["voz"] = VOZ  # Mantener config_data en sincronía
        print(f"  {C['verde']}✅ Voz cambiada a: {VOZ}{C['reset']}")
        # Preview
        print(f"  {C['cyan']}   🔈 Reproduciendo preview...{C['reset']}")
        hablar_sync("Hola, soy tu asistente de voz. Esta es mi nueva voz.")
    elif seleccionada:
        print(f"  {C['amarillo']}   ✅ Ya estaba seleccionada{C['reset']}")
    else:
        print(f"  {C['amarillo']}   Cancelado{C['reset']}")


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    global VOZ
    parser = argparse.ArgumentParser(description="SIMMOON — Puente de Voz")
    parser.add_argument("--listen", action="store_true", help="Escuchar una vez y transcribir")
    parser.add_argument("--say", type=str, help="Leer texto en voz alta", metavar="TEXTO")
    parser.add_argument("--clipboard", action="store_true", help="Leer portapapeles en voz alta")
    parser.add_argument("--hotkey", action="store_true", help="Modo hotkey (F4/F5/F6)")
    parser.add_argument("--no-type", action="store_true", help="Solo transcribir, sin escribir en ventana")
    parser.add_argument("--voz", type=str, default=VOZ, help=f"Voz edge-tts (default: {VOZ})")
    args = parser.parse_args()

    if args.voz:
        VOZ = args.voz

    if args.listen:
        logo()
        ciclo_escucha(auto_escribir=not args.no_type)
    elif args.say:
        logo()
        hablar_sync(args.say)
    elif args.clipboard:
        logo()
        if pyperclip:
            texto = pyperclip.paste()
            if texto.strip():
                hablar_sync(texto)
            else:
                print(f"  {C['rojo']}❌ Portapapeles vacío{C['reset']}")
        else:
            print(f"  {C['rojo']}❌ pyperclip no instalado{C['reset']}")
    elif args.hotkey:
        modo_hotkey()
    else:
        modo_interactivo()


if __name__ == "__main__":
    main()
