import sys, os, re, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ls = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo", "Local Storage", "leveldb")
PAT = re.compile(rb'[ -~]{20,}')

KEYS = (b"xiaomimimo", b"accessToken", b"access_token", b"refreshToken", b"mimo_token",
        b"platform.xiaomimimo", b"token-plan", b"api.xiaomimimo")

hits = []
for fn in sorted(os.listdir(ls)):
    p = os.path.join(ls, fn)
    if not os.path.isfile(p) or fn == "LOCK":
        continue
    try:
        data = open(p, "rb").read()
    except Exception:
        continue
    for m in PAT.finditer(data):
        s = m.group(0)
        if any(k in s for k in KEYS):
            hits.append((fn, s))
            if len(hits) > 60:
                break

print("命中 %d 条" % len(hits))
seen = set()
for fn, s in hits:
    t = s.decode("utf-8", "replace")
    # 打印 JSON 结构的
    if t in seen:
        continue
    seen.add(t)
    print("\n--- %s ---" % fn)
    print("  ", t[:600])
