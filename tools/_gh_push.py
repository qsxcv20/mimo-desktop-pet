# -*- coding: utf-8 -*-
"Upload the tree via GitHub Git Data API (github.com:443 git is blocked here)."
import base64, concurrent.futures, json, os, subprocess, sys, time, urllib.request, urllib.error
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = r"D:\桌面宠物"
OWNER = "qsxcv20"
REPO = "mimo-desktop-pet"
TOKEN = open(os.path.join(ROOT, ".gh_token"), encoding="utf-8").read().strip()
API = "https://api.github.com"

def api(path, method="GET", body=None, raw=None):
    req = urllib.request.Request(API + path, method=method, data=raw)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "mimo-desktop-pet-setup")
    if raw is not None:
        req.add_header("Content-Type", "application/octet-stream")
    elif body is not None:
        raw = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, data=raw, timeout=120) as r:
                data = r.read().decode("utf-8")
                return r.status, (json.loads(data) if data else {})
        except urllib.error.HTTPError as e:
            txt = e.read().decode("utf-8", "replace")[:300]
            if e.code in (502, 503, 504) and attempt < 3:
                time.sleep(2 * (attempt + 1)); continue
            return e.code, txt
        except Exception as e:
            if attempt < 3:
                time.sleep(2); continue
            return 0, str(e)
    return 0, "unreachable"

def blob(data):
    body = json.dumps({"content": base64.b64encode(data).decode("ascii"),
                      "encoding": "base64"}).encode("utf-8")
    s, r = api("/repos/%s/%s/git/blobs" % (OWNER, REPO), "POST", raw=body)
    if s not in (200, 201):
        raise RuntimeError("blob -> %s %s" % (s, r))
    return r["sha"]

# ---------- 0. bootstrap (empty repo refuses blobs; Contents API can init) ----------
st, rr = api("/repos/%s/%s/contents/README.md" % (OWNER, REPO), "PUT",
             {"message": "chore: init",
              "content": base64.b64encode(b"# mimo-desktop-pet\n").decode()})
print("bootstrap put ->", st, "" if st in (200, 201) else str(rr)[:160])

st, refinfo = api("/repos/%s/%s/git/refs/heads/main" % (OWNER, REPO))
if st != 200:
    print("!! no main ref yet:", str(refinfo)[:200]); raise SystemExit(1)
head_sha = refinfo["object"]["sha"]
st, headcommit = api("/repos/%s/%s/git/commits/%s" % (OWNER, REPO, head_sha))
base_tree = headcommit["tree"]["sha"]
parents = [head_sha]
print("head:", head_sha[:10], "| base_tree:", base_tree[:10])

# ---------- 1. file list ----------
# -z -> NUL separated raw paths; core.quotePath=false -> no \uXXXX escaping
_ls = subprocess.run(["git", "-c", "core.quotePath=false", "ls-files", "-z"],
                   cwd=ROOT, capture_output=True).stdout.decode("utf-8", "replace")
files = [f for f in _ls.split(chr(0)) if f]
print("files to upload:", len(files))

done = [0]
def worker(rel):
    with open(os.path.join(ROOT, rel.replace("/", os.sep)), "rb") as f:
        data = f.read()
    sha = blob(data)
    done[0] += 1
    if done[0] % 60 == 0:
        print("  blobs %d/%d" % (done[0], len(files)))
    return {"path": rel, "mode": "100644", "type": "blob", "sha": sha}

t0 = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    entries = list(ex.map(worker, files))
print("blobs done in %.1fs" % (time.time() - t0))

st, tree = api("/repos/%s/%s/git/trees" % (OWNER, REPO), "POST",
               {"tree": entries, "base_tree": base_tree})
print("create tree ->", st)
if st not in (200, 201):
    print("  !! detail:", str(tree)[:300]); raise SystemExit(1)

st, commit = api("/repos/%s/%s/git/commits" % (OWNER, REPO), "POST",
                 {"message": "feat: MiMo 桌面宠物 —— 联动唤醒/退出 + 额度气泡 + 彩蛋贴纸",
                  "tree": tree["sha"], "parents": parents})
print("create commit ->", st)
if st not in (200, 201):
    print("  !! detail:", str(commit)[:300]); raise SystemExit(1)

st, ref = api("/repos/%s/%s/git/refs/heads/main" % (OWNER, REPO), "PATCH",
              {"sha": commit["sha"], "force": True})
print("update ref ->", st)
if st not in (200, 201):
    print("  !! detail:", str(ref)[:300]); raise SystemExit(1)
print("")
print("DONE  https://github.com/%s/%s" % (OWNER, REPO))