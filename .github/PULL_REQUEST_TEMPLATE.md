## What this changes

<!-- One or two sentences. Link the issue if there is one: Closes #123 -->

## Type

- [ ] Engine (`apps/studio/voiceover.py`)
- [ ] UI (`apps/studio/gui.py`)
- [ ] Packaging / CI
- [ ] Docs

## Verified locally

<!-- All three must pass before you open the PR -->

- [ ] `python -m py_compile apps\studio\app.py apps\studio\gui.py apps\studio\voiceover.py apps\studio\models_setup.py apps\caption\caption.py`
- [ ] `python -m pytest tests/ -q`
- [ ] `python tools\gui_smoke.py`

## Checklist

- [ ] Tests added or updated for the change
- [ ] README / docs updated if a flag, shortcut or default changed
- [ ] No secrets, no model weights, no build output committed
- [ ] `voiceover.py` still does not import Tk
- [ ] Off-thread code puts work on a queue, never on a widget
