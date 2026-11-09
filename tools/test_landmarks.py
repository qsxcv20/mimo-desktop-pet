import sys, os, json
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

SRC = r"D:\桌面宠物\assets\src"
files = ["mimo-idle-v2@2048.png", "mimo-happy-v2@2048.png",
         "mimo-think-v2@2048.png", "mimo-tired-v2@2048.png"]

print("=== mediapipe 能力探测 ===")
import mediapipe as mp
print("  mediapipe", mp.__version__)
print("  has solutions:", hasattr(mp, "solutions"))
if hasattr(mp, "solutions"):
    print("  solutions 目录:", [x for x in dir(mp.solutions) if not x.startswith("_")][:20])

MODEL = os.path.join(os.path.expanduser("~"), ".cache", "mimo-face.t.task")
print("\n  模型文件:", MODEL, "存在" if os.path.isfile(MODEL) else "缺失")

# 尝试 legacy face_mesh
try:
    fm = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1,
                                          refine_landmarks=True,
                                          min_detection_confidence=0.2)
    print("\n  legacy FaceMesh 可用")
    from PIL import Image
    import numpy as np
    for fn in files:
        p = os.path.join(SRC, fn)
        img = Image.open(p).convert("RGBA")
        arr = np.array(img)
        rgb = arr[:, :, :3].copy()
        alpha = arr[:, :, 3]
        # 合成到白底（mediapipe 需要不透明图）
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(Image.fromarray(rgb), (0, 0), Image.fromarray(alpha))
        res = fm.process(np.array(bg))
        if res.multi_face_landmarks:
            lm = res.multi_face_landmarks[0].landmark
            # 关键索引（mediapipe 标准）
            L_EYE = 33, 133, 159, 145, 160, 158, 144, 153
            R_EYE = 362, 362, 386, 374, 387, 385, 373, 380
            l = lm[33]; r = lm[362]
            chin = lm[152]
            print("  %-26s 检测到脸  左眼(%.3f,%.3f) 右眼(%.3f,%.3f) 下巴(%.3f,%.3f)"
                  % (fn, l.x, l.y, r.x, r.y, chin.x, chin.y))
        else:
            print("  %-26s 未检测到人脸" % fn)
    fm.close()
except Exception as e:
    print("  legacy FaceMesh 失败:", type(e).__name__, e)
