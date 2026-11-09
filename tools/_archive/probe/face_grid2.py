import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw

SRC = r"D:\桌面宠物\assets\src"
OUT = r"D:\桌面宠物\_mimo"

p = os.path.join(SRC, "mimo-idle-v2@2048.png")
img = Image.open(p).convert("RGBA")
bb = img.getchannel("A").getbbox()
crop = img.crop(bb)
W, H = crop.size

Y0, Y1 = 780, 1500
band = crop.crop((0, Y0, W, Y1)).convert("RGB")
scale = 0.62
band = band.resize((int(W * scale), int((Y1 - Y0) * scale)), Image.LANCZOS)
d = ImageDraw.Draw(band)
for x in range(0, W, 100):
    X = int(x * scale)
    d.line([(X, 0), (X, band.height)], fill=(0, 120, 255), width=1)
    d.text((X + 2, 2), str(x), fill=(0, 90, 200))
for y in range(Y0, Y1, 100):
    Y = int((y - Y0) * scale)
    d.line([(0, Y), (band.width, Y)], fill=(0, 120, 255), width=1)
    d.text((2, Y + 2), str(y), fill=(0, 90, 200))
out = os.path.join(OUT, "face-grid2.png")
band.save(out)
print("已保存", out, band.size, " y 范围", Y0, Y1)
