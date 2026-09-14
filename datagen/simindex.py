"""Near-duplicate / leakage detection shared by the generators.

Extracted from the reference system (POC v1) held-out generator (normalize, load_train_queries, max_sim,
SimIndex) so that no datagen script depends on that code base. Pure stdlib.

Usage pattern (anti-leakage):
    leak = SimIndex()
    leak.add_many(load_train_queries("data/sgod/train.jsonl"))
    for path in cfg.EVAL_SETS_FOR_LEAKAGE: add_case_inputs(leak, path)   # skips missing files
    if leak.max_sim(candidate) < cfg.LEAKAGE_THRESHOLD: accept(candidate)

Usage pattern (intra-batch near-exact dedup, concurrent):
    seen = SimIndex()
    if seen.check_and_add(candidate, 0.92): accept(candidate)
"""
import json
import re
import sys
import threading
from difflib import SequenceMatcher
from pathlib import Path


def normalize(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[?!.,;:]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_train_queries(path) -> list:
    """Normalized user turns of a parity JSONL file (rows with `messages`)."""
    qs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            uq = next((m.get("content", "") for m in d.get("messages", [])
                       if m.get("role") == "user"), "")
            if uq:
                qs.append(normalize(uq))
    return qs


def load_case_inputs(path) -> list:
    """`input` fields of a case file: JSON list (eval/labeled) or JSONL (parity rows)."""
    p = Path(path)
    if p.suffix == ".jsonl":
        return load_train_queries(p)
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("cases") or data.get("results") or []
    return [c["input"] for c in data if isinstance(c, dict) and c.get("input")]


def max_sim(query: str, train_qs: list) -> float:
    """Brute-force reference implementation (small lists). Prefer SimIndex for bulk work."""
    qn = normalize(query)
    best = 0.0
    for tq in train_qs:
        r = SequenceMatcher(None, qn, tq).ratio()
        if r > best:
            best = r
        if best > 0.95:
            return best
    return best


class SimIndex:
    """Near-duplicate detector with char-trigram blocking — keeps bulk anti-leakage near-O(N)
    instead of O(N^2). `max_sim` only runs the expensive SequenceMatcher on candidates that share
    enough trigrams with the query (a cheap necessary condition for a high ratio). Hot trigrams
    (appearing in > df_cap entries) are skipped at query time: they carry no discriminative power.

    Thread-safe: generators call `check_and_add` concurrently from worker threads.
    """

    def __init__(self, df_cap: int = 4000, gate: float = 0.34):
        self.norms = []                      # normalized strings, by entry id
        self._tris = []                      # trigram set, by entry id
        self.index = {}                      # trigram -> list of entry ids
        self.df_cap = df_cap
        self.gate = gate
        self._lock = threading.Lock()

    def __len__(self):
        return len(self.norms)

    @staticmethod
    def trigrams(norm: str) -> set:
        s = f"  {norm} "
        return {s[i:i + 3] for i in range(len(s) - 2)}

    def _add_locked(self, qn: str, tri: set) -> None:
        idx = len(self.norms)
        self.norms.append(qn)
        self._tris.append(tri)
        for t in tri:
            self.index.setdefault(t, []).append(idx)

    def add(self, query: str) -> None:
        qn = normalize(query)
        with self._lock:
            self._add_locked(qn, self.trigrams(qn))

    def add_many(self, norms) -> None:
        for n in norms:
            self.add(n)   # add() re-normalizes idempotently

    def _best_locked(self, qn: str, tri: set) -> float:
        shared = {}
        for t in tri:
            posting = self.index.get(t)
            if not posting or len(posting) > self.df_cap:
                continue
            for cid in posting:
                shared[cid] = shared.get(cid, 0) + 1
        if not shared:
            return 0.0
        denom = max(1, len(tri))
        best = 0.0
        for cid, sh in sorted(shared.items(), key=lambda kv: kv[1], reverse=True):
            if sh / denom < self.gate:
                break
            r = SequenceMatcher(None, qn, self.norms[cid]).ratio()
            if r > best:
                best = r
            if best > 0.95:
                break
        return best

    def max_sim(self, query: str) -> float:
        qn = normalize(query)
        tri = self.trigrams(qn)
        with self._lock:
            return self._best_locked(qn, tri)

    def check_and_add(self, query: str, threshold: float) -> bool:
        """Atomic 'accept if novel': True and recorded iff max similarity to everything seen
        so far is < threshold."""
        qn = normalize(query)
        tri = self.trigrams(qn)
        with self._lock:
            if self._best_locked(qn, tri) >= threshold:
                return False
            self._add_locked(qn, tri)
            return True


def add_case_inputs(index: SimIndex, path, label: str = "") -> int:
    """Add every `input` of a case/parity file to `index`. Missing file -> warning, 0 added."""
    p = Path(path)
    if not p.exists():
        print(f"WARNING: leakage set {p} not found — skipping (create it before D Việc 5)",
              file=sys.stderr)
        return 0
    qs = load_case_inputs(p)
    for q in qs:
        index.add(q)
    print(f"  +{len(qs)} leakage queries from {label or p}")
    return len(qs)


def build_leak_index(eval_sets, train_paths=()) -> SimIndex:
    """Strict anti-leakage index over eval sets + existing train files (missing ones skipped)."""
    idx = SimIndex()
    for xf in eval_sets:
        add_case_inputs(idx, xf)
    for tp in train_paths:
        add_case_inputs(idx, tp)
    return idx
