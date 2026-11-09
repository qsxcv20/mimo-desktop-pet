#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
mimo_quota.py — 取小米 MiMo 额度 / 用量。

两条通路，按可靠性排序：

【A. 问 MiMo 自己】（首选）
    MiMo 桌面内部有 mimo:getUserUsage / mimo:getUserSubscription 两个 IPC，
    主进程用「persist:xiaomi-account」分区的账号会话去打
        https://mimo-server-cn.xiaomimimo.com/api/user/usage
    鉴权天然正确，我们只要通过 CDP 在渲染层调一下：
        window.mimo.getUserUsage()
    -> {ok:true, usage:{percent: 剩余%, resetDate: 'YYYY-MM-DD HH:MM:SS'}}
    前提：MiMo 以 --remote-debugging-port=<port> 启动（仅 127.0.0.1）。

【B. 开放平台 API】（兜底，能拿到余额/套餐/用户资料）
    https://platform.xiaomimimo.com/api/v1/{usage,tokenPlan/usage,
        tokenPlan/detail,balance,userProfile}
    现在这批接口强制要求签名头（否则 403 SIGN_MISSING）。签名算法逆向自
    开放平台前端 chunk：
      1) GET /api/v1/user/sign-key  -> {signKey, epoch, expiresAt}
         响应头 x-server-time 用来校准客户端时钟
      2) 待签串 = METHOD\nPATH\n排序后的query\nSHA256(body)\nTIMESTAMP
      3) X-Sign = HMAC-SHA256(待签串, signKey)   (hex)
         外加 X-Timestamp / X-Key-Epoch
    换票（拿平台票据）：
      GET https://account.xiaomi.com/pass/serviceLogin
          ?_locale=zh_CN&_snsNone=true&sid=api-platform&_json=true
      -> JSON 里的 loc -> 跟过去 -> Set-Cookie 下发 api-platform_serviceToken 等
      （与 MiMo 桌面 SSO SDK 同款，见 main~DAq2tHkd.mjs 的 ServiceTokenManager）

【C. 本地兜底】（永远可用）
    * MiMo 本地 API 的 SSE 事件 ui(kind=usage) -> 本轮真实 token 消耗
    * %APPDATA%\Xiaomi MiMo\xiaomi-last-confirmed.json -> 小米账号 id / 区域
"""

import base64
import ctypes
import hashlib
import hmac
import http.cookiejar
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from ctypes import wintypes

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

APPDATA = os.environ.get("APPDATA", "")
MIMO_UD = os.path.join(APPDATA, "Xiaomi MiMo")
PARTITIONS = os.path.join(MIMO_UD, "Partitions")
LOCAL_STATE = os.path.join(MIMO_UD, "Local State")
XIAOMI_CONFIRMED = os.path.join(MIMO_UD, "xiaomi-last-confirmed.json")
CRED_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "quota_cred.json")

PLATFORM = "https://platform.xiaomimimo.com"
ACCOUNT = "https://account.xiaomi.com/pass/serviceLogin"
PLATFORM_SID = "api-platform"

API_PATHS = {
    "usage": "/api/v1/usage",
    "plan_usage": "/api/v1/tokenPlan/usage",
    "plan_detail": "/api/v1/tokenPlan/detail",
    "balance": "/api/v1/balance",
    "profile": "/api/v1/userProfile",
}

UA = ("miNative PC/Normal Windows_NT/10.0.26200 SDKV/1.0.0 DEVT/PC "
      "DEVS/Windows APP/miaccount_desktop APPV/0.1.0")
HDR = {"Accept": "application/json", "User-Agent": UA,
       "X-Mimo-Source": "mimocode-desktop"}

ACCOUNT_COOKIES = ("passToken", "userId", "cUserId")
PLATFORM_COOKIE_NAMES = ("api-platform_serviceToken", "api-platform_slh",
                          "api-platform_ph", "userId")


# ---------------------------------------------------------------- DPAPI

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char))]


def dpapi_unprotect(data):
    """CryptUnprotectData（Windows DPAPI）解密。"""
    try:
        import win32crypt
        return win32crypt.CryptUnprotectData(data, None, None, None, 0)[1]
    except Exception:
        pass
    blob = DATA_BLOB()
    blob.cbData = len(data)
    buf = ctypes.create_string_buffer(data, len(data))
    blob.pbData = ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))
    out = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob), None, None, None, None, 0, ctypes.byref(out))
    if not ok:
        raise OSError("CryptUnprotectData 失败")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def master_key():
    """Chromium 的 AES 主密钥（Local State.os_crypt.encrypted_key -> DPAPI）。"""
    with open(LOCAL_STATE, "r", encoding="utf-8") as f:
        state = json.load(f)
    enc = state.get("os_crypt", {}).get("encrypted_key")
    if not enc:
        raise RuntimeError("Local State 里没有 os_crypt.encrypted_key")
    raw = base64.b64decode(enc)
    if raw[:5] == b"DPAPI":
        raw = raw[5:]
    return dpapi_unprotect(raw)[:32]


def decrypt_cookie(enc_value, key):
    """Chromium v10/v11 cookie 解密：AES-256-GCM(nonce|ciphertext)。"""
    if not enc_value:
        return ""
    if not enc_value.startswith(("v10", "v11")):
        return enc_value
    body = base64.b64decode(enc_value[3:])
    if len(body) < 12 + 16:
        return ""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        plain = AESGCM(key).decrypt(body[:12], body[12:], None)
    except Exception:
        return ""
    if b"\x00" in plain:
        plain = plain[:plain.rfind(b"\x00")]
    return plain.decode("utf-8", "replace")


# ---------------------------------------------------------------- cookie 库

def cookie_db_paths():
    out = []
    for name in ("xiaomi-account", "rp-browser", ""):
        p = (os.path.join(PARTITIONS, name, "Network", "Cookies") if name
             else os.path.join(MIMO_UD, "Network", "Cookies"))
        if os.path.isfile(p):
            out.append(p)
    return out


def read_cookie_db(path):
    """读一个 Chromium cookie 库，返回 {name: value}（只要 xiaomi 相关域）。"""
    tmp = os.path.join(tempfile.gettempdir(),
                       "mimo-ck-%d.db" % os.getpid())
    shutil.copyfile(path, tmp)
    try:
        con = sqlite3.connect(tmp)
        cur = con.cursor()
        try:
            rows = cur.execute(
                "SELECT host_key, name, encrypted_value, value FROM cookies"
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
        con.close()
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass

    key = None
    out = {}
    for host, name, enc, plain in rows:
        h = (host or "").lower()
        if not any(k in h for k in ("xiaomi", "mimo", "mi.com")):
            continue
        v = plain
        if not v and enc:
            if key is None:
                key = master_key()
            v = decrypt_cookie(enc, key)
        if v:
            out.setdefault(name, v)
    return out


def capture_credentials():
    """从 cookie 库抓取 passToken/userId/cUserId。抓不到返回 None。

    注意：Chromium 运行时对 xiaomi-account 分区的 cookie 库是独占锁，
    读不了 -> 只能在 MiMo 没跑的时候抓（见 tools/capture_creds.py）。
    """
    for path in cookie_db_paths():
        try:
            ck = read_cookie_db(path)
        except Exception:
            continue
        if ck.get("passToken") and ck.get("userId"):
            return {
                "passToken": ck.get("passToken"),
                "userId": ck.get("userId"),
                "cUserId": ck.get("cUserId") or "",
                "captured_at": int(time.time()),
                "source": path,
            }
    return None


def save_cache(cred):
    try:
        with open(CRED_CACHE, "w", encoding="utf-8") as f:
            json.dump(cred, f, ensure_ascii=False, indent=2)
        try:
            os.chmod(CRED_CACHE, 0o600)
        except Exception:
            pass
        return True
    except Exception:
        return False


def load_cache():
    try:
        with open(CRED_CACHE, "r", encoding="utf-8") as f:
            c = json.load(f)
        if c.get("passToken"):
            return c
    except Exception:
        pass
    return None


# ---------------------------------------------------------------- HTTP 基础设施

class _RawCookie(http.cookiejar.Cookie):
    def __init__(self, name, value, domain, path="/"):
        self.name = name
        self.value = value
        self.domain = domain
        self.domain_specified = True
        self.domain_initial_dot = domain.startswith(".")
        self.path = path
        self.path_specified = True
        self.port = None
        self.port_specified = False
        self.secure = False
        self.expires = None
        self.discard = True
        self.comment = None
        self.comment_url = None
        self.rest = {"HttpOnly": None}
        self.version = 0


def _build_opener(cred):
    jar = http.cookiejar.CookieJar()
    for n in ACCOUNT_COOKIES:
        v = cred.get(n)
        if v:
            jar.set_cookie(_RawCookie(n, v, ".xiaomi.com"))
    for n, v in (cred.get("platform_cookies") or {}).items():
        jar.set_cookie(_RawCookie(n, v, ".platform.xiaomimimo.com"))
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar),
        urllib.request.HTTPRedirectHandler())
    return opener, jar


def _get(opener, url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=headers or HDR)
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.geturl(), r.read(200000).decode("utf-8", "replace"), \
                dict(r.headers or {})
    except urllib.error.HTTPError as e:
        return (e.code, url, e.read(4000).decode("utf-8", "replace"),
                dict(e.headers or {}))
    except Exception as e:
        return None, url, str(e), {}


def _parse(body):
    try:
        j = json.loads(body)
    except Exception:
        return None
    if isinstance(j, dict) and j.get("code") == 0:
        return j.get("data")
    return None


# ---------------------------------------------------------------- 换票

def _account_cookie_header(cred):
    parts = []
    for n in ACCOUNT_COOKIES:
        v = cred.get(n)
        if v:
            parts.append("%s=%s" % (n, v))
    return "; ".join(parts)


def exchange_platform_ticket(cred):
    """用账号 cookie 换平台票据（api-platform_serviceToken 等）。

    返回 (platform_cookies dict, error str)。失败时返回 (None, err)。
    """
    pt, uid, cid = cred.get("passToken"), cred.get("userId"), \
        cred.get("cUserId")
    if not pt or not uid:
        return None, "没有小米账号会话"

    q = urllib.parse.urlencode({"_locale": "zh_CN", "_snsNone": "true",
                                "sid": PLATFORM_SID, "_json": "true"})
    hdr = {"User-Agent": UA, "Accept": "application/json",
           "Cookie": _account_cookie_header(cred)}
    req = urllib.request.Request(ACCOUNT + "?" + q, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read(20000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raw = e.read(8000).decode("utf-8", "replace")
    except Exception as e:
        return None, "换票请求失败: %s" % e

    b = raw
    if "&&&START&&&" in b:
        b = b.split("&&&START&&&", 1)[1]
    if "&&&END&&&" in b:
        b = b.split("&&&END&&&", 1)[0]
    try:
        j = json.loads(b)
    except Exception:
        return None, "换票返回非 JSON（小米会话可能已过期）"
    code = j.get("code")
    if code != 0:
        desc = j.get("description") or j.get("desc") or ""
        if code == 70016:
            desc = "小米账号会话已过期（70016），请在 MiMo 里重新登录"
        return None, "换票失败 code=%s %s" % (code, desc)
    loc = j.get("loc") or j.get("location")
    if not loc:
        return None, "换票失败：没有跳转地址"

    # 跟随 loc，Set-Cookie 里会下发平台票据
    opener, jar = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        urllib.request.HTTPRedirectHandler()), None
    cookie_jar = opener.handlers[0].cookiejar if opener.handlers else None
    opener2 = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar),
        urllib.request.HTTPRedirectHandler())
    req2 = urllib.request.Request(loc, headers=hdr)
    try:
        with opener2.open(req2, timeout=25) as r:
            r.read(4000)
    except urllib.error.HTTPError:
        pass
    except Exception:
        pass
    pc = {}
    for c in cookie_jar:
        if c.name in PLATFORM_COOKIE_NAMES:
            pc[c.name] = c.value
    if not pc:
        return None, "换票失败：没有拿到平台票据"
    return pc, None


# ---------------------------------------------------------------- 平台签名

class PlatformSigner(object):
    """开放平台请求签名（逆向自 platform.xiaomimimo.com 前端）。"""

    def __init__(self):
        self.key = None
        self.epoch = None
        self.expires_at = 0
        self.offset = 0.0          # 服务端时钟 - 本地时钟（毫秒）

    def _now(self):
        return (time.time() * 1000.0 + self.offset)

    def fetch_key(self, opener):
        st, url, body, hdrs = _get(opener, PLATFORM + "/api/v1/user/sign-key")
        srv = hdrs.get("x-server-time") or hdrs.get("X-Server-Time")
        if srv:
            try:
                v = float(srv)
                self.offset = (v if v > 1e12 else v * 1000.0) - \
                    (time.time() * 1000.0)
            except Exception:
                pass
        if st != 200:
            return False, "取 sign-key 失败 HTTP %s" % st
        j = json.loads(body)
        d = j.get("data") if isinstance(j, dict) else None
        d = d or j
        k = d.get("signKey")
        if not k:
            return False, "sign-key 返回异常"
        self.key = k
        self.epoch = d.get("epoch")
        self.expires_at = float(d.get("expiresAt") or 0)
        return True, None

    def valid(self):
        return bool(self.key) and self.expires_at > time.time() + 60

    def headers(self, method, url, body=""):
        u = urllib.parse.urlparse(url)
        query = u.query[1:] if u.query.startswith("?") else u.query
        q_sorted = "&".join(sorted([x for x in query.split("&") if x]))
        ts = str(int(self._now() / 1000.0))
        body_hash = "" if body == "" else \
            hashlib.sha256(body.encode("utf-8")).hexdigest()
        msg = "\n".join([method.upper(), u.path, q_sorted, body_hash, ts])
        sign = hmac.new(str(self.key).encode("utf-8"),
                        msg.encode("utf-8"), hashlib.sha256).hexdigest()
        h = {"X-Sign": sign, "X-Timestamp": ts}
        if self.epoch is not None:
            h["X-Key-Epoch"] = str(self.epoch)
        return h


def signed_get(opener, url, signer):
    hdr = dict(HDR)
    hdr.update(signer.headers("GET", url))
    req = urllib.request.Request(url, headers=hdr)
    try:
        with opener.open(req, timeout=20) as r:
            return r.status, r.read(200000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(4000).decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


# ---------------------------------------------------------------- 对外接口

class QuotaClient(object):
    """额度客户端。get() 返回快照 dict，永不抛异常。"""

    def __init__(self, token=None, cdp_port=None):
        self.token = token
        self._cache = None
        self._cache_at = 0.0
        self._ttl = 60.0
        self._last_error = None
        self.usage_log = []          # [(ts, tokens)]
        self._cred = load_cache()
        self._signer = None
        self._cdp = None
        self._cdp_port = cdp_port
        self._last_source = None

    # -- 本地 API 的实时用量（一定有）--

    def note_usage(self, tokens):
        try:
            n = int(tokens)
        except Exception:
            return
        self.usage_log.append((time.time(), n))
        if len(self.usage_log) > 300:
            self.usage_log = self.usage_log[-300:]

    def session_tokens(self):
        return sum(n for _, n in self.usage_log)

    # -- 账号信息（一定有）--

    def account_info(self):
        info = {}
        try:
            with open(XIAOMI_CONFIRMED, "r", encoding="utf-8") as f:
                d = json.load(f)
            info["user_id"] = d.get("userId")
            info["region"] = d.get("region")
        except Exception:
            pass
        return info

    # -- 凭据 --

    def _credential(self):
        if self.token:
            return {"passToken": self.token, "userId": "", "cUserId": ""}
        if self._cred:
            return self._cred
        cred = capture_credentials()
        if cred:
            self._cred = cred
            save_cache(cred)
        return cred

    def refresh_credential(self):
        """强制重新抓 cookie（MiMo 刚退出时用）。"""
        cred = capture_credentials()
        if cred:
            old = self._cred or {}
            if old.get("platform_cookies"):
                cred["platform_cookies"] = old["platform_cookies"]
            self._cred = cred
            save_cache(cred)
            self._cache = None
        return self._cred

    # -- A. 问 MiMo 自己（CDP）--

    def _cdp_client(self):
        if self._cdp is None:
            try:
                from mimo_cdp import MiMoCDP
                self._cdp = MiMoCDP(port=self._cdp_port) if self._cdp_port \
                    else MiMoCDP()
            except Exception:
                self._cdp = False
        return self._cdp or None

    def _via_mimo(self):
        c = self._cdp_client()
        if not c or not c.available():
            return None, "MiMo 未以调试端口启动，读不到额度"
        try:
            raw = c.raw_user_usage()
        except Exception as e:
            return None, "调用 MiMo 失败: %s" % str(e)[:80]
        if not isinstance(raw, dict):
            return None, "MiMo 未返回额度（账号可能未登录）"

        out = {}
        if raw.get("ok"):
            usage = raw.get("usage") or {}
            out["percent"] = usage.get("percent")
            out["reset_date"] = usage.get("resetDate")
            err = None
        else:
            kind = raw.get("kind") or ""
            msg = raw.get("error") or ""
            if kind == "auth-expired" or "401" in str(msg):
                err = "小米账号会话已过期，请在 MiMo 里重新登录"
            elif kind == "no-data" and "no active subscription" in str(msg):
                # 账号是好的，只是套餐到期了 —— 和「没登录」完全是两回事
                err = "无有效订阅（套餐已到期）"
            else:
                err = "MiMo 未返回额度：%s" % (msg or kind or "未知原因")

        # 订阅信息：即使额度取不到也能拿到（套餐名 / 状态 / 到期时间）
        try:
            sub = c.raw_user_subscription() or {}
            sdata = sub.get("data") or {}
            cur = sdata.get("current") or {}
            subs = sdata.get("subscriptions") or []
            if cur.get("title"):
                out["plan"] = cur.get("title")
                out["plan_status"] = cur.get("status") or "ACTIVE"
                out["plan_end"] = cur.get("endTime")
                out["plan_reset"] = cur.get("nextResetTime")
            elif subs:
                # 没有生效中的，取时间上最近的一份
                def _key(s):
                    return str(s.get("endTime") or "")
                subs2 = sorted(subs, key=_key, reverse=True)
                s0 = subs2[0]
                out["plan"] = s0.get("title")
                out["plan_status"] = s0.get("status") or ""
                out["plan_end"] = s0.get("endTime")
                out["plan_reset"] = s0.get("nextResetTime")
            if sub.get("ok") and sdata.get("percent") is not None:
                out["plan_percent"] = sdata.get("percent")
        except Exception:
            pass

        try:
            snap = c.get_auth_snapshot() or {}
            st = ((snap.get("xiaomi") or {}).get("status")) or ""
            if st:
                out["auth"] = st
                if st != "authenticated" and err is None:
                    err = "小米账号未登录"
        except Exception:
            pass

        return out, err

    # -- B. 开放平台 API（带签名）--

    def _via_platform(self):
        cred = self._credential()
        if not cred:
            return None, "没有小米账号会话"
        pc = cred.get("platform_cookies") or {}
        if not pc:
            pc, err = exchange_platform_ticket(cred)
            if not pc:
                return None, err
            cred = dict(cred)
            cred["platform_cookies"] = pc
            cred["captured_at"] = int(time.time())
            self._cred = cred
            save_cache(cred)

        opener, jar = _build_opener(cred)
        if self._signer is None:
            self._signer = PlatformSigner()
        if not self._signer.valid():
            ok, err = self._signer.fetch_key(opener)
            if not ok:
                self._signer = None
                return None, err or "取签名密钥失败"

        uid = pc.get("userId") or cred.get("userId") or ""
        out = {}
        errs = []
        for key, path in API_PATHS.items():
            url = PLATFORM + path + (("?userId=" + uid) if uid else "")
            st, body = signed_get(opener, url, self._signer)
            d = _parse(body)
            if d is None:
                errs.append("%s HTTP %s %s" % (key, st, (body or "")[:80]))
                continue
            out[key] = d
        if not out:
            return None, "平台接口失败: " + ("; ".join(errs) or "无数据")
        return out, None

    # -- 快照 --

    def get(self, force=False):
        now = time.time()
        if not force and self._cache and now - self._cache_at < self._ttl:
            return self._cache

        snap = {"error": None, "percent": None, "percent_used": None,
                "reset_date": None, "plan": None, "used": self.session_tokens() or None,
                "source": "local", "user_id": None, "region": None,
                "balance": None, "total_token": None, "cost": None}

        acct = self.account_info()
        snap["user_id"] = acct.get("user_id")
        snap["region"] = acct.get("region")

        # A：先问 MiMo 自己
        data, err = self._via_mimo()
        if data:
            snap["source"] = "mimo"
            if data.get("percent") is not None:
                snap["percent"] = data["percent"]
                snap["percent_used"] = max(0.0, 100.0 - float(data["percent"]))
            if data.get("reset_date"):
                snap["reset_date"] = data["reset_date"]
            if data.get("plan"):
                snap["plan"] = data["plan"]
            if data.get("plan_status"):
                snap["plan_status"] = data["plan_status"]
            if data.get("plan_end"):
                snap["plan_end"] = data["plan_end"]
            if data.get("plan_reset"):
                snap["plan_reset"] = data["plan_reset"]
            if data.get("auth"):
                snap["auth"] = data["auth"]
        if err:
            snap["error"] = err

        # B：补充余额 / 套餐 / 用量明细
        try:
            pdata, perr = self._via_platform()
        except Exception as e:
            pdata, perr = None, str(e)
        if pdata:
            snap["source"] = "platform" if snap["source"] == "local" \
                else snap["source"] + "+platform"
            usage = pdata.get("usage") or {}
            tu = usage.get("tokenUsage") or {}
            if tu.get("totalToken") is not None:
                snap["total_token"] = tu.get("totalToken")
            cu = usage.get("costUsage") or {}
            if cu.get("totalCost") is not None:
                snap["cost"] = cu.get("totalCost")
            rl = usage.get("accountRateLimit") or {}
            if rl.get("tpm"):
                snap["tpm"] = rl.get("tpm")

            pu = pdata.get("plan_usage") or {}
            used_pct = None
            for block in ("usage", "monthUsage"):
                b = pu.get(block) or {}
                p = b.get("percent")
                if isinstance(p, (int, float)):
                    used_pct = float(p)
                    for it in (b.get("items") or []):
                        if it.get("limit"):
                            snap["plan_limit"] = it.get("limit")
                            snap["plan_used"] = it.get("used")
                    break
            if used_pct is not None:
                snap["percent_used"] = used_pct
                if snap.get("percent") is None:
                    snap["percent"] = max(0.0, (1.0 - used_pct) * 100.0)

            pd = pdata.get("plan_detail") or {}
            if pd.get("planName") and not snap.get("plan"):
                snap["plan"] = pd.get("planName")
            if pd.get("currentPeriodEnd") and not snap.get("reset_date"):
                snap["reset_date"] = pd.get("currentPeriodEnd")
            if pd.get("expired") is not None:
                snap["expired"] = pd.get("expired")

            bal = pdata.get("balance") or {}
            if bal.get("balance") is not None:
                snap["balance"] = bal.get("balance")
                snap["currency"] = bal.get("currency") or "CNY"

            prof = pdata.get("profile") or {}
            if prof.get("userId"):
                snap["user_id"] = prof.get("userId")
            if prof.get("phone"):
                snap["phone"] = prof.get("phone")
            if not snap.get("error"):
                snap["error"] = None
        elif perr and snap.get("source") == "local":
            snap["error"] = snap.get("error") or perr

        self._cache = snap
        self._cache_at = now
        return snap


def _try_read(path):
    try:
        read_cookie_db(path)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    print("== cookie 库 ==")
    for p in cookie_db_paths():
        print("  ", p, "(可读)" if _try_read(p) else "(被锁)")
    print("\n== 抓取凭据 ==")
    cred = capture_credentials()
    if cred:
        print("  成功 userId=%s passToken=%s..."
              % (cred["userId"], cred["passToken"][:10]))
        if not load_cache():
            save_cache(cred)
    else:
        print("  失败（MiMo 正在运行，cookie 库被排他锁）")
    print("\n== 额度快照 ==")
    print(json.dumps(QuotaClient().get(force=True), ensure_ascii=False, indent=2))
