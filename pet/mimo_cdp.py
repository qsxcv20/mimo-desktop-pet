#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
mimo_cdp.py — 通过 Chrome DevTools Protocol 调 MiMo 渲染层里的 window.mimo 桥接。

为什么需要它：
    小米账号的 passToken 已被账号服务器判定失效（serviceLogin 返回 70016），
    我们无法自己换到平台票据；而平台开放接口 /api/v1/* 现在还要求
    X-Sign / X-Timestamp / X-Key-Epoch 签名头。
    唯一可靠的取数方式 = 让 MiMo 自己查：
        window.mimo.getUserUsage()       -> {ok, usage:{percent, resetDate}}
        window.mimo.getUserSubscription() -> {ok, data:{...}}
    这两个走的是主进程里带账号会话的 session.fetch，鉴权天然正确。

前提：MiMo 必须以 --remote-debugging-port=<port> 启动（仅监听 127.0.0.1）。

用法:
    from mimo_cdp import MiMoCDP
    c = MiMoCDP()
    print(c.available())
    print(c.get_user_usage())
"""

import json
import os
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass  # pythonw.exe 下 sys.stdout 是 None

DEFAULT_PORT = int(os.environ.get("MIMO_CDP_PORT", "9333"))


class MiMoCDP(object):
    def __init__(self, port=DEFAULT_PORT, host="127.0.0.1"):
        self.port = int(port)
        self.host = host

    # ---------------------------------------------------------- 基础

    def _http(self, path, timeout=3):
        url = "http://%s:%d%s" % (self.host, self.port, path)
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read(400000).decode("utf-8", "replace"))

    def available(self):
        """调试端口是否开着。"""
        try:
            self._http("/json/version", timeout=2)
            return True
        except Exception:
            return False

    def targets(self):
        try:
            lst = self._http("/json/list", timeout=3)
            return lst if isinstance(lst, list) else []
        except Exception:
            return []

    def pick_target(self):
        """挑 MiMo 主窗口的渲染层 target。"""
        best = None
        for t in self.targets():
            if t.get("type") != "page":
                continue
            url = t.get("url") or ""
            title = t.get("title") or ""
            if not t.get("webSocketDebuggerUrl"):
                continue
            # 主窗口：file:// 或 app:// 之类的本地页面
            score = 0
            if "Xiaomi MiMo" in title or "MiMo" in title:
                score += 2
            if url.startswith("file://") or url.startswith("app://") \
                    or url.startswith("http://localhost") \
                    or url.startswith("http://127.0.0.1"):
                score += 1
            if not score:
                continue
            if best is None or score > best[0]:
                best = (score, t)
        return best[1] if best else None

    def pick_login_target(self):
        """挑 account.xiaomi.com 的 SSO 登录页 target（MiMo 内嵌的隐藏 WebView）。"""
        for t in self.targets():
            if t.get("type") != "page":
                continue
            url = t.get("url") or ""
            if "account.xiaomi.com" in url and t.get("webSocketDebuggerUrl"):
                return t
        return None

    # ---------------------------------------------------------- 调用

    def evaluate(self, expression, timeout=10, target=None):
        """在渲染层里执行表达式（支持 awaitPromise）。返回 JS 值。"""
        tgt = target or self.pick_target()
        if not tgt:
            raise RuntimeError("找不到 MiMo 渲染层 target")
        ws_url = tgt["webSocketDebuggerUrl"]
        try:
            import websocket
        except ImportError:
            raise RuntimeError("缺少 websocket-client 库")

        ws = websocket.create_connection(ws_url, timeout=timeout,
                                         suppress_origin=True)
        try:
            ws.send(json.dumps({
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": expression,
                    "awaitPromise": True,
                    "returnByValue": True,
                    "userGesture": True,
                },
            }))
            deadline = timeout
            while deadline > 0:
                ws.settimeout(deadline)
                raw = ws.recv()
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", "replace")
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                if msg.get("id") != 1:
                    continue
                res = msg.get("result") or {}
                if res.get("exceptionDetails"):
                    det = res["exceptionDetails"]
                    text = (det.get("exception") or {}).get("description") \
                        or det.get("text") or "JS 异常"
                    raise RuntimeError(str(text)[:300])
                return (res.get("result") or {}).get("value")
            raise RuntimeError("CDP 超时")
        finally:
            try:
                ws.close()
            except Exception:
                pass

    # ---------------------------------------------------------- 业务

    def get_user_usage(self):
        """-> {'percent':剩余%, 'resetDate':...} 或 None"""
        v = self.evaluate("(async()=>{try{return await window.mimo.getUserUsage()}"
                           "catch(e){return {ok:false,error:String(e)}}})()")
        if isinstance(v, dict) and v.get("ok"):
            return v.get("usage") or {}
        return None

    def raw_user_usage(self):
        """原始返回值（含 ok / kind / error），用来区分「未登录」和「无有效订阅」。"""
        v = self.evaluate("(async()=>{try{return await window.mimo.getUserUsage()}"
                           "catch(e){return {ok:false,kind:'exception',error:String(e)}}})()")
        return v if isinstance(v, dict) else None

    def raw_user_subscription(self):
        """原始返回值：{ok, data:{groupCode, current, subscriptions:[...]}}"""
        v = self.evaluate("(async()=>{try{return await window.mimo.getUserSubscription()}"
                           "catch(e){return {ok:false,kind:'exception',error:String(e)}}})()")
        return v if isinstance(v, dict) else None

    def get_user_subscription(self):
        v = self.evaluate("(async()=>{try{return await window.mimo.getUserSubscription()}"
                           "catch(e){return {ok:false,error:String(e)}}})()")
        if isinstance(v, dict) and v.get("ok"):
            return v.get("data") or {}
        return None

    def get_auth_snapshot(self):
        v = self.evaluate("(async()=>{try{return await window.mimo.userAuthSnapshot()}"
                           "catch(e){return null}})()")
        return v


if __name__ == "__main__":
    c = MiMoCDP()
    print("调试端口 %d 可用: %s" % (c.port, c.available()))
    if c.available():
        for t in c.targets():
            print("  target: %-8s %-28s %s" % (t.get("type"),
                                              (t.get("title") or "")[:28],
                                              (t.get("url") or "")[:90]))
        print("\ngetUserUsage ->", json.dumps(c.get_user_usage(),
                                            ensure_ascii=False))
        print("getUserSubscription ->",
              json.dumps(c.get_user_subscription(), ensure_ascii=False)[:500])
