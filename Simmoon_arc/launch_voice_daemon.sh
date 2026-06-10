#!/bin/bash
# Wrapper para lanzar voice_bridge_wsl.py en tmux
# Resuelve el problema de PATH con paréntesis de Windows
export PATH="$HOME/.local/bin:$PATH"
exec python3 "$HOME/Simmoon_arc/voice_bridge_wsl.py" --daemon
