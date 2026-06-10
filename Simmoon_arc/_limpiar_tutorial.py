# -*- coding: utf-8 -*-
"""
Limpia el archivo juego_simmoon.py de las 3 copias duplicadas del tutorial.
Mantiene solo 1 copia limpia + el alias legacy + corrige renderizar().
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

RUTA = "Simmoon_arc/juego_simmoon.py"

with open(RUTA, encoding="utf-8") as f:
    content = f.read()

# Normalize line endings
content = content.replace('\r\n', '\n')
lines = content.split('\n')

# Find all key method positions
positions = {}
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith('def '):
        name = stripped.split('(')[0].split()[-1]
        positions[name] = i

# Debug: print found positions
for name, idx in sorted(positions.items(), key=lambda x: x[1]):
    print(f"Line {idx+1}: {name}")

# Extract the renderizar_tutorial method from the LAST copy (around line 5065)
# and renderizar_ayuda_estatica from the LAST copy (around line 5161)
# We know:
# - panel_finanzas ends at line 4588 (before first tutorial copy)
# - renderizar() starts after line 5229 (after alias)

last_tutorial_line = positions.get('renderizar_tutorial', 5064)
last_ayuda_line = positions.get('renderizar_ayuda_estatica', 5160)
alias_line = positions.get('renderizar_overlay_ayuda', 5223)
renderizar_line = positions.get('renderizar', 5230)

print(f"\nKey positions:")
print(f"  renderizar_panel_finanzas: {positions.get('renderizar_panel_finanzas')}")
print(f"  renderizar_tutorial (last): {last_tutorial_line}")
print(f"  renderizar_ayuda_estatica (last): {last_ayuda_line}")
print(f"  renderizar_overlay_ayuda: {alias_line}")
print(f"  renderizar: {renderizar_line}")

# Strategy:
# 1. Keep the LAST set of methods (last tutorial + last ayuda + alias)
# 2. Remove ALL duplicates before them
# 3. The code to remove is from line after panel_finanzas to before last tutorial

# Find where renderizar_panel_finanzas ends (next method after it)
# The duplicates are: lines[4588] through lines[5222]
# We want to keep: lines[5064-5222] (last set + alias)
# Remove: lines[4588-5063]
# But we need to find exactly where panel_finanzas ends

# Actually, the simplest approach:
# 1. Find all def renderizar_tutorial lines
# 2. Find all def renderizar_ayuda_estatica lines
# 3. The LAST occurrence of each is what we keep
# 4. Remove all earlier occurrences

# Let's find the exact line numbers of def statements in the duplicate range
tutorial_lines = []
ayuda_lines = []
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith('def renderizar_tutorial('):
        tutorial_lines.append(i)
    elif stripped.startswith('def renderizar_ayuda_estatica('):
        ayuda_lines.append(i)

print(f"\nTutorial def lines: {[l+1 for l in tutorial_lines]}")
print(f"Ayuda def lines: {[l+1 for l in ayuda_lines]}")

if len(tutorial_lines) >= 3:
    # Remove first 2 copies of renderizar_tutorial and their renderizar_ayuda_estatica
    # from panel_finanzas end to before last renderizar_tutorial
    
    # Find where panel_finanzas ends
    panel_end = positions.get('renderizar_panel_finanzas', 3703)
    # Find next method after panel_finanzas before first tutorial
    next_after_panel = tutorial_lines[0]  # This is where first tutorial starts
    
    # Find the last tutorial's ayuda_estatica end
    last_ayuda = ayuda_lines[-1]
    # Find next method after last ayuda
    next_after_last = renderizar_line  # This is renderizar() start
    
    # We need to find the NEXT method after the last ayuda_estatica
    # which determines where ayuda_estatica ends
    # Get all def lines after last_ayuda
    next_def_after_last_ayuda = renderizar_line  # renderizar is the next method
    
    # Now let's calculate what to remove
    # We want to keep: last tutorial (from tutorial_lines[-1]) through next_def_after_last_ayuda
    # Remove: from just after panel_finanzas to just before last tutorial
    
    # Find the last ayuda's end
    ayuda_end_line = next_def_after_last_ayuda
    
    # Find the first tutorial's start minus anything before it
    last_tutorial_start = tutorial_lines[-1]
    
    # The code to remove is: panel_finanzas_end to last_tutorial_start
    # But we need to find where panel_finanzas ends
    # Look for next method after panel_finanzas
    
    # Find ALL def lines
    all_defs = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('def ') and (line[:1] == ' ' or line[:1] == '\t'):
            # This is a method at class indentation level
            all_defs.append(i)
    
    print(f"\nAll class-level methods:")
    for idx in all_defs:
        print(f"  Line {idx+1}: {lines[idx].strip()[:60]}")
    
    # The original methods before duplicates are at indices before tutorial_lines[0]
    # The original overlay_ayuda was replaced. We need to find what was there.
    
    # Let's look at the code between panel_finanzas and first tutorial
    
    # Remove everything between just after the original method before first tutorial
    # ALL the way to just before the LAST tutorial
    # Then we'll have only the last set of methods
    
    # Find what's before first tutorial
    first_tut = tutorial_lines[0]
    prev_method_line = -1
    for idx in all_defs:
        if idx < first_tut:
            prev_method_line = idx
        else:
            break
    
    print(f"\nMethod before first tutorial: line {prev_method_line+1}: {lines[prev_method_line].strip()[:60] if prev_method_line >= 0 else 'N/A'}")
    
    # The code block to keep: last tutorial through last ayuda through alias
    # Remove: from just after the prev_method_line to just before last tutorial
    
    # Actually, the simplest approach: 
    # Find the END of the method before first tutorial (which is renderizar_panel_finanzas)
    # And remove from there to just before the last tutorial
    
    # Find end of panel_finanzas (it ends just before first tutorial)
    # Remove lines from first_tut to (last_tutorial_start - 1)
    
    remove_start = first_tut  # line index of first duplicate tutorial
    remove_end = last_tutorial_start  # line index of last (keep) tutorial
    
    print(f"\nRemoving lines {remove_start+1} to {remove_end} ({remove_end - remove_start} lines)")
    print(f"Keeping lines {last_tutorial_start+1} to {ayuda_end_line} (last set of methods)")
    
    # Build new content: keep [0:remove_start] + keep [remove_end:end]
    new_lines = lines[:remove_start] + lines[remove_end:]
    
    with open(RUTA, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print(f"\nDone! New file has {len(new_lines)} lines (was {len(lines)})")

# Now let's verify the result
with open(RUTA, encoding='utf-8') as f:
    content2 = f.read()
    lines2 = content2.split('\n')
    
print(f"\nRemaining renderizar methods:")
for i, line in enumerate(lines2):
    stripped = line.strip()
    if 'def renderizar_' in stripped and (line[:1] in (' ', '\t') or line.strip().startswith('def ')):
        if stripped.startswith('def '):
            print(f"  Line {i+1}: {stripped[:60]}")
