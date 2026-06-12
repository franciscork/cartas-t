#!/usr/bin/env python3
"""Generate HTML visual report of all Blender-generated sprites."""
import os, base64
from pathlib import Path
from PIL import Image

BASE = Path(__file__).parent

# Find all Blender sprites
sprites = []
for d in ['businesses_pixel','housing_pixel','infrastructure_pixel','vehicles_pixel','characters_pixel','lunar_flora_pixel']:
    dp = BASE / d
    if not dp.is_dir():
        continue
    for f in sorted(dp.glob('*_blender*.png')):
        img = Image.open(f)
        with open(f, 'rb') as fh:
            b64 = base64.b64encode(fh.read()).decode()
        sprites.append({
            'dir': d,
            'name': f.name,
            'w': img.size[0],
            'h': img.size[1],
            'kb': f.stat().st_size/1024,
            'b64': b64,
        })

# Also render originals
renders = []
rdir = BASE / 'blender_renders'
for f in sorted(rdir.glob('biz_*.png')):
    with open(f, 'rb') as fh:
        b64 = base64.b64encode(fh.read()).decode()
    renders.append({
        'name': f.name,
        'kb': f.stat().st_size/1024,
        'b64': b64,
    })
for f in sorted(rdir.glob('hou_*.png')):
    with open(f, 'rb') as fh:
        b64 = base64.b64encode(fh.read()).decode()
    renders.append({'name': f.name, 'kb': f.stat().st_size/1024, 'b64': b64})

# Build HTML
html = '''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>SIMMOON - Blender Assets</title>
<style>
body{background:#0a0a19;color:#ddd;font-family:Segoe UI,sans-serif;margin:20px}
h1{color:#ffd740;text-align:center}
h2{color:#80cbc4;border-bottom:2px solid #333;padding-bottom:5px;margin-top:30px}
.grid{display:flex;flex-wrap:wrap;gap:15px;justify-content:center}
.card{background:#12122a;border:1px solid #333;border-radius:10px;padding:10px;text-align:center;width:160px}
.card img{image-rendering:pixelated;border-radius:6px;background:#1a1a3a}
.card .name{font-size:11px;color:#aaa;margin-top:5px;word-break:break-word}
.card .size{font-size:10px;color:#666}
.card.small img{width:68px;height:68px}
.card.large img{width:128px;height:128px}
.stats{text-align:center;color:#888;margin:10px 0}
</style></head><body>
<h1>SIMMOON - Blender Assets</h1>
<div class="stats">Total: ''' + str(len(sprites)) + ''' sprites pixelados | ''' + str(len(renders)) + ''' renders originales</div>

<h2>Sprites Pixelados (68x68)</h2>
<div class="grid">
'''

for s in sprites:
    html += f'<div class="card small"><img src="data:image/png;base64,{s["b64"]}"><div class="name">{s["name"]}</div><div class="size">{s["kb"]:.2f}KB | {s["dir"]}</div></div>\n'

html += '</div>\n<h2>Renders Originales (512x512)</h2>\n<div class="grid">\n'

for r in renders:
    html += f'<div class="card large"><img src="data:image/png;base64,{r["b64"]}" width="128" height="128"><div class="name">{r["name"]}</div><div class="size">{r["kb"]:.0f}KB</div></div>\n'

html += '</div></body></html>'

out = BASE / 'simmoon_blender_assets.html'
out.write_text(html, encoding='utf-8')
print(f'OK: {out} ({len(html)} bytes, {len(sprites)} sprites, {len(renders)} renders)')
