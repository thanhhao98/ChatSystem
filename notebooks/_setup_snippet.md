# Ô "Thiết lập" chuẩn cho mọi notebook (Data và Fine-tune)

Mọi notebook trong `notebooks/` dùng **đúng một ô thiết lập** dưới đây (copy nguyên văn, không sửa) để chạy được
cả trên Colab/Kaggle lẫn trên máy cá nhân. Ô này phải đứng **trước** mọi `pip install -r requirements-train.txt`
vì file pins nằm trong repo.

Ô làm gì:

- **Colab / Kaggle:** đọc `GITHUB_TOKEN` từ *Secrets* (Colab: biểu tượng chìa khoá, bật *Notebook access*; Kaggle:
  *Add-ons → Secrets*), `git clone` repo private `thanhhao98/ChatSystem` (bỏ qua nếu đã có), rồi `chdir` vào `ChatSystem`.
  `GITHUB_TOKEN` là *Personal access token (classic)* với scope `repo` — repo private thuộc tài khoản cá nhân, bạn là collaborator,
  nên token chi tiết theo repo không dùng được (cách tạo: `notebooks/README.md`). Token chỉ nằm trong `.git/config` của VM tạm thời — **không bao giờ** `print` hay `!cat .git/config` vào output notebook.
- **Local:** đi lên từ thư mục hiện tại đến khi gặp `docs/contracts/cli.md` rồi `chdir` vào đó (vì vậy mở notebook
  từ bất kỳ thư mục con nào của repo đều được).
- Đặt biến `REPO` (`pathlib.Path` gốc repo), `GIT_SHA` (`git rev-parse --short HEAD`, hoặc `no-git`), `IN_COLAB`,
  `AUTHOR` (`$GITHUB_USER` → `git config user.name` → `"điền tên"`) và hàm `run(cmd)` để gọi script của repo
  (in lệnh, in output, in `[exit code = N]`, trả về `CompletedProcess`).

Không `pip install` gì trong ô này. Notebook Data chỉ cần stdlib + `matplotlib` (có sẵn trên Colab) + `transformers`
(chỉ tokenizer). Notebook Fine-tune đặt pins ở ô kế tiếp theo `requirements-train.txt`.

```python
# --- Thiết lập (Colab + local) --------------------------------------------------------------
# Colab : read GITHUB_TOKEN from Secrets, clone the private repo (skip if present), chdir into it.
# Local : walk up from the current directory until the repo root (docs/contracts/cli.md) is found.
# Sets REPO (Path), GIT_SHA, IN_COLAB, AUTHOR and a run() helper that calls repo scripts.
import os, shlex, subprocess, sys
from pathlib import Path

REPO_HTTPS = "github.com/thanhhao98/ChatSystem"
MARKER = "docs/contracts/cli.md"          # exists at the root of every checkout

try:
    import google.colab  # noqa: F401
    IN_COLAB = True
except ImportError:
    IN_COLAB = False
IN_KAGGLE = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE"))


def _github_token():
    # Colab Secrets -> Kaggle Secrets -> environment variable. Never print the value.
    if IN_COLAB:
        from google.colab import userdata
        return userdata.get("GITHUB_TOKEN")
    if IN_KAGGLE:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret("GITHUB_TOKEN")
    return os.environ["GITHUB_TOKEN"]


if IN_COLAB or IN_KAGGLE:
    try:
        _token = _github_token()
    except Exception as e:  # SecretNotFoundError / NotebookAccessError / KeyError
        raise RuntimeError(
            "Thiếu secret GITHUB_TOKEN. Colab: biểu tượng chìa khoá (Secrets) -> Add new secret: "
            "Name = GITHUB_TOKEN, Value = Personal access token (classic, scope repo) của tài khoản collaborator "
            "trên thanhhao98/ChatSystem, bật 'Notebook access'. Kaggle: Add-ons -> Secrets -> GITHUB_TOKEN. "
            "Rồi chạy lại ô này.") from e
    if not Path("ChatSystem").exists():
        _r = subprocess.run(["git", "clone", "--quiet", f"https://{_token}@{REPO_HTTPS}", "ChatSystem"],
                            capture_output=True, text=True)
        if _r.returncode != 0:
            raise RuntimeError("git clone thất bại: " + _r.stderr.replace(_token, "<token>"))
    os.chdir("ChatSystem")
    del _token
else:
    _here = Path.cwd().resolve()
    for _cand in [_here, *_here.parents]:
        if (_cand / MARKER).exists():
            os.chdir(_cand)
            break
    else:
        raise FileNotFoundError(f"Không tìm thấy gốc repo (không có {MARKER}) khi đi lên từ {_here}. "
                                "Mở notebook từ bên trong thư mục ChatSystem đã clone.")

REPO = Path.cwd()


def _git(*args):
    # Small helper: run a git command in REPO and return stdout ("" on any failure).
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


GIT_SHA = _git("rev-parse", "--short", "HEAD") or "no-git"
AUTHOR = os.environ.get("GITHUB_USER") or _git("config", "user.name") or "điền tên"


def run(cmd):
    # Run a repo script (list of args), echo the command, stream its output, return CompletedProcess.
    shown = " ".join(shlex.quote(c) for c in cmd).replace(shlex.quote(sys.executable), "python", 1)
    print("$ " + shown)
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if p.stdout:
        print(p.stdout.rstrip())
    if p.stderr:
        print(p.stderr.rstrip())
    print(f"[exit code = {p.returncode}]")
    return p


print(f"REPO      = {REPO}")
print(f"git HEAD  = {GIT_SHA}")
print(f"python    = {sys.version.split()[0]} · Colab = {IN_COLAB} · Kaggle = {IN_KAGGLE} · author = {AUTHOR}")
```

## Quy ước ô cuối "## Tạo báo cáo"

Ô cuối của mọi notebook in **một** khối Markdown bắt đầu bằng

```
## Báo cáo <tên task ClickUp> — <YYYY-MM-DD> — <github user hoặc 'điền tên'>
```

liệt kê đúng những con số mà mục *Tiêu chí hoàn thành* của task yêu cầu (kèm `GIT_SHA`, môi trường Colab/local và lệnh đã chạy).
Intern copy khối này dán vào comment của task. Mẫu:

```python
import datetime
TASK = "Tuần 1 — <tên task như trên ClickUp>"
lines = [
    f"## Báo cáo {TASK} — {datetime.date.today().isoformat()} — {AUTHOR}",
    f"- Notebook: `notebooks/<track>/<file>.ipynb` @ `{GIT_SHA}` · môi trường: {'Colab' if IN_COLAB else 'local'}",
    # ... one bullet per required number ...
]
print("\n".join(lines))
```

## Trước khi commit notebook

Xoá output để repo không chứa kết quả chạy (và không lỡ chứa token):

```bash
jupyter nbconvert --clear-output --inplace notebooks/<track>/<file>.ipynb
```
