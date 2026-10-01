# Contributing

Thanks for helping out. This is a small Windows desktop app — the loop is quick.

## Setup

```bash
git clone https://github.com/EslamNabawy/reel-studio.git
cd reel-studio

python -m venv .venv
.venv\Scripts\activate

pip install -r apps\studio\requirements.txt
pip install pytest
```

`ffmpeg` must be on `PATH`. Verify the toolchain:

```bash
ffmpeg -version
python apps\studio\app.py --models
```

You do **not** need a Gemini key to work on the app or the tests — the key only
affects script rewriting at runtime. Put one in `.env` if you want to exercise
that path.

## Before you open a PR

Run the same three checks CI runs:

```bash
python -m py_compile apps\studio\app.py apps\studio\gui.py \
    apps\studio\voiceover.py apps\studio\models_setup.py apps\caption\caption.py

python -m pytest tests/ -q
python tools\gui_smoke.py
python tools\keystore_check.py
python tools\check_docs.py
python tools\audit_history.py
```

`gui_smoke.py` builds the real Tk window (parked offscreen) and fails on any Tk
callback error, any unpainted rounded surface, and any card-ordering mistake. It
catches the class of bug that a plain import cannot.

`keystore_check.py` proves the key never lands beside the executable, using a
temporary `APPDATA` so it never touches your real profile.

`check_docs.py` asserts that every flag and shortcut in the docs exists in the
code, and that every relative link resolves.

`audit_history.py` scans every blob in git history for leaked credentials.

## Code layout

| Path | Role |
| --- | --- |
| `apps/studio/app.py` | entry point / router — GUI, CLI, model commands |
| `apps/studio/gui.py` | all UI: theme, widgets, layout, worker threads |
| `apps/studio/voiceover.py` | the pipeline; no Tk imports, so it stays testable |
| `apps/studio/keystore.py` | key storage + legacy migration; no Tk, no deps |
| `apps/studio/models_setup.py` | local model status / download |
| `apps/caption/caption.py` | captioning + VQA CLI |
| `tests/` | engine logic tests |
| `tools/` | GUI smoke test, keystore check, docs check, secret scanner |

Two rules worth keeping:

1. **`voiceover.py` must not import Tk.** It runs as a subprocess, so the engine
   stays testable and the UI stays responsive.
2. **Tk is not thread-safe.** Workers put lines on a `queue.Queue`; the main loop
   drains it in `_poll` / `_drain` via `after()`. Never touch a widget off-thread.

And one rule about secrets:

3. **Never write a credential into the app folder.** The key belongs in the
   per-user store (`keystore.py`). A file written next to the exe ends up in
   portable bundles and zips.

## Style

Follow the surrounding code. Concretely:

- 4-space indent, ~90 column soft limit, double quotes.
- f-strings for messages, `pathlib.Path` over string paths.
- Guard anything touching the filesystem or a subprocess with `try/except` and
  degrade rather than crash — the app runs on machines without models or ffmpeg.
- Comments explain *why*, not *what*. No commented-out code.

## Docs must match the code

The README documents the CLI and the keyboard shortcuts. If you add, remove or
rename a flag, update the docs in the same PR — CI will tell you if you forget:

```bash
python tools\dump_cli.py     # prints the current flag surface
python tools\check_docs.py   # fails on any flag/link drift
```

## Pull requests

1. Branch off `main`.
2. Make the change; add or update tests in `tests/`.
3. Keep the three CI checks green locally.
4. Open the PR using the template and say what you verified.

## Reporting bugs

Use the **Bug report** issue template. The most useful details are the Reel
version, your Windows version, whether `ffmpeg` is on `PATH`, whether the local
models are installed (`app.py --models`), and the Activity log copied from the
app.

## Releasing

Maintainers only: bump the version in `apps/studio/install.iss` and
`CHANGELOG.md`, then tag.

```bash
git tag v1.2.0 && git push origin v1.2.0
```

The Release workflow stamps the tag into the installer, runs the checks, and
uploads the bundle plus the installer.
