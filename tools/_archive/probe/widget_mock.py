"""Render a widget mock: chat page background + pet cut-out + code-drawn speech bubble.

Mirrors the layout language of dsh-whale-widget (bubble drawn in code, pet anchored
bottom-right), but with the MiMo orange palette.

Usage:
    python widget_mock.py --pet assets/mimo-idle-v2-610.png --out assets/mock.png \
        --label "Account balance" --amount "¥ 12.34" --hint "Today used ¥3.21"
"""

import argparse
import os

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = r"C:\Windows\Fonts"
BUBBLE_STROKE = "#8a3a0d"
LABEL_COLOR = "#b45309"
AMOUNT_COLOR = "#c2410c"
HINT_COLOR = "#b08d6a"
PAGE_BG = "#f6f7fb"
PANEL_BORDER = "#e6e8f0"
TEXT_COLOR = "#4b5563"


def font(name, size):
    path = os.path.join(FONT_DIR, name)
    if not os.path.exists(path):
        path = os.path.join(FONT_DIR, "arial.ttf")
    return ImageFont.truetype(path, size)


def draw_bubble(draw, box, tail, label, amount, hint):
    x, y, w, h = box
    bounds = (x, y, x + w, y + h)
    # tail first, then the ellipse covers its top edge
    draw.polygon(tail, fill="#ffffff", outline=BUBBLE_STROKE, width=5)
    draw.ellipse(bounds, fill="#ffffff", outline=BUBBLE_STROKE, width=5)

    cx = x + w / 2
    draw.text((cx, y + 26), label, font=font("msyhbd.ttc", 15), fill=LABEL_COLOR, anchor="ma")
    draw.text((cx, y + 52), amount, font=font("msyhbd.ttc", 30), fill=AMOUNT_COLOR, anchor="ma")
    draw.text((cx, y + 106), hint, font=font("msyh.ttc", 13), fill=HINT_COLOR, anchor="ma")


def render(pet_path, out_path, label, amount, hint, width=1180, height=560, pet_h=300):
    canvas = Image.new("RGBA", (width, height), PAGE_BG)
    draw = ImageDraw.Draw(canvas)

    # simulated chat panel
    draw.rounded_rectangle((20, 60, 490, 210), radius=18, fill="#ffffff", outline=PANEL_BORDER, width=2)
    body_font = font("msyh.ttc", 15)
    draw.text((44, 84), "Help me compile this month's usage stats into a table...", font=body_font, fill=TEXT_COLOR)
    draw.text((44, 146), "Reading local session logs and aggregating by model...", font=body_font, fill=TEXT_COLOR)

    # pet, bottom-right anchored
    pet = Image.open(pet_path).convert("RGBA")
    pet_w = int(pet.width * pet_h / pet.height)
    pet = pet.resize((pet_w, pet_h), Image.LANCZOS)
    canvas.alpha_composite(pet, (width - pet_w - 40, height - pet_h - 16))

    bx, by, bw, bh = 545, 95, 400, 165
    tail = [(bx + bw * 0.36, by + bh - 14), (bx + bw * 0.52, by + bh - 14), (bx + bw * 0.30, by + bh + 26)]
    draw_bubble(draw, (bx, by, bw, bh), tail, label, amount, hint)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    canvas.convert("RGB").save(out_path, "PNG")
    return out_path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pet", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--amount", required=True)
    p.add_argument("--hint", required=True)
    a = p.parse_args()
    print(render(a.pet, a.out, a.label, a.amount, a.hint))


if __name__ == "__main__":
    main()
