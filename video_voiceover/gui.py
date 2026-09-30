import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, ttk

try:
    from PIL import Image as PILImage, ImageFilter, ImageTk
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND = True
except Exception:
    DND = False

FROZEN = bool(getattr(sys, "frozen", False))
BASE = Path(sys.executable).parent if FROZEN else Path(__file__).parent
SCRIPT = Path(__file__).parent / "voiceover.py"

VOICES = [
    "Default (auto)",
    "en-US-AndrewNeural (male)",
    "en-US-AriaNeural (female)",
    "en-US-GuyNeural (male)",
    "en-GB-SoniaNeural (female)",
    "ar-EG-SalmaNeural (female)",
    "ar-EG-ShakirNeural (male)",
    "ar-SA-HamedNeural (male)",
    "ar-SA-ZariyahNeural (female)",
]
VOICE_IDS = {label: label.split(" ")[0] for label in VOICES}

# CLI values, kept next to their UI labels so nothing drifts
ASPECTS = [("source", "Source"), ("16:9", "16:9"), ("9:16", "9:16"),
           ("1:1", "1:1"), ("4:5", "4:5"), ("4:3", "4:3")]
HEIGHTS = [("source", "Auto"), ("2160", "4K"), ("1080", "1080p"),
           ("720", "720p"), ("480", "480p")]
FITS = [("cover", "Fill"), ("contain", "Fit"), ("blur", "Blur BG")]
MOTIONS = [("none", "Still"), ("zoom-in", "Zoom In"), ("zoom-out", "Zoom Out"),
           ("pan-left", "Pan Left"), ("pan-right", "Pan Right")]
QUALITY = [("draft", "Draft"), ("good", "Good"), ("high", "High")]
LANGS = [("auto", "Auto"), ("en", "English"), ("ar", "Arabic")]
NARRATION = [("ai", "AI Captions"), ("raw", "Raw Captions"), ("manual", "My Script")]

C = {
    "bg": "#0A0C11",
    "surface": "#11141C",
    "surface2": "#161A24",
    "elev": "#1C2130",
    "line": "#232A3A",
    "line2": "#2E3648",
    "text": "#E9EDF7",
    "text2": "#A8B2C8",
    "muted": "#6B7794",
    "accent": "#7C5CFF",
    "accent2": "#9A7BFF",
    "accent_dim": "#4B3AA8",
    "cyan": "#35D6ED",
    "green": "#3DDC97",
    "red": "#FF6B6B",
    "amber": "#FFB547",
}
C["line2"] = "#2E3648"

FONT = "Segoe UI"
FONT_DISPLAY = "Segoe UI Variable Display"

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

STAGES = [
    (re.compile(r"source:"), "Reading media"),
    (re.compile(r"frames:"), "Extracting frames"),
    (re.compile(r"Loading BLIP|captioned"), "Analyzing with AI"),
    (re.compile(r"narration"), "Writing narration"),
    (re.compile(r"TTS with"), "Synthesizing voice"),
    (re.compile(r"audio:"), "Mixing audio"),
    (re.compile(r"render:"), "Rendering frame"),
    (re.compile(r"OUTPUT:"), "Done"),
]


def font(size=10, weight="normal", display=False):
    return (FONT_DISPLAY if display else FONT, size, weight)


def ffprobe_info(path):
    """(w, h, duration) via ffprobe, (0, 0, 0.0) on failure."""
    exe = "ffprobe"
    if FROZEN:
        for cand in (BASE / "ffprobe.exe", BASE / "_internal" / "ffprobe.exe"):
            if cand.exists():
                exe = str(cand)
                break
    try:
        out = subprocess.run(
            [exe, "-v", "error", "-print_format", "json",
             "-show_streams", "-show_format", str(path)],
            capture_output=True, timeout=25)
        import json
        data = json.loads(out.stdout.decode(errors="replace") or "{}")
    except Exception:
        return 0, 0, 0.0
    w = h = 0
    dur = 0.0
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            w = int(s.get("width") or 0)
            h = int(s.get("height") or 0)
            break
    try:
        dur = float((data.get("format") or {}).get("duration") or 0.0)
    except (TypeError, ValueError):
        dur = 0.0
    return w, h, dur


def poster_frame(path, out_png, at=1.0):
    """Grab a video poster. Returns True on success."""
    exe = "ffmpeg"
    if FROZEN:
        for cand in (BASE / "ffmpeg.exe", BASE / "_internal" / "ffmpeg.exe"):
            if cand.exists():
                exe = str(cand)
                break
    try:
        out = subprocess.run(
            [exe, "-v", "error", "-y", "-ss", str(at), "-i", str(path),
             "-frames:v", "1", "-vf", "scale=720:-2", str(out_png)],
            capture_output=True, timeout=40)
        return out.returncode == 0 and out_png.exists()
    except Exception:
        return False


# ─────────────────────────────── widgets ───────────────────────────────

class Hover(tk.Frame):
    """Flat button with hover/press states."""

    def __init__(self, master, text, command=None, bg=None, fg=None, hover=None,
                 padx=14, pady=7, radius=0, font_=None, state="normal"):
        super().__init__(master, bg=bg or C["elev"], highlightthickness=1,
                         highlightbackground=C["line"], cursor="")
        self._bg = bg or C["elev"]
        self._hover = hover or C["accent_dim"]
        self._fg = fg or C["text"]
        self._cmd = command
        self._state = state
        self.label = tk.Label(self, text=text, bg=self._bg, fg=self._fg,
                              font=font_ or font(10, "bold"), padx=padx, pady=pady)
        self.label.pack()
        for w in (self, self.label):
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)
            w.bind("<Button-1>", self._click)
        self.set_state(state)

    def _set(self, bg, fg):
        self.configure(bg=bg, highlightbackground=bg)
        self.label.configure(bg=bg, fg=fg)

    def _enter(self, _=None):
        if self._state == "normal":
            self._set(self._hover, self._fg)

    def _leave(self, _=None):
        if self._state == "normal":
            self._set(self._bg, self._fg)

    def _click(self, _=None):
        if self._state == "normal" and self._cmd:
            self._cmd()

    def set_state(self, state):
        self._state = state
        if state == "disabled":
            self._set(C["surface2"], C["muted"])
            self.configure(cursor="")
            self.label.configure(cursor="")
        else:
            self._set(self._bg, self._fg)
            self.label.configure(cursor="hand2")


class Chip(tk.Frame):
    """One segment inside a Segmented row."""

    def __init__(self, master, text, value, group, command, padx=13):
        super().__init__(master, bg=C["surface2"], cursor="hand2")
        self.value = value
        self.group = group
        self.cmd = command
        self.lbl = tk.Label(self, text=text, bg=C["surface2"], fg=C["text2"],
                            font=font(9), padx=padx, pady=5, cursor="hand2")
        self.lbl.pack()
        for w in (self, self.lbl):
            w.bind("<Button-1>", lambda e: self._fire())
            w.bind("<Enter>", lambda e: self._hover(True))
            w.bind("<Leave>", lambda e: self._hover(False))
        self.active = False

    def _fire(self):
        self.group.select(self.value)
        if self.cmd:
            self.cmd(self.value)

    def _hover(self, on):
        if self.active:
            return
        col = C["elev"] if on else C["surface2"]
        self.configure(bg=col)
        self.lbl.configure(bg=col, fg=C["text"] if on else C["text2"])

    def set_active(self, on):
        self.active = on
        bg = C["accent"] if on else C["surface2"]
        fg = "#ffffff" if on else C["text2"]
        self.configure(bg=bg, highlightthickness=0)
        self.lbl.configure(bg=bg, fg=fg, font=font(9, "bold" if on else "normal"))


class Segmented(tk.Frame):
    """Row of chips, one active at a time."""

    def __init__(self, master, options, default, command=None):
        super().__init__(master, bg=C["surface"])
        self.options = options
        self.chips = {}
        self.value = None
        self.cmd = command
        for value, label in options:
            c = Chip(self, label, value, self, command)
            c.pack(side="left", padx=(0, 6))
            self.chips[value] = c
        self.set(default)

    def select(self, value):
        if value not in self.chips:
            return
        self.value = value
        for v, c in self.chips.items():
            c.set_active(v == value)

    def get(self):
        return self.value

    def set(self, value):
        self.select(value)


class Card(tk.Frame):
    """Titled panel. body is where content goes."""

    def __init__(self, master, title, subtitle="", pady=14):
        super().__init__(master, bg=C["surface"], highlightthickness=1,
                         highlightbackground=C["line"])
        head = tk.Frame(self, bg=C["surface"])
        head.pack(fill="x", padx=16, pady=(pady, 0))
        tk.Label(head, text=title, bg=C["surface"], fg=C["text"],
                 font=font(10, "bold")).pack(side="left")
        if subtitle:
            tk.Label(head, text=subtitle, bg=C["surface"], fg=C["muted"],
                     font=font(9)).pack(side="right")
        self.body = tk.Frame(self, bg=C["surface"])
        self.body.pack(fill="x", padx=16, pady=(10, pady))

    def hide(self):
        self.pack_forget()

    def show(self):
        self.pack(fill="x", pady=(0, 12))


class Field(tk.Frame):
    """Label above control."""

    def __init__(self, master, label):
        super().__init__(master, bg=C["surface"])
        tk.Label(self, text=label, bg=C["surface"], fg=C["text2"],
                 font=font(9, "bold")).pack(side="left")
        self.control = tk.Frame(self, bg=C["surface"])
        self.control.pack(fill="x", pady=(6, 0))


class Slider(tk.Frame):
    """Thin custom slider with a draggable knob and value readout."""

    def __init__(self, master, lo, hi, value, command, fmt="{:.2f}", width=200,
                 live_status=None):
        super().__init__(master, bg=C["surface"], height=26, cursor="hand2")
        self.lo, self.hi, self.value = lo, hi, value
        self.cmd = command
        self.fmt = fmt if callable(fmt) else (lambda v, _f=fmt: _f.format(v))
        self.live_status = live_status
        self.width_px = width
        self.readout = tk.Label(self, text=self.fmt(value), bg=C["surface"], fg=C["accent2"],
                                font=("Consolas", 9, "bold"))
        self.readout.pack(side="right", padx=(8, 0))
        self.canvas = tk.Canvas(self, height=26, bg=C["surface"],
                                highlightthickness=0, width=width)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._draw())
        self.canvas.bind("<Button-1>", self._click)
        self.canvas.bind("<B1-Motion>", self._drag)
        self._draw()

    def _pos(self):
        span = max(1e-9, self.hi - self.lo)
        return (self.value - self.lo) / span * (self.width_px - 16) + 8

    def _draw(self):
        self.width_px = self.canvas.winfo_width() or self.width_px
        c = self.canvas
        c.delete("all")
        y = 13
        c.create_line(8, y, self.width_px - 8, y, fill=C["line"], width=3)
        x = self._pos()
        c.create_line(8, y, x, y, fill=C["accent"], width=3)
        c.create_oval(x - 6, y - 6, x + 6, y + 6, fill=C["text"],
                      outline=C["accent"], width=2)
        self.readout.configure(text=self.fmt(self.value))

    def set(self, value, notify=False):
        self.value = max(self.lo, min(self.hi, value))
        self._draw()
        if notify and self.cmd:
            self.cmd(self.value)
        if notify and self.live_status:
            self.status.set(self.live_status(self.value))

    def get(self):
        return self.value

    def _click(self, e):
        self._set_from_x(e.x)

    def _drag(self, e):
        self._set_from_x(e.x)

    def _set_from_x(self, x):
        frac = (x - 8) / max(1, (self.width_px - 16))
        self.set(self.lo + frac * (self.hi - self.lo), notify=True)


class ScrollPane(tk.Frame):
    """Vertically scrollable column."""

    def __init__(self, master, bg=None):
        super().__init__(master, bg=bg or C["bg"])
        self.canvas = tk.Canvas(self, bg=bg or C["bg"], highlightthickness=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg or C["bg"])
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        _bind_wheel(self, self.canvas)

    def _on_inner(self, _=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)

    def _on_scroll(self, first, last):
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.bar.pack_forget()
        else:
            self.bar.pack(side="right", fill="y")
        self.bar.set(first, last)


def _bind_wheel(root, widget):
    def on_wheel(e):
        try:
            if widget.winfo_exists() and widget.winfo_ismapped():
                widget.yview_scroll(int(-1 * (e.delta / 120)), "units")
        except Exception:
            pass
    root.bind_all("<MouseWheel>", on_wheel, add="+")


# ─────────────────────────────── app ───────────────────────────────

class App:
    def __init__(self, root):
        self.root = root
        root.title("Reel — AI Voice-Over Studio")
        root.geometry("1240x860")
        root.minsize(1080, 720)
        root.configure(bg=C["bg"])
        icon = BASE / "icon.ico"
        if icon.exists():
            try:
                root.iconbitmap(icon)
            except Exception:
                pass

        self.proc = None
        self.log_queue = queue.Queue()
        self.info_queue = queue.Queue()
        self.running = False
        self.kind = ""            # "video" | "image" | ""
        self.src_info = (0, 0, 0.0)
        self.poster = None
        self._pending_poster = None
        self.preview_photo = None
        self._preview_job = None

        # state
        self.media_path = tk.StringVar()
        self.lang = tk.StringVar()
        self.voice = tk.StringVar(value=VOICES[0])
        self.interval = tk.StringVar(value="2")
        self.max_frames = tk.StringVar(value="0")
        self.manual = tk.StringVar()
        self.zoom = 1.0
        self.fx = 0.5
        self.fy = 0.5
        self.sub_size = 18
        self.sub_margin = 28
        self.rate = 0

        self.lang_seg = None
        self.aspect_seg = None
        self.height_seg = None
        self.fit_seg = None
        self.motion_seg = None
        self.quality_seg = None
        self.narr_seg = None
        self.sub_switch = None
        self.status = tk.StringVar(value="Drop a video or image to begin.")
        self.stage = tk.StringVar(value="Idle")

        self._style()
        self._build()
        self._apply_mode()
        root.bind("<Control-o>", lambda e: self.browse())
        root.bind("<Control-Return>", lambda e: self.start())
        root.bind("<Escape>", lambda e: self.cancel())
        root.after(80, self._poll)

    # ---------- style ----------

    def _style(self):
        st = ttk.Style(self.root)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("Vertical.TScrollbar", background=C["line"],
                     troughcolor=C["bg"], arrowcolor=C["muted"],
                     bordercolor=C["bg"], relief="flat")
        st.configure("TCombobox", fieldbackground=C["surface2"],
                     background=C["surface2"], foreground=C["text"],
                     arrowcolor=C["muted"], bordercolor=C["line"],
                     lightcolor=C["line"], darkcolor=C["line"], relief="flat")
        st.map("TCombobox",
               fieldbackground=[("readonly", C["surface2"])],
               foreground=[("readonly", C["text"])],
               bordercolor=[("focus", C["accent"])])
        st.configure("TFrame", background=C["surface"])
        st.configure("Reel.Horizontal.TProgressbar", troughcolor=C["surface2"],
                     background=C["accent"], bordercolor=C["surface2"],
                     lightcolor=C["accent"], darkcolor=C["accent"])

    # ---------- layout ----------

    def _build(self):
        root = self.root

        hdr = tk.Frame(root, bg=C["surface"], height=62)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="◉", bg=C["surface"], fg=C["accent"],
                 font=font(17, "bold", display=True)).pack(side="left", padx=(18, 8))
        tk.Label(hdr, text="Reel", bg=C["surface"], fg=C["text"],
                 font=font(15, "bold", display=True)).pack(side="left")
        tk.Label(hdr, text="AI voice-over studio", bg=C["surface"], fg=C["muted"],
                 font=font(9)).pack(side="left", padx=(10, 0))
        tk.Label(hdr, text="frames → AI captions → narration → voice + subtitles",
                 bg=C["surface"], fg=C["text2"], font=font(9)).pack(side="right", padx=18)

        body = tk.Frame(root, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=14)

        left = tk.Frame(body, bg=C["bg"], width=470)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self._build_left(left)

        right = tk.Frame(body, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))
        self.pane = ScrollPane(right)
        self.pane.pack(fill="both", expand=True)
        col = self.pane.inner
        self._build_options(col)

        self._build_footer(root)

    def _build_left(self, parent):
        # drop zone
        self.drop = tk.Frame(parent, bg=C["surface"], height=64,
                             highlightthickness=1, highlightbackground=C["line"],
                             cursor="hand2")
        self.drop.pack(fill="x")
        self.drop.pack_propagate(False)
        self.drop.bind("<Button-1>", lambda e: self.browse())
        inner = tk.Frame(self.drop, bg=C["surface"])
        inner.place(relx=0.5, rely=0.5, anchor="center")
        self.drop_lbl = tk.Label(inner, text="Drop video or image", bg=C["surface"],
                                 fg=C["text"], font=font(10, "bold"))
        self.drop_lbl.pack()
        tk.Label(inner, text="click to browse  ·  mp4 mov avi mkv webm  |  jpg png webp",
                 bg=C["surface"], fg=C["muted"], font=font(8)).pack()
        if DND and self._dnd_ready(self.root):
            try:
                self.drop.drop_target_register(DND_FILES)
                self.drop.dnd_bind("<<Drop>>", self._on_drop)
                self.drop.dnd_bind("<<DropEnter>>", lambda e: self._drop_state(True))
                self.drop.dnd_bind("<<DropLeave>>", lambda e: self._drop_state(False))
            except Exception:
                pass

        # file chip
        frow = tk.Frame(parent, bg=C["bg"])
        frow.pack(fill="x", pady=(8, 10))
        self.kind_chip = tk.Label(frow, text="  NO MEDIA  ", bg=C["surface2"],
                                  fg=C["muted"], font=("Consolas", 9, "bold"))
        self.kind_chip.pack(side="left")
        self.path_lbl = tk.Label(frow, text="—", bg=C["bg"], fg=C["text2"],
                                 font=("Consolas", 8), anchor="w")
        self.path_lbl.pack(side="left", padx=8, fill="x", expand=True)

        # preview card
        pc = tk.Frame(parent, bg=C["surface"], highlightthickness=1,
                      highlightbackground=C["line"])
        pc.pack(fill="x")
        ph = tk.Frame(pc, bg=C["surface"], height=34)
        ph.pack(fill="x", padx=14, pady=(12, 0))
        ph.pack_propagate(False)
        tk.Label(ph, text="PREVIEW", bg=C["surface"], fg=C["text2"],
                 font=font(9, "bold")).pack(side="left")
        self.preview_meta = tk.Label(ph, text="", bg=C["surface"], fg=C["muted"],
                                     font=("Consolas", 8))
        self.preview_meta.pack(side="right")

        self.preview = tk.Canvas(pc, bg=C["surface"], height=215, highlightthickness=0,
                                 cursor="hand2")
        self.preview.pack(fill="x", padx=14, pady=10)
        self.preview.bind("<Configure>", lambda e: self._draw_preview())
        self.preview.bind("<Button-1>", self._preview_click)
        self.preview.bind("<Motion>", self._preview_motion)
        self.hint = tk.Label(pc, text="Click the preview to set the focal point",
                             bg=C["surface"], fg=C["muted"], font=font(8))
        self.hint.pack(pady=(0, 12))

        # run controls
        act = tk.Frame(parent, bg=C["bg"])
        act.pack(fill="x", pady=(12, 0))
        self.start_btn = Hover(act, "▶   Generate", command=self.start,
                               bg=C["accent"], hover=C["accent2"],
                               padx=20, pady=10, font_=font(11, "bold"))
        self.start_btn.pack(side="left")
        self.cancel_btn = Hover(act, "■  Cancel", command=self.cancel,
                                bg=C["surface2"], fg=C["red"],
                                padx=12, pady=10, state="disabled")
        self.cancel_btn.pack(side="left", padx=(8, 0))
        Hover(act, "Open output", command=self.open_output,
              padx=12, pady=10).pack(side="right")

        # stage strip
        strip = tk.Frame(parent, bg=C["surface"], highlightthickness=1,
                         highlightbackground=C["line"])
        strip.pack(fill="x", pady=(12, 0))
        self.stage_lbl = tk.Label(strip, textvariable=self.stage, bg=C["surface"],
                                  fg=C["cyan"], font=font(10, "bold"), anchor="w")
        self.stage_lbl.pack(fill="x", padx=14, pady=(12, 0))
        self.dots = tk.Frame(strip, bg=C["surface"])
        self.dots.pack(fill="x", padx=14, pady=(8, 0))
        for name in ["Read", "Frames", "Vision", "Script", "Voice", "Mix", "Render"]:
            d = tk.Label(self.dots, text=name, bg=C["surface"], fg=C["line"],
                         font=("Consolas", 8, "bold"))
            d.pack(side="left")
        self.bar = ttk.Progressbar(strip, style="Reel.Horizontal.TProgressbar",
                                   mode="determinate", maximum=100)
        self.bar.pack(fill="x", padx=14, pady=(10, 14))

        # log
        lf = tk.Frame(parent, bg=C["surface"], highlightthickness=1,
                      highlightbackground=C["line"])
        lf.pack(fill="both", expand=True, pady=(12, 0))
        lh = tk.Frame(lf, bg=C["surface"])
        lh.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(lh, text="ACTIVITY", bg=C["surface"], fg=C["text2"],
                 font=font(9, "bold")).pack(side="left")
        Hover(lh, "Clear", command=self._clear_log, padx=10,
              pady=3, font_=font(8)).pack(side="right")
        inner = tk.Frame(lf, bg=C["surface"])
        inner.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self.log = tk.Text(inner, wrap="word", state="disabled", bd=0, height=7,
                           bg=C["surface"], fg=C["text2"], insertbackground=C["text"],
                           font=("Consolas", 8), selectbackground=C["accent"],
                           relief="flat", padx=8, pady=8)
        sb = ttk.Scrollbar(inner, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        for tag, col in [("err", C["red"]), ("out", C["green"]), ("cap", C["cyan"]),
                         ("dim", C["muted"]), ("cmd", C["amber"])]:
            self.log.tag_configure(tag, foreground=col)

    def _build_options(self, col):
        # voice card
        c1 = Card(col, "Language & voice")
        c1.pack(fill="x", pady=(0, 12))
        r1 = tk.Frame(c1.body, bg=C["surface"])
        r1.pack(fill="x")
        self.lang_seg = Segmented(r1, LANGS, "auto", command=self._set_lang)
        self.lang_seg.pack(side="left")

        r2 = tk.Frame(c1.body, bg=C["surface"])
        r2.pack(fill="x", pady=(12, 0))
        tk.Label(r2, text="VOICE", bg=C["surface"], fg=C["text2"],
                 font=font(8, "bold")).pack(side="left")
        vc = ttk.Combobox(r2, textvariable=self.voice, values=VOICES,
                          state="readonly", width=30, font=font(9))
        vc.pack(side="left", padx=10)
        self.rate_sl = Slider(r2, -30, 40, 0, self._set_rate, "{:+.0f}%", 130)
        self.rate_sl.pack(side="left")
        tk.Label(r2, text="rate", bg=C["surface"], fg=C["muted"],
                 font=font(8)).pack(side="left", padx=(6, 0))

        # narration card
        c2 = Card(col, "Narration source")
        c2.pack(fill="x", pady=(0, 12))
        self.narr_seg = Segmented(c2.body, NARRATION, "ai", command=self._on_narration)
        self.narr_seg.pack(anchor="w")
        self.narr_hint = tk.Label(c2.body, text="BLIP describes frames, Gemini writes the script",
                                  bg=C["surface"], fg=C["muted"], font=font(8))
        self.narr_hint.pack(anchor="w", pady=(8, 0))
        self.manual_box = tk.Text(c2.body, height=4, bd=0, wrap="word",
                                  bg=C["surface2"], fg=C["text"],
                                  insertbackground=C["accent"],
                                  font=("Segoe UI", 10), padx=10, pady=8,
                                  relief="flat", highlightthickness=1,
                                  highlightbackground=C["line"])

        # video card (only for video)
        self.card_video = Card(col, "Frame sampling", "videos only")
        self.card_video.pack(fill="x", pady=(0, 12))
        vr = tk.Frame(self.card_video.body, bg=C["surface"])
        vr.pack(fill="x")
        f1 = Field(vr, "Sample every")
        f1.pack(side="left", fill="x", expand=True, padx=(0, 16))
        self.interval_sl = Slider(f1.control, 0.5, 10, 2.0, self._set_interval, "{:.1f} s")
        self.interval_sl.pack(fill="x")
        f2 = Field(vr, "Max frames")
        f2.pack(side="left", fill="x", expand=True)
        self.maxframes_sl = Slider(f2.control, 0, 60, 0, self._set_maxframes, "{:.0f}")
        self.maxframes_sl.pack(fill="x")

        # image frame card (only for image)
        self.card_frame = Card(col, "Frame", "images only")
        self.card_frame.pack(fill="x", pady=(0, 12))

        self.aspect_seg = Segmented(self.card_frame.body, ASPECTS, "source",
                                    command=lambda v: self._draw_preview())
        self.aspect_seg.pack(anchor="w")

        r3 = tk.Frame(self.card_frame.body, bg=C["surface"])
        r3.pack(fill="x", pady=(12, 0))
        self.height_seg = Segmented(r3, HEIGHTS, "source",
                                    command=lambda v: self._draw_preview())
        self.height_seg.pack(side="left")
        tk.Label(r3, text="  height", bg=C["surface"], fg=C["muted"],
                 font=font(8)).pack(side="left")

        tk.Label(self.card_frame.body, text="FIT", bg=C["surface"], fg=C["text2"],
                 font=font(8, "bold")).pack(anchor="w", pady=(14, 6))
        self.fit_seg = Segmented(self.card_frame.body, FITS, "cover",
                                 command=self._on_fit)
        self.fit_seg.pack(anchor="w")

        f3 = Field(self.card_frame.body, "Zoom")
        f3.pack(fill="x", pady=(14, 0))
        self.zoom_sl = Slider(f3.control, 1.0, 2.0, 1.0, self._set_zoom, "{:.2f}×")
        self.zoom_sl.pack(fill="x")

        tk.Label(self.card_frame.body, text="MOTION", bg=C["surface"], fg=C["text2"],
                 font=font(8, "bold")).pack(anchor="w", pady=(14, 6))
        self.motion_seg = Segmented(self.card_frame.body, MOTIONS, "none",
                                    command=lambda v: self._draw_preview())
        self.motion_seg.pack(anchor="w")

        f4 = Field(self.card_frame.body, "Minimum length")
        f4.pack(fill="x", pady=(14, 0))
        self.min_sl = Slider(f4.control, 0, 60, 0, self._set_min, "{:.0f} s",
                             live_status=lambda v: (f"Minimum clip length {int(round(v))}s"
                                                   if v else "Minimum length: auto"))
        self.min_sl.pack(fill="x")
        self.min_val = 0.0

        # subtitles
        self.card_sub = Card(col, "Subtitles")
        self.card_sub.pack(fill="x", pady=(0, 12))
        sr = tk.Frame(self.card_sub.body, bg=C["surface"])
        sr.pack(fill="x")
        self.sub_on = tk.BooleanVar(value=True)
        sw = tk.Checkbutton(sr, text="Burn subtitles", variable=self.sub_on,
                            bg=C["surface"], fg=C["text2"], selectcolor=C["surface2"],
                            activebackground=C["surface"], activeforeground=C["text"],
                            font=font(9), cursor="hand2",
                            command=self._toggle_subs)
        sw.pack(side="left")
        f5 = Field(sr, "Size")
        f5.pack(side="left", fill="x", expand=True, padx=(20, 12))
        self.sub_size_sl = Slider(f5.control, 10, 48, 18, self._set_sub_size, "{:.0f}")
        self.sub_size_sl.pack(fill="x")
        f6 = Field(self.card_sub.body, "Bottom margin")
        f6.pack(fill="x", pady=(12, 0))
        self.sub_margin_sl = Slider(f6.control, 0, 120, 28, self._set_sub_margin, "{:.0f}")
        self.sub_margin_sl.pack(fill="x")

        # output
        c3 = Card(col, "Output")
        c3.pack(fill="x", pady=(0, 12))
        self.quality_seg = Segmented(c3.body, QUALITY, "good")
        self.quality_seg.pack(anchor="w")
        tk.Label(c3.body, text="Draft = fast preview  ·  Good = default  ·  High = CRF 19",
                 bg=C["surface"], fg=C["muted"], font=font(8)).pack(anchor="w", pady=(8, 0))

    def _build_footer(self, root):
        bar = tk.Frame(root, bg=C["surface"], height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Label(bar, textvariable=self.status, bg=C["surface"], fg=C["text2"],
                 font=font(8), anchor="w").pack(fill="x", padx=16)
        self.shortcut_lbl = tk.Label(bar, text="Ctrl+O browse   ·   Ctrl+Enter generate   ·   Esc cancel",
                                     bg=C["surface"], fg=C["muted"], font=font(8))
        self.shortcut_lbl.pack(side="right", padx=16)

    # ---------- option callbacks ----------

    def _on_fit(self, v):
        self.hint.configure({
            "cover": "Click the preview to move the focal point",
            "contain": "Whole image is kept — no focal point needed",
            "blur": "Blurred backdrop fills the frame behind the image",
        }.get(v, ""))
        self._draw_preview()

    def _set_rate(self, v):
        self.rate = int(round(v))
        self.status.set(f"Speech rate {self.rate:+d}%")

    def _set_lang(self, v):
        self.lang_var = v
        self.status.set(f"Language: {v}")

    def _set_interval(self, v):
        self.interval.set(f"{v:.1f}")

    def _set_maxframes(self, v):
        self.max_frames.set(str(int(round(v))))

    def _set_zoom(self, v):
        self.zoom = round(v, 2)
        self._draw_preview()

    def _set_min(self, v):
        self.min_val = round(v, 1)

    def _set_sub_size(self, v):
        self.sub_size = int(round(v))

    def _set_sub_margin(self, v):
        self.sub_margin = int(round(v))

    def _on_narration(self, v):
        if v == "manual":
            self.manual_box.pack(fill="x", pady=(10, 0))
            self.narr_hint.configure(text="One segment per line — becomes the voice script")
        else:
            self.manual_box.pack_forget()
            self.narr_hint.configure(
                text="BLIP describes frames, Gemini writes the script" if v == "ai"
                else "Speak the BLIP captions verbatim, no Gemini rewrite")

    def _toggle_subs(self):
        on = self.sub_on.get()
        col = C["text2"] if on else C["muted"]
        for sl in (self.sub_size_sl, self.sub_margin_sl):
            sl.readout.configure(fg=C["accent2"] if on else C["muted"])
            sl.canvas.configure(cursor="hand2" if on else "arrow")

    # ---------- media selection ----------

    @staticmethod
    def _dnd_ready(root):
        try:
            return bool(root.tk.call("info", "commands", "tkdnd::drop_target"))
        except Exception:
            return False

    def _drop_state(self, on):
        self.drop.configure(highlightbackground=C["accent"] if on else C["line"])
        self.drop_lbl.configure(fg=C["accent"] if on else C["text"])

    def _on_drop(self, event):
        self._drop_state(False)
        raw = event.data.strip()
        paths = [p[1:-1] if p.startswith("{") and p.endswith("}") else p
                 for p in re.findall(r"\{[^}]+\}|[^\s]+", raw)]
        if paths:
            self._set_path(paths[0])

    def browse(self):
        p = filedialog.askopenfilename(
            title="Choose video or image",
            filetypes=[("Media", "*.mp4 *.mov *.avi *.mkv *.webm "
                                 "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
                       ("Video", "*.mp4 *.mov *.avi *.mkv *.webm"),
                       ("Image", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
                       ("All", "*.*")])
        if p:
            self._set_path(p)

    def _set_path(self, p: str):
        path = Path(p)
        if not path.exists():
            self.status.set(f"Not found: {p}")
            return
        self.media_path.set(str(path))
        ext = path.suffix.lower()
        if ext in IMAGE_EXTS:
            self.kind = "image"
            chip, col = "  IMAGE  ", C["amber"]
        elif ext in VIDEO_EXTS:
            self.kind = "video"
            chip, col = "  VIDEO  ", C["cyan"]
        else:
            self.kind = ""
            chip, col = "  UNSUPPORTED  ", C["red"]
        self.kind_chip.configure(text=chip, fg=col)
        self.path_lbl.configure(text=path.name, fg=C["text"])
        size_kb = path.stat().st_size / 1024
        size = f"{size_kb / 1024:.1f} MB" if size_kb >= 1024 else f"{size_kb:.0f} KB"
        self.status.set(f"{path.name}  ·  {size}")
        self.poster = None
        threading.Thread(target=self._probe_worker, args=(path,), daemon=True).start()
        self._apply_mode()

    def _probe_worker(self, path):
        if self.kind == "image":
            info = (0, 0, 0.0)
            try:
                if HAVE_PIL:
                    with PILImage.open(path) as im:
                        info = (im.width, im.height, 0.0)
            except Exception:
                info = (0, 0, 0.0)
            poster = None
        else:
            info = ffprobe_info(path)
            poster = None
            if HAVE_PIL:
                tmp = Path(tempfile.gettempdir()) / f"reel_poster_{os.getpid()}.png"
                if poster_frame(path, tmp):
                    poster = tmp
        # Tk is not thread-safe: hand results to the main loop
        self.info_queue.put((str(path), info, poster))

    def _set_info(self, info, path=None):
        if path and path != self.media_path.get():
            return  # user already picked something else
        if path:
            self.poster = self._pending_poster
        self.src_info = info
        w, h, dur = info
        if self.kind == "image":
            self.preview_meta.configure(text=f"{w}x{h}" if w else "")
        else:
            mins = f"{int(dur // 60)}:{int(dur % 60):02d}" if dur else "?"
            self.preview_meta.configure(text=f"{w}x{h}  ·  {mins}" if w else "")
        if self.kind == "image" and self.aspect_seg.get() == "source" and w and h:
            self.aspect_seg.set("source")
        self._draw_preview()

    def _apply_mode(self):
        if self.kind == "image":
            self.card_video.pack_forget()
            self.card_frame.pack(fill="x", pady=(0, 12), before=self.card_sub)
            self.hint.configure(text="Click the preview to move the focal point")
        elif self.kind == "video":
            self.card_frame.pack_forget()
            self.card_video.pack(fill="x", pady=(0, 12), before=self.card_sub)
            self.hint.configure(text="Video frame — preview shows a poster still")
        else:
            self.card_video.pack_forget()
            self.card_frame.pack_forget()
            self.hint.configure(text="Choose a video or image")
        self.manual_box.pack_forget()
        self.preview.delete("all")
        if not HAVE_PIL:
            self.preview.create_text(
                200, 180, text="preview needs Pillow\npip install Pillow",
                fill=C["muted"], font=font(9), justify="center")

    # ---------- preview ----------

    def _out_size(self):
        """(w, h) of the render target from the aspect/height segments."""
        src_w, src_h, _ = self.src_info
        if not src_w or not src_h:
            src_w, src_h = 1920, 1080
        aspect = self.aspect_seg.get() if self.kind == "image" else "source"
        height = self.height_seg.get() if self.kind == "image" else "source"
        ratios = {"source": src_w / src_h, "16:9": 16 / 9, "9:16": 9 / 16,
                  "1:1": 1.0, "4:5": 4 / 5, "4:3": 4 / 3}
        ar = ratios.get(aspect, src_w / src_h)
        if height == "source":
            base = max(src_w, src_h)
        else:
            base = int(height)
        w = base * ar
        w = max(2, int(round(w / 2)) * 2)
        h = max(2, int(round(w / ar / 2)) * 2)
        if w > 3840:
            w = 3840
            h = max(2, int(round(w / ar / 2)) * 2)
        return w, h

    def _load_preview_image(self):
        if not HAVE_PIL or not self.media_path.get():
            return None
        try:
            if self.poster and Path(self.poster).exists():
                return PILImage.open(self.poster).convert("RGB")
            return PILImage.open(self.media_path.get()).convert("RGB")
        except Exception:
            return None

    def _draw_preview(self):
        c = self.preview
        c.delete("all")
        wpx = c.winfo_width() or 430
        hpx = c.winfo_height() or 360
        if wpx < 60 or hpx < 60:
            return  # not laid out yet
        if not self.kind or not HAVE_PIL:
            c.create_text(wpx / 2, hpx / 2, text="no media", fill=C["muted"], font=font(9))
            return
        img = self._load_preview_image()
        if img is None:
            c.create_text(wpx / 2, hpx / 2, text="cannot read file", fill=C["muted"], font=font(9))
            return

        ow, oh = self._out_size()
        pad = 16
        box_w, box_h = wpx - pad * 2, hpx - pad * 2
        ar = ow / oh
        if box_w / box_h > ar:
            box_w = box_h * ar
        else:
            box_h = box_w / ar
        x0, y0 = (wpx - box_w) / 2, (hpx - box_h) / 2
        rect = (x0, y0, x0 + box_w, y0 + box_h)
        c.create_rectangle(*rect, fill="#05070B", outline=C["line"], width=1)

        fit = self.fit_seg.get() if self.kind == "image" else "cover"
        zoom = self.zoom if self.kind == "image" else 1.0
        iw, ih = img.size

        if fit == "blur":
            bg = img.copy()
            bg.thumbnail((int(box_w), int(box_h)))
            bg = bg.filter(ImageFilter.GaussianBlur(18))
            bg = bg.resize((max(1, int(box_w)), max(1, int(box_h))))
            self._blit(c, bg, x0, y0)
            fg = img.copy()
            fg.thumbnail((max(1, int(box_w)), max(1, int(box_h))))
            self._blit(c, fg, x0 + (box_w - fg.width) / 2, y0 + (box_h - fg.height) / 2)
        else:
            if fit == "contain":
                view = img.copy()
                view.thumbnail((max(1, int(box_w)), max(1, int(box_h))))
                self._blit(c, view, x0 + (box_w - view.width) / 2, y0 + (box_h - view.height) / 2)
            else:
                scale = max(box_w / iw, box_h / ih) * zoom
                disp_w, disp_h = iw * scale, ih * scale
                cw, ch = min(disp_w, box_w), min(disp_h, box_h)
                sx = (disp_w * self.fx) - cw / 2
                sy = (disp_h * self.fy) - ch / 2
                sx = max(0, min(disp_w - cw, sx))
                sy = max(0, min(disp_h - ch, sy))
                crop = img.crop((int(sx), int(sy), int(sx + cw), int(sy + ch)))
                crop = crop.resize((max(1, int(box_w)), max(1, int(box_h))))
                self._blit(c, crop, x0, y0)

        c.create_rectangle(*rect, outline=C["line"], width=1)
        # thirds guides
        for i in (1, 2):
            c.create_line(x0 + box_w * i / 3, y0, x0 + box_w * i / 3, y0 + box_h,
                          fill="#FFFFFF", stipple="gray25")
            c.create_line(x0, y0 + box_h * i / 3, x0 + box_w, y0 + box_h * i / 3,
                          fill="#FFFFFF", stipple="gray25")
        if self.kind == "image" and fit == "cover":
            fx_px = x0 + box_w * self.fx
            fy_px = y0 + box_h * self.fy
            c.create_line(fx_px - 9, fy_px, fx_px + 9, fy_px, fill=C["amber"], width=2)
            c.create_line(fx_px, fy_px - 9, fx_px, fy_px + 9, fill=C["amber"], width=2)
            c.create_oval(fx_px - 12, fy_px - 12, fx_px + 12, fy_px + 12,
                          outline=C["amber"], width=1)
        c.create_text(x0, y0 - 6, anchor="sw", text=f"{ow}x{oh}",
                      fill=C["muted"], font=("Consolas", 8))

    def _blit(self, canvas, img, x, y):
        photo = ImageTk.PhotoImage(img)
        self.preview_photo = photo
        canvas.create_image(x, y, image=photo, anchor="nw")

    def _preview_hit(self, event):
        c = self.preview
        wpx = c.winfo_width()
        hpx = c.winfo_height()
        ow, oh = self._out_size()
        pad = 16
        bw, bh = wpx - pad * 2, hpx - pad * 2
        ar = ow / oh
        if bw / bh > ar:
            bw = bh * ar
        else:
            bh = bw / ar
        x0, y0 = (wpx - bw) / 2, (hpx - bh) / 2
        return event.x, event.y, x0, y0, bw, bh

    def _preview_click(self, event):
        if self.kind != "image":
            return
        if self.fit_seg.get() != "cover":
            self.status.set("Focal point applies to Fill mode")
            return
        x, y, x0, y0, bw, bh = self._preview_hit(event)
        self.fx = max(0.0, min(1.0, (x - x0) / bw))
        self.fy = max(0.0, min(1.0, (y - y0) / bh))
        self._draw_preview()

    def _preview_motion(self, event):
        if self.kind == "image" and self.fit_seg.get() == "cover":
            self.preview.configure(cursor="crosshair")
        else:
            self.preview.configure(cursor="")

    # ---------- pipeline ----------

    def _build_args(self):
        a = ["--lang", getattr(self, "lang_var", "auto")]
        voice = VOICE_IDS.get(self.voice.get(), "Default")
        if voice != "Default":
            a += ["--voice", voice]
        if self.rate:
            a += ["--rate", f"{self.rate:+d}%"]
        if not self.sub_on.get():
            a += ["--no-subtitles"]
        a += ["--sub-size", str(self.sub_size), "--sub-margin-v", str(self.sub_margin)]
        a += ["--quality", self.quality_seg.get()]

        if self.narr_seg.get() == "manual":
            script = self.manual_box.get("1.0", "end").strip()
            if not script:
                raise ValueError("Narration script is empty — add lines or switch source.")
            a += ["--caption", " | ".join(l.strip() for l in script.splitlines() if l.strip())]
        elif self.narr_seg.get() == "raw":
            a += ["--raw-captions"]

        if self.kind == "image":
            a += ["--aspect", self.aspect_seg.get(),
                  "--height", self.height_seg.get(),
                  "--fit", self.fit_seg.get(),
                  "--zoom", f"{self.zoom:.2f}",
                  "--fx", f"{self.fx:.4f}",
                  "--fy", f"{self.fy:.4f}",
                  "--motion", self.motion_seg.get()]
            if self.min_val > 0:
                a += ["--min-duration", f"{self.min_val:.1f}"]
        else:
            a += ["--interval", self.interval.get()]
            if int(self.max_frames.get() or 0) > 0:
                a += ["--max-frames", self.max_frames.get()]
        return a

    def start(self):
        path = self.media_path.get().strip()
        if not path:
            self.status.set("Choose a video or image first.")
            return
        if not Path(path).exists():
            self.status.set(f"Not found: {path}")
            return
        if self.running:
            return
        try:
            args = self._build_args()
        except ValueError as e:
            self.status.set(str(e))
            return

        if FROZEN:
            cli = BASE / "VideoVoiceOver_CLI.exe"
            cmd = [str(cli if cli.exists() else sys.executable), path] + args
        else:
            cmd = [sys.executable, "-u", str(SCRIPT), path] + args

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        self._log("$ " + " ".join(Path(c).name if i == 0 else c for i, c in enumerate(cmd)), "cmd")
        self.start_btn.set_state("disabled")
        self.cancel_btn.set_state("normal")
        self.running = True
        self.stage.set("Starting…")
        self.stage_lbl.configure(fg=C["cyan"])
        self.status.set("Running — this can take a few minutes")
        self.bar["value"] = 4

        def runner():
            try:
                self.proc = subprocess.Popen(
                    cmd, cwd=str(BASE), env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, encoding="utf-8", errors="replace",
                    text=True, creationflags=(subprocess.CREATE_NO_WINDOW
                                              if os.name == "nt" else 0))
            except Exception as e:
                self.log_queue.put("__EXIT__-1")
                self.log_queue.put(f"failed to start: {e}")
                return
            for line in self.proc.stdout:
                self.log_queue.put(line.rstrip("\n"))
            for line in self.proc.stderr:
                self.log_queue.put(line.rstrip("\n"))
            self.log_queue.put(f"__EXIT__{self.proc.wait()}")

        threading.Thread(target=runner, daemon=True).start()

    def cancel(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.status.set("Cancelling…")
            self.stage.set("Cancelled")

    def open_output(self):
        out = BASE / "output"
        out.mkdir(exist_ok=True)
        if os.name == "nt":
            os.startfile(out)

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _log(self, line, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n", tag or ())
        self.log.see("end")
        self.log.configure(state="disabled")

    def _tag_for(self, line):
        if "OUTPUT:" in line:
            return "out"
        if any(k in line for k in ("Error", "error:", "Traceback", "failed", "Exception")):
            return "err"
        if line.startswith("  - "):
            return "cap"
        if line.startswith("$"):
            return "cmd"
        if line.startswith(("---", "==")):
            return "dim"
        return ""

    def _set_stage(self, index):
        for i, child in enumerate(self.dots.winfo_children()):
            if i < index:
                child.configure(fg=C["green"])
            elif i == index:
                child.configure(fg=C["accent"])
            else:
                child.configure(fg=C["line"])
        self.bar["value"] = max(6, min(96, 6 + index * 14))

    def _poll(self):
        try:
            while True:
                path, info, poster = self.info_queue.get_nowait()
                self._pending_poster = poster
                self._set_info(info, path)
        except queue.Empty:
            pass
        try:
            while True:
                line = self.log_queue.get_nowait()
                if line.startswith("__EXIT__"):
                    code = line[7:]
                    self.running = False
                    self.proc = None
                    self.start_btn.set_state("normal")
                    self.cancel_btn.set_state("disabled")
                    if code == "0":
                        self.stage.set("Done")
                        self.stage_lbl.configure(fg=C["green"])
                        self.bar["value"] = 100
                        for child in self.dots.winfo_children():
                            child.configure(fg=C["green"])
                        self.status.set("Done — files in the output folder")
                        self._log("--- finished ---", "out")
                    else:
                        self.stage.set(f"Stopped (exit {code})")
                        self.stage_lbl.configure(fg=C["red"])
                        self.status.set(f"Stopped (exit code {code})")
                        self._log(f"--- exit code {code} ---", "err")
                else:
                    self._log(line, self._tag_for(line))
                    for i, (pat, name) in enumerate(STAGES):
                        if pat.search(line):
                            self.stage.set(name)
                            self.stage_lbl.configure(fg=C["cyan"])
                            self._set_stage(i)
                            break
        except queue.Empty:
            pass
        self.root.after(80, self._poll)


def main():
    try:
        root = TkinterDnD.Tk() if DND else tk.Tk()
    except Exception:
        root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
