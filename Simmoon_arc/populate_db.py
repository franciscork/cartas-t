#!/usr/bin/env python3
"""
SIMMOON Database Population Script
Reads simmoon_prompts.json and inserts all asset metadata + generation batch info
into the PostgreSQL 'simmoon' database.

Requires: psycopg2-binary (or psycopg3)
"""

import json
import os
import sys
from datetime import datetime, timezone

# ── CONFIG ───────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "simmoon",
    "user": "postgres",
    # No password for local trust auth; adjust if needed
}

GENERATION_META = {
    "generation_name": "ComfyUI Batch — SIMMOON Assets v2 (2.5D Professional)",
    "backend": "comfyui",
    "model": "v1-5-pruned-emaonly.safetensors",
    "total_images": 108,
    "succeeded": 108,
    "failed": 0,
    "duration_seconds": 1800.0,
    "status": "completed",
    "started_at": "2026-06-04T12:00:00+00:00",
    "completed_at": "2026-06-04T12:30:00+00:00",
    "config_json": {
        "checkpoint": "v1-5-pruned-emaonly.safetensors",
        "width": 512,
        "height": 512,
        "steps": 28,
        "cfg": 9.0,
        "sampler": "euler_ancestral",
        "scheduler": "karras",
        "seed_mode": "random",
        "batch_categories": 13,
    },
}

ASSET_DEFAULTS = {
    "width": 512,
    "height": 512,
    "steps": 28,
    "cfg_scale": 9.0,
    "sampler": "euler_ancestral",
    "backend": "comfyui",
    "model": "v1-5-pruned-emaonly.safetensors",
    "checkpoint": "v1-5-pruned-emaonly.safetensors",
    "status": "generated",
    "generated_at": "2026-06-04T12:00:00+00:00",
    "pixelated_at": "2026-06-04T12:35:00+00:00",
}

# Category icons mapped from viewer.html
CATEGORY_ICONS = {
    "businesses": "🏢",
    "vehicles": "🚗",
    "greenhouses": "🌿",
    "solar_energy": "☀️",
    "lunar_map": "🗺️",
    "buildings_misc": "🏠",
    "ui_elements": "🎮",
    "lunar_sites": "🛰️",
    "roads": "🛣️",
    "decorations": "🎨",
    "characters": "👨‍🚀",
    "lunar_flora": "🌱",
    "infrastructure": "🔧",
}


def get_db_conn():
    try:
        import psycopg
        return psycopg.connect(**DB_CONFIG)
    except ImportError:
        import psycopg2
        return psycopg2.connect(**DB_CONFIG)


def load_prompts(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def insert_categories(cur, categories):
    """Insert categories and return slug->id mapping."""
    slug_to_id = {}
    for slug, data in categories.items():
        icon = CATEGORY_ICONS.get(slug, "📁")
        cur.execute(
            """
            INSERT INTO categories (slug, label, icon, output_dir, description)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                label = EXCLUDED.label,
                icon = EXCLUDED.icon,
                output_dir = EXCLUDED.output_dir
            RETURNING id;
            """,
            (
                slug,
                slug.replace("_", " ").title(),
                icon,
                data.get("output_dir", ""),
                None,
            ),
        )
        slug_to_id[slug] = cur.fetchone()[0]
    return slug_to_id


def insert_generation(cur):
    """Insert the generation batch record and return its id."""
    cur.execute(
        """
        INSERT INTO generations
            (generation_name, backend, model, total_images, succeeded, failed,
             duration_seconds, config_json, status, started_at, completed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (
            GENERATION_META["generation_name"],
            GENERATION_META["backend"],
            GENERATION_META["model"],
            GENERATION_META["total_images"],
            GENERATION_META["succeeded"],
            GENERATION_META["failed"],
            GENERATION_META["duration_seconds"],
            json.dumps(GENERATION_META["config_json"]),
            GENERATION_META["status"],
            GENERATION_META["started_at"],
            GENERATION_META["completed_at"],
        ),
    )
    return cur.fetchone()[0]


def safe_filename(name):
    return name.lower().replace(" ", "_").replace("-", "_")


def insert_assets(cur, categories, slug_to_id, generation_id):
    """Insert all assets and link them to the generation."""
    prompt_order = 0

    for slug, data in categories.items():
        cat_id = slug_to_id[slug]
        output_dir = data.get("output_dir", "").split("/")[-1] or slug
        for p in data.get("prompts", []):
            asset_id = p["id"]
            name = p["name"]
            safe = safe_filename(name)
            path_original = f"{output_dir}/{asset_id}_{safe}.png"
            path_pixel = f"{output_dir}_pixel/{asset_id}_{safe}_pixel.png"
            tags = p.get("tags", [])
            seed = None  # Random seeds were used

            cur.execute(
                """
                INSERT INTO assets
                    (asset_id, name, category_id, prompt, negative_prompt, tags,
                     path_original, path_pixel, width, height, steps, cfg_scale,
                     sampler, backend, model, checkpoint, status,
                     generated_at, pixelated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (asset_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    prompt = EXCLUDED.prompt,
                    negative_prompt = EXCLUDED.negative_prompt,
                    tags = EXCLUDED.tags,
                    path_original = EXCLUDED.path_original,
                    path_pixel = EXCLUDED.path_pixel,
                    updated_at = NOW()
                RETURNING id;
                """,
                (
                    asset_id,
                    name,
                    cat_id,
                    p.get("prompt", ""),
                    p.get("negative_prompt", ""),
                    tags,
                    path_original,
                    path_pixel,
                    ASSET_DEFAULTS["width"],
                    ASSET_DEFAULTS["height"],
                    ASSET_DEFAULTS["steps"],
                    ASSET_DEFAULTS["cfg_scale"],
                    ASSET_DEFAULTS["sampler"],
                    ASSET_DEFAULTS["backend"],
                    ASSET_DEFAULTS["model"],
                    ASSET_DEFAULTS["checkpoint"],
                    ASSET_DEFAULTS["status"],
                    ASSET_DEFAULTS["generated_at"],
                    ASSET_DEFAULTS["pixelated_at"],
                ),
            )
            db_id = cur.fetchone()[0]

            # Link to generation
            cur.execute(
                """
                INSERT INTO generation_assets (generation_id, asset_id, prompt_order, seed_used)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (generation_id, asset_id) DO NOTHING;
                """,
                (generation_id, db_id, prompt_order, seed),
            )
            prompt_order += 1


def verify_counts(cur):
    """Print row counts for sanity check."""
    print("\n--- DATABASE COUNTS ---")
    for t in ("categories", "assets", "generations", "generation_assets"):
        cur.execute("SELECT COUNT(*) FROM " + t + ";")
        count = cur.fetchone()[0]
        print(f"  {t}: {count}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompts_path = os.path.join(script_dir, "simmoon_prompts.json")

    if not os.path.exists(prompts_path):
        print(f"[ERROR] Not found: {prompts_path}")
        sys.exit(1)

    data = load_prompts(prompts_path)
    categories = data.get("categories", {})

    print(f"Loaded {len(categories)} categories with "
          f"{sum(len(c.get('prompts', [])) for c in categories.values())} prompts.")

    conn = get_db_conn()
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Categories
        print("\n→ Inserting categories...")
        slug_to_id = insert_categories(cur, categories)
        print("  Done.")

        # 2. Generation batch
        print("\n→ Inserting generation batch...")
        gen_id = insert_generation(cur)
        print(f"  Generation ID: {gen_id}")

        # 3. Assets + junction
        print("\n→ Inserting assets...")
        insert_assets(cur, categories, slug_to_id, gen_id)
        print("  Done.")

        conn.commit()
        print("\n[OK] All data committed.")

        # Verify
        verify_counts(cur)

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        cur.close()
        conn.close()

    print("\nDatabase population complete.")


if __name__ == "__main__":
    main()
