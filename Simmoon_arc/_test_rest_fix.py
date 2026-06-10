#!/usr/bin/env python3
"""Quick test: verify list_notes fix works with dashboard's collect_obsidian_status logic."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from obsidian_memory import ObsidianMemory

# Same logic as dashboard._get_obsidian()
SCRIPT_DIR = Path(__file__).parent
config_path = SCRIPT_DIR / "obsidian_rest_config.json"
cfg = json.loads(open(config_path).read())
rest_api_key = cfg.get("api_key", "")
rest_port = cfg.get("port", 27123)
rest_https = cfg.get("https", False)

obsidian = ObsidianMemory(
    vault_path=str(Path.home() / "simmoon-memoria"),
    agent_name="Buffy",
    project="SIMMOON",
    rest_port=rest_port if rest_api_key else None,
    rest_api_key=rest_api_key or None,
    rest_https=rest_https,
)

print(f"Mode: {'REST' if obsidian.rest_available else 'FS'}")
print(f"REST available: {obsidian.rest_available}")
print()

if obsidian.rest_available:
    stats = {}
    total = 0
    for mt in obsidian.MEMORY_TYPES:
        prefix = f"Buffy/{mt}/"
        files = obsidian.rest_client.list_notes(prefix=prefix)
        count = len([f for f in files if f.endswith(".md")])
        print(f"  Buffy/{mt}/: {count} files")
        for f in files[:3]:
            print(f"    {f}")
        if count > 0:
            stats[mt] = count
            total += count
    print()
    print(f"TOTAL ENTRIES: {total}")
    print(f"by_type: {json.dumps(stats)}")
    
    if total > 0:
        print()
        print("✅ FIX WORKS! Dashboard should show these entries after restart.")
    else:
        print()
        print("❌ Still 0 entries - check REST API response format.")
