import json, sys, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\runtime-res\resource-index.json"
d = json.load(open(p, encoding="utf-8"))
s = json.dumps(d, ensure_ascii=False)

for kw in ["pet", "Pet", "mate", "Mate", "spritesheet", "koala", "panda", "leijun"]:
    idxs = [m.start() for m in re.finditer(re.escape(kw), s)]
    print("%-12s %d" % (kw, len(idxs)))

print("\n--- node/path entries mentioning pet/mate/koala/panda ---")
def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, path + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, path + "/%d" % i)
    else:
        if isinstance(o, str) and re.search(r"pet|mate|koala|panda|leijun|spritesheet", o, re.I):
            yield (path, o[:300])

hits = list(walk(d))
print("count", len(hits))
for path, val in hits[:80]:
    print("%-60s %s" % (path[-60:], val))
