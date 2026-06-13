#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_cargar_factorygames_texto.py — Genera la nota markdown del white-paper
fundacional de FactoryGames a partir del TXT fuente, usando el módulo
canónico `obsidian_memory.ObsidianMemory` (REST API o filesystem).

Uso:
    python _cargar_factorygames_texto.py
    python _cargar_factorygames_texto.py --src /path/to/Estudio.txt
    python _cargar_factorygames_texto.py --vault ~/otro-vault
"""
import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

# ── Encoding fix for Windows ───────────────────────────────────────────────
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# Default TXT source location
DEFAULT_SRC = Path(r"C:\Users\docus\Desktop\FactoryGames — Estudio.txt")


def build_markdown(content: str) -> tuple[str, int, int, int]:
    """Build the markdown note with proper frontmatter.

    Returns: (md_text, n_chars, n_lines, n_words)
    """
    content = content.lstrip("\ufeff")
    # n_lines usa splitlines() para no fallar cuando el archivo NO termina en \n
    n_chars = len(content)
    n_lines = len(content.splitlines())
    n_words = len(content.split())

    # Usar 4-backtick fence para evitar inyección de triple-backtick dentro del TXT
    # (Obsidian renderiza el código correctamente, sin romper la fence)
    md = f"""---
title: 'FactoryGames — Estudio (Texto Fundador)'
date: 2026-06-12
tags:
  - factorygames
  - estudio
  - texto-fundador
  - fundacional
  - white-paper
  - arquitectura
  - enjambre
  - agentes
  - opensource
importance: 5
empresa: FactoryGames
version: '1.0'
tipo: white-paper
archivo_adjunto: FactoryGames-Estudio-Texto-Fundador.txt
caracteres: {n_chars}
lineas: {n_lines}
palabras: {n_words}
idioma: es
cargado_por: 'Buffy · Codebuff CLI'
---

# 🏭 FactoryGames — White Paper: Arquitectura de Fábrica de Software Autónoma

> **Documento fundacional (white-paper técnico).** Describe la arquitectura completa del enjambre de agentes, stack tecnológico, hardware mínimo, topología de roles, pipeline 8 fases, bus de comunicación Telegram, análisis de riesgos y roadmap de 5 meses.

## 📄 Archivos

- [[FactoryGames-Estudio-Texto-Fundador.txt]] — Texto plano original ({n_chars:,} caracteres · {n_lines:,} líneas · {n_words:,} palabras)
- [[FactoryGames-Estudio-Concepto-v1.0.pdf]] — PDF resumen ejecutivo (8 páginas)

## 📚 Contenido completo

````
{content}
````

## 🏷️ Secciones cubiertas

1. **Introducción y Visión** — Problema (trilema coste/tiempo/alcance) + Solución propuesta
2. **Arquitectura de Software** — Stack (Ollama, Qwen, Mistral, CrewAI, LangGraph, ComfyUI, Blender, Telegram)
3. **Topología del Enjambre** — 8 agentes Hermes + Buffy + Claude Code + Audio-Bot + Community-Bot
4. **Pipeline de Producción** — 8 fases (Concepción → Diseño → Arte → 3D → Código → QA → Despliegue)
5. **Bus de Comunicación** — 5 bots Telegram (Director, Build, PR, Community, Monitor)
6. **Análisis de Riesgos** — Deadlocks, alucinaciones, diffusion drift + mitigaciones
7. **Roadmap 5 meses** — 5 fases incrementales con SimMoon como piloto

---

*Documento cargado desde escritorio por Buffy vía Codebuff CLI · {datetime.now().strftime('%Y-%m-%d %H:%M')} · fuente: escritorio local*
"""
    return md, n_chars, n_lines, n_words


def save_via_obsidian_memory(md_text: str, vault_path: str = None) -> bool:
    """Guarda el markdown en `FactoryGames/` del vault (REST API o filesystem).

    NO usa `obs.save()` porque ese método siempre escribe a `Buffy/{type}/...`
    y el usuario quiere el archivo en `FactoryGames/`. En su lugar escribe
    directamente a la ruta correcta, usando REST API si está disponible.
    """
    from obsidian_memory import ObsidianMemory

    rest_api_key = os.environ.get("OBSIDIAN_REST_API_KEY", "")
    rest_port = None
    if rest_api_key:
        rest_port = int(os.environ.get("OBSIDIAN_REST_PORT", "27124"))

    obs = ObsidianMemory(
        vault_path=vault_path,
        agent_name="Buffy",
        project="FACTORYGAMES",
        rest_port=rest_port,
        rest_api_key=rest_api_key or None,
        rest_https=os.environ.get("OBSIDIAN_REST_HTTPS", "").lower() == "true",
    )

    rel_path = "FactoryGames/FactoryGames-Estudio-Texto-Fundador.md"
    mode = "REST" if obs.rest_available else "FS"
    print(f"  🪨 Guardando via ObsidianMemory [{mode}]: {rel_path}")

    if obs.rest_available and obs.rest_client:
        # REST API: ruta personalizada via write_note (acepta cualquier path)
        ok = obs.rest_client.write_note(rel_path, md_text)
    else:
        # Filesystem: escribir a vault/FactoryGames/FactoryGames-Estudio-Texto-Fundador.md
        dest = obs.vault_path / rel_path
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(md_text, encoding="utf-8")
            ok = True
        except Exception as e:
            print(f"  ❌ Error escribiendo filesystem: {e}")
            ok = False

    if ok:
        print(f"  ✅ Guardado exitoso en vault")
    else:
        print(f"  ❌ Error al guardar")
    return ok


def _resolve_vault(vault_path: str = None) -> tuple[Optional["ObsidianMemory"], Optional[Path], str]:
    """Resuelve (obs, vault_root, mode) una sola vez al inicio.

    Returns (None, None, 'REST_NO_IMPORT') si la importación de
    obsidian_memory falla (caso patológico, no debería ocurrir).
    """
    from obsidian_memory import ObsidianMemory

    rest_api_key = os.environ.get("OBSIDIAN_REST_API_KEY", "")
    rest_port = int(os.environ.get("OBSIDIAN_REST_PORT", "27124")) if rest_api_key else None

    obs = ObsidianMemory(
        vault_path=vault_path,
        agent_name="Buffy",
        project="FACTORYGAMES",
        rest_port=rest_port,
        rest_api_key=rest_api_key or None,
        rest_https=os.environ.get("OBSIDIAN_REST_HTTPS", "").lower() == "true",
    )
    mode = "REST" if obs.rest_available else "FS"
    return obs, obs.vault_path, mode


def main():
    parser = argparse.ArgumentParser(
        description="Carga el white-paper fundacional de FactoryGames en Obsidian"
    )
    parser.add_argument("--src", default=str(DEFAULT_SRC),
                        help=f"Ruta al TXT fuente (default: {DEFAULT_SRC})")
    parser.add_argument("--vault", default=None,
                        help="Ruta al vault Obsidian (default: ~/simmoon-memoria)")
    parser.add_argument("--skip-txt-copy", action="store_true",
                        help="No copiar el TXT adjunto (asume que ya está en el vault)")
    args = parser.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"  ❌ No se encontró el TXT fuente: {src}")
        print(f"     Coloca el archivo en: {src}")
        print(f"     O usa --src /ruta/al/archivo.txt")
        return 1

    print(f"  📄 Leyendo {src}...")
    content = src.read_text(encoding="utf-8", errors="replace")
    md_text, n_chars, n_lines, n_words = build_markdown(content)
    print(f"     {n_chars:,} caracteres · {n_lines:,} líneas · {n_words:,} palabras")

    # ── Resolver vault una sola vez ──
    obs, vault_root, mode = _resolve_vault(vault_path=args.vault)
    rel_path_md = "FactoryGames/FactoryGames-Estudio-Texto-Fundador.md"
    rel_path_txt = "FactoryGames/FactoryGames-Estudio-Texto-Fundador.txt"
    print(f"  🪨 Modo: {mode} | Vault: {vault_root}")

    # ── 1) Copiar TXT (filesystem o REST) ──
    if not args.skip_txt_copy:
        if obs.rest_available and obs.rest_client:
            # REST: subir el TXT también para que el wikilink funcione
            ok_txt = obs.rest_client.write_note(rel_path_txt, content)
            if ok_txt:
                print(f"  ✅ TXT subido via REST: {rel_path_txt}")
            else:
                print(f"  ⚠️  No se pudo subir TXT via REST")
        else:
            # Filesystem: escribir a vault/FactoryGames/
            txt_dest = vault_root / rel_path_txt
            try:
                txt_dest.parent.mkdir(parents=True, exist_ok=True)
                txt_dest.write_text(content, encoding="utf-8")
                print(f"  ✅ TXT copiado a: {txt_dest}")
            except Exception as e:
                print(f"  ⚠️  No se pudo copiar TXT: {e}")

    # ── 2) Guardar markdown via ObsidianMemory (REST custom path o FS) ──
    print(f"  🪨 Guardando markdown [{mode}]: {rel_path_md}")
    if obs.rest_available and obs.rest_client:
        ok_md = obs.rest_client.write_note(rel_path_md, md_text)
    else:
        md_dest = vault_root / rel_path_md
        try:
            md_dest.parent.mkdir(parents=True, exist_ok=True)
            md_dest.write_text(md_text, encoding="utf-8")
            ok_md = True
        except Exception as e:
            print(f"  ❌ Error escribiendo filesystem: {e}")
            ok_md = False

    if ok_md:
        print(f"  ✅ Markdown guardado exitosamente")
        print(f"\n  🎉 White-paper de FactoryGames cargado en Obsidian")
        return 0
    print(f"  ❌ Error al guardar markdown")
    return 1


if __name__ == "__main__":
    sys.exit(main())
