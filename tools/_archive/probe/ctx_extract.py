"""Extract bounded context windows around keyword hits from large bundled JS files.

Bundled/minified files are single huge lines, so line-based grep is useless.
This writes small, readable extracts instead.

Usage:
    python ctx_extract.py <file> <keyword> [keyword ...] [--window 900] [--max 4]
"""

import argparse
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("keywords", nargs="+")
    p.add_argument("--window", type=int, default=900)
    p.add_argument("--max", type=int, default=4)
    a = p.parse_args()

    with open(a.file, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    for kw in a.keywords:
        hits = 0
        for m in re.finditer(re.escape(kw), text):
            lo = max(0, m.start() - a.window // 3)
            hi = min(len(text), m.end() + a.window)
            print(f"\n{'=' * 90}")
            print(f"### {kw} @ {m.start()}")
            print("=" * 90)
            print(text[lo:hi])
            hits += 1
            if hits >= a.max:
                break
        if hits == 0:
            print(f"\n### {kw}: no match")


if __name__ == "__main__":
    main()
