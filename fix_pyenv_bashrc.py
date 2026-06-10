#!/usr/bin/env python3
"""Añade pyenv a ~/.bashrc sin expansión de variables."""
bashrc_path = "/home/docus/.bashrc"

# Limpiar entradas viejas de pyenv
with open(bashrc_path, "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.strip() == "# pyenv":
        skip = True
        continue
    if skip and line.startswith("export PYENV_ROOT"):
        continue
    if skip and line.startswith("[[ -d"):
        continue
    if skip and line.strip().startswith("eval"):
        continue
    if skip and line.strip() == "":
        skip = False
        continue
    new_lines.append(line)

# Añadir líneas correctas
new_lines.append("\n")
new_lines.append("# pyenv\n")
new_lines.append('export PYENV_ROOT="$HOME/.pyenv"\n')
new_lines.append('[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"\n')
new_lines.append('eval "$(pyenv init - bash)"\n')

with open(bashrc_path, "w") as f:
    f.writelines(new_lines)

print("pyenv added to bashrc with literal $ variables")
# Verificar
with open(bashrc_path) as f:
    for line in f:
        if "pyenv" in line or "PYENV_ROOT" in line:
            print(f"  {line.rstrip()}")
