import importlib, sys, subprocess, os, glob, tempfile
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

for m in ("numpy", "mediapipe", "cv2", "scipy", "skimage"):
    try:
        mod = importlib.import_module(m)
        print("  OK  ", m, getattr(mod, "__version__", "?"))
    except Exception as e:
        print("  --  ", m, type(e).__name__)

tmp = os.path.join(tempfile.gettempdir(), "mpchk")
os.makedirs(tmp, exist_ok=True)
print("\n--- mediapipe 是否有 py3.13 轮子 ---")
r = subprocess.run([sys.executable, "-m", "pip", "index", "versions", "mediapipe"],
                   capture_output=True, text=True, timeout=90)
print((r.stdout or r.stderr)[:400])
