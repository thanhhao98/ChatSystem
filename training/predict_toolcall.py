#!/usr/bin/env python3
"""Single-shot tool-selection predictor (docs/contracts/eval_metric.md, docs/contracts/cli.md).

For every eval record the model sees exactly two messages -- the system preamble and the user
input -- plus the tool catalogue, and answers ONCE. No tool is executed, no second turn happens.
The output is a predictions JSONL that ``training/eval_toolcall.py`` scores offline.

Backends
--------
openai        any OpenAI-compatible ``/v1`` endpoint (vLLM, a gateway, OpenAI itself):
              ``chat.completions.create(tools=..., tool_choice="auto", temperature=T)``.
              If the server rejects the ``temperature`` parameter (some frontier models only accept
              the default), the request is retried once without it and the header records
              ``sampling.temperature_rejected = true``.
transformers  local ``AutoModelForCausalLM`` (+ optional PEFT adapter). The prompt is rendered with
              ``tokenizer.apply_chat_template([system, user], tools=..., add_generation_prompt=True)``
              (the same rendering the trainer uses), greedy decoding, left-padded batches.
              dtype: bf16 when CUDA compute capability >= 8, otherwise fp16; ``FORCE_FP16=1`` forces
              fp16 (T4 emulation); CPU falls back to fp32.

Per record
----------
system = the ``--system`` preamble with its slots filled EXACTLY as the trainer does
         (``datagen/build_parity_trainset.py::Preamble.render`` / ``tools/sgod/validate_tools.py``):
           {role}      -> the record's ``user_role``
           {role_vi}   -> ``roles.json["role_names_vi"][user_role]`` (roles.json next to --tools, else
                          ``tools/sgod/roles.json`` in the repo, else the built-in fallback table)
           {full_name} -> "Người dùng"          (GENERIC_CONTEXT, the training value)
           {user_id}   -> "usr-001"             (GENERIC_CONTEXT, the training value)
         A preamble without slots (v0) is used verbatim. Any ``{slot}`` still unfilled after rendering
         is a FATAL error (exit 1) -- the model must never see a literal ``{full_name}``.
         ``sha256_preamble`` in the header is computed over the UNRENDERED template (after .strip()),
         so the same hash covers every role; the filled values are listed in ``header.preamble_context``.
tools  = ``record["tools"]`` when present (public eval, per-row tools) else the ``--tools`` catalogue
         filtered to the record's ``user_role`` via ``tool_policy.json`` next to the catalogue.
         The policy file is REQUIRED (catalogue and policy must match 1:1, like finetune_qlora.py);
         ``--no-policy`` is the explicit opt-out that offers every tool to every role (smoke only).
         Every tool -- per-record or catalogue -- is stripped to
         ``{type, function: {name, description, parameters}}`` (``clean_tool``, same as
         ``finetune_qlora.clean_tool``) so sidecar metadata such as ``x_sgod`` never reaches the model
         and the serve-time prompt is byte-identical to the train-time prompt.

Output file
-----------
Line 1 header::

    {"header": true, "model", "backend", "base_url_host", "date", "git_sha", "sha256_eval",
     "sha256_tools" (null when tools are per-record), "sha256_preamble" (unrendered template),
     "sampling": {...}, "n", "limit" (smoke runs only -- eval_toolcall.py then scores just those ids),
     "preamble_slots_filled", "preamble_context", "policy_path", "roles_path"}

then one line per record::

    {"id", "user_role", "predicted_tool_calls": [{"name", "arguments": {...}}], "predicted_tool",
     "raw_text", "finish_reason", "latency_ms", "error"}

Records are appended to ``<out>.part`` while running, so a crashed run keeps its partial output;
the final file (header + records) is assembled at the end and ``.part`` is removed.

Examples
--------
  # vLLM or a gateway
  python training/predict_toolcall.py --eval data/public/xlam_2k.eval.json --out results/ft_pred.jsonl \\
      --backend openai --base-url http://localhost:8000/v1 --model qwen-ft

  # local transformers (base model, 3 records, CPU is fine)
  python training/predict_toolcall.py --eval data/public/xlam_2k.eval.json --out /tmp/pred.jsonl \\
      --backend transformers --model-path Qwen/Qwen2.5-0.5B-Instruct --limit 3

Exit code 0 when every record produced a line (records with ``error`` set still count as produced);
1 on a fatal setup error (missing file, backend import failure, unfilled preamble slot, catalogue
without a matching tool_policy.json entry, missing policy file without ``--no-policy``).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
DEFAULT_PREAMBLE = REPO / "prompts" / "system_preamble_v0.txt"
DEFAULT_ROLES = REPO / "tools" / "sgod" / "roles.json"
TOOL_POLICY_FILENAME = "tool_policy.json"
ROLES_FILENAME = "roles.json"
TOOL_CALL_RE = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)

# Preamble slots. MUST stay identical to datagen/build_parity_trainset.py (Preamble.render / KNOWN_SLOTS),
# datagen/config_sgod.py (GENERIC_CONTEXT, _ROLE_NAMES_VI_FALLBACK) and tools/sgod/validate_tools.py
# (GENERIC_CONTEXT): the training rows and the token budget are rendered with these exact values.
PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")
KNOWN_SLOTS = ("role", "role_vi", "full_name", "user_id")
GENERIC_CONTEXT = {"full_name": "Người dùng", "user_id": "usr-001"}
ROLE_NAMES_VI_FALLBACK = {
    "employee": "Nhân viên",
    "company_admin": "Quản trị viên doanh nghiệp",
    "system_admin": "Quản trị hệ thống",
}
# What the model may see of a tool. Same as finetune_qlora.RENDERED_FUNCTION_KEYS / clean_tool().
RENDERED_FUNCTION_KEYS = ("name", "description", "parameters")


# ────────────────────────────────────────────────────────────────── helpers ──
def sha256_file(path: str | Path | None) -> str | None:
    if path is None:
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """sha256 of text after .strip() -- the contract's convention for the preamble hash."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def rel(path) -> str | None:
    """Path relative to the repo root when inside it (keeps headers machine-independent)."""
    if path is None:
        return None
    try:
        return Path(path).resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def git_sha() -> str | None:
    """HEAD sha of the repo containing this script, or None when not inside a git repo."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                             text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None
    except Exception:
        return None


def load_eval(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        for key in ("records", "cases", "data"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON list of eval records")
    return data


def tool_name(tool: dict) -> str | None:
    return (tool.get("function") or {}).get("name") or tool.get("name")


def clean_tool(tool: dict) -> dict:
    """Keep only what the model must see: {type, function: {name, description, parameters}}.

    Identical to finetune_qlora.clean_tool(): the Qwen template serialises the WHOLE tool object, so
    sidecar metadata (``x_sgod``: service, path, allowed_roles, notes, ...) would leak into the prompt,
    waste tokens and break parity with training. A legacy flat tool {name, description, parameters}
    is wrapped into the function shape."""
    fn = tool.get("function") if isinstance(tool.get("function"), dict) else tool
    return {"type": "function", "function": {k: fn[k] for k in RENDERED_FUNCTION_KEYS if k in fn}}


def load_tools(path: str | None, no_policy: bool = False) -> tuple[list[dict] | None, dict | None, str | None]:
    """Return (tools, policy, policy_path). policy = {tool_name: [roles...]} from tool_policy.json
    next to the catalogue.

    Mirrors finetune_qlora.load_catalogue(): the policy file is REQUIRED and every catalogue tool must
    have an entry with a ``roles`` list (1:1 bijection) -- a policy gap must fail here, not be offered
    to every role and then scored as a denial violation by eval_toolcall.py. ``no_policy=True`` is the
    explicit opt-out (policy None -> every tool offered to every role; smoke tests only)."""
    if not path:
        return None, None, None
    with open(path, encoding="utf-8") as f:
        tools = json.load(f)
    if isinstance(tools, dict) and isinstance(tools.get("tools"), list):
        tools = tools["tools"]
    if not isinstance(tools, list) or not all(isinstance(t, dict) and tool_name(t) for t in tools):
        raise SystemExit(f"error: --tools must be a JSON list of {{type: function, function: {{name, ...}}}} objects: {path}")
    pol_path = Path(path).parent / TOOL_POLICY_FILENAME
    if no_policy:
        print(f"  [warn] --no-policy: every tool in {path} is offered to EVERY role "
              f"(smoke test only; never for a reported number)", file=sys.stderr)
        return tools, None, None
    if not pol_path.exists():
        raise SystemExit(
            f"error: {TOOL_POLICY_FILENAME} not found next to --tools ({pol_path}). It is required to filter the "
            f"catalogue by the record's user_role (finetune_qlora.py does the same). Pass --no-policy to "
            f"deliberately offer every tool to every role (smoke test only).")
    with open(pol_path, encoding="utf-8") as f:
        raw = json.load(f)
    policy: dict[str, list[str]] = {}
    for name, entry in raw.items():
        roles = entry.get("roles") if isinstance(entry, dict) else entry
        if not isinstance(roles, list):
            raise SystemExit(f"error: {pol_path}: entry for '{name}' has no 'roles' list")
        policy[name] = list(roles)
    missing = [tool_name(t) for t in tools if tool_name(t) not in policy]
    if missing:
        raise SystemExit(f"error: {pol_path} has no entry for tool(s): {missing} "
                         f"(catalogue and policy must match 1:1)")
    extra = sorted(set(policy) - {tool_name(t) for t in tools})
    if extra:
        print(f"  [warn] {pol_path} lists tool(s) absent from the catalogue: {extra}", file=sys.stderr)
    return tools, policy, str(pol_path)


def tools_for_role(tools: list[dict] | None, policy: dict | None, role: str) -> list[dict] | None:
    """Catalogue tools the role may call, stripped with clean_tool(). policy None (= --no-policy): all."""
    if tools is None:
        return None
    if policy is None:
        return [clean_tool(t) for t in tools]
    return [clean_tool(t) for t in tools if role in policy[tool_name(t)]]


def load_role_names_vi(tools_path: str | None) -> tuple[dict[str, str], str]:
    """{role: Vietnamese label} for the {role_vi} slot and where it came from.

    Order: roles.json next to --tools, then tools/sgod/roles.json in the repo, then the built-in
    fallback (identical to datagen/config_sgod._ROLE_NAMES_VI_FALLBACK)."""
    candidates = []
    if tools_path:
        candidates.append(Path(tools_path).parent / ROLES_FILENAME)
    candidates.append(DEFAULT_ROLES)
    names = dict(ROLE_NAMES_VI_FALLBACK)
    for cand in candidates:
        if cand.exists():
            try:
                data = json.loads(cand.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"error: {cand} is not valid JSON ({exc})") from exc
            if isinstance(data, dict) and isinstance(data.get("role_names_vi"), dict):
                names.update({str(k): str(v) for k, v in data["role_names_vi"].items()})
                return names, rel(cand) or str(cand)
    return names, "built-in fallback"


def render_system(preamble: str, role: str, role_names_vi: dict[str, str] | None = None) -> str:
    """Fill the preamble slots for one role -- byte-identical to Preamble.render in the trainer.

    str.replace (not str.format) so JSON braces elsewhere in the template stay untouched. A preamble
    without slots (v0) is returned unchanged. Use unfilled_slots() afterwards to fail fast."""
    names = role_names_vi or ROLE_NAMES_VI_FALLBACK
    txt = preamble.replace("{role}", role)
    txt = txt.replace("{role_vi}", names.get(role, role))
    for slot, val in GENERIC_CONTEXT.items():
        txt = txt.replace("{" + slot + "}", val)
    return txt.strip()


def unfilled_slots(text: str) -> list[str]:
    """``{slot}`` placeholders still present after rendering (bare lowercase identifiers only)."""
    return sorted(set(PLACEHOLDER_RE.findall(text)))


def parse_tool_calls(text: str) -> list[dict]:
    """Extract ``<tool_call>{...}</tool_call>`` blocks into [{name, arguments(dict)}]."""
    calls = []
    for block in TOOL_CALL_RE.findall(text or ""):
        try:
            obj = json.loads(block)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or not obj.get("name"):
            continue
        args = coerce_args(obj.get("arguments", obj.get("parameters", {})))
        if args is None:          # contract: a call with broken JSON arguments is dropped (kept in raw_text)
            continue
        calls.append({"name": str(obj["name"]), "arguments": args})
    return calls


def coerce_args(args) -> dict | None:
    """Arguments as a dict; None when they are a string that is not a JSON object."""
    if isinstance(args, dict):
        return args
    if args is None:
        return {}
    if isinstance(args, str):
        if not args.strip():
            return {}
        try:
            parsed = json.loads(args)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def make_record(rec: dict, calls: list[dict], raw_text: str, finish_reason: str | None,
                latency_ms: int, error: str | None) -> dict:
    return {
        "id": rec.get("id"),
        "user_role": rec.get("user_role"),
        "predicted_tool_calls": calls,
        "predicted_tool": calls[0]["name"] if calls else None,
        "raw_text": raw_text or "",
        "finish_reason": finish_reason,
        "latency_ms": int(latency_ms),
        "error": error,
    }


# ────────────────────────────────────────────────────────────────── backends ──
class OpenAIBackend:
    name = "openai"

    def __init__(self, args):
        try:
            from openai import OpenAI  # noqa: WPS433 (lazy: not needed for --help)
        except ImportError as exc:
            raise SystemExit(f"openai SDK missing ({exc}); pip install openai") from exc
        import openai
        self._openai = openai
        base_url = args.base_url or os.environ.get("OPENAI_BASE_URL") or "http://localhost:8000/v1"
        api_key = os.environ.get(args.api_key_env) or "EMPTY"
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=args.timeout, max_retries=1)
        self.model = args.model
        self.temperature = args.temperature
        self.max_tokens = args.max_new_tokens
        self.temperature_rejected = False
        self.base_url_host = urlparse(base_url).netloc or base_url      # host[:port], never the key
        self.batch_size = 1

    def sampling(self) -> dict:
        return {"temperature": self.temperature, "max_tokens": self.max_tokens,
                "tool_choice": "auto", "temperature_rejected": self.temperature_rejected,
                "decoding": "server-default" if self.temperature_rejected else "temperature"}

    def _call(self, messages, tools, with_temperature: bool):
        kwargs = dict(model=self.model, messages=messages, max_tokens=self.max_tokens)
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if with_temperature:
            kwargs["temperature"] = self.temperature
        return self.client.chat.completions.create(**kwargs)

    def predict_batch(self, batch: list[tuple[dict, str, list | None]]) -> list[dict]:
        out = []
        for rec, system, tools in batch:
            messages = [{"role": "system", "content": system},
                        {"role": "user", "content": rec.get("input", "")}]
            t0 = time.time()
            try:
                try:
                    resp = self._call(messages, tools, with_temperature=not self.temperature_rejected)
                except self._openai.BadRequestError as exc:
                    if (not self.temperature_rejected) and "temperature" in str(exc).lower():
                        print(f"  [warn] server rejected 'temperature' -> retrying without it "
                              f"(recorded in header.sampling)", file=sys.stderr)
                        self.temperature_rejected = True
                        resp = self._call(messages, tools, with_temperature=False)
                    else:
                        raise
                latency = (time.time() - t0) * 1000
                choice = resp.choices[0]
                msg = choice.message
                calls, raw_calls = [], []
                for tc in (msg.tool_calls or []):
                    fn = getattr(tc, "function", None)
                    if fn is None or not getattr(fn, "name", None):
                        continue
                    raw_calls.append({"name": fn.name, "arguments": fn.arguments})
                    args = coerce_args(fn.arguments)
                    if args is None:      # broken JSON arguments: dropped from the list, kept in raw_text
                        continue
                    calls.append({"name": fn.name, "arguments": args})
                content = msg.content or ""
                # Some servers (e.g. vLLM without a tool parser) emit <tool_call> tags as plain text.
                if not raw_calls and "<tool_call>" in content:
                    calls = parse_tool_calls(content)
                raw_text = content
                if raw_calls:
                    raw_text += ("\n" if content else "") + json.dumps(raw_calls, ensure_ascii=False)
                out.append(make_record(rec, calls, raw_text, choice.finish_reason, latency, None))
            except Exception as exc:  # network / HTTP / parsing -> recorded, never fatal
                latency = (time.time() - t0) * 1000
                out.append(make_record(rec, [], "", None, latency, f"{type(exc).__name__}: {exc}"[:500]))
        return out


class TransformersBackend:
    name = "transformers"

    def __init__(self, args):
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise SystemExit(f"transformers/torch missing ({exc}); pip install -r requirements-train.txt") from exc
        self.torch = torch
        self.model_path = args.model_path
        self.adapter = args.adapter
        self.max_new_tokens = args.max_new_tokens
        self.batch_size = max(1, args.batch_size)
        self.base_url_host = "transformers"          # contract: no endpoint for the local backend
        self.temperature = args.temperature

        self.device, self.dtype, self.dtype_reason = pick_device_dtype(torch)
        print(f"  device={self.device} dtype={self.dtype} ({self.dtype_reason})")

        self.tok = AutoTokenizer.from_pretrained(self.model_path)
        self.tok.padding_side = "left"
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        try:
            model = AutoModelForCausalLM.from_pretrained(self.model_path, dtype=self.dtype)
        except TypeError:  # transformers < 4.56 spelled it torch_dtype
            model = AutoModelForCausalLM.from_pretrained(self.model_path, torch_dtype=self.dtype)
        if self.adapter:
            # Colab environment may pre-install torchao < 0.16.0, which causes peft 0.20.0
            # to raise an ImportError during tuner inspection. Patching is_torchao_available avoids this.
            try:
                import peft.import_utils
                peft.import_utils.is_torchao_available = lambda: False
            except Exception:
                pass
            try:
                from peft import PeftModel
            except ImportError as exc:
                raise SystemExit(f"--adapter given but peft is missing ({exc})") from exc
            model = PeftModel.from_pretrained(model, self.adapter)
            print(f"  adapter loaded: {self.adapter}")
        self.model = model.to(self.device).eval()
        self.model_label = args.model or (self.model_path + (f"+{Path(self.adapter).name}" if self.adapter else ""))

    def sampling(self) -> dict:
        return {"temperature": self.temperature, "do_sample": False, "decoding": "greedy",
                "max_new_tokens": self.max_new_tokens, "dtype": str(self.dtype).replace("torch.", ""),
                "device": self.device, "batch_size": self.batch_size,
                "adapter": self.adapter}

    def predict_batch(self, batch: list[tuple[dict, str, list | None]]) -> list[dict]:
        torch = self.torch
        prompts = []
        for rec, system, tools in batch:
            msgs = [{"role": "system", "content": system},
                    {"role": "user", "content": rec.get("input", "")}]
            kwargs = {"tokenize": False, "add_generation_prompt": True}
            if tools:
                kwargs["tools"] = tools
            prompts.append(self.tok.apply_chat_template(msgs, **kwargs))
        t0 = time.time()
        try:
            enc = self.tok(prompts, return_tensors="pt", padding=True).to(self.device)
            with torch.no_grad():
                gen = self.model.generate(
                    **enc, max_new_tokens=self.max_new_tokens, do_sample=False,
                    pad_token_id=self.tok.pad_token_id,
                )
            new_tokens = gen[:, enc["input_ids"].shape[1]:]
            per_item_ms = (time.time() - t0) * 1000 / len(batch)
            # Qwen ends a turn with <|im_end|> (eos) and generate() pads afterwards with pad_token_id.
            stop_ids = {self.tok.eos_token_id, self.tok.pad_token_id} - {None}
            out = []
            for (rec, _, _), ids in zip(batch, new_tokens):
                ids_list = ids.tolist()
                # finish_reason: "stop" when an end token was generated, else "length" (budget hit).
                hit_stop = any(t in stop_ids for t in ids_list)
                text = self.tok.decode(ids, skip_special_tokens=True).strip()
                calls = parse_tool_calls(text)
                out.append(make_record(rec, calls, text, "stop" if hit_stop else "length",
                                       per_item_ms, None))
            return out
        except Exception as exc:
            latency = (time.time() - t0) * 1000 / len(batch)
            return [make_record(rec, [], "", None, latency, f"{type(exc).__name__}: {exc}"[:500])
                    for rec, _, _ in batch]


def pick_device_dtype(torch):
    """bf16 iff CUDA compute capability >= 8; fp16 otherwise (or when FORCE_FP16=1); fp32 on CPU.

    Deliberately NOT torch.cuda.is_bf16_supported(): it returns True on a T4 (emulated bf16) and
    the run then silently crawls or NaNs.
    """
    force = os.environ.get("FORCE_FP16", "").strip() in {"1", "true", "yes"}
    if torch.cuda.is_available():
        major, minor = torch.cuda.get_device_capability(0)
        if force:
            return "cuda", torch.float16, f"FORCE_FP16=1 (cc {major}.{minor})"
        if major >= 8:
            return "cuda", torch.bfloat16, f"compute capability {major}.{minor} >= 8"
        return "cuda", torch.float16, f"compute capability {major}.{minor} < 8"
    return "cpu", torch.float32, "no CUDA -> CPU fp32"


# ────────────────────────────────────────────────────────────────────── main ──
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--eval", required=True, help="eval JSON (list of records per eval_metric.md)")
    p.add_argument("--out", required=True, help="predictions JSONL to write (header + one line per record)")
    p.add_argument("--backend", choices=["openai", "transformers"], required=True)
    # openai backend
    p.add_argument("--base-url", default=None,
                   help="OpenAI-compatible base URL (default: $OPENAI_BASE_URL or http://localhost:8000/v1)")
    p.add_argument("--model", default=None,
                   help="served model name (openai backend; required). For transformers: label only")
    p.add_argument("--api-key-env", default="OPENAI_API_KEY",
                   help="env var holding the API key (default OPENAI_API_KEY; 'EMPTY' if unset)")
    p.add_argument("--timeout", type=float, default=120.0, help="per-request timeout in seconds (openai)")
    # transformers backend
    p.add_argument("--model-path", default="Qwen/Qwen2.5-0.5B-Instruct",
                   help="HF id or local dir of the base model (transformers backend)")
    p.add_argument("--adapter", default=None, help="PEFT adapter dir to load on top (transformers)")
    p.add_argument("--batch-size", type=int, default=8, help="generation batch size (transformers)")
    p.add_argument("--max-new-tokens", type=int, default=256,
                   help="max generated tokens (transformers) / max_tokens (openai)")
    # shared
    p.add_argument("--tools", default=None,
                   help="tool catalogue JSON (tool_policy.json and roles.json are read from the same directory); "
                        "ignored for records that carry their own 'tools'")
    p.add_argument("--no-policy", action="store_true",
                   help="offer EVERY catalogue tool to every role instead of requiring tool_policy.json "
                        "next to --tools (smoke test only; the header records it)")
    p.add_argument("--system", default=str(DEFAULT_PREAMBLE), help="system preamble text file")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--limit", type=int, default=None, help="only the first N records (smoke test)")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.backend == "openai" and not args.model:
        print("error: --model is required for --backend openai", file=sys.stderr)
        return 1
    for path, label in ((args.eval, "--eval"), (args.system, "--system"), (args.tools, "--tools")):
        if path and not Path(path).exists():
            print(f"error: {label} file not found: {path}", file=sys.stderr)
            return 1

    records = load_eval(args.eval)
    if args.limit is not None:
        records = records[: args.limit]
        print(f"  [warn] --limit {args.limit}: SMOKE RUN -- eval_toolcall.py will score only these ids "
              f"(header.limit); never use the result for a reported number", file=sys.stderr)
    with open(args.system, encoding="utf-8") as f:
        preamble = f.read().strip()
    try:
        catalogue, policy, policy_path = load_tools(args.tools, args.no_policy)
        role_names_vi, roles_src = load_role_names_vi(args.tools)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1
    per_record_tools = all("tools" in r for r in records) if records else False
    if not per_record_tools and catalogue is None:
        missing = sum(1 for r in records if "tools" not in r)
        print(f"error: {missing} record(s) have no 'tools' and no --tools catalogue was given", file=sys.stderr)
        return 1

    # Render the system turn once per role BEFORE loading any model: an unfilled slot is fatal.
    slots_in_template = [s for s in KNOWN_SLOTS if "{" + s + "}" in preamble]
    roles_seen = sorted({r.get("user_role") or "employee" for r in records})
    system_by_role: dict[str, str] = {}
    for role in roles_seen:
        rendered = render_system(preamble, role, role_names_vi)
        left = unfilled_slots(rendered)
        if left:
            print(f"error: preamble {args.system} still has unfilled slot(s) {left} after rendering for role "
                  f"'{role}'. Known slots: {list(KNOWN_SLOTS)} (values: role, role_vi from {roles_src}, "
                  f"GENERIC_CONTEXT {GENERIC_CONTEXT}). Fix the template or the slot names.", file=sys.stderr)
            return 1
        if role not in role_names_vi and "{role_vi}" in preamble:
            print(f"  [warn] role '{role}' has no Vietnamese label in {roles_src}; {{role_vi}} <- '{role}'",
                  file=sys.stderr)
        system_by_role[role] = rendered
    if slots_in_template:
        print(f"  preamble slots filled: {slots_in_template} (role_vi from {roles_src}; "
              f"full_name/user_id = GENERIC_CONTEXT) -- sha256_preamble is over the unrendered template")
    if catalogue is not None and not per_record_tools:
        for role in roles_seen:
            if not tools_for_role(catalogue, policy, role) and any((r.get("user_role") or "employee") == role
                                                                 and "tools" not in r for r in records):
                print(f"  [warn] role '{role}' is offered no tool by {policy_path or 'the catalogue'}", file=sys.stderr)

    print(f"predict_toolcall: backend={args.backend} n={len(records)} eval={args.eval}")
    backend = OpenAIBackend(args) if args.backend == "openai" else TransformersBackend(args)
    model_label = args.model if args.backend == "openai" else backend.model_label

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    part_path = out_path.with_suffix(out_path.suffix + ".part")

    n_done = n_err = n_calls = 0
    t_start = time.time()
    with open(part_path, "w", encoding="utf-8") as part:
        bs = backend.batch_size
        for start in range(0, len(records), bs):
            chunk = records[start:start + bs]
            batch = []
            for rec in chunk:
                role = rec.get("user_role") or "employee"
                if "tools" in rec:
                    tools = [clean_tool(t) for t in (rec["tools"] or []) if isinstance(t, dict) and tool_name(t)]
                else:
                    tools = tools_for_role(catalogue, policy, role)
                batch.append((rec, system_by_role[role], tools))
            for row in backend.predict_batch(batch):
                part.write(json.dumps(row, ensure_ascii=False) + "\n")
                n_done += 1
                n_err += 1 if row["error"] else 0
                n_calls += 1 if row["predicted_tool"] else 0
                status = "ERR " if row["error"] else ("call" if row["predicted_tool"] else "text")
                print(f"  [{n_done:4d}/{len(records)}] {status} {row['id']:<16} "
                      f"{(row['predicted_tool'] or '-')[:32]:<32} {row['latency_ms']:6d}ms")
            part.flush()

    header = {
        "header": True,
        "model": model_label,
        "backend": args.backend,
        "base_url_host": backend.base_url_host,
        "date": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "sha256_eval": sha256_file(args.eval),
        "sha256_tools": None if per_record_tools else sha256_file(args.tools),
        "sha256_preamble": sha256_text(preamble),      # over the UNRENDERED template, stripped (contract)
        "sampling": backend.sampling(),
        "n": n_done,
        "eval_path": rel(args.eval),
        "tools_path": None if per_record_tools else rel(args.tools),
        "preamble_path": rel(args.system),
        "limit": args.limit,                          # non-null = smoke run; eval_toolcall.py restricts to these ids
        "preamble_slots_filled": slots_in_template,
        "preamble_context": {**GENERIC_CONTEXT,
                             "role_vi": {r: role_names_vi.get(r, r) for r in roles_seen} if "{role_vi}" in preamble else None,
                             "roles_source": roles_src if "{role_vi}" in preamble else None},
        "policy_path": None if per_record_tools else (rel(policy_path) if policy_path else None),
        "no_policy": bool(args.no_policy) and not per_record_tools,
        "tools_cleaned": "type+function.{name,description,parameters}",
    }
    with open(out_path, "w", encoding="utf-8") as f, open(part_path, encoding="utf-8") as part:
        f.write(json.dumps(header, ensure_ascii=False) + "\n")
        for line in part:
            f.write(line)
    part_path.unlink()

    elapsed = time.time() - t_start
    print(f"SUMMARY predict_toolcall: model={model_label} backend={args.backend} n={n_done} "
          f"tool_calls={n_calls} errors={n_err} elapsed={elapsed:.1f}s -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
