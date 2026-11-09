# -*- coding: utf-8 -*-
import json, os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
ROOT = r"D:\桌面宠物"

merged = []
for name in ("_gen_args.json", "_ref_args.json"):
    src = os.path.join(ROOT, name)
    if not os.path.isfile(src):
        continue
    d = json.load(open(src, encoding="utf-8-sig"))
    for req in d.get("requests", []):
        req.pop("input_urls", None)
        merged.append(req)
    os.remove(src)
    print("merged + removed:", name)

note = ("角色形象生成规格（图像生成 prompt 原文）。"
        "原始参考图 URL 带阿里云临时签名、早已过期，故移除；"
        "形象设定以本文件与 assets/src 下的源图为准。")
out = {"_note": note, "requests": merged}
dst = os.path.join(ROOT, "docs", "角色生成规格.json")
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("wrote:", dst, "| requests:", len(merged))

for junk in ("_bg.json", "_urls.txt"):
    p = os.path.join(ROOT, junk)
    if os.path.isfile(p):
        os.remove(p)
        print("removed junk:", junk)