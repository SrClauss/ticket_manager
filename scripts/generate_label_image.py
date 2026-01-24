#!/usr/bin/env python3
"""
Generate a label image sized in mm for printing (converts mm -> pixels using DPI).
Usage: python scripts/generate_label_image.py --width-mm 69 --height-mm 99 --dpi 300 --text "Nome do Participante" --outfile label.png
"""

import argparse
from PIL import Image, ImageDraw, ImageFont

MM_PER_INCH = 25.4


def mm_to_px(mm: float, dpi: int) -> int:
    return int(round(mm * dpi / MM_PER_INCH))


def make_label(width_mm: float, height_mm: float, dpi: int, bg: str, fg: str, text: str, outfile: str, font_path: str | None = None):
    w = mm_to_px(width_mm, dpi)
    h = mm_to_px(height_mm, dpi)

    img = Image.new("RGB", (w, h), color=bg)
    draw = ImageDraw.Draw(img)

    # Load a default truetype font if available, otherwise use PIL default
    font_size = max(10, int(min(w, h) * 0.12))
    font = None
    try:
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
        else:
            # try common fonts
            for fp in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 
                       "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
                try:
                    font = ImageFont.truetype(fp, font_size)
                    break
                except Exception:
                    font = None
            if font is None:
                font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # center the text
    if text:
        text_lines = str(text).split("\\n")
        total_h = 0
        line_sizes = []
        for line in text_lines:
            size = draw.textsize(line, font=font)
            line_sizes.append(size)
            total_h += size[1]
        # starting y to center vertically
        y = (h - total_h) // 2
        for i, line in enumerate(text_lines):
            tw, th = line_sizes[i]
            x = (w - tw) // 2
            draw.text((x, y), line, font=font, fill=fg)
            y += th

    # Save with DPI metadata for downstream systems
    try:
        img.save(outfile, dpi=(dpi, dpi))
    except Exception:
        img.save(outfile)

    print(f"Saved: {outfile} ({w}x{h} px, dpi={dpi})")


def main():
    p = argparse.ArgumentParser(description="Generate label image in mm size for Brother printing")
    p.add_argument("--width-mm", type=float, default=69, help="label width in millimeters (default: 69)")
    p.add_argument("--height-mm", type=float, default=99, help="label height in millimeters (default: 99)")
    p.add_argument("--dpi", type=int, default=300, help="dots per inch to render the image (default: 300)")
    p.add_argument("--bg", default="#FFFFFF", help="background color (default white)")
    p.add_argument("--fg", default="#000000", help="foreground/text color (default black)")
    p.add_argument("--text", default="", help="text to render centered on label")
    p.add_argument("--outfile", default="label.png", help="output filename (default: label.png)")
    p.add_argument("--font", default=None, help="optional TTF font path")

    args = p.parse_args()

    make_label(args.width_mm, args.height_mm, args.dpi, args.bg, args.fg, args.text, args.outfile, args.font)


if __name__ == '__main__':
    main()
