#!/usr/bin/env python3
"""Extract SIMMOON API key from config.json into .env.voteapi for systemd."""
import json, os

cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.voteapi")

try:
    with open(cfg_path) as f:
        cfg = json.load(f)
    key = cfg.get("vote_api", {}).get("api_key", "")
    with open(env_path, "w") as f:
        f.write(f"SIMMOON_API_KEY={key}\n")
    os.chmod(env_path, 0o600)
    print(f"OK: .env.voteapi updated (key={key[:10]}...)")
except Exception as e:
    print(f"ERROR: {e}")
