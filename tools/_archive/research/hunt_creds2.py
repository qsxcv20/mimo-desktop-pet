import sys, os, shutil, json, glob
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("=== mimo-free-client ===")
p = os.path.join(os.path.expanduser("~"), ".local", "share", "mimocode", "mimo-free-client")
if os.path.isfile(p):
    print("  ", open(p, encoding="utf-8", errors="replace").read()[:300])
else:
    print("   缺失")

print("\n=== 尝试拷贝 Local Storage leveldb（被 Chromium 锁） ===")
ls = os.path.join(os.environ["APPDATA"], "Xiaomi MiMo", "Local Storage", "leveldb")
if os.path.isdir(ls):
    for fn in sorted(os.listdir(ls)):
        src = os.path.join(ls, fn)
        if not os.path.isfile(src):
            continue
        try:
            with open(src, "rb") as f:
                data = f.read()
            hit = [k for k in (b"xiaomi", b"accessToken", b"token", b"mimo") if k in data]
            print("   %-22s %9d  命中 %s" % (fn[:22], len(data), [h.decode() for h in hit]))
            if b"xiaomi" in data or b"accessToken" in data:
                i = max(data.find(b"xiaomi"), data.find(b"accessToken"))
                print("      ", data[max(0, i-100):i+260].decode("utf-8", "replace").replace("\n", " "))
        except Exception as e:
            print("   %-22s 读取失败: %s" % (fn[:22], type(e).__name__))
else:
    print("   无 leveldb 目录")

print("\n=== mimocode.db 里找 xiaomi 凭据表 ===")
db = os.path.join(os.path.expanduser("~"), ".local", "share", "mimocode", "mimocode.db")
if os.path.isfile(db):
    print("   大小 %.0f MB" % (os.path.getsize(db) / 1048576))
    try:
        import sqlite3
        con = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
        tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
        print("   表:", tabs[:30])
        for t in tabs:
            if re.search(r'auth|cred|key|token|session', t, re.I) if (re := __import__('re')) else False:
                try:
                    rows = con.execute('select * from "%s" limit 5' % t).fetchall()
                    cols = [c[1] for c in con.execute('PRAGMA table_info("%s")' % t)]
                    print("   [%s] cols=%s" % (t, cols))
                    for r in rows:
                        print("      ", str(r)[:200])
                except Exception as e:
                    print("   [%s] err %s" % (t, e))
        con.close()
    except Exception as e:
        print("   sqlite err", e)
