import sqlite3, sys, os, re, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UD = r"C:\Users\yang2\AppData\Roaming\Xiaomi MiMo\db"
print("=== db dir ===")
for fn in sorted(os.listdir(UD)):
    p = os.path.join(UD, fn)
    print("  %-30s %10d" % (fn, os.path.getsize(p)))

def dump_db(path, label):
    print("\n############ %s ############" % label)
    try:
        con = sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)
        cur = con.cursor()
        tabs = cur.execute("select name from sqlite_master where type='table'").fetchall()
        print("tables:", [t[0] for t in tabs])
        for (t,) in tabs:
            cols = cur.execute('PRAGMA table_info("%s")' % t).fetchall()
            print("  %s: %s" % (t, [c[1] for c in cols]))
            n = cur.execute('select count(*) from "%s"' % t).fetchone()[0]
            print("    rows:", n)
            for row in cur.execute('select * from "%s" limit 3' % t):
                s = str(row)
                print("      ", s[:300])
        con.close()
    except Exception as e:
        print("  ERR", e)

for fn in sorted(os.listdir(UD)):
    p = os.path.join(UD, fn)
    if fn.endswith(".db"):
        dump_db(p, fn)

# raw context of 'spritesheet' in artifacts.db
raw = open(os.path.join(UD, "artifacts.db"), "rb").read()
out = []
for kw in (b"spritesheet", b"are-you-ok", b"leijun"):
    for m in re.finditer(re.escape(kw), raw):
        i = m.start()
        ctx = raw[max(0, i - 600):i + 900]
        out.append("\n\n########## %s @ %d ##########\n%s" % (kw.decode(), i, ctx.decode("utf-8", "replace")))
open(r"D:\桌面宠物\_mimo\artifacts-db-ctx.txt", "w", encoding="utf-8").write("\n".join(out[:40]))
print("\nwrote artifacts-db-ctx.txt, contexts:", min(40, len(out)))
