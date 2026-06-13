import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('juego_simmoon.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

out = open('_dup_block.txt', 'w', encoding='utf-8')

for i, line in enumerate(lines):
    if 'Eventos siempre activos' in line and 'ESC' in line:
        out.write(f"FOUND at line {i+1}: {line.rstrip()}\n")
        out.write("\n--- 5 lines BEFORE ---\n")
        for j in range(max(0, i-5), i):
            out.write(f"{j+1}: {lines[j].rstrip()}\n")
        out.write(f"\n--- BLOCK START (line {i+1}) ---\n")
        for j in range(i, min(i+280, len(lines))):
            out.write(f"{j+1}: {lines[j].rstrip()}\n")
        out.write(f"\n--- ENDED at line ~{min(i+280, len(lines))} ---\n")
        break
out.close()
print("Done - output saved to _dup_block.txt")
