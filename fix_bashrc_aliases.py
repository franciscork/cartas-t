import re

with open('/home/docus/.bashrc', 'r') as f:
    content = f.read()
    lines = content.splitlines(keepends=True)

fixed = 0

# Fix broken aliases with escaped quotes - use regex
for i, line in enumerate(lines):
    # Fix alias simmoon= with broken quotes
    if 'alias simmoon=' in line and '\\\"' in line:
        lines[i] = 'alias simmoon="source ~/simmoon-env/bin/activate"\n'
        fixed += 1
    elif 'alias crewai=' in line and '\\\"' in line:
        lines[i] = 'alias crewai="source ~/crewai-env/bin/activate"\n'
        fixed += 1
    elif 'alias launch_all=' in line and '\\\"' in line:
        lines[i] = 'alias launch_all="bash ~/launch_all.sh"\n'
        fixed += 1
    elif 'alias a1111=' in line and '\\\"' in line:
        lines[i] = 'alias a1111="cd ~/stable-diffusion-webui && ./venv/bin/python launch.py --api --listen"\n'
        fixed += 1
    elif 'alias simmoon-gen=' in line and '\\\"' in line:
        lines[i] = 'alias simmoon-gen="cd ~/Simmoon_arc && bash generate.sh"\n'
        fixed += 1
    elif 'alias simmoon-update=' in line and ('\\\\' in line or '\\\"' in line):
        lines[i] = 'alias simmoon-update="cd ~/Simmoon_arc && git pull"\n'
        fixed += 1

# Ensure /usr/local/bin is in PATH
for i, line in enumerate(lines):
    if line.startswith('export PATH='):
        if '/usr/local/bin' not in line:
            lines[i] = line.replace(
                ':/usr/lib/wsl/lib:',
                ':/usr/lib/wsl/lib:/usr/local/bin:'
            )
            fixed += 1
            print('Added /usr/local/bin to PATH')
        break

with open('/home/docus/.bashrc', 'w') as f:
    f.writelines(lines)

print(f'Fixed {fixed} issues')
