#!/usr/bin/env python3
"""QLoRA SFT for tool-calling SLMs with train/serve parity (Colab / Kaggle T4 friendly).

THE PARITY IDEA (read this first)
  1. At serve time vLLM receives `messages` + `tools=[...]` and lets the Qwen chat template render
     the tools into a `<tools>...</tools>` block inside the system turn.
  2. If training instead pastes tools as plain text into the system prompt, the model sees a
     DIFFERENT prompt at train and serve time. In POC v1 this mismatch cost ~18 pp accuracy.
  3. So here the training prompt is built the exact same way:
         prompt     = tokenizer.apply_chat_template(messages[:-1], tools=<tools>, add_generation_prompt=True)
         completion = messages[-1]["content"] + eos
  4. <tools> comes from the row itself (`replay_tools`, public xLAM rows) or from the catalogue
     (`--tools`, SGOD rows) filtered by the row's `role` through `tool_policy.json` — exactly the
     list the executor would offer that role at serve time.
  5. Loss is computed on the completion only (the `<tool_call>` text), never on the prompt.
  6. A row whose prompt+completion is longer than --max-len would be silently cut by the trainer
     (the completion is at the END, so it is the first thing to go): this script refuses to train
     instead of truncating. See the POC v1 incident: loss 0 because every label was masked.

Usage
  # CPU, no model download (tokenizer only): render row 0, check masks, count over-long rows
  python training/finetune_qlora.py --dry-run --data data/public/xlam_2k.train.jsonl --max-len 2560

  # GPU (T4): defaults are the fixed T4 config from docs/contracts/cli.md
  python training/finetune_qlora.py --data data/public/xlam_2k.train.jsonl \
      --val data/public/xlam_2k.val.jsonl --output-dir runs/xlam_0.5b_r16

  # Same, but take defaults from a recipe file (CLI flags still override)
  python training/finetune_qlora.py --recipe training/recipes/public_anchor.yaml \
      --data data/public/xlam_2k.train.jsonl --output-dir runs/public_anchor_s42

Outputs in --output-dir: adapter_config.json, adapter_model.safetensors, tokenizer files,
log_history.json (trainer.state.log_history), training_config.json (args + resolved dtype +
library versions), checkpoint-*/ (for --resume-from-checkpoint).

Flags are a contract (docs/contracts/cli.md): do not rename them without a PR to that document.
"""

import argparse
import json
import os
import platform
import random
import re
import string
import sys
import time

# ── Defaults (docs/contracts/cli.md — the fixed T4 config) ───────────────────────────────────
DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
DEFAULT_EPOCHS = 2
DEFAULT_LR = 1e-4
DEFAULT_BATCH_SIZE = 4
DEFAULT_GRAD_ACCUM = 4          # effective batch = 4 * 4 = 16
DEFAULT_MAX_LEN = 2560          # T4 budget that fits EVERY committed public row (longest 2426 tokens,
                                # p95 990; 1536 blocked 5 rows). Batches pad to their longest row, so
                                # only the few long rows cost VRAM. The guard below enforces it.
DEFAULT_LORA_RANK = 16
DEFAULT_LORA_DROPOUT = 0.05     # alpha defaults to 2 * rank (ToolACE recipe, arXiv:2409.00920)
DEFAULT_SAVE_STEPS = 50
DEFAULT_LOGGING_STEPS = 10
DEFAULT_SEED = 42

# LoRA on all 7 projection modules of a Llama/Qwen block (attention + MLP)
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

# Fixed (not flags): same schedule as the POC v1 recipe run on the GPU box of the reference infrastructure
WARMUP_RATIO = 0.1
WEIGHT_DECAY = 0.01
LR_SCHEDULER = "cosine"
MAX_GRAD_NORM = 0.3
SAVE_TOTAL_LIMIT = 2

TOOL_POLICY_FILENAME = "tool_policy.json"   # sidecar of --tools, same directory
RECIPE_META_KEYS = {"arm", "notes", "description"}  # yaml keys that are not CLI flags


def fail(msg, code=1):
    """Print a clear error and exit non-zero (every hard error in this file goes through here)."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# ── Data loading ──────────────────────────────────────────────────────────────────────────────

def read_jsonl(path, max_rows=None):
    """Read training rows (docs/contracts/training_row_format.md). --max-rows keeps the FIRST N rows
    in file order, so every recipe arm trains on the same fixed subset."""
    if not os.path.exists(path):
        fail(f"data file not found: {path}")
    rows = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                fail(f"{path}:{line_no}: invalid JSON ({e}) — run training/validate_dataset.py first")
            row.setdefault("id", f"{os.path.basename(path)}:{line_no}")
            rows.append(row)
            if max_rows is not None and len(rows) >= max_rows:
                break
    if not rows:
        fail(f"no rows in {path}")
    return rows


def load_catalogue(tools_path):
    """Load the OpenAI-function tool catalogue (--tools) and its role sidecar tool_policy.json.

    Returns (tools, policy) where policy = {tool_name: [roles...]}. Both are None when --tools is
    not given (public rows carry their own `replay_tools`)."""
    if not tools_path:
        return None, None
    if not os.path.exists(tools_path):
        fail(f"--tools file not found: {tools_path}")
    with open(tools_path, encoding="utf-8") as f:
        tools = json.load(f)
    if isinstance(tools, dict) and "tools" in tools:
        tools = tools["tools"]
    if not isinstance(tools, list) or not all(isinstance(t, dict) and "function" in t for t in tools):
        fail(f"--tools must be a JSON list of {{type: function, function: {{...}}}} objects: {tools_path}")

    policy_path = os.path.join(os.path.dirname(os.path.abspath(tools_path)), TOOL_POLICY_FILENAME)
    if not os.path.exists(policy_path):
        fail(f"{TOOL_POLICY_FILENAME} not found next to --tools ({policy_path}); "
             "it is required to filter the catalogue by the row's role")
    with open(policy_path, encoding="utf-8") as f:
        raw_policy = json.load(f)
    policy = {}
    for name, entry in raw_policy.items():
        roles = entry.get("roles") if isinstance(entry, dict) else entry
        if not isinstance(roles, list):
            fail(f"{policy_path}: entry for '{name}' has no 'roles' list")
        policy[name] = list(roles)
    missing = [t["function"]["name"] for t in tools if t["function"]["name"] not in policy]
    if missing:
        fail(f"{policy_path} has no entry for tool(s): {missing} (catalogue and policy must match 1:1)")
    return tools, policy


RENDERED_FUNCTION_KEYS = ("name", "description", "parameters")


def clean_tool(tool):
    """Keep only what the model must see: {type, function: {name, description, parameters}}.

    The Qwen template serialises the WHOLE tool object, so sidecar metadata such as `x_sgod`
    (service, path, allowed_roles, ...) would leak into the prompt, waste tokens and break parity
    with serving. predict_toolcall.py / the backend must strip tools the same way."""
    fn = tool["function"]
    return {"type": "function", "function": {k: fn[k] for k in RENDERED_FUNCTION_KEYS if k in fn}}


def tools_for_row(row, catalogue, policy):
    """Pick the tool list rendered for this row: its own replay_tools, else the role-filtered catalogue."""
    if row.get("replay_tools"):
        return [clean_tool(t) for t in row["replay_tools"]]
    role = row.get("role")
    if catalogue is None:
        fail(f"row {row.get('id')} has no replay_tools and no --tools catalogue was given")
    if not role:
        fail(f"row {row.get('id')} has no 'role' — needed to filter --tools by tool_policy.json")
    tools = [clean_tool(t) for t in catalogue if role in policy[t["function"]["name"]]]
    if not tools:
        fail(f"row {row.get('id')}: role '{role}' is offered no tool by {TOOL_POLICY_FILENAME}")
    return tools


# ── Function-name masking (Hammer, arXiv:2410.04587) — TRAIN ONLY, default off ────────────────
# On a fraction of rows, rename the gold tool consistently in (a) the rendered tool schema,
# (b) any literal mention in the system/user text and (c) the assistant <tool_call>. The model
# must then read the tool DESCRIPTION instead of memorising the name. Parameter names are kept.

_TOOLCALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


def _random_fn_name(rng):
    """A plausible but meaningless function name, e.g. 'fn_a8kd2p'."""
    return "fn_" + "".join(rng.choice(string.ascii_lowercase + string.digits) for _ in range(6))


def _extract_gold_tool_name(completion_content):
    """Tool name of the first <tool_call> in the assistant turn, or None for text-only replies."""
    m = _TOOLCALL_RE.search(completion_content or "")
    if not m:
        return None
    try:
        return json.loads(m.group(1)).get("name")
    except json.JSONDecodeError:
        return None


def maybe_mask_fn_name(row, prob, rng):
    """Return a (possibly) name-masked copy of `row`; unchanged when masking does not fire, the
    row is text-only (refusal/deflect) or the gold name cannot be parsed.

    The rename is recorded in row["_fn_rename"] = [old, new] so `to_prompt_completion` can apply it
    to whichever tool list is rendered (replay_tools or the catalogue)."""
    if prob <= 0 or rng.random() >= prob:
        return row
    messages = row.get("messages", [])
    if len(messages) < 2:
        return row
    gold = _extract_gold_tool_name(messages[-1].get("content", ""))
    if not gold:
        return row
    new_name = _random_fn_name(rng)
    pattern = re.compile(r"\b" + re.escape(gold) + r"\b")  # word-boundary: get_asset != get_asset_history
    out = dict(row)
    out["messages"] = [{**m, "content": pattern.sub(new_name, m.get("content", "") or "")} for m in messages]
    out["_fn_rename"] = [gold, new_name]
    return out


def _rename_tool(tools, rename):
    if not rename:
        return tools
    old, new = rename
    return [({**t, "function": {**t["function"], "name": new}} if t["function"]["name"] == old else t)
            for t in tools]


# ── Prompt / completion rendering (the parity step) ───────────────────────────────────────────

def to_prompt_completion(row, tokenizer, catalogue=None, policy=None):
    """Render one row exactly like vLLM does at serve time.

    prompt     = chat template over messages[:-1] with tools=<tools>, generation prompt appended
    completion = assistant content + eos  (loss is computed on this part only)"""
    messages = row.get("messages") or []
    if len(messages) < 2:
        fail(f"row {row.get('id')}: needs at least [system/user..., assistant] messages, got {len(messages)}")
    tools = _rename_tool(tools_for_row(row, catalogue, policy), row.get("_fn_rename"))
    prompt = tokenizer.apply_chat_template(
        messages[:-1], tools=tools, tokenize=False, add_generation_prompt=True)
    completion = (messages[-1].get("content") or "") + tokenizer.eos_token
    return {"id": row.get("id"), "prompt": prompt, "completion": completion}


def render_rows(rows, tokenizer, catalogue, policy, mask_prob=0.0, seed=DEFAULT_SEED):
    """Render every row; masking (if any) is deterministic per (seed, row index)."""
    out = []
    for idx, row in enumerate(rows):
        if mask_prob > 0:
            row = maybe_mask_fn_name(row, mask_prob, random.Random(seed * 1_000_003 + idx))
        out.append(to_prompt_completion(row, tokenizer, catalogue, policy))
    return out


def count_tokens(tokenizer, rendered):
    """Token counts the way trl tokenises prompt-completion rows (add_special_tokens=False)."""
    prompt_ids = tokenizer(rendered["prompt"], add_special_tokens=False)["input_ids"]
    full_ids = tokenizer(rendered["prompt"] + rendered["completion"], add_special_tokens=False)["input_ids"]
    return len(prompt_ids), len(full_ids)


def truncation_guard(tokenizer, rendered_rows, max_len, label):
    """Count rows whose prompt+completion exceeds max_len. Prints the offending ids.
    Returns (n_overlong, max_tokens). Never truncates anything."""
    overlong, max_tokens, lengths = [], 0, []
    for r in rendered_rows:
        _, n = count_tokens(tokenizer, r)
        lengths.append(n)
        max_tokens = max(max_tokens, n)
        if n > max_len:
            overlong.append((r["id"], n))
    lengths.sort()
    p95 = lengths[int(0.95 * (len(lengths) - 1))] if lengths else 0
    print(f"[{label}] rows={len(rendered_rows)} max_len={max_len} "
          f"tokens(prompt+completion): max={max_tokens} p95={p95} over_limit={len(overlong)}")
    if overlong:
        print(f"[{label}] rows longer than --max-len {max_len} (id: tokens):")
        for rid, n in overlong:
            print(f"    {rid}: {n}")
        print(f"[{label}] all rows would fit at --max-len {max_tokens}")
    return len(overlong), max_tokens


# ── dtype selection: by compute capability, NOT torch.cuda.is_bf16_supported() ────────────────
# T4 (sm_75) reports is_bf16_supported()==True via emulation but trains ~4x slower and can NaN.

def pick_dtype(torch):
    """Return (use_bf16, compute_capability, gpu_name). bf16 iff capability >= 8 and FORCE_FP16 != 1."""
    force_fp16 = os.environ.get("FORCE_FP16", "0") == "1"
    if not torch.cuda.is_available():
        return False, (0, 0), "cpu"
    cap = torch.cuda.get_device_capability(0)
    name = torch.cuda.get_device_name(0)
    return (cap[0] >= 8 and not force_fp16), cap, name


# ── Tokenizer (shared by --dry-run and train) ─────────────────────────────────────────────────

def load_tokenizer(model_name):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_name)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"
    if not tok.eos_token:
        fail(f"tokenizer of {model_name} has no eos_token; completion needs one")
    return tok


# ── --dry-run: tokenizer only, no torch model ─────────────────────────────────────────────────

def dry_run(args):
    print(f"[dry-run] model={args.model} data={args.data} max_len={args.max_len}")
    tokenizer = load_tokenizer(args.model)
    catalogue, policy = load_catalogue(args.tools)
    rows = read_jsonl(args.data, args.max_rows)

    # 1. Render row 0 and show it — this is what the model actually sees.
    r0 = to_prompt_completion(rows[0], tokenizer, catalogue, policy)
    print(f"\n[dry-run] row 0 id={r0['id']}")
    print("---------- prompt (rendered by apply_chat_template, tools=...) ----------")
    print(r0["prompt"])
    print("---------- completion (loss is computed here only) ----------")
    print(r0["completion"])
    print("-------------------------------------------------------------")
    ok = True
    if "<tools>" not in r0["prompt"]:
        print("ASSERT FAILED: '<tools>' not found in the rendered prompt — tools are not being "
              "rendered by the chat template (wrong tokenizer or missing tools).")
        ok = False
    else:
        print("assert '<tools>' in prompt: OK")

    # 2. Completion tokens that stay unmasked under completion-only loss.
    n_prompt, n_full = count_tokens(tokenizer, r0)
    n_completion = n_full - n_prompt
    print(f"prompt tokens: {n_prompt}")
    print(f"unmasked completion tokens: {n_completion}")
    if n_completion <= 0:
        print("ASSERT FAILED: no completion tokens would receive loss.")
        ok = False
    if n_full > args.max_len:
        print(f"row 0 alone is longer than --max-len ({n_full} > {args.max_len}).")

    # 3. Truncation guard over the whole file(s) — the same check train() runs before training.
    rendered = render_rows(rows, tokenizer, catalogue, policy)
    n_over, _ = truncation_guard(tokenizer, rendered, args.max_len, "data")
    if args.val:
        val_rendered = render_rows(read_jsonl(args.val), tokenizer, catalogue, policy)
        n_over += truncation_guard(tokenizer, val_rendered, args.max_len, "val")[0]

    status = "OK" if (ok and n_over == 0) else "FAIL"
    print(f"\nfinetune_qlora --dry-run: {status} rows={len(rows)} unmasked_completion_tokens={n_completion} "
          f"over_limit={n_over}")
    sys.exit(0 if status == "OK" else 1)


# ── train(): GPU path; heavy libraries are imported HERE so --help/--dry-run work anywhere ────

def train(args, recipe=None):
    import torch
    import transformers
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig, set_seed
    from trl import SFTConfig, SFTTrainer
    import accelerate
    import bitsandbytes
    import datasets as datasets_lib
    import peft
    import trl

    set_seed(args.seed)
    random.seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    # ── dtype by compute capability (bf16 on Ampere+, fp16 on T4) ─────────────────────────
    if not torch.cuda.is_available():
        fail("no CUDA GPU detected. Training needs a GPU; use --dry-run on CPU.")
    use_bf16, cap, gpu_name = pick_dtype(torch)
    HALF = torch.bfloat16 if use_bf16 else torch.float16
    print(f"GPU: {gpu_name} · compute capability {cap} · FORCE_FP16={os.environ.get('FORCE_FP16', '0')} "
          f"· USE_BF16={use_bf16} → {str(HALF).replace('torch.', '')}")

    lora_alpha = args.lora_alpha if args.lora_alpha is not None else 2 * args.lora_rank
    versions = {
        "python": platform.python_version(), "torch": torch.__version__,
        "transformers": transformers.__version__, "trl": trl.__version__, "peft": peft.__version__,
        "bitsandbytes": bitsandbytes.__version__, "accelerate": accelerate.__version__,
        "datasets": datasets_lib.__version__,
    }
    config = {
        "args": vars(args), "recipe": recipe,
        "resolved": {"dtype": str(HALF).replace("torch.", ""), "use_bf16": use_bf16,
                     "compute_capability": list(cap), "gpu": gpu_name, "lora_alpha": lora_alpha,
                     "effective_batch": args.batch_size * args.grad_accum,
                     "target_modules": TARGET_MODULES, "warmup_ratio": WARMUP_RATIO,
                     "weight_decay": WEIGHT_DECAY, "lr_scheduler": LR_SCHEDULER,
                     "max_grad_norm": MAX_GRAD_NORM, "optim": "paged_adamw_8bit"},
        "versions": versions, "status": "started", "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    def write_config():
        with open(os.path.join(args.output_dir, "training_config.json"), "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False, default=str)

    write_config()  # written early so an interrupted Colab run still leaves its config behind

    # ── Data: render prompt/completion, then refuse to train if anything would be truncated ──
    tokenizer = load_tokenizer(args.model)
    catalogue, policy = load_catalogue(args.tools)
    train_rows = read_jsonl(args.data, args.max_rows)
    val_rows = read_jsonl(args.val) if args.val else None

    train_rendered = render_rows(train_rows, tokenizer, catalogue, policy,
                                 mask_prob=args.mask_fn_names, seed=args.seed)  # masking: train only
    val_rendered = render_rows(val_rows, tokenizer, catalogue, policy) if val_rows else None
    print(f"Train rows: {len(train_rendered)}" + (f" · Val rows: {len(val_rendered)}" if val_rendered else ""))
    if args.mask_fn_names > 0:
        n_masked = sum(1 for i, r in enumerate(train_rows)
                       if "_fn_rename" in maybe_mask_fn_name(r, args.mask_fn_names,
                                                             random.Random(args.seed * 1_000_003 + i)))
        print(f"Function-name masking ON: p={args.mask_fn_names} → {n_masked} masked train rows (val unmasked)")

    n_over, _ = truncation_guard(tokenizer, train_rendered, args.max_len, "data")
    if val_rendered:
        n_over += truncation_guard(tokenizer, val_rendered, args.max_len, "val")[0]
    if n_over:
        config["status"] = "aborted_truncation_guard"
        write_config()
        fail(f"{n_over} row(s) exceed --max-len {args.max_len}; refusing to truncate silently. "
             "Raise --max-len or shorten/remove those rows.")

    train_ds = Dataset.from_list([{"prompt": r["prompt"], "completion": r["completion"]} for r in train_rendered])
    val_ds = (Dataset.from_list([{"prompt": r["prompt"], "completion": r["completion"]} for r in val_rendered])
              if val_rendered else None)

    # ── Model: NF4 4-bit base + LoRA adapters ─────────────────────────────────────────────
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=HALF,
        bnb_4bit_use_double_quant=True,
    )
    t0 = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=bnb_config,
        device_map={"": 0},   # one GPU; Kaggle's second T4 is intentionally left unused
        torch_dtype=HALF,
    )
    model.config.use_cache = False  # incompatible with gradient checkpointing
    model.config.torch_dtype = HALF
    model = prepare_model_for_kbit_training(
        model, use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False})
    lora_config = LoraConfig(
        r=args.lora_rank, lora_alpha=lora_alpha, lora_dropout=args.lora_dropout,
        target_modules=TARGET_MODULES, bias="none", task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    for name, module in model.named_modules():
        if "lora_" in name:
            module.to(HALF)
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model loaded in {time.time() - t0:.0f}s · params {total / 1e6:.0f}M · "
          f"trainable {trainable / 1e6:.2f}M ({100 * trainable / total:.2f}%)")
    config["resolved"].update({"total_params": total, "trainable_params": trainable})

    # ── Trainer ───────────────────────────────────────────────────────────────────────────
    completion_only = bool(args.completion_only)
    effective_batch = args.batch_size * args.grad_accum
    steps_per_epoch = -(-len(train_ds) // effective_batch)          # ceil
    total_steps = int(-(-steps_per_epoch * args.epochs // 1))       # ceil for fractional epochs
    warmup_steps = max(1, int(total_steps * WARMUP_RATIO))          # transformers 5 deprecates warmup_ratio
    config["resolved"].update({"steps_per_epoch": steps_per_epoch, "planned_steps": total_steps,
                               "warmup_steps": warmup_steps})
    # transformers 5 deprecates logging_dir= in favour of this env var (tensorboard writes here)
    os.environ.setdefault("TENSORBOARD_LOGGING_DIR", os.path.join(args.output_dir, "tensorboard"))
    sft_config = SFTConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type=LR_SCHEDULER,
        warmup_steps=warmup_steps,
        weight_decay=WEIGHT_DECAY,
        max_grad_norm=MAX_GRAD_NORM,
        optim="paged_adamw_8bit",
        bf16=use_bf16,
        fp16=not use_bf16,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        logging_steps=args.logging_steps,
        logging_first_step=True,
        report_to=["tensorboard"],
        save_strategy="steps",
        save_steps=args.save_steps,
        save_total_limit=SAVE_TOTAL_LIMIT,
        eval_strategy="steps" if val_ds is not None else "no",
        eval_steps=args.save_steps if val_ds is not None else None,
        seed=args.seed,
        dataloader_num_workers=2,
        # SFT specifics: prompt/completion dataset, loss on the completion only, no packing
        max_length=args.max_len,
        packing=False,
        completion_only_loss=completion_only,
    )
    trainer = SFTTrainer(
        model=model, args=sft_config, processing_class=tokenizer,
        train_dataset=train_ds, eval_dataset=val_ds,
    )
    print(f"Training: epochs={args.epochs} bs={args.batch_size}x{args.grad_accum} (eff {effective_batch}) "
          f"steps≈{total_steps} warmup={warmup_steps} lr={args.lr} r={args.lora_rank} alpha={lora_alpha} "
          f"completion_only={completion_only} max_len={args.max_len} seed={args.seed}")

    # ── Train (optionally resuming) ───────────────────────────────────────────────────────
    if args.resume_from_checkpoint and not os.path.isdir(args.resume_from_checkpoint):
        fail(f"--resume-from-checkpoint is not a directory: {args.resume_from_checkpoint}")
    if args.resume_from_checkpoint:
        print(f"Resuming from {args.resume_from_checkpoint}")
    torch.cuda.reset_peak_memory_stats()
    t_start = time.time()
    result = trainer.train(resume_from_checkpoint=args.resume_from_checkpoint or None)
    wall_min = (time.time() - t_start) / 60

    # ── Save adapter + tokenizer + logs ───────────────────────────────────────────────────
    model.save_pretrained(args.output_dir)      # adapter_config.json + adapter_model.safetensors
    tokenizer.save_pretrained(args.output_dir)
    with open(os.path.join(args.output_dir, "log_history.json"), "w", encoding="utf-8") as f:
        json.dump(trainer.state.log_history, f, indent=2)
    eval_loss = None
    if val_ds is not None:
        eval_loss = trainer.evaluate().get("eval_loss")
    config["status"] = "done"
    config["resolved"].update({
        "steps": trainer.state.global_step, "wall_clock_min": round(wall_min, 2),
        "train_loss": result.training_loss, "eval_loss": eval_loss,
        "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
        "n_train": len(train_ds), "n_val": len(val_ds) if val_ds is not None else 0,
    })
    write_config()
    print(f"finetune_qlora: DONE steps={trainer.state.global_step} train_loss={result.training_loss:.4f} "
          f"wall={wall_min:.1f}min dtype={config['resolved']['dtype']} adapter={args.output_dir}")


# ── CLI ───────────────────────────────────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(
        description="QLoRA SFT with train/serve parity (tools rendered by the chat template, "
                    "completion-only loss). Flags are fixed by docs/contracts/cli.md.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--data", required=True, help="training rows JSONL (training_row_format.md)")
    p.add_argument("--val", default=None, help="optional validation rows JSONL (eval_loss every --save-steps)")
    p.add_argument("--tools", default=None,
                   help="tool catalogue JSON for rows WITHOUT replay_tools; filtered per row role via "
                        "tool_policy.json in the same directory")
    p.add_argument("--model", default=DEFAULT_MODEL, help="base model id or local path")
    p.add_argument("--output-dir", default="runs/qlora", help="adapter + logs + checkpoints go here")
    p.add_argument("--epochs", type=float, default=DEFAULT_EPOCHS)
    p.add_argument("--lr", type=float, default=DEFAULT_LR)
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="per-device batch size")
    p.add_argument("--grad-accum", type=int, default=DEFAULT_GRAD_ACCUM, help="gradient accumulation steps")
    p.add_argument("--max-len", type=int, default=DEFAULT_MAX_LEN,
                   help="max prompt+completion tokens; longer rows abort the run (never truncated)")
    p.add_argument("--lora-rank", type=int, default=DEFAULT_LORA_RANK)
    p.add_argument("--lora-alpha", type=int, default=None, help="default 2 * --lora-rank")
    p.add_argument("--lora-dropout", type=float, default=DEFAULT_LORA_DROPOUT)
    p.add_argument("--completion-only", type=int, default=1, choices=[0, 1],
                   help="1 = loss on the assistant completion only; 0 = full sequence (ablation)")
    p.add_argument("--mask-fn-names", type=float, default=0.0,
                   help="Hammer-style function-name masking probability per TRAIN row (0 = off)")
    p.add_argument("--max-rows", type=int, default=None, help="use only the first N training rows")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--save-steps", type=int, default=DEFAULT_SAVE_STEPS)
    p.add_argument("--logging-steps", type=int, default=DEFAULT_LOGGING_STEPS)
    p.add_argument("--resume-from-checkpoint", default=None, help="checkpoint-N directory to resume from")
    p.add_argument("--recipe", default=None,
                   help="YAML whose keys are these flags (underscore form); values become defaults, "
                        "explicit CLI flags still override")
    p.add_argument("--dry-run", action="store_true",
                   help="tokenizer only: render row 0, check <tools> and unmasked completion tokens, "
                        "run the truncation guard, exit 0/1")
    return p


def apply_recipe(parser, argv):
    """--recipe <yaml>: load once, turn its keys into parser defaults (typed like the flag)."""
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--recipe", default=None)
    known, _ = pre.parse_known_args(argv)
    if not known.recipe:
        return None
    try:
        import yaml
    except ImportError:
        fail("--recipe needs PyYAML (pip install pyyaml)")
    if not os.path.exists(known.recipe):
        fail(f"--recipe file not found: {known.recipe}")
    with open(known.recipe, encoding="utf-8") as f:
        recipe = yaml.safe_load(f) or {}
    if not isinstance(recipe, dict):
        fail(f"--recipe must be a YAML mapping: {known.recipe}")
    actions = {a.dest: a for a in parser._actions}
    defaults = {}
    for key, value in recipe.items():
        if key in RECIPE_META_KEYS:
            continue
        dest = key.replace("-", "_")
        if dest not in actions or dest in ("help", "recipe", "dry_run"):
            fail(f"recipe key '{key}' is not a finetune_qlora.py flag (see --help)")
        action = actions[dest]
        if action.type is not None and value is not None:
            try:
                value = action.type(value)
            except (TypeError, ValueError):
                fail(f"recipe key '{key}': cannot convert {value!r} with {action.type.__name__}")
        defaults[dest] = value
    parser.set_defaults(**defaults)
    print(f"recipe: {known.recipe} → defaults {json.dumps(defaults, default=str)}")
    return recipe


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    recipe = apply_recipe(parser, argv)
    args = parser.parse_args(argv)
    if args.dry_run:
        dry_run(args)
    else:
        train(args, recipe)


if __name__ == "__main__":
    main()
