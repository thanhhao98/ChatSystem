
"""
Task 5 [D-V5] - Controlled Leakage DROP

Target: SN0380008
Source: data/sgod/verified.json

Default: DRY-RUN
Apply: python scripts/task5/drop_leakage.py --apply

- Không sửa benchmark
- Không paraphrase
- Giữ nguyên dữ liệu nguồn raw/labeled
- Backup trước khi ghi
- Giữ nguyên định dạng các bản ghi còn lại
"""

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "data/sgod/verified.json"

TARGET_ID = "SN0380008"
EXPECTED_COUNT = 489
EXPECTED_INPUT = (
    "tôi muốn có danh sách đầy đủ các yêu cầu "
    "từ nhân viên để xem xét."
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def locate_objects(text):
    """Find JSON array objects without reformatting the file."""
    decoder = json.JSONDecoder()
    spans = []

    def skip_space(pos):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        return pos

    pos = skip_space(0)

    if text[pos] != "[":
        raise ValueError("Expected top-level JSON array")

    pos += 1

    while True:
        pos = skip_space(pos)

        if text[pos] == "]":
            break

        start = pos
        obj, end = decoder.raw_decode(text, pos)

        if not isinstance(obj, dict):
            raise ValueError("Expected JSON object")

        spans.append((start, end, obj))
        pos = skip_space(end)

        if text[pos] == ",":
            pos += 1
        elif text[pos] == "]":
            break
        else:
            raise ValueError("Invalid JSON array separator")

    return spans


def main(apply):
    print("=" * 60)
    print("TASK 5 - CONTROLLED LEAKAGE DROP")
    print("=" * 60)

    original = FILE.read_bytes()
    has_bom = original.startswith(b"\xef\xbb\xbf")

    payload = original[3:] if has_bom else original
    text = payload.decode("utf-8")

    rows = json.loads(text)
    spans = locate_objects(text)

    matches = [
        i for i, (_, _, row) in enumerate(spans)
        if row.get("id") == TARGET_ID
    ]

    print("Source:", FILE)
    print("Original records:", len(rows))
    print("Original SHA256:", sha256(original))
    print("Target ID:", TARGET_ID)
    print("Target occurrences:", len(matches))

    if len(rows) != EXPECTED_COUNT:
        raise RuntimeError(
            "Dataset count changed. Stop and re-audit."
        )

    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one target record."
        )

    index = matches[0]
    start, end, target = spans[index]

    if target.get("input", "").strip().casefold() != EXPECTED_INPUT:
        raise RuntimeError(
            "Target input does not match audited evidence."
        )

    # Remove just one object while preserving other records.
    if index < len(spans) - 1:
        next_start = spans[index + 1][0]
        updated_text = text[:start] + text[next_start:]
    else:
        if index == 0:
            raise RuntimeError("Unexpected single-record dataset")

        prev_end = spans[index - 1][1]
        updated_text = text[:prev_end] + text[end:]

    updated_rows = json.loads(updated_text)

    if len(updated_rows) != len(rows) - 1:
        raise RuntimeError("Unexpected record count after DROP")

    if any(r.get("id") == TARGET_ID for r in updated_rows):
        raise RuntimeError("Target still present after DROP")

    result_bytes = (
        (b"\xef\xbb\xbf" if has_bom else b"")
        + updated_text.encode("utf-8")
    )

    print("Expected records after DROP:", len(updated_rows))
    print("New SHA256:", sha256(result_bytes))

    if not apply:
        print("\nDRY-RUN PASS")
        print("No files were modified.")
        print("Use --apply after Lead approval.")
        return

    # Backup outside the Git repository.
    backup_dir = (
        Path(tempfile.gettempdir())
        / "sgod-task5-backups"
    )
    backup_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup = backup_dir / f"verified_{stamp}.json"

    shutil.copy2(FILE, backup)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".verified-",
            suffix=".tmp",
            dir=FILE.parent,
            delete=False,
        ) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(result_bytes)

        # Prevent overwriting if another process changed the file.
        if FILE.read_bytes() != original:
            raise RuntimeError("Source changed during audit. Stop.")

        os.replace(temp_path, FILE)

    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    print("\nDROP COMPLETED")
    print("Removed:", TARGET_ID)
    print("Records:", len(rows), "->", len(updated_rows))
    print("Backup:", backup)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the audited DROP",
    )
    args = parser.parse_args()
    main(args.apply)
