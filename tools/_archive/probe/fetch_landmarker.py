import sys, os, subprocess, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL_DIR = os.path.join(os.path.expanduser("~"), ".cache", "mimo-models")
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL = os.path.join(MODEL_DIR, "face_landmarker.task")

URLS = [
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1.1/face_landmarker.task",
]

if not os.path.isfile(MODEL):
    for u in URLS:
        try:
            print("downloading", u)
            urllib.request.urlretrieve(u, MODEL)
            print("  ok", os.path.getsize(MODEL))
            break
        except Exception as e:
            print("  fail", type(e).__name__, str(e)[:120])
else:
    print("已存在", MODEL, os.path.getsize(MODEL))

if not os.path.isfile(MODEL):
    sys.exit(1)

import numpy as np
from PIL import Image
import mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision

opts = vision.FaceLandmarkerOptions(
    base_options=mpp.BaseOptions(model_asset_path=MODEL),
    running_mode=vision.RunningMode.IMAGE,
    num_faces=1,
    min_face_detection_confidence=0.2,
    min_face_presence_confidence=0.2,
)
lm = vision.FaceLandmarker.create_from_options(opts)

SRC = r"D:\桌面宠物\assets\src"
files = ["mimo-idle-v2@2048.png", "mimo-happy-v2@2048.png",
         "mimo-think-v2@2048.png", "mimo-tired-v2@2048.png"]

for fn in files:
    img = Image.open(os.path.join(SRC, fn)).convert("RGBA")
    rgb = np.array(img)[:, :, :3]
    alpha = np.array(img)[:, :, 3]
    bg = Image.new("RGB", img.size, (255, 255, 255))
    bg.paste(Image.fromarray(rgb), (0, 0), Image.fromarray(alpha))
    res = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.array(bg)))
    if res.face_landmarks:
        L = res.face_landmarks[0]
        def px(i):
            return (L[i].x, L[i].y)
        print("  %-26s OK  左眼(%.3f,%.3f) 右眼(%.3f,%.3f) 眉L(%.3f,%.3f) 下巴(%.3f,%.3f) 脸宽=%.3f"
              % (fn, *px(33), *px(362), *px(105), *px(152),
                 abs(L[234].x - L[454].x)))
    else:
        print("  %-26s 未检测到" % fn)
lm.close()
