import sys

full_path = (
    "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:"
    "/usr/games:/usr/local/games:/usr/lib/wsl/lib:"
    "/mnt/c/Program Files/Git/mingw64/bin:"
    "/mnt/c/Program Files/Git/usr/bin:"
    "/mnt/c/Users/docus/bin:"
    "/mnt/c/Program Files/PowerShell/7:"
    "/mnt/c/Python314/Scripts/:/mnt/c/Python314/:"
    "/mnt/c/Program Files/Microsoft MPI/Bin/:"
    "/mnt/c/WINDOWS/system32:/mnt/c/WINDOWS:"
    "/mnt/c/WINDOWS/System32/Wbem:"
    "/mnt/c/WINDOWS/System32/WindowsPowerShell/v1.0/:"
    "/mnt/c/WINDOWS/System32/OpenSSH/:"
    "/mnt/c/Program Files/Autofirma/Autofirma:"
    "/mnt/c/Program Files/Git/cmd:"
    "/mnt/c/Program Files/nodejs/:"
    "/mnt/c/ProgramData/chocolatey/bin:"
    "/mnt/c/Program Files/NVIDIA Corporation/NVIDIA App/NvDLISR:"
    "/mnt/c/Program Files (x86)/NVIDIA Corporation/PhysX/Common:"
    "/mnt/c/Program Files (x86)/PowerShell/7/:"
    "/mnt/c/Users/docus/AppData/Local/Programs/Python/Python311/Scripts/:"
    "/mnt/c/Users/docus/AppData/Local/Programs/Python/Python311/:"
    "/mnt/c/Users/docus/AppData/Local/Programs/Jan/resources/bin:"
    "/mnt/c/Users/docus/AppData/Local/Microsoft/WindowsApps:"
    "/mnt/c/Users/docus/.cache/lm-studio/bin:"
    "/mnt/c/Users/docus/AppData/Local/Programs/Ollama:"
    "/mnt/c/Users/docus/AppData/Local/Programs/Microsoft VS Code/bin:"
    "/mnt/c/Users/docus/AppData/Local/Programs/Antigravity/bin:"
    "/mnt/c/Users/docus/AppData/Roaming/npm:"
    "/mnt/c/Users/docus/AppData/Roaming/Python/Scripts:"
    "/mnt/c/Users/docus/AppData/Local/Programs/Antigravity IDE/bin:"
    "/mnt/c/Users/docus/Documents:"
    "/mnt/c/Program Files/LM Studio:"
    "/mnt/c/Users/docus/AppData/Local/Programs/Pinokio:"
    "/home/docus/.local/bin:/home/docus/go/bin"
)

filepath = sys.argv[1] if len(sys.argv) > 1 else "/home/docus/.bashrc"

with open(filepath, "r") as f:
    lines = f.readlines()

# Line 148 is index 147
lines[147] = 'export PATH="' + full_path + '"\n'

with open(filepath, "w") as f:
    f.writelines(lines)

print("PATH restored with proper quoting on line 148")
