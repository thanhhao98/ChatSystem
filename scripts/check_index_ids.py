#!/usr/bin/env python3
"""results/INDEX.md: ids R### must be unique and strictly increasing in table order (R000 = example row).

Usage: python scripts/check_index_ids.py [results/INDEX.md]   -> exit 0 OK, 1 otherwise.
"""
import re
import sys


def main(path: str) -> int:
    ids = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^\|\s*R(\d{3,})\s*\|", line)
            if m:
                ids.append(int(m.group(1)))
    bad = [(a, b) for a, b in zip(ids, ids[1:]) if b <= a]
    if bad:
        print(f"check_index_ids: FAIL {path}: ids not strictly increasing at " +
              ", ".join(f"R{a:03d}->R{b:03d}" for a, b in bad))
        return 1
    last = f"R{ids[-1]:03d}" if ids else "-"
    print(f"check_index_ids: OK {path}: {len(ids)} rows, last {last}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "results/INDEX.md"))
