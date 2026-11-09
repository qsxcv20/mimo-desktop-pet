#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""probe_engine_api.py — 找 engine 本地服务端口并探测额度类端点。"""
import json
import os
import re
import socket
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def listening_ports():
    """用 netstat 找本机 LISTENING 端口 + 归属进程名。"""
    import subprocess
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True,
                         text=True, errors="replace").stdout
    pid2name = {}
    try:
        out2 = subprocess.run(["tasklist", "/FO", "CSV"], capture_output=True,
                              text=True, errors="replace").stdout
        for line in out2.splitlines()[1:]:
            parts = [x.strip('"') for x in line.split('","')]
            if len(parts) >= 2:
                try:
                    pid2name[int(parts[1])] = parts[0]
                except ValueError:
                    pass
    except Exception:
        pass
    res = []
    for line in out.splitlines():
        m = re.match(r"\s*TCP\s+(\S+):(\d+)\s+(\S+)\s+LISTENING\s+(\d+)", line)
        if m:
            res.append((int(m.group(2)), int(m.group(4)),
                        pid2name.get(int(m.group(4)), "?")))
    return res


def probe(port, path, timeout=3):
    url = "http://127.0.0.1:%d%s" % (port, path)
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)


ports = listening_ports()
print("=== LISTENING 端口 ===")
interesting = []
for port, pid, name in sorted(ports):
    if port in (135, 139, 445, 5040, 5051, 5357, 3580, 3581, 3582):
        continue
    print("  %-6d pid=%-7d %s" % (port, pid, name))
    interesting.append((port, pid, name))

CANDIDATES = ["/api/meta", "/api/usage", "/api/balance", "/api/v1/usage",
              "/api/v1/balance", "/api/v1/tokenPlan/detail",
              "/api/v1/tokenPlan/usage", "/api/v1/userProfile",
              "/api/events", "/api/messages", "/health", "/meta",
              "/api/account", "/api/quota", "/api/credit"]

print("\n=== 逐端口探测 ===")
for port, pid, name in interesting:
    for path in CANDIDATES:
        st, body = probe(port, path, timeout=2)
        if st and st != 404 and st is not None:
            short = body if len(body) < 600 else body[:600] + " ...(截断)"
            print("\n>>> %s:%d %s -> %s" % (name, port, path, st))
            print(short)
