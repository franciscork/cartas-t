#!/usr/bin/env python3
"""Patch agatha_actas.py — add Buffy & Claude Code activity section to reports."""
import sys

path = 'Simmoon_arc/agatha_actas.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if already patched
if 'BUFFY_Y_CLAUDE' in content:
    print('ALREADY_PATCHED')
    sys.exit(0)

# Insert the Buffy & Claude activity section into format_report()
# Right after the "⚙️ Actividad de Generación" block and before "Estado de Fábrica"
marker = '    if data["last_generation"]:\n        lines.append(f"🔄 Última generación: {data[\'last_generation\']}")'
idx = content.find(marker)
if idx < 0:
    print('ERROR: marker1 not found')
    sys.exit(1)

# Find the end of this block - it's followed by "    # Estado consolidado de la fábrica"
section_end = content.find('\n    # Estado consolidado de la fábrica', idx)
if section_end < 0:
    print('ERROR: marker2 not found')
    sys.exit(1)

activity_section = """

    # ── BUFFY & CLAUDE CODE ACTIVITY ──
    lines.append("")
    lines.append("━" * 30)
    lines.append("*BUFFY & CLAUDE CODE*")
    lines.append("━" * 30)
    
    try:
        from system_logger import get_agent_activity
        buffy_acts = get_agent_activity(\"Buffy\", limit=3)
        claude_acts = get_agent_activity(\"Claude Code\", limit=3)
        
        if buffy_acts:
            for act in buffy_acts:
                lines.append(f"🦙 {act.get('message', '?')}")
        else:
            lines.append("🦙 Buffy: sin actividad registrada")
        
        if claude_acts:
            for act in claude_acts:
                lines.append(f"🤖 {act.get('message', '?')}")
        else:
            lines.append("🤖 Claude Code: sin actividad registrada")
    except Exception:
        lines.append("🦙 Buffy: sin actividad registrada")
        lines.append("🤖 Claude Code: sin actividad registrada")
    
"""

new_content = content[:section_end] + activity_section + content[section_end:]

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

lines = len(new_content.split('\n'))
print(f'OK {lines} lines')
