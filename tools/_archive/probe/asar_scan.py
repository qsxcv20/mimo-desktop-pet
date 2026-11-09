"""Scan an Electron app.asar for keyword hits and print surrounding context.

app.asar stores file contents uncompressed, so the pet engine's manifest
schema and state mapping are visible as plain text inside the archive.

Usage:
    python asar_scan.py <app.asar> <keyword> [keyword ...] [--context 2500]
"""

import argparse
import json
import struct
import sys


def read_header(data):
    header_size = struct.unpack("<I", data[4:8])[0]
    header_buf = data[8:8 + header_size]
    str_len = struct.unpack("<I", header_buf[4:8])[0]
    return json.loads(header_buf[8:8 + str_len].decode("utf-8"))


def walk(node, prefix=""):
    files = node.get("files", {})
    for name, meta in files.items():
        path = f"{prefix}{name}"
        if "files" in meta:
            yield from walk(meta, path + "/")
        else:
            yield path, meta


def main():
    p = argparse.ArgumentParser()
    p.add_argument("asar")
    p.add_argument("keywords", nargs="+")
    p.add_argument("--context", type=int, default=2500)
    p.add_argument("--list", action="store_true", help="only list matching paths")
    a = p.parse_args()

    with open(a.asar, "rb") as f:
        data = f.read()

    header = read_header(data)
    base = 8 + struct.unpack("<I", data[4:8])[0]

    if a.list:
        for path, meta in walk(header):
            if any(k.lower() in path.lower() for k in a.keywords):
                print(f"{meta.get('size', 0):>10}  {path}")
        return

    for path, meta in walk(header):
        offset = meta.get("offset")
        if offset is None:
            continue
        start = base + int(offset)
        blob = data[start:start + meta.get("size", 0)]
        for kw in a.keywords:
            kb = kw.encode("utf-8")
            idx = blob.find(kb)
            if idx == -1:
                continue
            lo = max(0, idx - a.context // 3)
            hi = min(len(blob), idx + a.context)
            snippet = blob[lo:hi].decode("utf-8", errors="replace")
            print(f"\n{'=' * 100}")
            print(f"### {path}  [keyword: {kw}]")
            print("=" * 100)
            print(snippet)


if __name__ == "__main__":
    main()
