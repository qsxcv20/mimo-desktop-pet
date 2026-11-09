import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw

SRC = r"D:\桌面宠物\assets\src"
OUT = r"D:\桌面宠物\_mimo"

p = os.path.join(SRC, "mimo-idle-v2@2048.png")
img = Image.open(p).convert("RGBA")
bb = img.getchannel("A").getbbox()
print("原图", img.size, "alpha bbox", bb)

crop = img.crop(bb)
W, H = crop.size
print("内容尺寸", (W, H))

# 只取头部（上面 55%）
head_h = int(H * 0.55)
head = crop.crop((0, 0, W, head_h)).convert("RGB")
scale = 0.62
head = head.resize((int(W * scale), int(head_h * scale)), Image.LANCZOS)
d = ImageDraw.Draw(head)
STEP = 100
for x in range(0, W, STEP):
    X = int(x * scale)
    d.line([(X, 0), (X, head.height)], fill=(0, 120, 255), width=1)
    d.text((X + 2, 2), str(x), fill=(0, 90, 200))
for y in range(0, head_h, STEP):
    Y = int(y * scale)
    d.line([(0, Y), (head.width, Y)], fill=(0, 120, 255), width=1)
    d.text((2, Y + 2), str(y), fill=(0, 90, 200))
out = os.path.join(OUT, "face-grid.png")
head.save(out)
print("已保存", out, head.size, "（网格坐标 = 原内容坐标）")
