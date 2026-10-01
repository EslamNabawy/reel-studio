"""Smoke-construct the Tk GUI: build, switch media modes and sections, tear down.

Run: python tools/gui_smoke.py
Catches layout/pack errors that a plain import cannot.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "studio"))

import tkinter as tk

import gui


def main() -> int:
    root = tk.Tk()
    root.withdraw()
    app = gui.App(root)
    root.update_idletasks()
    root.update()

    # no media yet
    assert app.kind == "", app.kind
    assert app.card_frame.winfo_manager() == "", "frame card visible with no media"
    assert app.card_video.winfo_manager() == "", "video card visible with no media"
    # section switching, no media
    for s in ("all", "frame", "voice", "text", "output"):
        app._on_section(s)
        root.update()
    assert app.section == "output"

    # simulate each media kind and re-run every section
    for kind in ("image", "video", ""):
        app.kind = kind
        for s in ("all", "frame", "voice", "text", "output"):
            app._on_section(s)
            root.update()
        # declared order must be preserved when showing all
        app._on_section("all")
        root.update()
        order = [c for c, _sect, _kinds in app._opt_cards
                 if c.winfo_manager() == "pack"]
        if kind == "image":
            assert app.card_frame in order and app.card_video not in order
        elif kind == "video":
            assert app.card_video in order and app.card_frame not in order
        else:
            assert app.card_frame not in order and app.card_video not in order

    # option callbacks that touch layout
    app.kind = "image"
    app._on_section("all")
    for fit in ("cover", "contain", "blur"):
        app._on_fit(fit)
        root.update()
    for motion in ("none", "zoom-in", "pan-left"):
        app.motion_seg.set(motion)
        root.update()
    for asp in ("source", "9:16", "1:1"):
        app.aspect_seg.set(asp)
        root.update()
    app.sub_on.set(False)
    app._toggle_subs()
    app.sub_on.set(True)
    app._toggle_subs()
    for narr in ("ai", "raw", "manual", "ai"):
        app._on_narration(narr)
        root.update()

    # args build must not explode
    args = app._build_args()
    assert "--aspect" in args and "--quality" in args, args

    root.destroy()
    print("gui smoke ok — layout, sections, callbacks, arg build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
