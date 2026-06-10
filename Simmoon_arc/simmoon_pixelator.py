#!/usr/bin/env python3
"""
SIMMOON Pixelator - Professional pixel art conversion pipeline.
Converts generated images to genuine retro game sprites in SimCity 2000 style.
Uses: downsampling, color quantization to retro palette, 1px outline detection,
and nearest-neighbor upscaling. Supports RGBA transparency.

Usage:
    python simmoon_pixelator.py --directory businesses/ --game-res 64 --colors 16
    python simmoon_pixelator.py -i test.png -o test_pixel.png -g 64 -c 16
"""

import argparse
import os
from pathlib import Path
from PIL import Image, ImageFilter

# ============================================================================
# RETRO PALETTES - SimCity 2000 / VGA inspired
# ============================================================================

PALETTE_8 = [
    (0, 0, 0), (255, 255, 255), (128, 128, 128), (200, 50, 50),
    (50, 100, 200), (50, 180, 50), (200, 200, 50), (100, 80, 60),
]

PALETTE_16 = [
    (0, 0, 0), (255, 255, 255), (128, 128, 128), (192, 192, 192),
    (64, 64, 64), (200, 50, 50), (50, 100, 200), (50, 180, 50),
    (200, 200, 50), (200, 100, 50), (150, 80, 180), (50, 180, 180),
    (180, 120, 80), (100, 150, 200), (200, 180, 150), (80, 80, 80),
]

PALETTE_32 = [
    (0, 0, 0), (255, 255, 255), (100, 100, 100), (140, 140, 140),
    (180, 180, 180), (220, 220, 220), (60, 60, 60), (30, 30, 30),
    (220, 60, 60), (180, 40, 40), (60, 120, 220), (40, 80, 180),
    (60, 200, 60), (40, 140, 40), (220, 220, 60), (180, 160, 40),
    (220, 120, 40), (180, 80, 30), (160, 80, 200), (120, 40, 160),
    (40, 200, 200), (20, 140, 140), (200, 140, 100), (140, 100, 60),
    (120, 160, 220), (80, 120, 180), (220, 200, 160), (180, 160, 120),
    (200, 160, 200), (160, 140, 180), (60, 100, 60), (80, 60, 40),
]


def _make_palette_image(palette_colors):
    """Create a proper P-mode image with the palette set correctly.
    Pillow's quantize() requires the palette to be set on a P-mode image
    with the raw palette data as 768 bytes (256 * 3)."""
    # Create a 16x16 image in P mode
    pal_img = Image.new("P", (16, 16))
    # Flatten palette colors into a 768-byte array (pad with zeros)
    raw_palette = []
    for r, g, b in palette_colors:
        raw_palette.extend([r, g, b])
    # Pad to 768 bytes (256 colors * 3)
    raw_palette.extend([0, 0, 0] * (256 - len(palette_colors)))
    pal_img.putpalette(raw_palette)
    return pal_img


def pixelate_image(input_path, output_path, game_res=64, colors=16,
                   palettes=None, outline_strength=1.5, add_outlines=True):
    """
    Full pixel art conversion pipeline with RGBA support.
    
    1. Downsample to game resolution (nearest-neighbor)
    2. Quantize colors to retro palette
    3. Add 1px outlines (edge detection)
    4. Upscale with nearest-neighbor
    5. Preserve transparency
    """
    # Select palette
    if palettes and str(colors) in palettes:
        palette_list = palettes[str(colors)]
    elif colors <= 8:
        palette_list = PALETTE_8
    elif colors <= 16:
        palette_list = PALETTE_16
    else:
        palette_list = PALETTE_32

    # Load image preserving alpha
    img = Image.open(input_path)
    has_alpha = img.mode in ("RGBA", "LA", "PA")
    
    if has_alpha:
        img_rgb = img.convert("RGBA")
    else:
        img_rgb = img.convert("RGB")

    orig_w, orig_h = img_rgb.size
    aspect = orig_w / orig_h
    target_w = max(1, int(game_res * aspect))
    target_h = game_res

    # STEP 1: Downsample to game resolution
    small = img_rgb.resize((target_w, target_h), Image.NEAREST)

    # STEP 2: Color quantization
    palette_img = _make_palette_image(palette_list)
    
    if has_alpha:
        # For RGBA: separate alpha, quantize RGB, reapply alpha
        alpha_ch = small.split()[-1]  # Get alpha channel
        rgb_part = small.convert("RGB")
        quantized = rgb_part.quantize(palette=palette_img, dither=Image.Dither.NONE)
        pixel_rgb = quantized.convert("RGB")
        # Recombine with alpha
        pixel_rgba = pixel_rgb.convert("RGBA")
        # Apply threshold to alpha (make semi-transparent pixels either full or transparent)
        alpha_data = alpha_ch.point(lambda x: 255 if x > 128 else 0)
        pixel_rgba.putalpha(alpha_data)
        pixel_art = pixel_rgba
    else:
        quantized = small.quantize(palette=palette_img, dither=Image.Dither.NONE)
        pixel_art = quantized.convert("RGB")

    # STEP 3: Add 1px outlines (edge detection without dilation)
    if add_outlines and outline_strength > 0:
        pixel_art = _add_1px_outlines(pixel_art, outline_strength)

    # STEP 4: Upscale with nearest-neighbor (keeps hard pixel edges)
    upscale = max(2, 512 // max(target_w, target_h))
    final_size = (target_w * upscale, target_h * upscale)
    final = pixel_art.resize(final_size, Image.NEAREST)

    # Save
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    final.save(output_path, "PNG")
    return final.size


def _add_1px_outlines(img, strength=1.5):
    """Add clean 1-pixel outlines using edge detection.
    No dilation - preserves 1px thickness for pixel art authenticity."""
    gray = img.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    
    threshold = int(128 - (strength * 20))
    edge_mask = edges.point(lambda x: 255 if x > threshold else 0)

    result = img.copy()
    pixels = result.load()
    mask_pixels = edge_mask.load()
    w, h = result.size

    for y in range(h):
        for x in range(w):
            if mask_pixels[x, y] > 128:
                if result.mode == "RGBA":
                    r, g, b, a = pixels[x, y]
                    if a > 0:
                        pixels[x, y] = (max(0, r - 60), max(0, g - 60), max(0, b - 60), a)
                else:
                    r, g, b = pixels[x, y]
                    pixels[x, y] = (max(0, r - 60), max(0, g - 60), max(0, b - 60))
    return result


def process_directory(input_dir, output_dir, game_res=64, colors=16,
                      outline_strength=1.5, suffix="_pixel"):
    """Process all PNG images in a directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    os.makedirs(output_path, exist_ok=True)

    files = sorted(input_path.glob("*.png"))
    files = [f for f in files if "_pixel" not in f.stem]

    if not files:
        print(f"  [WARN] No PNG files found in {input_dir}")
        return 0

    count = 0
    for f in files:
        out_name = f"{f.stem}{suffix}.png"
        out_file = output_path / out_name
        try:
            pixelate_image(str(f), str(out_file), game_res=game_res,
                          colors=colors, outline_strength=outline_strength)
            count += 1
            print(f"  [OK] {f.name} -> {out_name} ({game_res}x{game_res}px, {colors} colors)")
        except Exception as e:
            print(f"  [FAIL] {f.name}: {e}")

    return count


def main():
    parser = argparse.ArgumentParser(
        description="SIMMOON Pixelator - Convert images to retro pixel art game sprites"
    )
    parser.add_argument("--input", "-i", help="Single input image path")
    parser.add_argument("--output", "-o", help="Single output image path")
    parser.add_argument("--directory", "-d", help="Directory of images to process")
    parser.add_argument("--output-dir", help="Output directory (default: input_dir + '_pixel')")
    parser.add_argument("--game-res", "-g", type=int, default=64,
                        help="Game resolution in pixels (default: 64)")
    parser.add_argument("--colors", "-c", type=int, default=16, choices=[8, 16, 32],
                        help="Number of palette colors (default: 16)")
    parser.add_argument("--outline", "-ol", type=float, default=1.5,
                        help="Outline strength (0=none, 3=strong, default: 1.5)")
    parser.add_argument("--suffix", default="_pixel",
                        help="Output file suffix (default: _pixel)")
    parser.add_argument("--list-palettes", action="store_true",
                        help="Show available color palettes")

    args = parser.parse_args()

    if args.list_palettes:
        print("\nRetro palettes:")
        for n, p in [("8", PALETTE_8), ("16", PALETTE_16), ("32", PALETTE_32)]:
            print(f"  {n} colors: {len(p)} colors defined")
        print("\nRecommended: buildings=64px/16col, vehicles=48px/16col, sites=128px/32col, UI=32px/8col")
        return

    if args.directory:
        input_dir = args.directory
        output_dir = args.output_dir or (input_dir.rstrip("/\\") + "_pixel")
        total = process_directory(input_dir, output_dir, game_res=args.game_res,
                                  colors=args.colors, outline_strength=args.outline,
                                  suffix=args.suffix)
        print(f"\nProcessed {total} images: {input_dir} -> {output_dir}")

    elif args.input and args.output:
        pixelate_image(args.input, args.output, game_res=args.game_res,
                       colors=args.colors, outline_strength=args.outline)
        print(f"[OK] {args.input} -> {args.output}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
