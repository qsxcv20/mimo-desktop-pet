import sys, os, json, struct, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASAR = r"C:\Users\yang2\AppData\Local\Programs\Xiaomi MiMo\resources\app.asar"
raw = open(ASAR, "rb").read()
print("asar size", len(raw))

# 解析 asar header
a, b, c, d = struct.unpack("<IIII", raw[:16])
print("header sizes:", a, b, c, d)
header_size = b
hdr = raw[16:16 + c]
try:
    files = json.loads(hdr.decode("utf-8"))
except Exception:
    files = json.loads(raw[16:16 + d].decode("utf-8"))
base = 16 + header_size

def walk(node, path=""):
    for name, meta in node.get("files", {}).items():
        p = path + "/" + name
        if "files" in meta:
            yield from walk(meta, p)
        else:
            yield p, meta.get("offset"), meta.get("size")

entries = list(walk(files))
print("entries:", len(entries))
for p, off, sz in entries:
    print("   %-60s size=%s off=%s" % (p, sz, off))

KEYS = [b"pets", b"pet", b"mate", b"Mate", b"sprite", b"frameWidth", b"leijun",
        b"loadURL", b"BrowserWindow", b"transparent", b"alwaysOnTop", b"manifest.json"]
print("\n=== asar 内容关键字 ===")
for p, off, sz in entries:
    if off is None:
        continue
    data = raw[base + int(off): base + int(off) + int(sz)]
    found = [(k.decode(), data.count(k)) for k in KEYS if k in data]
    if found:
        print("  %-52s %s" % (p, found))
        for pat in (b"pets", b"mate", b"Mate", b"transparent", b"alwaysOnTop"):
            i = data.find(pat)
            if i != -1:
                print("      %s @%d :: %s" % (pat.decode(), i,
                      data[max(0,i-180):i+220].decode("utf-8","replace").replace("\n"," ")))
                break
