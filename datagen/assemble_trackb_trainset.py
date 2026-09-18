#!/usr/bin/env python3
"""Stage 6: assemble the FINAL parity trainset from three streams (config_sgod.MIX_TARGETS):
  - domain      : verified net-new SGOD scenarios (case-shaped)          target ~55%
  - replay      : public xLAM rows already in parity format (preamble v0,
                  own `replay_tools`; datagen/convert_xlam.py output)     target ~35%
  - irrelevance : genuine no-call cases (case-shaped)                    target ~10%

Domain + irrelevance are converted with build_parity_trainset.Preamble (preamble v1, REFUSAL/DEFLECT).
Ratios are enforced by subsampling whichever stream is over-represented; the final size shrinks so
the ratios stay honest when a stream is short. Val is taken from DOMAIN only (net-new dev split) so
best-checkpoint selection measures domain generalisation. A final exact-normalised dedup runs across
streams (anti-leakage backstop; the generators did the SequenceMatcher < 0.65 screen).

Usage:
  python3 datagen/assemble_trackb_trainset.py --domain data/sgod/verified.json \
      --irrelevance data/sgod/irrelevance.json --replay data/sgod/replay.train.jsonl \
      --out-dir data/sgod --val-ratio 0.05
"""
import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_sgod as cfg  # noqa: E402
import build_parity_trainset as bp  # noqa: E402
import simindex  # noqa: E402


def load_cases_as_parity(path, stream, pre):
    p = cfg.repo_path(path)
    if not p.exists():
        print(f"  WARNING: {stream} file {p} not found — assembling WITHOUT {stream}")
        return []
    return [pre.row(tc, stream) for tc in bp.load_cases(p)]


def load_replay(path):
    p = cfg.repo_path(path)
    if not p.exists():
        print(f"  WARNING: replay file {p} not found — assembling WITHOUT replay")
        return []
    rows = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                r["stream"] = "replay"
                rows.append(r)
    return rows


def user_text(row):
    return next((m["content"] for m in row["messages"] if m["role"] == "user"), "")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--domain", default=f"{cfg.DATA_DIR}/verified.json")
    p.add_argument("--irrelevance", default=f"{cfg.DATA_DIR}/irrelevance.json")
    p.add_argument("--replay", default=f"{cfg.REPLAY_CONFIG['converted_prefix']}.train.jsonl")
    p.add_argument("--out-dir", default=cfg.DATA_DIR)
    p.add_argument("--val-ratio", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=cfg.DEFAULT_SEED)
    p.add_argument("--preamble", default=cfg.PREAMBLE_V1_PATH)
    p.add_argument("--fixed-replies", default=cfg.FIXED_REPLIES_PATH)
    p.add_argument("--no-mix-enforce", action="store_true", help="keep every row; ignore MIX_TARGETS ratios")
    p.add_argument("--keep-placeholders", action="store_true",
                   help="emit the preamble template verbatim (see build_parity_trainset.py)")
    args = p.parse_args()
    rng = random.Random(args.seed)
    pre = bp.Preamble(args.preamble, args.fixed_replies, keep_placeholders=args.keep_placeholders)

    domain = load_cases_as_parity(args.domain, "domain", pre)
    irrel = load_cases_as_parity(args.irrelevance, "irrelevance", pre)
    replay = load_replay(args.replay)
    print(f"loaded: domain={len(domain)} irrelevance={len(irrel)} replay={len(replay)}")
    if not domain:
        print("SUMMARY assemble: no domain rows — nothing to assemble")
        return 1

    # cross-stream exact-normalised dedup (domain has priority)
    seen, dedup = set(), {"domain": [], "irrelevance": [], "replay": []}
    for stream, rows in (("domain", domain), ("irrelevance", irrel), ("replay", replay)):
        for r in rows:
            k = simindex.normalize(user_text(r))
            if k and k not in seen:
                seen.add(k)
                dedup[stream].append(r)
    domain, irrel, replay = dedup["domain"], dedup["irrelevance"], dedup["replay"]

    mt = cfg.MIX_TARGETS
    d_frac, r_frac, i_frac = mt["domain_verified"], mt["replay"], mt["irrelevance"]
    if args.no_mix_enforce:
        n_d, n_r, n_i = len(domain), len(replay), len(irrel)
    else:
        final_from_domain = int(len(domain) / d_frac)
        want_replay, want_irrel = int(final_from_domain * r_frac), int(final_from_domain * i_frac)
        if want_replay > len(replay) or want_irrel > len(irrel):
            cap_final = min(len(domain) / d_frac,
                            (len(replay) / r_frac) if replay else float("inf"),
                            (len(irrel) / i_frac) if irrel else float("inf"))
            final = int(cap_final)
            n_d, n_r, n_i = int(final * d_frac), int(final * r_frac), int(final * i_frac)
            if not replay:
                n_d, n_i = len(domain), min(len(irrel), int(len(domain) / d_frac * i_frac))
        else:
            n_d, n_r, n_i = len(domain), want_replay, want_irrel

    rng.shuffle(domain)
    rng.shuffle(replay)
    rng.shuffle(irrel)
    domain, replay, irrel = domain[:n_d], replay[:n_r], irrel[:n_i]
    total = len(domain) + len(replay) + len(irrel)
    print(f"mix: domain={len(domain)} ({len(domain) / total:.1%}) replay={len(replay)} ({len(replay) / total:.1%}) "
          f"irrelevance={len(irrel)} ({len(irrel) / total:.1%}) | total={total}")
    note = ""
    if not (mt["final_min"] <= total <= mt["final_max"]):
        note = f" NOTE: total outside [{mt['final_min']},{mt['final_max']}] — scale generation or adjust MIX_TARGETS"
        print(" " + note.strip())

    nval = int(len(domain) * args.val_ratio)
    val = domain[:nval]
    train = domain[nval:] + replay + irrel
    rng.shuffle(train)

    out = cfg.repo_path(args.out_dir)
    train_path = bp.write_jsonl(out / "train.jsonl", train)
    val_path = bp.write_jsonl(out / "val.jsonl", val)
    print("train targets:", dict(Counter(pre.target_kind(r) for r in train)))
    print("train streams:", dict(Counter(r["stream"] for r in train)))
    print(f"SUMMARY assemble: train={len(train)} val={len(val)} (domain-only dev) seed={args.seed} "
          f"-> {train_path}, {val_path}{note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
