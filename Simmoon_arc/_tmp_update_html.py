#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Update sistema_documentos.html with InvokeAI analysis and tool recommendations."""

import pathlib

HTML_PATH = pathlib.Path(r"C:\Users\docus\Desktop\sistema_documentos.html")
if not HTML_PATH.exists():
    print(f"❌ No encontrado: {HTML_PATH}")
    exit(1)

html = HTML_PATH.read_text(encoding="utf-8")

# ── Nueva sección: Análisis de herramientas de imagen ────────────────
NEW_SECTION = """
<!-- ═══════════════════════════════════════════════════════════════ -->
<!--  Sección: Stack de Imagen — Análisis Buffy                    -->
<!-- ═══════════════════════════════════════════════════════════════ -->

<div class="section" id="imagen">
  <div class="section-header" onclick="toggleSection('imagen')">
    <span class="arrow">▶</span>
    🎨 <strong>Análisis del Stack de Imagen — por Buffy</strong>
  </div>
  <div class="section-content" id="imagen-content">

    <div class="card">
      <h3>🖼️ ¿InvokeAI o ComfyUI?</h3>
      <p><strong>InvokeAI ya estaba desinstalado</strong> (commit anterior). Y tienes razón: ComfyUI hace todo lo que InvokeAI hace, pero mejor:</p>
      <table>
        <tr><th>Característica</th><th>ComfyUI</th><th>InvokeAI</th></tr>
        <tr><td>Workflows visuales</td><td>✅ Nodos personalizables</td><td>⚠️ Canvas único</td></tr>
        <tr><td>ControlNet/IP-Adapter</td><td>✅ Nativo + community nodes</td><td>⚠️ Limitado</td></tr>
        <tr><td>LoRAs personalizados</td><td>✅ Carga/descarga directa</td><td>✅ Sí</td></tr>
        <tr><td>AnimateDiff/Video</td><td>✅ Via nodes</td><td>❌ No</td></tr>
        <tr><td>Rendimiento GPU</td><td>✅ Óptimo, cola de trabajos</td><td>⚠️ Más pesado</td></tr>
        <tr><td>Pipeline automatizado</td><td>✅ API REST + argumentos CLI</td><td>⚠️ API REST básica</td></tr>
        <tr><td>Batch processing</td><td>✅ Nativo</td><td>⚠️ Limitado</td></tr>
      </table>
      <p><strong>Veredicto:</strong> ComfyUI es superior en todos los aspectos que necesitamos. InvokeAI fue eliminado del registro de agentes.</p>
    </div>

    <div class="card">
      <h3>📋 Stack actual de imagen</h3>
      <table>
        <tr><th>Herramienta</th><th>Rol</th><th>Estado</th></tr>
        <tr><td>🎨 <strong>ComfyUI</strong></td><td>Generación principal (workflows visuales)</td><td>🟢 Activo</td></tr>
        <tr><td>🎨 <strong>GIMP</strong></td><td>Post-procesado (contraste, paleta, bordes)</td><td>🟢 Instalado</td></tr>
        <tr><td>🧊 <strong>Blender</strong></td><td>Modelado 3D, renders isométricos</td><td>🟢 Instalado</td></tr>
        <tr><td>🎮 <strong>Pixelator</strong></td><td>Conversión a pixel-art</td><td>🟢 Script propio</td></tr>
      </table>
    </div>

    <div class="card">
      <h3>🔧 ¿Falta alguna herramienta?</h3>
      <p>Después de investigar el ecosistema open-source de 2026, estas son las herramientas que <strong>recomiendo considerar</strong>:</p>
      <table>
        <tr><th>Herramienta</th><th>Para qué</th><th>Prioridad</th><th>Alternativa actual</th></tr>
        <tr>
          <td><strong>ImageMagick</strong></td>
          <td>Batch CLI: redimensionar, convertir, componer miles de assets en segundos</td>
          <td><span class="tag tag-high">🔴 Alta</span></td>
          <td>N/A — no hay nada similar</td>
        </tr>
        <tr>
          <td><strong>FFmpeg</strong></td>
          <td>Video/animación: convertir frames a GIFs, spritesheets animados, cinemáticas</td>
          <td><span class="tag tag-high">🔴 Alta</span></td>
          <td>simmoon_gifs.py (limitado)</td>
        </tr>
        <tr>
          <td><strong>Pixelorama</strong></td>
          <td>Edición manual de pixel-art con CLI para batch export</td>
          <td><span class="tag tag-mid">🟡 Media</span></td>
          <td>Solo pipeline automática</td>
        </tr>
        <tr>
          <td><strong>Upscayl</strong></td>
          <td>AI upscaling local (Real-ESRGAN) sin watermark</td>
          <td><span class="tag tag-mid">🟡 Media</span></td>
          <td>ComfyUI upscale nodes</td>
        </tr>
        <tr>
          <td><strong>Laigter</strong></td>
          <td>Generar normal/parallax/specular maps desde sprites 2D</td>
          <td><span class="tag tag-low">🟢 Baja</span></td>
          <td>Blender + GIMP</td>
        </tr>
      </table>

      <h4 style="margin-top:1.2em;">📊 Resumen de recomendaciones</h4>
      <p>
        <strong>ImageMagick + FFmpeg</strong> son las únicas que cubren funcionalidad 
        <em>inexistente</em> en el stack actual. ImageMagick para batch processing de 
        sprites (redimensionar 500 assets en un comando) y FFmpeg para convertir 
        secuencias de frames a GIFs/Spritesheets sin depender de scripts caseros.
      </p>
      <p>
        Pixelorama, Upscayl y Laigter son <strong>nice-to-have</strong> — ComfyUI 
        ya cubre upscaling con nodes, y el pixel-art pipeline automático funciona.
      </p>
    </div>
  </div>
</div>
"""

# ── Insertar la nueva sección antes del footer ────────────────────────
FOOTER_MARK = '<div class="footer">'
if FOOTER_MARK in html:
    html = html.replace(FOOTER_MARK, f"{NEW_SECTION}\n\n{FOOTER_MARK}", 1)
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"✅ HTML actualizado ({len(html):,} bytes)")
else:
    print("❌ No se encontró el marcador del footer en el HTML")

# ── Verificar
if HTML_PATH.exists():
    print(f"✅ Archivo final: {HTML_PATH}")
    print(f"   Tamaño: {HTML_PATH.stat().st_size:,} bytes")
