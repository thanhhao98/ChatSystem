
"""
Task 5 [D-V5] - Yield & Consensus Audit
READ-ONLY: Không chỉnh sửa dataset.

Kiểm tra:
- Số lượng Raw, Labeled, Verified, Quarantine
- Yield toàn bộ và theo seed_tool
- Liên kết ID giữa các stage
- Số proposal/model thực tế
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/sgod"

FILES = [
    "raw.json",
    "labeled.json",
    "verified.json",
    "quarantine.json",
    "label_report.json",
]


def load_rows(filename):
    path = DATA / filename
    rows = json.loads(path.read_text(encoding="utf-8-sig"))

    if not isinstance(rows, list):
        raise ValueError(f"{filename} must be a JSON array")

    if any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{filename} contains non-object rows")

    return rows


def normalized_id(value):
    if not isinstance(value, str):
        return value
    if value.startswith("SC"):
        return "SN" + value[2:]
    return value


def audit():
    print("=" * 65)
    print("TASK 5 - YIELD & CONSENSUS AUDIT")
    print("=" * 65)

    try:
        datasets = {
            name: load_rows(name)
            for name in FILES
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("FAIL | Cannot load data:", exc)
        return 1

    raw = datasets["raw.json"]
    labeled = datasets["labeled.json"]
    verified = datasets["verified.json"]
    quarantine = datasets["quarantine.json"]
    reports = datasets["label_report.json"]

    print("\n[1] ROWS PER STAGE")
    for name, rows in datasets.items():
        print(f"{name:22} {len(rows):5}")

    if not raw:
        print("FAIL | Raw dataset is empty")
        return 1

    yield_rate = len(verified) / len(raw)

    print("\n[2] OVERALL YIELD")
    print(f"Raw:       {len(raw)}")
    print(f"Verified:  {len(verified)}")
    print(f"Yield:     {yield_rate:.2%}")
    print(f"Threshold: 45%")

    print(
        "PASS" if yield_rate >= 0.45 else "FAIL",
        "| Yield threshold"
    )

    # Đối chiếu ID các stage
    raw_ids = [normalized_id(r.get("id")) for r in raw]
    labeled_ids = [r.get("id") for r in labeled]
    verified_ids = [r.get("id") for r in verified]

    duplicate_raw = len(raw_ids) != len(set(raw_ids))
    duplicate_labeled = len(labeled_ids) != len(set(labeled_ids))
    duplicate_verified = len(verified_ids) != len(set(verified_ids))

    raw_set = set(raw_ids)
    labeled_set = set(labeled_ids)
    verified_set = set(verified_ids)

    invalid_labeled = labeled_set - raw_set
    invalid_verified = verified_set - labeled_set

    print("\n[3] DATA LINEAGE")
    print("Duplicate raw IDs:", duplicate_raw)
    print("Duplicate labeled IDs:", duplicate_labeled)
    print("Duplicate verified IDs:", duplicate_verified)
    print("Labeled not in Raw:", len(invalid_labeled))
    print("Verified not in Labeled:", len(invalid_verified))

    lineage_ok = not (
        duplicate_raw or duplicate_labeled or duplicate_verified
        or invalid_labeled or invalid_verified
    )

    # Tính Yield theo cùng nhóm seed_tool ban đầu
    raw_by_tool = Counter(
        r.get("seed_tool", "UNKNOWN")
        for r in raw
    )

    raw_seed_by_id = {
        normalized_id(r.get("id")): r.get("seed_tool", "UNKNOWN")
        for r in raw
    }

    verified_by_tool = Counter(
        raw_seed_by_id.get(r.get("id"), "UNMATCHED")
        for r in verified
    )

    print("\n[4] YIELD BY ORIGINAL SEED TOOL")
    print(f"{'TOOL':35} {'RAW':>6} {'VERIFIED':>9} {'YIELD':>9}")

    for tool in sorted(raw_by_tool):
        r = raw_by_tool[tool]
        v = verified_by_tool[tool]
        rate = v / r if r else 0
        print(f"{tool:35} {r:6} {v:9} {rate:9.2%}")

    print("\n[5] MODEL CONSENSUS")

    proposal_counts = Counter()
    model_counts = Counter()
    unsupported_reports = 0

    for row in reports:
        proposals = row.get("proposals", [])

        if not isinstance(proposals, list):
            unsupported_reports += 1
            continue

        proposal_counts[len(proposals)] += 1

        for proposal in proposals:
            if isinstance(proposal, (list, tuple)) and proposal:
                model_counts[str(proposal[0])] += 1

    print("Total label reports:", len(reports))
    print("Proposals per row:", dict(sorted(proposal_counts.items())))
    print("Models:", dict(model_counts))
    print("Invalid proposal structures:", unsupported_reports)

    multi_model_rows = sum(
        count
        for n, count in proposal_counts.items()
        if n >= 2
    )

    print("Rows with 2+ proposals:", multi_model_rows)

    # Số proposal >= 2 chưa chứng minh model độc lập
    distinct_model_rows = 0
    for row in reports:
        proposals = row.get("proposals", [])
        if not isinstance(proposals, list):
            continue
        names = {
            str(p[0])
            for p in proposals
            if isinstance(p, (list, tuple)) and p
        }
        if len(names) >= 2:
            distinct_model_rows += 1

    print("Rows with 2+ distinct models:", distinct_model_rows)

    print("\n[6] KNOWN LEAKAGE CASE")
    target = "SN0380008"
    found = [r for r in verified if r.get("id") == target]
    print("SN0380008 in Verified:", bool(found))

    print("\n[7] SUMMARY")
    print("Lineage:", "PASS" if lineage_ok else "FAIL")
    print("Yield:", "PASS" if yield_rate >= 0.45 else "FAIL")
    print(
        "Multi-model evidence:",
        "PRESENT" if distinct_model_rows == len(reports) and reports
        else "INSUFFICIENT"
    )
    print("Leakage: must run independent scanner")

    return 0 if lineage_ok and yield_rate >= 0.45 else 1


if __name__ == "__main__":
    sys.exit(audit())
