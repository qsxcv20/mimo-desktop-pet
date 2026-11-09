#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
mimo_link.py — MiMo Desktop 本地 API 客户端（纯标准库，无 GUI 依赖，可单测）

本地 API 契约（逆向自 main~DAq2tHkd.mjs 的路由表 $Z()）：
    GET  /v1/health
    GET  /v1/sessions?limit=N
    GET  /v1/sessions/<sid>/messages
    GET  /v1/sessions/<sid>/events        <- SSE 事件流
    POST /v1/sessions/<sid>/turns
鉴权：Authorization: Bearer <token>，token/port 来自 userData\desktop-api.json
Host 必须是 127.0.0.1:<port> 或 localhost:<port>，否则 403 forbidden-host
"""

import json
import os
import ssl
import threading
import time
import urllib.error
import urllib.request

DESKTOP_API_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "Xiaomi MiMo", "desktop-api.json"
)


class MimoError(Exception):
    pass


def load_credentials(api_file=DESKTOP_API_FILE):
    """读取 userData/desktop-api.json -> (port, token)"""
    if not os.path.isfile(api_file):
        raise MimoError("找不到 %s（MiMo Desktop 可能没启动）" % api_file)
    try:
        with open(api_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        raise MimoError("desktop-api.json 解析失败: %s" % e)
    port = cfg.get("port")
    token = cfg.get("token")
    if not port or not token:
        raise MimoError("desktop-api.json 缺少 port/token")
    return int(port), token


class MimoClient(object):
    def __init__(self, api_file=DESKTOP_API_FILE, timeout=10):
        self.api_file = api_file
        self.timeout = timeout
        self._port = None
        self._token = None

    # ---------- 底层 ----------

    def _creds(self, refresh=False):
        if refresh or self._port is None:
            self._port, self._token = load_credentials(self.api_file)
        return self._port, self._token

    def base_url(self):
        port, _ = self._creds()
        return "http://127.0.0.1:%d" % port

    def refresh_creds(self):
        """强制重新读 desktop-api.json。

        MiMo 重启会换端口和 token（实测 52848 -> 56551）。SSE 流断开
        走的是 stream_events，不经过 _request 的异常清理路径，缓存的
        旧凭据会一直留着 -> 下一轮请求打在一个没人听的端口上，
        得等 10 秒超时才恢复。重连时主动刷新就不用等。
        """
        self._port = None
        self._token = None
        return self._creds()

    def _request(self, path, method="GET", body=None, timeout=None):
        port, token = self._creds()
        url = "http://127.0.0.1:%d%s" % (port, path)
        data = None
        headers = {
            "Authorization": "Bearer " + token,
            "Host": "127.0.0.1:%d" % port,   # forbidden-host 校验
            "Accept": "application/json",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            raise MimoError("HTTP %d %s %s" % (e.code, method, path))
        except Exception as e:
            # 连不上 -> 多半是 MiMo 重启换了端口/token。
            # 丢弃缓存的凭据，让下一次调用重新读 desktop-api.json。
            self._port = None
            self._token = None
            raise MimoError("%s %s 失败: %s" % (method, path, e))
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return raw.decode("utf-8", "replace")

    # ---------- API ----------

    def health(self):
        return self._request("/v1/health")

    def sessions(self, limit=20):
        data = self._request("/v1/sessions?limit=%d" % int(limit))
        return data if isinstance(data, list) else []

    def active_session(self):
        """最近更新的会话 = 视作当前活动会话。"""
        items = self.sessions(limit=20)
        if not items:
            return None

        def updated(s):
            try:
                return int((s.get("time") or {}).get("updated") or 0)
            except Exception:
                return 0

        items.sort(key=updated, reverse=True)
        return items[0]

    def messages(self, session_id, directory=None):
        path = "/v1/sessions/%s/messages" % session_id
        if directory:
            path += "?dir=" + urllib.request.quote(directory)
        return self._request(path)

    def stream_events(self, session_id, directory=None, stop_event=None):
        """SSE 事件流生成器。产出 (event_type, payload_dict)。

        stop_event: 可选的 threading.Event，置位后尽快退出。
        """
        port, token = self._creds()
        path = "/v1/sessions/%s/events" % session_id
        if directory:
            path += "?dir=" + urllib.request.quote(directory)
        url = "http://127.0.0.1:%d%s" % (port, path)
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": "Bearer " + token,
                "Host": "127.0.0.1:%d" % port,
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
            },
        )
        ev_type = None
        with urllib.request.urlopen(req, timeout=None) as resp:
            for raw in resp:
                if stop_event is not None and stop_event.is_set():
                    return
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                if not line:
                    ev_type = None
                    continue
                if line.startswith(":"):
                    continue          # ping / 注释
                if line.startswith("event:"):
                    ev_type = line[6:].strip()
                elif line.startswith("data:"):
                    payload = line[5:].strip()
                    try:
                        obj = json.loads(payload) if payload else {}
                    except Exception:
                        obj = {"_raw": payload}
                    if ev_type:
                        if isinstance(obj, dict):
                            obj.setdefault("type", ev_type)
                        yield (ev_type, obj)


class PetBrain(object):
    """把 MiMo 事件翻译成桌宠表情状态。

    状态：idle / happy / think / tired
    """

    STATES = ("idle", "happy", "think", "tired")

    # 忙碌超过该秒数 -> tired（长时间运行/疑似卡住）
    BUSY_TIRED_AFTER = 150
    # happy 表情保持时长（秒）
    HAPPY_HOLD = 2.6

    def __init__(self):
        self.state = "idle"
        self.manual = None          # 手动锁定的表情，None = 自动
        self.session_id = None
        self.busy_since = None
        self.happy_until = 0.0
        self.last_event = None
        self.updated_at = 0.0
        self.error_state = False
        self.log = []

    # ---- 事件处理 ----

    def handle(self, ev_type, data):
        now = time.time()
        self.last_event = ev_type
        self.updated_at = now
        ev = (ev_type or "").lower()
        payload = data if isinstance(data, dict) else {}
        changed = False

        if ev == "busy":
            # 新的一轮任务开始 -> 思考脸
            self.busy_since = now
            self.error_state = False
            changed = self._set("think")

        elif ev == "text-partial":
            # 正在流式输出 -> 保持思考脸
            changed = self._set("think")

        elif ev == "ui":
            ui = payload.get("ui") or {}
            kind = str(ui.get("kind") or "")
            if kind == "error":
                self.error_state = True
                changed = self._set("tired")
            elif kind == "usage":
                # 本轮 token 结算 = 任务完成
                self.happy_until = now + self.HAPPY_HOLD
                changed = self._set("happy")

        elif ev == "idle":
            if self.error_state:
                changed = self._set("tired")
            elif self.state in ("think", "tired") or self.busy_since:
                # busy/text-partial 之后紧跟 idle = 这一轮干完了
                self.happy_until = now + self.HAPPY_HOLD
                changed = self._set("happy")
            else:
                changed = self._set("idle")
            self.busy_since = None

        elif "permission" in ev:
            changed = self._set("tired")

        elif "error" in ev:
            self.error_state = True
            changed = self._set("tired")

        elif ev.startswith("message"):
            info = payload.get("info") or {}
            tinfo = info.get("time") or {}
            if info.get("role") == "assistant" and tinfo.get("completed"):
                self.happy_until = now + self.HAPPY_HOLD
                changed = self._set("happy")
            elif ev == "message.removed":
                changed = self._set("idle")

        if changed:
            self.log.append((round(now, 2), ev_type, self.state))

        return self.state

    def _set(self, state):
        if self.state == state:
            return False
        self.state = state
        return True

    # ---- 定时维护 ----

    def tick(self, now=None):
        """由定时器调用：处理 happy 超时回落、busy 超时转 tired、手动锁释放。"""
        now = now or time.time()
        if self.manual:
            return self.state
        if self.state == "happy" and now >= self.happy_until:
            self.state = "think" if self.busy_since else "idle"
            return True
        if self.state == "think" and self.busy_since and \
                (now - self.busy_since) > self.BUSY_TIRED_AFTER:
            self.state = "tired"
            return True
        return False

    def set_manual(self, state):
        if state in (None, "auto"):
            self.manual = None
            return self.state
        if state not in self.STATES:
            raise ValueError("未知表情: %s" % state)
        self.manual = state
        self.state = state
        return state

    def release_manual(self):
        self.manual = None
        return self.state


class MimoListener(threading.Thread):
    """后台线程：持续订阅活动会话的 SSE，把事件喂给 PetBrain。"""

    daemon = True

    def __init__(self, brain, client=None, on_change=None, poll=4.0,
                 on_event=None):
        threading.Thread.__init__(self)
        self.brain = brain
        self.client = client or MimoClient()
        self.on_change = on_change
        self.on_event = on_event
        self.poll = poll
        self.stop_event = threading.Event()
        self.connected = False
        self.session_id = None
        self.last_error = None

    def run(self):
        while not self.stop_event.is_set():
            try:
                # 每次重连都刷新凭据：MiMo 重启会换端口和 token
                self.client.refresh_creds()
                sid = self.client.active_session()
                if not sid:
                    self.last_error = "没有可用会话"
                    self._sleep(self.poll)
                    continue
                new_id = sid.get("id")
                if new_id != self.session_id:
                    self.session_id = new_id
                    self.brain.session_id = new_id
                directory = sid.get("directory")
                self.connected = True
                self.last_error = None      # 连上了就别留着上次的报错
                for ev_type, payload in self.client.stream_events(
                    new_id, directory=directory, stop_event=self.stop_event
                ):
                    if self.stop_event.is_set():
                        break
                    self.brain.handle(ev_type, payload)
                    if self.on_event:
                        try:
                            self.on_event(ev_type, payload)
                        except Exception:
                            pass
                    if self.on_change:
                        try:
                            self.on_change(self.brain.state)
                        except Exception:
                            pass
            except Exception as e:
                self.connected = False
                self.last_error = str(e)
                self._sleep(1.5)
        self.connected = False

    def _sleep(self, seconds):
        self.stop_event.wait(seconds)

    def stop(self):
        self.stop_event.set()
