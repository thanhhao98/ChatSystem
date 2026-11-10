
#!/usr/bin/env python3
"""
Task 5 [D-V5] - Benchmark Integrity Audit

Kiểm tra:
1. eval_v1.json: 500 records
2. eval_human_core.jsonl: 150 records
3. Cú pháp JSON/JSONL
4. ID trùng lặp hoặc không hợp lệ
5. SHA256 Local vs Git HEAD
6. SHA256 eval_v1 vs frozen baseline
7. SHA256 human_core vs baseline được duyệt (nếu có)

READ-ONLY: Không chỉnh sửa dữ liệu.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


EXPECTED_EVAL_SHA256 = (
    "04aec49d857248e7421bb3919b7e5ab8988ea1a15f2443e30f6e7d2b0a9eaf52"
)

# Snapshot đã quan sát, chưa phải baseline chính thức
OBSERVED_CORE_SHA256 = (
    "41c7e7bd1bc04af86aaf748382b3a2a405f7c91a26e66d8ff7d74a7feb8a1106"
)

FILES = {
    "data/sgod/eval_v1.json": 500,
    "data/sgod/eval_human_core.jsonl": 150,
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def find_repo_root():
    for start in [Path(__file__).resolve().parent, Path.cwd()]:
        for path in [start, *start.parents]:
            if (path / ".git").exists() and (path / "data/sgod").is_dir():
                return path
    raise RuntimeError("Không tìm thấy repository ChatSystem")


def read_git_bytes(root, filename):
    result = subprocess.run(
        ["git", "show", f"HEAD:{filename}"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return result.stdout


def load_records(data, filename):
    text = data.decode("utf-8-sig")

    if filename.endswith(".jsonl"):
        records = []
        for line_num, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                raise ValueError(f"JSONL có dòng trống tại dòng {line_num}")
            records.append(json.loads(line))
    else:
        records = json.loads(text)

    if not isinstance(records, list):
        raise ValueError("Dữ liệu phải là một danh sách records")

    if any(not isinstance(row, dict) or not row for row in records):
        raise ValueError("Có record không phải JSON object hợp lệ")

    return records


def check_duplicate_ids(records):
    ids = [row["id"] for row in records if "id" in row]

    if not ids:
        return True, "Không có trường ID để kiểm tra"

    if len(ids) != len(records):
        return False, "Một số record thiếu ID"

    if any(
        not isinstance(i, (str, int)) or not str(i).strip()
        for i in ids
    ):
        return False, "ID rỗng hoặc sai kiểu"

    duplicates = [
        value
        for value, count in Counter(ids).items()
        if count > 1
    ]

    if duplicates:
        return False, f"ID trùng: {duplicates[:10]}"

    return True, "ID hợp lệ, không trùng lặp"


def check_eval_baseline(root, actual_hash):
    checksum_file = root / "data/sgod/eval_v1.sha256"
    text = checksum_file.read_text(encoding="utf-8-sig")

    matches = re.findall(r"\b[a-fA-F0-9]{64}\b", text)

    if len(matches) != 1:
        return False, "File baseline không chứa đúng một SHA256"

    baseline = matches[0].lower()

    passed = (
        baseline == EXPECTED_EVAL_SHA256
        and actual_hash == baseline
    )

    return passed, f"Baseline: {baseline}"


def test_benchmark(human_core_baseline=None):
    root = find_repo_root()
    failures = []
    total_records = 0

    print("=" * 65)
    print("TASK 5 [D-V5] - BENCHMARK INTEGRITY TEST")
    print("=" * 65)
    print(f"Repository: {root}")
    print("Mode: READ-ONLY")

    for filename, expected_count in FILES.items():
        print(f"\n{'-' * 65}")
        print(f"FILE: {filename}")
        print("-" * 65)

        try:
            local_bytes = (root / filename).read_bytes()
            git_bytes = read_git_bytes(root, filename)

            records = load_records(local_bytes, filename)
            total_records += len(records)

            local_hash = sha256(local_bytes)
            git_hash = sha256(git_bytes)

            checks = {
                "JSON/JSONL syntax": True,
                "Record count": len(records) == expected_count,
                "Local == Git bytes": local_bytes == git_bytes,
            }

            id_pass, id_message = check_duplicate_ids(records)
            checks["Unique IDs"] = id_pass

            print(f"Records:      {len(records)}/{expected_count}")
            print(f"Local SHA256: {local_hash}")
            print(f"Git SHA256:   {git_hash}")
            print(f"ID check:     {id_message}")

            if filename.endswith("eval_v1.json"):
                checks["Frozen SHA256"] = (
                    local_hash == EXPECTED_EVAL_SHA256
                )

                baseline_pass, baseline_message = check_eval_baseline(
                    root, local_hash
                )
                checks["Baseline checksum"] = baseline_pass
                print(baseline_message)

            else:
                snapshot_match = local_hash == OBSERVED_CORE_SHA256

                print(f"Observed snapshot: {OBSERVED_CORE_SHA256}")
                print(f"Snapshot matches:  {snapshot_match}")

                if human_core_baseline:
                    checks["Approved human_core SHA256"] = (
                        local_hash == human_core_baseline.lower()
                    )
                else:
                    print(
                        "PENDING | human_core chưa có "
                        "baseline độc lập được phê duyệt"
                    )

            print("\nCHECK RESULTS:")

            for name, passed in checks.items():
                status = "PASS" if passed else "FAIL"
                print(f"  [{status}] {name}")

                if not passed:
                    failures.append(f"{filename}: {name}")

        except Exception as exc:
            print(f"[FAIL] {type(exc).__name__}: {exc}")
            failures.append(f"{filename}: {exc}")

    print("\n" + "=" * 65)
    print("FINAL RESULT")
    print("=" * 65)

    print(f"Total records parsed: {total_records}")

    if failures:
        print(f"FAIL - {len(failures)} check(s) failed")

        for failure in failures:
            print(f"  - {failure}")

        return 1

    print("PASS - All executed integrity checks passed")

    if not human_core_baseline:
        print("PENDING - human_core frozen baseline not independently verified")

    print("NOTE - Leakage scan is a separate Task 5 check")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--human-core-sha256",
        help="SHA256 chính thức của human_core đã được nhóm phê duyệt",
    )

    args = parser.parse_args()

    if args.human_core_sha256 and not re.fullmatch(
        r"[0-9a-fA-F]{64}", args.human_core_sha256
    ):
        parser.error("SHA256 phải có đúng 64 ký tự hexadecimal")

    sys.exit(test_benchmark(args.human_core_sha256))
