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
    # Real geometry, parked offscreen: withdrawn windows report 1x1 widgets, so
    # layout code bails early and the test would prove nothing.
    root.geometry("1240x860+-3200+-3200")

    # Tkinter swallows callback exceptions and only prints them. Trap them so a
    # broken <Configure>/<Map> handler fails the run instead of hiding.
    errors: list[str] = []

    def trap(exc_type, exc, tb):
        errors.append(f"{exc_type.__name__}: {exc}")

    root.report_callback_exception = trap

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

    # empty-state + drop-state painting must not throw
    app.kind = ""
    app._draw_preview()
    root.update()
    app._drop_state(True)
    app._drop_state(False)
    root.update()

    # rounded surfaces must actually paint their shape
    app.kind = "image"
    app._on_section("all")
    root.update()
    for card, _sect, _kinds in app._opt_cards:
        if card.winfo_manager() == "pack":
            assert card.canvas.find_withtag("shape"), f"{card} drew no shape"
            assert card.canvas.cget("height") != "", f"{card} has no height"
    assert app.drop.canvas.find_withtag("shape"), "drop zone drew no shape"

    root.update()
    assert not errors, "Tk callback errors:\n  " + "\n  ".join(errors[:8])

    root.destroy()
    print("gui smoke ok - layout, sections, callbacks, arg build, no Tk errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
