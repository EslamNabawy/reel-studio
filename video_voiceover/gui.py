import os
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, ttk

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
    "ar-EG-SalmaNeural (female)",
    "ar-EG-ShakirNeural (male)",
    "ar-SA-HamedNeural (male)",
    "ar-SA-ZariyahNeural (female)",
]
VOICE_IDS = {label: label.split(" ")[0] for label in VOICES}

C = {
    "bg": "#12121b",
    "panel": "#1b1b28",
    "panel2": "#232334",
    "border": "#32324a",
    "text": "#e6e9f2",
    "dim": "#8b90a6",
    "accent": "#6d5efc",
    "accent_dark": "#5a4de0",
    "cyan": "#22d3ee",
    "green": "#34d399",
    "red": "#f87171",
    "amber": "#fbbf24",
}

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

STAGES = [
    (re.compile(r"duration|Reading|=== "), "Reading media"),
    (re.compile(r"frames:|Extracting"), "Extracting frames"),
    (re.compile(r"Loading BLIP|captioned"), "Analyzing with AI"),
    (re.compile(r"narration segments|Loading weights"), "Writing narration"),
    (re.compile(r"TTS with"), "Synthesizing voice"),
    (re.compile(r"audio:|Mixing"), "Mixing + subtitles"),
    (re.compile(r"OUTPUT:"), "Done"),
]


class HoverButton(tk.Frame):
    """Flat button with hover states."""

    def __init__(self, master, text, command=None, bg=None, fg=None,
                 hover=None, padx=16, pady=8, state="normal", font=None):
        super().__init__(master, bg=bg or C["panel2"], highlightthickness=1,
                         highlightbackground=C["border"], cursor="hand2")
        self._bg = bg or C["panel2"]
        self._hover = hover or C["border"]
        self._fg = fg or C["text"]
        self._cmd = command
        self._state = state
        self.label = tk.Label(self, text=text, bg=self._bg, fg=self._fg,
                              font=font or ("Segoe UI", 10, "bold"), padx=padx, pady=pady)
        self.label.pack()
        self.configure(bg=self._bg)
        for w in (self, self.label):
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)
            w.bind("<Button-1>", self._click)

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

    def set_state(self, state: str):
        self._state = state
        if state == "disabled":
            self._set(C["panel"], C["dim"])
            self.label.configure(cursor="")
        else:
            self._set(self._bg, self._fg)
            self.label.configure(cursor="hand2")


class App:
    def __init__(self, root):
        self.root = root
        root.title("Video Voice-Over")
        root.geometry("860x680")
        root.minsize(780, 600)
        root.configure(bg=C["bg"])
        icon = BASE / "icon.ico"
        if not FROZEN and not icon.exists():
            icon = Path(__file__).parent / "icon.ico"
        if icon.exists():
            try:
                root.iconbitmap(icon)
            except Exception:
                pass

        self.proc = None
        self.log_queue = queue.Queue()
        self.running = False
        self.media_path = tk.StringVar()
        self.lang = tk.StringVar(value="auto")
        self.interval = tk.StringVar(value="2")
        self.voice = tk.StringVar(value=VOICES[0])
        self.stage = tk.StringVar(value="Ready.")
        self.kind = tk.StringVar(value="")

        self._build()
        self.root.after(80, self._poll)

    # ---------- UI ----------

    def _build(self):
        pad = {"padx": 20}
        root = self.root

        # header
        hdr = tk.Frame(root, bg=C["panel"], height=64)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="◉", bg=C["panel"], fg=C["accent"],
                 font=("Segoe UI", 18)).pack(side="left", padx=(20, 6))
        tk.Label(hdr, text="Video Voice-Over", bg=C["panel"], fg=C["text"],
                 font=("Segoe UI", 15, "bold")).pack(side="left")
        tk.Label(hdr, text="frames → AI captions → narration → voice + subtitles",
                 bg=C["panel"], fg=C["dim"], font=("Segoe UI", 9)).pack(
            side="right", padx=20)

        body = tk.Frame(root, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=18, pady=14)

        # drop zone
        self.drop = tk.Frame(body, bg=C["panel"], height=76,
                             highlightthickness=1, highlightbackground=C["border"],
                             cursor="hand2")
        self.drop.pack(fill="x")
        self.drop.pack_propagate(False)
        self.drop.bind("<Button-1>", lambda e: self.browse())

        inner = tk.Frame(self.drop, bg=C["panel"])
        inner.place(relx=0.5, rely=0.5, anchor="center")
        self.drop_lbl = tk.Label(inner, bg=C["panel"], fg=C["text"],
                                 font=("Segoe UI", 11, "bold"),
                                 text="⬇  Drop video or image here")
        self.drop_lbl.pack()
        tk.Label(inner, bg=C["panel"], fg=C["dim"], font=("Segoe UI", 9),
                 text="or click to browse  ·  mp4 mov avi mkv webm  |  png jpg jpeg webp bmp gif").pack()

        if DND and self._dnd_ready(root):
            try:
                self.drop.drop_target_register(DND_FILES)
                self.drop.dnd_bind("<<Drop>>", self._on_drop)
                self.drop.dnd_bind("<<DropEnter>>", lambda e: self._drop_state(True))
                self.drop.dnd_bind("<<DropLeave>>", lambda e: self._drop_state(False))
            except Exception:
                pass

        # chosen file row
        frow = tk.Frame(body, bg=C["bg"])
        frow.pack(fill="x", pady=(8, 0))
        self.kind_chip = tk.Label(frow, text="  NO FILE  ", bg=C["panel2"],
                                  fg=C["dim"], font=("Consolas", 9, "bold"))
        self.kind_chip.pack(side="left")
        self.path_lbl = tk.Label(frow, text="no media selected", bg=C["bg"],
                                 fg=C["dim"], font=("Consolas", 9), anchor="w")
        self.path_lbl.pack(side="left", padx=10, fill="x", expand=True)
        HoverButton(frow, "Browse…", command=self.browse, padx=14, pady=4).pack(side="right")

        # options card
        card = tk.Frame(body, bg=C["panel"], highlightthickness=1,
                        highlightbackground=C["border"])
        card.pack(fill="x", pady=(12, 0))

        r1 = tk.Frame(card, bg=C["panel"])
        r1.pack(fill="x", padx=16, pady=(14, 6))

        tk.Label(r1, text="LANGUAGE", bg=C["panel"], fg=C["dim"],
                 font=("Segoe UI", 8, "bold")).pack(side="left")
        self.lang_btns = {}
        seg = tk.Frame(r1, bg=C["panel"])
        seg.pack(side="left", padx=(10, 0))
        for val, txt in [("auto", "Auto detect"), ("en", "English"), ("ar", "Arabic")]:
            b = tk.Button(seg, text=txt, relief="flat", bd=0, padx=12, pady=3,
                          font=("Segoe UI", 9), cursor="hand2",
                          command=lambda v=val: self._set_lang(v))
            b.pack(side="left", padx=3)
            self.lang_btns[val] = b
        self._set_lang("auto")

        tk.Label(r1, text="FRAME EVERY", bg=C["panel"], fg=C["dim"],
                 font=("Segoe UI", 8, "bold")).pack(side="left", padx=(28, 6))
        spin = tk.Spinbox(r1, from_=0.5, to=30, increment=0.5, width=6,
                          textvariable=self.interval, font=("Consolas", 10),
                          bg=C["panel2"], fg=C["text"], buttonbackground=C["panel2"],
                          relief="flat", highlightthickness=1,
                          highlightbackground=C["border"])
        spin.pack(side="left")
        tk.Label(r1, text="sec", bg=C["panel"], fg=C["dim"],
                 font=("Segoe UI", 9)).pack(side="left", padx=(4, 0))

        r2 = tk.Frame(card, bg=C["panel"])
        r2.pack(fill="x", padx=16, pady=(2, 14))

        tk.Label(r2, text="VOICE", bg=C["panel"], fg=C["dim"],
                 font=("Segoe UI", 8, "bold")).pack(side="left")
        vc = ttk.Combobox(r2, textvariable=self.voice, values=VOICES,
                          state="readonly", width=32, font=("Segoe UI", 9))
        vc.pack(side="left", padx=10)
        self._style_combo(vc)

        # action row
        act = tk.Frame(body, bg=C["bg"])
        act.pack(fill="x", pady=(14, 0))
        self.start_btn = HoverButton(act, "▶  START", command=self.start,
                                     bg=C["accent"], hover=C["accent_dark"],
                                     padx=28, pady=9, font=("Segoe UI", 11, "bold"))
        self.start_btn.pack(side="left")
        self.cancel_btn = HoverButton(act, "■  Cancel", command=self.cancel,
                                      bg=C["panel2"], fg=C["red"],
                                      padx=14, pady=9, state="disabled")
        self.cancel_btn.pack(side="left", padx=(10, 0))
        HoverButton(act, "Open output folder", command=self.open_output,
                    padx=14, pady=9).pack(side="right")

        # stage + progress
        stg = tk.Frame(body, bg=C["bg"])
        stg.pack(fill="x", pady=(12, 0))
        self.stage_lbl = tk.Label(stg, textvariable=self.stage, bg=C["bg"],
                                  fg=C["cyan"], font=("Segoe UI", 10, "bold"),
                                  anchor="w")
        self.stage_lbl.pack(fill="x")
        self.bar = ttk.Progressbar(stg, mode="indeterminate", length=100)
        self.bar.pack(fill="x", pady=(6, 0))

        # log
        lf = tk.LabelFrame(body, text=" LOG ", bg=C["panel"], fg=C["dim"],
                           font=("Segoe UI", 9, "bold"), labelanchor="n",
                           highlightthickness=1, highlightbackground=C["border"])
        lf.pack(fill="both", expand=True, pady=(12, 0))
        self.log = tk.Text(lf, wrap="word", state="disabled", bd=0,
                           bg=C["panel"], fg=C["text"], insertbackground=C["text"],
                           font=("Consolas", 9), selectbackground=C["accent"],
                           relief="flat", padx=10, pady=8)
        sb = ttk.Scrollbar(lf, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        for tag, col in [("err", C["red"]), ("out", C["green"]),
                         ("cap", C["cyan"]), ("dim", C["dim"]), ("cmd", C["amber"])]:
            self.log.tag_configure(tag, foreground=col)

        # status bar
        sbar = tk.Frame(root, bg=C["panel"], height=26)
        sbar.pack(fill="x", side="bottom")
        sbar.pack_propagate(False)
        self.status = tk.StringVar(value="Ready.")
        tk.Label(sbar, textvariable=self.status, bg=C["panel"], fg=C["dim"],
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=16)

    def _style_combo(self, combo):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TCombobox", fieldbackground=C["panel2"],
                        background=C["panel2"], foreground=C["text"],
                        arrowcolor=C["dim"], bordercolor=C["border"],
                        lightcolor=C["border"], darkcolor=C["border"])
        style.map("TCombobox", fieldbackground=[("readonly", C["panel2"])],
                  foreground=[("readonly", C["text"])])
        style.configure("TProgressbar", troughcolor=C["panel2"],
                        background=C["accent"], bordercolor=C["panel2"],
                        lightcolor=C["accent"], darkcolor=C["accent"])
        style.configure("Vertical.TScrollbar", background=C["panel2"],
                        troughcolor=C["bg"], arrowcolor=C["dim"],
                        bordercolor=C["bg"])
        combo.configure(foreground=C["text"])

    @staticmethod
    def _dnd_ready(root) -> bool:
        try:
            return bool(root.tk.call("info", "commands", "tkdnd::drop_target"))
        except Exception:
            return False

    def _set_lang(self, val):
        self.lang.set(val)
        for v, b in self.lang_btns.items():
            if v == val:
                b.configure(bg=C["accent"], fg="#ffffff", activebackground=C["accent_dark"],
                            activeforeground="#ffffff")
            else:
                b.configure(bg=C["panel2"], fg=C["dim"], activebackground=C["border"],
                            activeforeground=C["text"])

    def _drop_state(self, on):
        self.drop.configure(highlightbackground=C["accent"] if on else C["border"])
        self.drop_lbl.configure(fg=C["accent"] if on else C["text"])

    def _on_drop(self, event):
        self._drop_state(False)
        raw = event.data.strip()
        paths = [p[1:-1] if p.startswith("{") and p.endswith("}") else p
                 for p in re.findall(r"\{[^}]+\}|[^\s]+", raw)]
        if paths:
            self._set_path(paths[0])

    def _set_path(self, p: str):
        path = Path(p)
        if not path.exists():
            self.status.set(f"Not found: {p}")
            return
        self.media_path.set(str(path))
        ext = path.suffix.lower()
        if ext in IMAGE_EXTS:
            kind = "IMAGE"
            col = C["amber"]
        elif ext in VIDEO_EXTS:
            kind = "VIDEO"
            col = C["cyan"]
        else:
            kind = "FILE"
            col = C["dim"]
        self.kind_chip.configure(text=f"  {kind}  ", fg=col)
        self.path_lbl.configure(text=str(path), fg=C["text"])
        self.status.set(f"Selected {path.name}")

    def browse(self):
        p = filedialog.askopenfilename(
            title="Choose video or image",
            filetypes=[("Media", "*.mp4 *.mov *.avi *.mkv *.webm "
                                 "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
                       ("All", "*.*")])
        if p:
            self._set_path(p)

    def open_output(self):
        out = BASE / "output"
        out.mkdir(exist_ok=True)
        if os.name == "nt":
            os.startfile(out)

    # ---------- pipeline ----------

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

        args = ["--interval", self.interval.get(), "--lang", self.lang.get()]
        voice = VOICE_IDS[self.voice.get()]
        if voice != "Default":
            args += ["--voice", voice]

        if FROZEN:
            cli = BASE / "VideoVoiceOver_CLI.exe"
            cmd = [str(cli if cli.exists() else sys.executable), path] + args
        else:
            cmd = [sys.executable, "-u", str(SCRIPT), path] + args

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        self._log("$ " + " ".join(Path(c).name if i == 0 else c
                                  for i, c in enumerate(cmd)), "cmd")
        self.start_btn.set_state("disabled")
        self.cancel_btn.set_state("normal")
        self.bar.start(14)
        self.running = True
        self.stage.set("Starting…")
        self.status.set("Running…")

        def runner():
            try:
                self.proc = subprocess.Popen(
                    cmd, cwd=str(BASE), env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    encoding="utf-8", errors="replace", text=True,
                    creationflags=(subprocess.CREATE_NO_WINDOW
                                   if os.name == "nt" else 0))
            except Exception as e:
                self.log_queue.put(f"__EXIT__-1")
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

    def _log(self, line: str, tag: str = None):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n", tag or ())
        self.log.see("end")
        self.log.configure(state="disabled")

    def _tag_for(self, line: str) -> str:
        if "OUTPUT:" in line:
            return "out"
        if "failed" in line or "Error" in line or "error:" in line or "Traceback" in line:
            return "err"
        if line.startswith("  - "):
            return "cap"
        if line.startswith("$"):
            return "cmd"
        if line.startswith("---") or line.startswith("=="):
            return "dim"
        return ""

    def _poll(self):
        try:
            while True:
                line = self.log_queue.get_nowait()
                if line.startswith("__EXIT__"):
                    code = line[7:]
                    self.running = False
                    self.proc = None
                    self.start_btn.set_state("normal")
                    self.cancel_btn.set_state("disabled")
                    self.bar.stop()
                    if code == "0":
                        self.stage.set("Done ✓")
                        self.stage_lbl.configure(fg=C["green"])
                        self.status.set("Done. Files in output\\ folder.")
                        self._log("--- finished OK ---", "out")
                    else:
                        self.stage.set(f"Stopped (exit {code})")
                        self.stage_lbl.configure(fg=C["red"])
                        self.status.set(f"Stopped (exit code {code}).")
                        self._log(f"--- exit code {code} ---", "err")
                else:
                    self._log(line, self._tag_for(line))
                    for pat, name in STAGES:
                        if pat.search(line):
                            self.stage.set(name + "…")
                            self.stage_lbl.configure(fg=C["cyan"])
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
