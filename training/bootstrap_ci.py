#!/usr/bin/env python3
"""Bootstrap 95% CIs, paired-difference CI and exact McNemar for scored runs (eval_metric.md, H1).

    python training/bootstrap_ci.py --run base=results/base.json --run ft=results/ft.json [--run ...]
        [--pair base ft] [--pair ...] [--paired-diff-margin 5] [--n-boot 2000] [--seed 20260625] [--md <out.md>]

Inputs are ``results.json`` files written by ``training/eval_toolcall.py`` (``results[].id`` and
``results[].pass`` are all that is read). Each ``--run LABEL=PATH`` gets a point estimate + 95%
percentile bootstrap CI (``boot_ci``, 2000 resamples, same body as the POC v1 script). Each
``--pair A B`` is evaluated on the id INTERSECTION of the two runs:

* paired bootstrap CI of ``acc_A - acc_B`` (pp): ids are resampled JOINTLY, so both accuracies come
  from the same resample; ``H1`` verdict: "A không thấp hơn B quá <margin>pp" GIỮ iff the 2.5th
  percentile of the difference is > -margin (pre-registered in docs/contracts/eval_metric.md);
* exact two-sided McNemar on the discordant pairs (b = A passes & B fails, c = the reverse).

A missing file or an unreadable run is printed and skipped -- the script never crashes on it. Ids
present in only one run of a pair are reported (they are excluded from the paired statistics).
Randomness: a fresh ``random.Random(seed)`` per statistic, so a number does not depend on the order
of the CLI arguments. Exit code 0 when at least one run was loaded, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

DEFAULT_SEED = 20260625
DEFAULT_N_BOOT = 2000


# ───────────────────────────────────────────── the two bodies kept from POC v1 ──
def boot_ci(flags, n_boot: int = DEFAULT_N_BOOT, rng: random.Random | None = None):
    """95% bootstrap CI (percentile) of the mean of a 0/1 list, in percent: (point, lo, hi)."""
    rng = rng or random.Random(DEFAULT_SEED)
    n = len(flags)
    if n == 0:
        return (0.0, 0.0, 0.0)
    means = []
    for _ in range(n_boot):
        s = sum(flags[rng.randrange(n)] for _ in range(n))
        means.append(100.0 * s / n)
    means.sort()
    pt = 100.0 * sum(flags) / n
    lo = means[int(0.025 * n_boot)]
    hi = means[int(0.975 * n_boot)]
    return pt, lo, hi


def mcnemar(A: dict, B: dict):
    """Exact two-sided McNemar on paired 0/1 dicts keyed by id: (b, c, p, n_paired)."""
    ids = sorted(set(A) & set(B))
    b = sum(1 for i in ids if A[i] and not B[i])   # A wins
    c = sum(1 for i in ids if B[i] and not A[i])   # B wins
    n = b + c
    if n == 0:
        return b, c, 1.0, len(ids)
    k = min(b, c)
    p = min(1.0, 2.0 * sum(math.comb(n, j) for j in range(k + 1)) * (0.5 ** n))  # exact two-sided
    return b, c, p, len(ids)


# ──────────────────────────────────────────────────────────── paired difference ──
def paired_diff_ci(A: dict, B: dict, n_boot: int, rng: random.Random):
    """Percentile CI of acc_A - acc_B (pp) resampling ids jointly. Returns (point, lo, hi, n)."""
    ids = sorted(set(A) & set(B))
    n = len(ids)
    if n == 0:
        return 0.0, 0.0, 0.0, 0
    a = [A[i] for i in ids]
    b = [B[i] for i in ids]
    diffs = []
    for _ in range(n_boot):
        sa = sb = 0
        for _ in range(n):
            j = rng.randrange(n)
            sa += a[j]
            sb += b[j]
        diffs.append(100.0 * (sa - sb) / n)
    diffs.sort()
    pt = 100.0 * (sum(a) - sum(b)) / n
    return pt, diffs[int(0.025 * n_boot)], diffs[int(0.975 * n_boot)], n


# ──────────────────────────────────────────────────────────────────── loading ──
def load_run(path: str) -> dict | None:
    """{id: 0/1} from a results.json; None (after printing why) when unusable."""
    p = Path(path)
    if not p.exists():
        print(f"  (missing) {path}", file=sys.stderr)
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        rows = data["results"] if isinstance(data, dict) else data
        out = {}
        for r in rows:
            rid = r.get("id")
            if rid is None:
                continue
            out[rid] = 1 if r.get("pass") else 0
        if not out:
            print(f"  (empty results) {path}", file=sys.stderr)
            return None
        return out
    except Exception as exc:
        print(f"  (unreadable: {type(exc).__name__}: {exc}) {path}", file=sys.stderr)
        return None


def parse_run_arg(s: str) -> tuple[str, str]:
    if "=" not in s:
        raise argparse.ArgumentTypeError(f"--run expects LABEL=PATH, got {s!r}")
    label, path = s.split("=", 1)
    label, path = label.strip(), path.strip()
    if not label or not path:
        raise argparse.ArgumentTypeError(f"--run expects LABEL=PATH, got {s!r}")
    return label, path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", action="append", type=parse_run_arg, default=[], metavar="LABEL=PATH",
                   help="a scored run (results.json from eval_toolcall.py); repeatable")
    p.add_argument("--pair", action="append", nargs=2, default=[], metavar=("A", "B"),
                   help="paired comparison A vs B (labels from --run); repeatable")
    p.add_argument("--paired-diff-margin", type=float, default=5.0,
                   help="H1 margin in pp: GIỮ iff the 2.5th percentile of acc_A - acc_B > -margin")
    p.add_argument("--n-boot", type=int, default=DEFAULT_N_BOOT)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--md", default=None, help="also write the tables as Markdown to this path")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not args.run:
        print("error: at least one --run LABEL=PATH is required", file=sys.stderr)
        return 1

    runs: dict[str, dict] = {}
    for label, path in args.run:
        if label in runs:
            print(f"WARNING: duplicate run label {label!r}; the later one wins", file=sys.stderr)
        flags = load_run(path)
        if flags is not None:
            runs[label] = flags
    if not runs:
        print("SUMMARY bootstrap_ci: no run could be loaded", file=sys.stderr)
        return 1

    md: list[str] = [
        "# Bootstrap CI + McNemar",
        "",
        f"> **Ghi chú trục đo**: percentile bootstrap, {args.n_boot} resamples, seed {args.seed}; "
        f"margin H1 = {args.paired_diff_margin:g}pp; McNemar exact two-sided. "
        "Chỉ so sánh các run chấm trên cùng eval/tools/preamble sha256.",
        "",
    ]

    # ── runs ──
    print(f"Bootstrap 95% CI (percentile, {args.n_boot} resamples, seed {args.seed})\n")
    print(f"{'run':24} {'acc %':>7}  {'95% CI':>16}  {'n':>5}")
    print("-" * 60)
    md += ["## Từng run", "", "| run | accuracy (%) | 95% CI | n |", "|---|---|---|---|"]
    run_stats = {}
    for label, flags in runs.items():
        vals = [flags[i] for i in sorted(flags)]
        pt, lo, hi = boot_ci(vals, args.n_boot, random.Random(args.seed))
        run_stats[label] = (pt, lo, hi, len(vals))
        print(f"{label:24} {pt:7.1f}  [{lo:5.1f}, {hi:5.1f}]  {len(vals):5d}")
        md.append(f"| {label} | {pt:.1f} | [{lo:.1f}, {hi:.1f}] | {len(vals)} |")

    # ── pairs ──
    n_pairs_done = 0
    if args.pair:
        print(f"\nPaired comparisons (id intersection; diff = acc_A - acc_B in pp; "
              f"H1 margin {args.paired_diff_margin:g}pp)\n")
        md += ["", "## Từng cặp (paired)", "",
               "| A | B | n paired | diff (pp) | 95% CI diff | A không thấp hơn B quá margin | H1 | "
               "McNemar b (A thắng) | c (B thắng) | p | kết luận |",
               "|---|---|---|---|---|---|---|---|---|---|---|"]
        for a_label, b_label in args.pair:
            if a_label not in runs or b_label not in runs:
                missing = [x for x in (a_label, b_label) if x not in runs]
                print(f"  pair {a_label} vs {b_label}: skipped (run not loaded: {', '.join(missing)})")
                md.append(f"| {a_label} | {b_label} | – | – | – | bỏ qua (thiếu run {', '.join(missing)}) | – | – | – | – | – |")
                continue
            A, B = runs[a_label], runs[b_label]
            only_a, only_b = sorted(set(A) - set(B)), sorted(set(B) - set(A))
            pt, lo, hi, n = paired_diff_ci(A, B, args.n_boot, random.Random(args.seed))
            b, c, p, _ = mcnemar(A, B)
            hold = lo > -args.paired_diff_margin
            verdict = (f"{a_label} không thấp hơn {b_label} quá {args.paired_diff_margin:g}pp: "
                       f"{'GIỮ' if hold else 'KHÔNG GIỮ'} ({'H1 giữ' if hold else 'H1 không giữ'})")
            mc_verdict = "khác biệt có ý nghĩa (p<0.05)" if p < 0.05 else "trong nhiễu (n.s.)"
            print(f"  {a_label} vs {b_label}: n_paired={n}"
                  + (f" (only in {a_label}: {len(only_a)}, only in {b_label}: {len(only_b)})" if only_a or only_b else ""))
            if n == 0:
                print("    no common ids -> skipped")
                md.append(f"| {a_label} | {b_label} | 0 | – | – | không có id chung | – | – | – | – | – |")
                continue
            print(f"    diff = {pt:+.1f}pp  95% CI [{lo:+.1f}, {hi:+.1f}]  -> {verdict}")
            print(f"    McNemar b={b} c={c} p={p:.4f} -> {mc_verdict}")
            if only_a or only_b:
                print(f"    ids only in {a_label}: {only_a[:5]}{'…' if len(only_a) > 5 else ''}; "
                      f"only in {b_label}: {only_b[:5]}{'…' if len(only_b) > 5 else ''}")
            md.append(f"| {a_label} | {b_label} | {n} | {pt:+.1f} | [{lo:+.1f}, {hi:+.1f}] | "
                      f"{'GIỮ' if hold else 'KHÔNG GIỮ'} | {'H1 giữ' if hold else 'H1 không giữ'} | "
                      f"{b} | {c} | {p:.4f} | {mc_verdict} |")
            n_pairs_done += 1

    if args.md:
        md += ["", "_Lệnh_: `python training/bootstrap_ci.py "
               + " ".join(f"--run {l}={p}" for l, p in args.run)
               + "".join(f" --pair {a} {b}" for a, b in args.pair)
               + f" --paired-diff-margin {args.paired_diff_margin:g} --n-boot {args.n_boot} --seed {args.seed}`", ""]
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        with open(args.md, "w", encoding="utf-8") as f:
            f.write("\n".join(md))

    print(f"\nSUMMARY bootstrap_ci: runs={len(runs)}/{len(args.run)} pairs={n_pairs_done}/{len(args.pair)} "
          f"n_boot={args.n_boot} seed={args.seed}" + (f" -> {args.md}" if args.md else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
