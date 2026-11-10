
"""
Task 5 [D-V5] - Anti-Leakage Configuration Test

Kiểm tra:
- Leakage threshold = 0.65
- Đủ 2 benchmark
- Đường dẫn benchmark hợp lệ
- Không chỉnh sửa cấu hình hoặc dataset
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "datagen/config_sgod.py"

EXPECTED_THRESHOLD = 0.65
EXPECTED_EVAL_SETS = {
    "data/sgod/eval_v1.json",
    "data/sgod/eval_human_core.jsonl",
}


def read_constant(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue

        if any(
            isinstance(t, ast.Name) and t.id == name
            for t in targets
        ):
            return ast.literal_eval(node.value)

    raise ValueError(f"Missing constant: {name}")


def main():
    print("=" * 60)
    print("TASK 5 - ANTI-LEAKAGE CONFIGURATION TEST")
    print("=" * 60)

    if not CONFIG.is_file():
        print(f"FAIL - Missing configuration: {CONFIG}")
        return 1

    try:
        tree = ast.parse(CONFIG.read_text(encoding="utf-8-sig"))

        threshold = read_constant(tree, "LEAKAGE_THRESHOLD")
        eval_sets = read_constant(tree, "EVAL_SETS_FOR_LEAKAGE")

        checks = {
            "Threshold = 0.65":
                threshold == EXPECTED_THRESHOLD,
            "Benchmark paths match":
                isinstance(eval_sets, list)
                and len(eval_sets) == 2
                and set(eval_sets) == EXPECTED_EVAL_SETS,
        }

        print(f"Leakage threshold: {threshold}")
        print(f"Benchmark sets: {eval_sets}")

        if isinstance(eval_sets, list):
            for path in eval_sets:
                if not isinstance(path, str):
                    checks["Benchmark paths are strings"] = False
                    continue

                exists = (ROOT / path).is_file()
                checks[f"Exists: {path}"] = exists

        for name, passed in checks.items():
            print(f"{'PASS' if passed else 'FAIL'} | {name}")

        if not all(checks.values()):
            print("\nFINAL RESULT: FAIL")
            return 1

        print("\nFINAL RESULT: PASS")
        print("Configuration declarations are correct.")
        print("Runtime filtering not yet verified.")
        return 0

    except (SyntaxError, ValueError, TypeError) as exc:
        print(f"FAIL - Cannot verify config: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
