#!/usr/bin/env python3
"""Provenance gate for Markdown reports under docs/reports/ and results/ (stdlib only).

Rule (HUONG_DAN_LAM_VIEC.md, "Mọi con số phải truy vết được"): every reported number in a report must
have a matching number in the ``số`` column of ``results/INDEX.md`` -- the append-only table that ties a
number to its results file, command, git sha, eval/tools sha, model, date and author.

What counts as a reported number
  * a percentage written with its sign: ``75.6%`` / ``75,6 %`` / ``+6.5%``;
  * a p-value: ``p = 0.84`` / ``p < 0.001`` / ``p=0.0021``;
  * inside a Markdown table: every bare number in a cell whose COLUMN HEADER contains ``%`` or ``pp``
    (``accuracy (%)``, ``95% CI``, ``diff (pp)``), or whose ROW LABEL (first cell) contains ``%``
    (``| accuracy (strict, %) | 74.5 |``) -- this is how ``training/eval_toolcall.py --md`` and
    ``training/bootstrap_ci.py --md`` write their tables;
  * inside a Markdown table: every bare number in a column headed ``p`` / ``p-value`` / ``p (McNemar)``.

Escapes (deterministic, keep them few)
  * a line containing ``<!-- no-prov -->`` is skipped;
  * everything between a line containing ``<!-- no-prov-start -->`` and one containing
    ``<!-- no-prov-end -->`` is skipped (use it around pasted CLI output);
  * inline code spans ```...``` are never scanned (commands, file paths, the scorer version string);
  * the ``Ghi chú trục đo`` line is metadata (sha256 prefixes, seeds, scorer id) and is not scanned;
  * table header rows and separator rows are not scanned;
  * a percentage right after a threshold operator (``≥ ≤ >= <=``) is a rule, not a result (``≥50% khoá``);
  * ``90% / 95% / 99%`` next to ``CI`` / ``tin cậy`` is a confidence level; ``p < 0.05`` alone is the
    conventional alpha level (write an exact ``p = 0.0123`` or ``p < 0.001`` for a real result);
  * INDEX rows whose text contains ``ví dụ`` (worked examples such as R000) are ignored.

Usage:
  python scripts/check_provenance.py <report.md> [--index results/INDEX.md]

Exit codes: 0 = every number is indexed, 1 = at least one un-indexed number, 2 = usage / IO error.
A missing ``Ghi chú trục đo`` header is reported as a warning (the axis note is required by the
eval contract, but this gate only enforces number provenance).
"""
import argparse
import os
import re
import sys

PCT_RE = re.compile(r"(?<![\w.,])[+\-−]?(\d{1,3}(?:[.,]\d+)?)\s?(?:%|％)")
PVAL_RE = re.compile(
    r"\bp\s*(=|<=|>=|<|>|≤|≥|＝)\s*([01]?[.,]\d+|[01](?:[.,]0+)?)\b", re.IGNORECASE
)
NUM_RE = re.compile(r"(?<![\w.,])(\d+(?:[.,]\d+)?)(?![\w])")
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
THRESHOLD_TAIL_RE = re.compile(r"(?:≥|≤|>=|<=|≧|≦)\s*$")
PP_HEADER_RE = re.compile(r"\bpp\b|điểm phần trăm", re.IGNORECASE)
P_HEADER_RE = re.compile(r"^\W*p(?:[\s\-_(]|value|$)", re.IGNORECASE)
LINE_SKIP = "<!-- no-prov -->"
REGION_START = "<!-- no-prov-start -->"
REGION_END = "<!-- no-prov-end -->"
EXAMPLE_MARKER = "ví dụ"
AXIS_NOTE = "Ghi chú trục đo"
# "95% CI" / "khoảng tin cậy 95%" names a confidence LEVEL, not a result -> not a reportable number.
CONF_LEVELS = {90.0, 95.0, 99.0}
CONF_CONTEXT_RE = re.compile(r"\bci\b|tin cậy|ktc|confidence", re.IGNORECASE)
ALPHA_LEVEL = 0.05


def norm(num_text: str) -> float:
    """'75,6' / '75.60' / '.84' -> a rounded float so text variants compare equal."""
    return round(float(num_text.replace(",", ".")), 6)


def is_confidence_level(line: str, m) -> bool:
    """True for '95% CI', 'CI 95%', 'khoảng tin cậy 95%' -- a confidence level, not a result."""
    if norm(m.group(1)) not in CONF_LEVELS:
        return False
    window = line[max(0, m.start() - 20): m.end() + 20]
    return bool(CONF_CONTEXT_RE.search(window))


def is_threshold(line: str, m) -> bool:
    """True for '≥50%' / '<= 10 %' -- a rule stated in a label, not a measured value."""
    return bool(THRESHOLD_TAIL_RE.search(line[: m.start()]))


def is_alpha_level(m) -> bool:
    """True for 'p<0.05' / 'p < 0.05' -- the conventional significance threshold, not a result."""
    return m.group(1) in ("<", "<=", "≤") and norm(m.group(2)) == ALPHA_LEVEL


def is_separator_row(cells):
    return all(re.fullmatch(r":?-{1,}:?", c) for c in cells if c) and any(cells)


def is_pipe_row(line: str) -> bool:
    return line.lstrip().startswith("|")


def split_row(line: str):
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.strip() for c in inner.split("|")]


def strip_code_spans(line: str) -> str:
    return CODE_SPAN_RE.sub(" ", line)


def load_index_numbers(path: str):
    """Return (set of normalised numbers found in the 'số' column, number of data rows read)."""
    numbers, rows_read, col = set(), 0, None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not is_pipe_row(line):
                continue
            cells = split_row(line)
            if is_separator_row(cells):
                continue
            lowered = [c.lower() for c in cells]
            if col is None:
                # header row: needs an "id" column and a "số" column
                if "id" in lowered:
                    for i, c in enumerate(lowered):
                        if c in ("số", "so", "number", "giá trị"):
                            col = i
                            break
                    if col is None:
                        col = 1
                continue
            if any(EXAMPLE_MARKER in c.lower() for c in cells):
                continue
            if col >= len(cells):
                continue
            rows_read += 1
            for m in NUM_RE.finditer(cells[col]):
                numbers.add(norm(m.group(1)))
    return numbers, rows_read


def table_columns(header):
    """Indices of percent-valued and p-valued columns from a lower-cased header row."""
    pct_cols = {j for j, h in enumerate(header) if "%" in h or PP_HEADER_RE.search(h)}
    p_cols = {j for j, h in enumerate(header) if P_HEADER_RE.match(h)}
    return pct_cols, p_cols


def scan_report(path: str):
    """Return (list of (lineno, kind, text, value) outside escapes, has_axis_note)."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    found, has_axis_note, in_region = [], False, False
    header = None  # lower-cased header cells of the table we are inside, else None

    for idx, raw in enumerate(lines):
        lineno = idx + 1
        line = raw.rstrip()
        is_axis = AXIS_NOTE.lower() in line.lower()
        if is_axis:
            has_axis_note = True
        if REGION_START in line:
            in_region = True
            continue
        if REGION_END in line:
            in_region = False
            continue
        if in_region or LINE_SKIP in line or is_axis:
            continue
        if not is_pipe_row(line):
            header = None
            if not line.strip():
                continue

        text = strip_code_spans(line)
        seen = set()

        def add(kind, num_text, shown=None):
            val = norm(num_text)
            key = (kind, val)
            if key not in seen:
                seen.add(key)
                found.append((lineno, kind, (shown or num_text).strip(), val))

        if is_pipe_row(text):
            cells = split_row(text)
            if is_separator_row(cells):
                continue
            if header is None:
                nxt = lines[idx + 1] if idx + 1 < len(lines) else ""
                if is_pipe_row(nxt) and is_separator_row(split_row(nxt)):
                    header = [c.lower() for c in cells]
                    continue  # header row: labels only
            else:
                pct_cols, p_cols = table_columns(header)
                row_is_pct = bool(cells) and "%" in cells[0]
                for j, cell in enumerate(cells):
                    if j in p_cols:
                        for m in NUM_RE.finditer(cell):
                            add("p", m.group(1))
                    elif j in pct_cols or (row_is_pct and j > 0):
                        for m in NUM_RE.finditer(cell):
                            add("pct", m.group(1))

        for m in PCT_RE.finditer(text):
            if is_confidence_level(text, m) or is_threshold(text, m):
                continue
            add("pct", m.group(1), m.group(0))
        for m in PVAL_RE.finditer(text):
            if is_alpha_level(m):
                continue
            add("p", m.group(2), m.group(0))
    return found, has_axis_note


def resolve_index(path: str) -> str:
    if os.path.exists(path):
        return path
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alt = os.path.join(repo_root, path)
    return alt if os.path.exists(alt) else path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Fail (exit 1) when a report contains a percentage or p-value that has no row in results/INDEX.md."
    )
    ap.add_argument("report", help="Markdown report to check (docs/reports/*.md, results/**/*.md)")
    ap.add_argument("--index", default="results/INDEX.md", help="INDEX table (default: results/INDEX.md)")
    args = ap.parse_args(argv)

    index_path = resolve_index(args.index)
    if not os.path.isfile(args.report):
        print(f"check_provenance: report not found: {args.report}", file=sys.stderr)
        return 2
    if not os.path.isfile(index_path):
        print(f"check_provenance: INDEX not found: {args.index}", file=sys.stderr)
        return 2

    indexed, rows = load_index_numbers(index_path)
    found, has_axis_note = scan_report(args.report)

    missing = [(ln, kind, text, val) for (ln, kind, text, val) in found if val not in indexed]
    for ln, kind, text, _ in missing:
        label = "p-value" if kind == "p" else "percent"
        print(f"[MISSING] {args.report}:{ln}: {label} `{text}` không có dòng nào trong {args.index}")
    if not has_axis_note:
        print(f"[WARN] {args.report}: thiếu header 'Ghi chú trục đo' (xem docs/contracts/eval_metric.md)")

    verdict = "OK" if not missing else "FAIL"
    print(
        f"check_provenance: report={args.report} index={args.index} index_rows={rows} "
        f"numbers={len(found)} indexed={len(found) - len(missing)} missing={len(missing)} "
        f"axis_note={'yes' if has_axis_note else 'no'} -> {verdict}"
    )
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
