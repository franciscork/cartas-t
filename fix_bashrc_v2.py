#!/usr/bin/env python3
"""Fix .bashrc PATH: merge duplicate PATH lines into one properly quoted export."""
import re

with open("/home/docus/.bashrc", "r") as f:
    content = f.read()

# Remove any line containing "merged_path" (artifact from broken fix)
lines = content.splitlines(keepends=True)
cleaned = [l for l in lines if "merged_path" not in l]
content = "".join(cleaned)

# Find all export PATH lines
path_lines = []
for i, line in enumerate(cleaned):
    if line.strip().startswith("export PATH="):
        path_lines.append(i)

print(f"Found {len(path_lines)} export PATH line(s) at indices: {path_lines}")

if len(path_lines) == 1:
    # Check if the single line is properly quoted
    idx = path_lines[0]
    line = cleaned[idx]
    if '"' not in line:
        # Unquoted - needs fixing
        # Extract the path value
        value = line.split("=", 1)[1].strip()
        cleaned[idx] = f'export PATH="{value}"\n'
        print(f"Added quotes to line {idx}")
    else:
        print(f"Line {idx} already quoted")
    
    with open("/home/docus/.bashrc", "w") as f:
        f.writelines(cleaned)
    print("✅ .bashrc fixed: single properly-quoted PATH line")

elif len(path_lines) >= 2:
    # Multiple PATH lines - merge them
    # Re-read from cleaned content
    # Find the last one and merge all unique paths into it
    all_paths = []
    for idx in path_lines:
        line = cleaned[idx]
        # Extract path value (handle both quoted and unquoted)
        match = re.search(r'export PATH="?([^"]*)"?', line)
        if match:
            val = match.group(1).rstrip(":")
            all_paths.extend(val.split(":"))
    
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for p in all_paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    
    merged_path = ":".join(unique)
    
    # Remove all PATH lines and insert one merged line at the position of the last one
    last_idx = path_lines[-1]
    cleaned[last_idx] = f'export PATH="{merged_path}"\n'
    for idx in sorted(path_lines[:-1], reverse=True):
        del cleaned[idx]
    
    with open("/home/docus/.bashrc", "w") as f:
        f.writelines(cleaned)
    print(f"✅ .bashrc fixed: merged {len(path_lines)} PATH lines into 1 with {len(unique)} paths")

print("Done.")
