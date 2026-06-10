#!/usr/bin/env python3
"""Patch juego_simmoon.py to handle PyInstaller frozen mode paths."""
import sys
from pathlib import Path

src = Path("juego_simmoon.py")
content = src.read_text(encoding="utf-8")

# Ensure sys is imported at the top
if "import sys" not in content.split("\n")[:30]:
    content = content.replace("import os", "import os\nimport sys", 1)

# Patch line 3500: self.dir_assets = str(Path(__file__).parent)
old1 = "        self.dir_assets = str(Path(__file__).parent)"
new1 = "        self.dir_assets = str(Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent)"
if old1 in content:
    content = content.replace(old1, new1, 1)
    print("[OK] Patched self.dir_assets in JuegoSimmoon.__init__")
else:
    print("[WARN] Could not find self.dir_assets patch target")

# Patch line 5884: dir_assets = str(Path(__file__).parent)
old2 = "    dir_assets = str(Path(__file__).parent)"
new2 = "    dir_assets = str(Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent)"
if old2 in content:
    content = content.replace(old2, new2, 1)
    print("[OK] Patched dir_assets in __main__ block")
else:
    print("[WARN] Could not find __main__ dir_assets patch target")

src.write_text(content, encoding="utf-8")
print("Done.")
