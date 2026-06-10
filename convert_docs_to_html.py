#!/usr/bin/env python3
"""
Convierte todos los archivos .md de documentacion/ a .html estilizados.
Doble clic en el .html → se abre en Chrome con formato, tablas, código y enlaces.
"""

import re
import os
from pathlib import Path

CSS = """
:root {
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --orange: #d2991d;
    --red: #f85149;
    --code-bg: #1c2129;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    padding: 2rem;
    max-width: 900px;
    margin: 0 auto;
}
h1 { font-size: 2rem; border-bottom: 2px solid var(--border); padding-bottom: 0.5rem; margin: 2rem 0 1rem; color: #fff; }
h2 { font-size: 1.4rem; margin: 1.8rem 0 0.8rem; color: var(--accent); }
h3 { font-size: 1.1rem; margin: 1.2rem 0 0.5rem; color: #c9d1d9; }
p { margin: 0.6rem 0; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
code {
    background: var(--code-bg);
    padding: 0.15em 0.4em;
    border-radius: 4px;
    font-size: 0.9em;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
}
pre {
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    overflow-x: auto;
    margin: 0.8rem 0;
    font-size: 0.85rem;
}
pre code { background: none; padding: 0; }
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
    font-size: 0.9rem;
}
th, td {
    border: 1px solid var(--border);
    padding: 0.5rem 0.8rem;
    text-align: left;
}
th { background: var(--card); color: var(--accent); font-weight: 600; }
tr:nth-child(even) { background: rgba(255,255,255,0.02); }
ul, ol { margin: 0.5rem 0 0.5rem 1.5rem; }
li { margin: 0.3rem 0; }
blockquote {
    border-left: 3px solid var(--orange);
    padding: 0.5rem 1rem;
    margin: 1rem 0;
    background: rgba(210,153,29,0.08);
    border-radius: 0 6px 6px 0;
    color: var(--orange);
}
blockquote code { background: rgba(0,0,0,0.3); }
hr { border: none; border-top: 1px solid var(--border); margin: 2rem 0; }
strong { color: #fff; }
.back-link {
    display: inline-block;
    margin-bottom: 1.5rem;
    padding: 0.4rem 1rem;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 0.85rem;
}
.back-link:hover { background: var(--border); text-decoration: none; }
.warning { color: var(--orange); }
.good { color: var(--green); }
.bad { color: var(--red); }
"""


def md_to_html(text: str) -> str:
    """Conversor Markdown → HTML ultra-simple pero efectivo."""
    
    # --- Bloques de código (procesar primero) ---
    code_blocks = []
    def save_code(m):
        code_content = (m.group(2) or "").strip()
        code_blocks.append(code_content)
        return f"%%CODEBLOCK_{len(code_blocks)-1}%%"
    text = re.sub(r'```(\w*)\n(.*?)```', save_code, text, flags=re.DOTALL)

    # --- Código inline ---
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    # --- Headers ---
    text = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)

    # --- Negrita e itálica ---
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

    # --- Links ---
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    # --- Imágenes ---
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', text)

    # --- Blockquotes ---
    lines = text.split('\n')
    result = []
    in_blockquote = False
    for line in lines:
        if line.startswith('> '):
            if not in_blockquote:
                result.append('<blockquote>')
                in_blockquote = True
            result.append(line[2:])
        else:
            if in_blockquote:
                result.append('</blockquote>')
                in_blockquote = False
            result.append(line)
    if in_blockquote:
        result.append('</blockquote>')
    text = '\n'.join(result)

    # --- Línea horizontal ---
    text = re.sub(r'^---$', '<hr>', text, flags=re.MULTILINE)

    # --- Tablas ---
    def process_table(m):
        rows = m.group(0).strip().split('\n')
        html = '<table>\n'
        for i, row in enumerate(rows):
            cells = [c.strip() for c in row.split('|') if c.strip()]
            if all(re.match(r'^[-:]+$', c) for c in cells):
                continue  # skip separator row
            tag = 'th' if i == 0 else 'td'
            html += '<tr>\n'
            for cell in cells:
                html += f'  <{tag}>{cell}</{tag}>\n'
            html += '</tr>\n'
        html += '</table>'
        return html
    
    text = re.sub(r'(?:^\|.+\|$\n?)+', process_table, text, flags=re.MULTILINE)

    # --- Listas ---
    lines = text.split('\n')
    result = []
    in_ul = in_ol = False
    for line in lines:
        # UL
        if re.match(r'^- (.+)', line):
            if not in_ul:
                if in_ol:
                    result.append('</ol>')
                    in_ol = False
                result.append('<ul>')
                in_ul = True
            result.append(f'<li>{re.sub(r"^- ", "", line)}</li>')
        # OL
        elif re.match(r'^\d+\. (.+)', line):
            if not in_ol:
                if in_ul:
                    result.append('</ul>')
                    in_ul = False
                result.append('<ol>')
                in_ol = True
            result.append(f'<li>{re.sub(r"^\d+\. ", "", line)}</li>')
        else:
            if in_ul:
                result.append('</ul>')
                in_ul = False
            if in_ol:
                result.append('</ol>')
                in_ol = False
            result.append(line)
    if in_ul:
        result.append('</ul>')
    if in_ol:
        result.append('</ol>')
    text = '\n'.join(result)

    # --- Párrafos: líneas no vacías que no son ya HTML ---
    lines = text.split('\n')
    result = []
    buf = []
    for line in lines:
        stripped = line.strip()
        if stripped == '':
            if buf:
                content = ' '.join(buf)
                if not re.match(r'^\s*<', content):
                    content = f'<p>{content}</p>'
                result.append(content)
                buf = []
            result.append('')
        elif re.match(r'^\s*<', stripped):
            if buf:
                content = ' '.join(buf)
                if not re.match(r'^\s*<', content):
                    content = f'<p>{content}</p>'
                result.append(content)
                buf = []
            result.append(line)
        else:
            buf.append(stripped)
    if buf:
        content = ' '.join(buf)
        if not re.match(r'^\s*<', content):
            content = f'<p>{content}</p>'
        result.append(content)
    text = '\n'.join(result)

    # --- Restaurar bloques de código ---
    for i, code in enumerate(code_blocks):
        text = text.replace(f'<p>%%CODEBLOCK_{i}%%</p>', f'<pre><code>{code}</code></pre>')
        text = text.replace(f'%%CODEBLOCK_{i}%%', f'<pre><code>{code}</code></pre>')

    # --- Limpiar párrafos vacíos ---
    text = re.sub(r'<p>\s*</p>', '', text)
    
    return text


def convert_file(md_path: Path, html_path: Path, title: str, is_index: bool = False):
    """Convierte un .md a .html con el template CSS."""
    md_content = md_path.read_text(encoding='utf-8')
    body_html = md_to_html(md_content)
    
    if not is_index:
        body_html = f'<a href="index.html" class="back-link">← Volver al índice</a>\n\n{body_html}'
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — Documentación IA</title>
    <style>{CSS}</style>
</head>
<body>
{body_html}
</body>
</html>"""
    
    html_path.write_text(html, encoding='utf-8')
    return html_path


def generate_index(doc_folder: Path) -> Path:
    """Genera index.html con enlaces a todas las guías."""
    
    docs = sorted([
        ("Guia_IAS", "🚀", "IAS — Lanzador Unificado de IAs", "Un solo comando para gestionar todos los servicios de IA"),
        ("Guia_Dashboard_Monitor", "📊", "Dashboard Web + Monitor del Sistema", "Monitoreo en tiempo real de GPU, RAM, servicios y alertas"),
        ("Guia_Ollama", "🦙", "Ollama — Modelos Locales de IA", "8 modelos de lenguaje (Qwen3, Gemma3, Phi3, DeepSeek)"),
        ("Guia_ComfyUI", "🎨", "ComfyUI — Stable Diffusion (Nodos)", "Generación de imágenes con interfaz de nodos visuales"),
        ("Guia_InvokeAI", "🎯", "InvokeAI — Suite Canvas Profesional", "Suite de generación con canvas unificado e inpaint/outpaint"),
        ("Guia_Hermes", "🧠", "Hermes Agent — Agente Multi-Agente", "Sistema autónomo con Gateway + TUI + Dashboard"),
        ("Guia_OpenHuman_Primeros_Pasos", "💬", "OpenHuman — Asistente de Escritorio", "Asistente IA local-first con Ollama y WSLg"),
        ("Guia_OpenJarvis_Primeros_Pasos", "🎤", "OpenJarvis — Asistente con Voz", "Asistente IA con TTS/STT offline usando Ollama"),
        ("Integraciones_OpenHuman", "🔗", "Integraciones OpenHuman", "Gmail, Notion, Calendar, repositorio local"),
        ("Integraciones_OpenJarvis", "🔗", "Integraciones OpenJarvis", "Voz, wake word, Home Assistant, plugins"),
        ("Guia_PostgreSQL", "🗄️", "PostgreSQL 18 — Base de Datos", "Backend de Simmoon (schema, backups, conexión)"),
        ("Guia_Docker_NVIDIA", "🐳", "Docker + NVIDIA Toolkit", "Contenedores con aceleración GPU CUDA 12.4"),
        ("Guia_Simmoon", "🎮", "Simmoon — Juego + Generador IA", "Juego de assets generados por IA con ComfyUI/Leonardo"),
    ])
    
    cards = []
    for slug, emoji, title, desc in docs:
        cards.append(f"""    <a href="{slug}.html" class="card">
        <div class="card-emoji">{emoji}</div>
        <div class="card-title">{title}</div>
        <div class="card-desc">{desc}</div>
    </a>""")
    
    def C(slice):
        """Join card list slice into string."""
        return "\n".join(cards[slice])
    
    index_content = f"""<h1>📚 Documentación del Ecosistema de IA</h1>
<p style="color: var(--muted); font-size: 1.05rem; margin-bottom: 2rem;">
    Guías de referencia rápida para todas las aplicaciones de IA instaladas en el sistema.
    <strong>Doble clic</strong> en cualquier archivo <code>.html</code> para abrirlo en el navegador.
</p>

<h2>🚀 Lanzadores y Monitoreo</h2>
<div class="cards">
{C(slice(0,2))}
</div>

<h2>🤖 Modelos y Asistentes de IA</h2>
<div class="cards">
{C(slice(2,3))}
{C(slice(5,10))}
</div>

<h2>🎨 Generación de Imágenes</h2>
<div class="cards">
{C(slice(3,5))}
</div>

<h2>🗄️ Infraestructura</h2>
<div class="cards">
{C(slice(10,13))}
</div>

<h2>🖥️ Sistema</h2>
<table>
    <tr><th>Componente</th><th>Especificación</th></tr>
    <tr><td>GPU</td><td>NVIDIA GeForce RTX 4070 Laptop (8GB VRAM)</td></tr>
    <tr><td>Driver</td><td>610.47</td></tr>
    <tr><td>CUDA</td><td>12.4</td></tr>
    <tr><td>Sistema</td><td>Windows 11 + WSL2 Ubuntu 26.04 LTS</td></tr>
    <tr><td>Python</td><td>3.14.4</td></tr>
    <tr><td>Docker</td><td>29.1.3</td></tr>
    <tr><td>NVIDIA Toolkit</td><td>1.19.1</td></tr>
</table>

<h2>⚡ Acceso Rápido</h2>
<table>
    <tr><th>Herramienta</th><th>Acceso</th></tr>
    <tr><td><strong>IAS Launcher</strong></td><td>Doble clic en <code>ias_desktop.bat</code> (escritorio)</td></tr>
    <tr><td><strong>Dashboard</strong></td><td><a href="http://localhost:5000">http://localhost:5000</a></td></tr>
    <tr><td><strong>ComfyUI</strong></td><td><a href="http://localhost:8188">http://localhost:8188</a></td></tr>
    <tr><td><strong>InvokeAI</strong></td><td><a href="http://localhost:9090">http://localhost:9090</a> (requiere instalación)</td></tr>
    <tr><td><strong>Hermes Dashboard</strong></td><td><a href="http://localhost:9120">http://localhost:9120</a></td></tr>
    <tr><td><strong>Verificar servicios</strong></td><td>Doble clic en <code>SIMMOON_Launch.bat</code></td></tr>
</table>
"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📚 Documentación IA — Índice</title>
    <style>
        {CSS}
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 0.8rem;
            margin: 0.8rem 0 2rem;
        }}
        .card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1.2rem;
            text-decoration: none;
            color: var(--text);
            transition: all 0.15s;
            display: block;
        }}
        .card:hover {{
            border-color: var(--accent);
            background: #1c2433;
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(88,166,255,0.1);
            text-decoration: none;
        }}
        .card-emoji {{
            font-size: 1.8rem;
            margin-bottom: 0.5rem;
        }}
        .card-title {{
            font-weight: 600;
            font-size: 1rem;
            color: #fff;
            margin-bottom: 0.3rem;
        }}
        .card-desc {{
            font-size: 0.85rem;
            color: var(--muted);
            line-height: 1.4;
        }}
    </style>
</head>
<body>
{index_content}
</body>
</html>"""
    
    index_path = doc_folder / "index.html"
    index_path.write_text(html, encoding='utf-8')
    return index_path


def main():
    project_root = Path(__file__).parent.parent if '__file__' in dir() else Path(os.getcwd())
    desktop_docs = Path("/mnt/c/Users/docus/Desktop/documentacion")
    
    # Intentar ruta local también
    if not desktop_docs.exists():
        desktop_docs = Path("C:/Users/docus/Desktop/documentacion")
    
    if not desktop_docs.exists():
        print(f"Error: No se encuentra {desktop_docs}")
        print("Asegúrate de que la carpeta documentacion existe en el escritorio.")
        return

    print(f"📁 Carpeta docs: {desktop_docs}")
    
    # Convertir todos los .md a .html
    md_files = sorted(desktop_docs.glob("*.md"))
    print(f"📄 {len(md_files)} archivos .md encontrados")
    
    converted = 0
    for md_file in md_files:
        html_name = md_file.stem + ".html"
        html_path = desktop_docs / html_name
        
        # Determinar título
        title = md_file.stem.replace("Guia_", "").replace("Integraciones_", "Integraciones: ").replace("_", " ")
        if md_file.stem == "README_DOCS":
            title = "Índice de Documentación"
        
        convert_file(md_file, html_path, title)
        converted += 1
        print(f"  ✅ {md_file.name} → {html_name}")

    # Generar index.html
    generate_index(desktop_docs)
    print(f"  ✅ index.html generado (índice visual)")
    
    print(f"\n🎉 {converted} guías convertidas a HTML + índice.")
    print(f"   Doble clic en: {desktop_docs / 'index.html'}")


if __name__ == "__main__":
    main()
