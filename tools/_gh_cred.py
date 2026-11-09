# -*- coding: utf-8 -*-
import ctypes, json, sys, urllib.request, urllib.error
from ctypes import wintypes
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

class CREDENTIAL_ATTRIBUTEW(ctypes.Structure):
    _fields_ = [("Keyword", wintypes.LPWSTR), ("Flags", wintypes.DWORD),
                ("ValueSize", wintypes.DWORD), ("Value", ctypes.c_char_p)]

class CREDENTIALW(ctypes.Structure):
    _fields_ = [("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
                ("LastWritten", wintypes.FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.POINTER(CREDENTIAL_ATTRIBUTEW)),
                ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR)]

advapi = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
advapi.CredReadW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
                             ctypes.POINTER(ctypes.POINTER(CREDENTIALW))]
advapi.CredReadW.restype = wintypes.BOOL
advapi.CredFree.argtypes = [ctypes.c_void_p]

ptr = ctypes.POINTER(CREDENTIALW)()
target = "git:https://github.com"
if not advapi.CredReadW(target, 1, 0, ctypes.byref(ptr)):
    print("CredRead failed, winerr =", ctypes.get_last_error())
    raise SystemExit(1)
c = ptr.contents
blob = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize)
user = c.UserName or ""
advapi.CredFree(ptr)
print("username :", user)
print("secret len:", len(blob))
secret = blob.decode("utf-16-le").rstrip("\x00")
print("secret chars:", len(secret), "| token-like:", secret.startswith(("ghp_","gho_","ghu_","github_pat_")))

def api(path, method="GET", body=None):
    req = urllib.request.Request("https://api.github.com" + path, method=method)
    req.add_header("Authorization", "Bearer " + secret)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "mimo-desktop-pet-setup")
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=40) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except Exception as e:
        return 0, str(e)

st, info = api("/user")
print("GET /user ->", st)
if st == 200:
    print("login    :", info.get("login"))
    print("name     :", info.get("name"))
    with open(r"D:\桌面宠物\.gh_token", "w", encoding="utf-8") as f:
        f.write(secret)
    print("token cached -> .gh_token")
else:
    print("detail:", info)