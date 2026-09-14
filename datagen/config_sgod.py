"""Single config for the SGOD data-generation pipeline — edit THIS (and prompts/) to retarget.

Ported from the reference system (POC v1) datagen config. The pipeline
itself is app-agnostic; everything that knows about the SGOD domain lives here or in
`datagen/prompts/`. The retarget checklist (kept from the POC v1 docstring, adapted):

  1. TOOL_DEFS_PATH  -> tools/sgod/sgod_tools.json  (list of {"type","function","x_sgod"}).
  2. POLICY_PATH     -> tools/sgod/tool_policy.json ({tool: {"writes": bool, "roles": [...]}}).
     Permissions are derived from that file ONLY (see audit_test_cases.load_permissions).
  3. ROLES_PATH      -> tools/sgod/roles.json (chat-role vocabulary + aliases) -> ROLE_MAP.
  4. DOMAIN_SYSTEM   -> generation system prompt (domain + language + example entities).
  5. CATEGORY_HINTS  -> scenario taxonomy (bucket -> one-line hint). NO multi-turn / multi_step.
  6. ENTITY_POOLS / PARAM_SAMPLER / BUCKET_PLAN / TRACKB_BUCKET_PLAN -> entity + tool coverage.
Everything else (anti-leakage, batched generation, multi-LLM consensus, schema validation,
parity row formatting) carries over unchanged.

Every block marked TODO(D-Việc-3) is a STUB with 1-2 worked entries. The Data interns fill them
in from `tools/sgod/sgod_tools.json`, `fixtures/sgod/` and `docs/personas_sgod.md`. POC v1 values
are kept in comments as examples of the expected density.

Nothing here imports from the reference system (POC v1). No secrets: OPENAI_API_KEY / OPENAI_BASE_URL are
read from the environment at call time only (see `require_openai_client`).
"""
import json
import os
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def repo_path(p) -> Path:
    """Resolve a CLI/config path: absolute paths are kept, relative ones are repo-rooted."""
    p = Path(p)
    return p if p.is_absolute() else REPO / p


# ───────────────────────────────────────────────────────────────────────────
# 0. FILE LOCATIONS (contract 4: tool catalogue shape; contract 3: roles)
# ───────────────────────────────────────────────────────────────────────────
TOOL_DEFS_PATH = os.environ.get("TOOL_DEFS_PATH", "tools/sgod/sgod_tools.json")
POLICY_PATH = os.environ.get("TOOL_POLICY_PATH", "tools/sgod/tool_policy.json")
ROLES_PATH = os.environ.get("ROLES_PATH", "tools/sgod/roles.json")

PREAMBLE_V1_PATH = "prompts/system_preamble_v1.txt"   # SGOD rows: {role_vi}/{full_name}/{user_id}
#   (+ optional {role}) filled from GENERIC_CONTEXT / role_names_vi
PREAMBLE_V0_PATH = "prompts/system_preamble_v0.txt"   # public/replay rows (neutral)
FIXED_REPLIES_PATH = "prompts/fixed_replies.json"     # REFUSAL_VI / DEFLECT_VI
PROMPT_DIR = "datagen/prompts"                        # training-data prompts (interns edit)
PROMPT_DIR_EVAL = "datagen/prompts_eval"              # eval-augmentation prompts (DISJOINT set)
DATA_DIR = "data/sgod"                                # every stage output lands here

# ───────────────────────────────────────────────────────────────────────────
# 1. LLM MODEL PLACEHOLDERS — models are switched in ONE place.
#    Scripts read these as their --model defaults. The values are placeholder names; the real
#    served name depends on the OPENAI_BASE_URL gateway of the reference infrastructure.
# ───────────────────────────────────────────────────────────────────────────
GEN_MODEL = "gpt-4o"                       # generate_scenarios / generate_irrelevance
LABEL_MODELS = ["gpt-4o", "gpt-4o-mini"]   # label_scenarios + verify_trainset stage C (consensus)
ARBITER_MODEL = "gpt-4o"                   # polish_scenarios / audit_test_cases pass 2
                                           # (for eval_v1 augmentation MUST differ from the GPT under test)

# ───────────────────────────────────────────────────────────────────────────
# 2. ROLES — chat roles come from tools/sgod/roles.json (contract 3). ROLE_MAP maps the labels
#    used in case files ("admin", "employee") to the chat-role vocabulary the policy uses.
#    Never key on SGOD role ObjectIds.
# ───────────────────────────────────────────────────────────────────────────
_ROLE_MAP_FALLBACK = {"admin": "company_admin", "employee": "employee"}
_CHAT_ROLES_FALLBACK = ["employee", "company_admin", "system_admin"]

_ROLE_NAMES_VI_FALLBACK = {
    "employee": "Nhân viên",
    "company_admin": "Quản trị viên doanh nghiệp",
    "system_admin": "Quản trị hệ thống",
}

# Generic per-user context for the {full_name} / {user_id} preamble slots. Training rows carry
# GENERIC values (the model learns structure, not ids); serve fills the real user. MUST equal
# tools/sgod/validate_tools.py GENERIC_CONTEXT so token budgets are measured on the same text.
GENERIC_CONTEXT = {"full_name": "Người dùng", "user_id": "usr-001"}


def load_role_names_vi(path=None):
    """Vietnamese role labels for the {role_vi} slot: roles.json "role_names_vi" when present."""
    p = repo_path(path or ROLES_PATH)
    names = dict(_ROLE_NAMES_VI_FALLBACK)
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(d, dict) and isinstance(d.get("role_names_vi"), dict):
                names.update({str(k): str(v) for k, v in d["role_names_vi"].items()})
        except json.JSONDecodeError:
            pass
    return names


ROLE_NAMES_VI = load_role_names_vi()


def load_roles(path=None):
    """Return (chat_roles: list[str], role_map: dict) from roles.json, tolerant to its shape.

    Accepted shapes (the S-team owns the file; the first matching rule wins):
      {"roles": [..], "aliases": {"admin": "company_admin"}, "tier_to_role": {...}}
      {"roles": {"company_admin": {...}, "employee": {...}}, ...}
      ["employee", "company_admin", "system_admin"]
      {"company_admin": {...}, "employee": {...}}          # role -> anything
    Missing file -> fallback vocabulary + {"admin": "company_admin", "employee": "employee"}.
    """
    p = repo_path(path or ROLES_PATH)
    roles, aliases = list(_CHAT_ROLES_FALLBACK), {}
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"WARNING: {p} is not valid JSON ({exc}); using fallback roles", file=sys.stderr)
            d = None
        if isinstance(d, list):
            roles = [str(r) for r in d]
        elif isinstance(d, dict):
            r = d.get("roles") or d.get("chat_roles")
            if isinstance(r, list):
                roles = [str(x) for x in r]
            elif isinstance(r, dict):
                roles = list(r.keys())
            elif "tiers" in d or "tier_to_role" in d or "aliases" in d or "role_map" in d:
                tiers = d.get("tiers") or d.get("tier_to_role") or {}
                roles = sorted(set(tiers.values()) | set(_CHAT_ROLES_FALLBACK))
            else:
                roles = list(d.keys())
            aliases = dict(d.get("aliases") or d.get("role_map") or {})
    role_map = dict(_ROLE_MAP_FALLBACK)
    role_map.update({str(k): str(v) for k, v in aliases.items()})
    for r in roles:
        role_map.setdefault(r, r)
    return roles, role_map


CHAT_ROLES, ROLE_MAP = load_roles()
CASE_ROLES = ["employee", "admin"]   # labels used in case files / bucket plans (mapped via ROLE_MAP)

# ───────────────────────────────────────────────────────────────────────────
# 3. DOMAIN SYSTEM PROMPT for net-new query generation.
#    TODO(D-Việc-3): rewrite for SGOD (entities: assetCode "000000001", asset names, locations,
#    categories, maintenance schedule status ...) from fixtures/sgod/ and docs/personas_sgod.md.
#    A file datagen/prompts/domain_system.md, when present, OVERRIDES this string.
# ───────────────────────────────────────────────────────────────────────────
DOMAIN_SYSTEM = """Bạn tạo dữ liệu kiểm thử cho một chatbot quản lý tài sản doanh nghiệp tiếng Việt (nền tảng SGOD).
Tạo các câu truy vấn NGƯỜI DÙNG THẬT sẽ gõ — KHÔNG phải diễn giải lại của nhau, mà là các TÌNH HUỐNG KHÁC NHAU.
Đa dạng hoá: tên tài sản (vd "Laptop Dell Latitude", "Máy in Canon tầng 3"), mã tài sản (vd 000000012),
vị trí/kho, danh mục, trạng thái, lịch bảo trì, số lượng, mốc thời gian.
Trộn văn phong: trang trọng, thân mật, viết tắt, có lỗi chính tả nhẹ, dùng "ạ/nhé/giùm".
Chỉ trả về MỘT mảng JSON các chuỗi câu truy vấn tiếng Việt. KHÔNG giải thích, KHÔNG nêu tên công cụ."""
# POC v1 example (for density): mentioned asset codes AS-021/AS-117, offices Hà Nội/Đà Nẵng/Sài Gòn,
# statuses available/assigned/maintenance/retired/lost, conditions new/good/fair/poor.

# ───────────────────────────────────────────────────────────────────────────
# 4. CATEGORY HINTS — scenario taxonomy: category -> one-line generation hint.
#    Single-turn only. The POC v1 "multi_step" category is REMOVED on purpose (phase 2 = single turn).
#    TODO(D-Việc-3): extend to cover every tool in sgod_tools.json (~20 read-only tools).
#    A file datagen/prompts/category_<name>.md, when present, OVERRIDES that category's hint.
# ───────────────────────────────────────────────────────────────────────────
CATEGORY_HINTS = {
    # worked entries
    "my_assets": "NGƯỜI DÙNG hỏi về TÀI SẢN của CHÍNH MÌNH / của doanh nghiệp mình: tài sản tôi đang có, "
                 "danh sách tài sản, lọc theo trạng thái/danh mục/vị trí (KHÔNG hỏi về người khác)",
    "asset_detail": "xem chi tiết MỘT tài sản cụ thể theo tên hoặc mã tài sản (mã tài sản dạng số, vd 000000012)",
    "maintenance": "xem lịch bảo trì: lịch sắp tới, lịch đang hoạt động/đã hoàn tất, tài sản cần bảo trì",
    "permission_denial": "NGƯỜI DÙNG YÊU CẦU một hành động mà vai trò của họ KHÔNG được phép làm",
    "out_of_scope": "câu lạc đề hoặc ngoài phạm vi quản lý tài sản (thời tiết, lập trình, tán gẫu)",
    # TODO(D-Việc-3): add e.g. "asset_query", "location_query", "category_query", "transfer_query",
    # "dashboard", "my_profile" ... one hint per intent family in the catalogue.
}
# POC v1 example hints (kept for reference — the wording style is what matters):
#   "multi_filter": "liệt kê/tìm tài sản với NHIỀU bộ lọc CÙNG LÚC ... luôn có ≥2 điều kiện lọc"
#   "admin_daily_read": "việc đọc hằng ngày của quản trị: đơn chờ duyệt, dashboard, thống kê ..."

# ───────────────────────────────────────────────────────────────────────────
# 5. BUCKET_PLAN — (category, role, count) for a representative, READ-heavy benchmark.
#    Roles are CASE roles ("employee" / "admin"); ROLE_MAP turns "admin" into "company_admin".
#    TODO(D-Việc-3): size to the eval_v1 targets (≥15/tool, every role, ≥10% null, ≥10% denied).
# ───────────────────────────────────────────────────────────────────────────
BUCKET_PLAN = [
    ("my_assets", "employee", 12), ("my_assets", "admin", 8),
    ("asset_detail", "employee", 8), ("asset_detail", "admin", 8),
    ("maintenance", "admin", 8), ("maintenance", "employee", 4),
    ("permission_denial", "employee", 6),
    ("out_of_scope", "employee", 3), ("out_of_scope", "admin", 3),
]  # POC v1: ~500 total, ~85% reads, roughly balanced roles

# ───────────────────────────────────────────────────────────────────────────
# 6. ENTITY POOLS — realistic values injected into generation prompts (surface diversity).
#    TODO(D-Việc-3): fill from fixtures/sgod/ (real asset names, categories, locations, statuses,
#    schedule statuses). Keep values PII-free. POC v1 had ~15 keys incl. asset_code/office/employee/
#    department/category/status/condition/report_type/date_phrase/register.
# ───────────────────────────────────────────────────────────────────────────
ENTITY_POOLS = {
    "asset_code": [f"{i:09d}" for i in range(1, 60)],                  # SGOD sequential assetCode
    "asset_name": ["Laptop Dell Latitude 5540", "Máy in Canon LBP", "Màn hình LG 27 inch",
                   "Máy chiếu Epson", "Xe nâng tay", "Máy lạnh Daikin", "QA Test Laptop"],
    "category": ["laptop", "máy in", "màn hình", "thiết bị mạng", "bàn ghế", "xe"],
    "location": ["kho tầng 1", "văn phòng tầng 3", "chi nhánh Đà Nẵng", "kho miền Nam"],
    "asset_status": ["active", "inactive"],                             # TODO(D-Việc-3): real enum
    "asset_status_vi": {"active": "đang hoạt động", "inactive": "ngừng sử dụng"},
    "schedule_status": ["active", "complete"],                          # TODO(D-Việc-3): real enum
    "schedule_status_vi": {"active": "đang hoạt động", "complete": "đã hoàn tất"},
    "date_phrase": ["hôm nay", "tuần này", "tháng này", "quý này", "30 ngày qua", "tuần trước"],
    "quantity": ["3", "5", "10", "tất cả", "20"],
    "register": ["trang trọng", "thân mật", "viết tắt", "có lỗi chính tả nhẹ",
                 "ra lệnh ngắn gọn", "lịch sự dùng ạ/nhé"],
}


def _pick(rng, key):
    return rng.choice(ENTITY_POOLS[key])


# ───────────────────────────────────────────────────────────────────────────
# 7. PARAM SAMPLER — tool -> fn(rng) -> {slot_label_vi: concrete_value}. Steers each generated
#    query to a specific point of the tool's PARAMETER space (the anti-paraphrase lever). Slot
#    labels are Vietnamese; the labeler assigns canonical schema params independently.
#    TODO(D-Việc-3): one entry per tool in sgod_tools.json (param names must exist in its schema).
# ───────────────────────────────────────────────────────────────────────────
PARAM_SAMPLER = {
    "list_my_assets": lambda r: r.choice([
        {},
        {"trạng thái": ENTITY_POOLS["asset_status_vi"][_pick(r, "asset_status")]},
        {"danh mục": _pick(r, "category")},
        {"số lượng": _pick(r, "quantity")},
    ]),
    "get_asset": lambda r: r.choice([
        {"tên tài sản": _pick(r, "asset_name")},
        {"mã tài sản": _pick(r, "asset_code")},
    ]),
    "list_maintenance_schedules": lambda r: r.choice([
        {},
        {"trạng thái lịch": ENTITY_POOLS["schedule_status_vi"][_pick(r, "schedule_status")]},
        {"thời gian": _pick(r, "date_phrase")},
    ]),
}


def sample_param_hint(tool, rng):
    """Return {slot_vi: value} hints for `tool`, or {} when the tool has no sampler."""
    fn = PARAM_SAMPLER.get(tool)
    return fn(rng) if fn else {}


# ───────────────────────────────────────────────────────────────────────────
# 8. TRACKB_BUCKET_PLAN — LARGE plan keyed by TOOL: (tool, category, role, count).
#    generate_scenarios.py --trackb uses it together with PARAM_SAMPLER. `tool` is only a hint
#    carried as "seed_tool"; the labeler decides the label independently.
#    TODO(D-Việc-3): one or more rows per tool; reads >> writes (phase 2 catalogue is read-only).
#    POC v1: 48 rows over 33 tools, counts 200..1700, sum ≈ 22.5k.
# ───────────────────────────────────────────────────────────────────────────
TRACKB_BUCKET_PLAN = [
    ("list_my_assets", "my_assets", "employee", 20),
    ("list_my_assets", "my_assets", "admin", 12),
    ("get_asset", "asset_detail", "employee", 12),
    ("get_asset", "asset_detail", "admin", 12),
    ("list_maintenance_schedules", "maintenance", "admin", 12),
    ("list_maintenance_schedules", "maintenance", "employee", 8),
]
# Verify the total with:
#   python3 -c "import sys; sys.path.insert(0,'datagen'); import config_sgod as c; print(sum(n for *_,n in c.TRACKB_BUCKET_PLAN))"

# Complexity layering (single-turn only). "dependent" (multi-step chains) from POC v1 is REMOVED.
COMPLEXITY_MIX = {"single": 0.85, "multi_constraint": 0.15}

# ───────────────────────────────────────────────────────────────────────────
# 9. IRRELEVANCE / NO-CALL targets — ~10% of the FINAL trainset (Hammer: 19% is over-conservative).
#    All map to expected_tool=null + expected_permission="allowed" -> DEFLECT_VI target.
#    TODO(D-Việc-3): tune hints to SGOD vocabulary; keep the four kinds.
# ───────────────────────────────────────────────────────────────────────────
IRRELEVANCE_CONFIG = {
    "target_fraction": 0.10,
    "kinds": {
        "out_of_scope": 0.40,
        "chitchat": 0.20,
        "ambiguous": 0.20,
        "procedure_question": 0.20,
    },
    "out_of_scope_hint": "Câu hỏi HOÀN TOÀN ngoài lĩnh vực quản lý tài sản: thời tiết, thể thao, "
                         "nấu ăn, lập trình, toán học, tin tức, sức khoẻ, dịch thuật chung.",
    "chitchat_hint": "Chào hỏi, cảm ơn, tán gẫu, hỏi bạn là ai, khen/chê chung — không yêu cầu tác vụ.",
    "ambiguous_hint": "Liên quan tài sản nhưng THIẾU thông tin để chọn công cụ (vd 'xem cái đó', "
                      "'kiểm tra giúp tôi', 'cái kia sao rồi') — cần hỏi lại để làm rõ.",
    "procedure_question_hint": "Câu hỏi CÁCH LÀM / quy trình / giải thích, KHÔNG yêu cầu hệ thống thực "
                               "hiện ngay (vd 'quy trình đăng ký tài sản mới ra sao?', 'làm sao để in mã QR?') "
                               "— trả lời hướng dẫn, KHÔNG gọi tool.",
}

# ───────────────────────────────────────────────────────────────────────────
# 10. REPLAY — public xLAM slice already in the repo (no HF download, no token).
#     datagen/convert_xlam.py turns the raw slice into parity rows with preamble v0.
# ───────────────────────────────────────────────────────────────────────────
REPLAY_CONFIG = {
    "target_fraction": 0.35,
    "source": "Salesforce/xlam-function-calling-60k (2k slice, see data/public/ATTRIBUTION.md)",
    "license": "CC-BY-4.0 (permissive; attribution required)",
    "local_path": "data/public/xlam_raw_2k.jsonl",       # converter input (committed)
    "converter": "datagen/convert_xlam.py",
    "converted_prefix": "data/sgod/replay",             # -> replay.{train,val,test}.jsonl + replay.eval.json
    "converter_seed": 20260913,                          # SAME seed as data/public/xlam_2k.* -> identical split
    "min_tools": 1, "max_tools": 4,
}

# ───────────────────────────────────────────────────────────────────────────
# 11. FINAL MIX TARGETS — composition of the assembled trainset (assemble_trackb_trainset.py).
#     POC v1 SFT-v2 lesson: small clean domain + ~2k absolute xLAM replay beat big synthetic sets.
#     TODO(D-Việc-5): set final_* to the sizes reachable with the 0.58 yield budget.
# ───────────────────────────────────────────────────────────────────────────
MIX_TARGETS = {
    "domain_verified": 0.55,
    "replay": 0.35,
    "irrelevance": 0.10,
    "final_min": 300,      # pilot-friendly floor; POC v1: 4500
    "final_max": 6500,
    "final_target": 3000,  # POC v1: 5800
}

# Yield budget from the POC v1 run: generation fill ~70% × verify pass ~84% ≈ 0.58 of the plan
# survives to the trainset. Size the plan as target / YIELD_BUDGET.
YIELD_BUDGET = 0.58

# ───────────────────────────────────────────────────────────────────────────
# 12. ANTI-LEAKAGE — SequenceMatcher threshold + the eval sets generated rows must NOT resemble.
#     eval_v1.json does not exist until Điểm đồng bộ 2; generators skip missing files with a WARNING.
# ───────────────────────────────────────────────────────────────────────────
LEAKAGE_THRESHOLD = 0.65
EVAL_SETS_FOR_LEAKAGE = ["data/sgod/eval_v1.json"]

DEFAULT_SEED = 20260616


def make_rng(seed=DEFAULT_SEED):
    return random.Random(seed)


# ───────────────────────────────────────────────────────────────────────────
# 13. SHARED HELPERS (prompt overrides, OpenAI client, call meter)
# ───────────────────────────────────────────────────────────────────────────
def load_prompt(name, default, prompt_dir=None):
    """Return the text of <prompt_dir>/<name>.md when it exists, else `default`.

    Lets interns iterate on prompts as Markdown files without touching Python. Training prompts
    live in datagen/prompts/, eval-augmentation prompts in datagen/prompts_eval/ (must stay disjoint).
    """
    d = repo_path(prompt_dir or PROMPT_DIR)
    f = d / f"{name}.md"
    if f.exists():
        txt = f.read_text(encoding="utf-8").strip()
        if txt:
            return txt
    return default


MISSING_KEY_MSG = ("LỖI: thiếu biến môi trường OPENAI_API_KEY. Bước này gọi LLM nên chạy trên hạ tầng tham chiếu "
                   "(export OPENAI_API_KEY=...; tuỳ chọn OPENAI_BASE_URL=https://<gateway>/v1). "
                   "Thực tập sinh: gửi PR prompts/config; datagen/run_pipeline.sh được chạy trên hạ tầng tham chiếu "
                   "và output được commit vào data/sgod/.")


def require_openai_client():
    """Build the OpenAI client from the environment or exit 2 with a Vietnamese message.

    Every LLM stage MUST go through here so OPENAI_BASE_URL is always honoured.
    """
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print(MISSING_KEY_MSG, file=sys.stderr)
        raise SystemExit(2)
    from openai import OpenAI  # imported lazily: offline stages never need the package
    return OpenAI(api_key=key, base_url=os.environ.get("OPENAI_BASE_URL") or None)


class CallMeter:
    """Counts chat.completions calls and tokens so every run can report cost in its summary line."""

    def __init__(self):
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.errors = 0

    def add(self, resp):
        self.calls += 1
        u = getattr(resp, "usage", None)
        if u is not None:
            self.prompt_tokens += int(getattr(u, "prompt_tokens", 0) or 0)
            self.completion_tokens += int(getattr(u, "completion_tokens", 0) or 0)

    def summary(self):
        return (f"llm_calls={self.calls} prompt_tokens={self.prompt_tokens} "
                f"completion_tokens={self.completion_tokens} errors={self.errors}")


METER = CallMeter()
