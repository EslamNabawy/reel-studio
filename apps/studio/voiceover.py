import argparse
import asyncio
import difflib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image

FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    BASE = Path(sys.executable).resolve().parent
    os.environ.setdefault("HF_HOME", str(BASE / "models"))
else:
    BASE = Path(__file__).resolve().parent
    # share one cache with the GUI model installer and the frozen build
    os.environ.setdefault("HF_HOME", str(BASE / "models"))
if FROZEN:
    load_dotenv(BASE / ".env")
else:
    load_dotenv(BASE / ".env")
    load_dotenv(BASE.parent / ".env")

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

for _stream in (sys.stdout, sys.stderr, sys.stdin):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BLIP_MODEL = "Salesforce/blip-image-captioning-base"
WHISPER_MODEL = "tiny"
VOICES = {"en": "en-US-AndrewNeural", "ar": "ar-EG-SalmaNeural"}
GAP = 0.3
FPS = 25
VID_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

ASPECTS = {
    "source": None,
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "4:3": (1440, 1080),
}
HEIGHTS = {"source": None, "2160": 2160, "1080": 1080, "720": 720, "480": 480}
FITS = ("cover", "contain", "blur")
MOTIONS = ("none", "zoom-in", "zoom-out", "pan-left", "pan-right")
QUALITY = {"draft": (30, "veryfast"), "good": (23, "veryfast"), "high": (19, "medium")}


def is_image(p: Path) -> bool:
    return p.suffix.lower() in IMG_EXTS


def _tool(name: str) -> str:
    if FROZEN:
        for cand in (BASE / f"{name}.exe", BASE / "_internal" / f"{name}.exe"):
            if cand.exists():
                return str(cand)
    return name


def run(cmd: list[str], cwd: Path | None = None) -> None:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(
            f"cmd failed: {' '.join(map(str, cmd))}\n{p.stderr.decode(errors='replace')[-800:]}"
        )


def duration_of(path: Path) -> float:
    p = subprocess.run(
        [_tool("ffprobe"), "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True,
    )
    return float(p.stdout.decode().strip())


def probe(path: Path) -> dict:
    """ffprobe json: dimensions, duration, fps."""
    p = subprocess.run(
        [_tool("ffprobe"), "-v", "error", "-print_format", "json",
         "-show_streams", "-show_format", str(path)],
        capture_output=True,
    )
    try:
        return json.loads(p.stdout.decode(errors="replace"))
    except Exception:
        return {}


def media_info(path: Path) -> dict:
    data = probe(path)
    info = {"w": 0, "h": 0, "dur": 0.0, "fps": 0.0, "kind": "video"}
    fmt = data.get("format") or {}
    try:
        info["dur"] = float(fmt.get("duration") or 0.0)
    except (TypeError, ValueError):
        pass
    for s in data.get("streams") or []:
        if s.get("codec_type") != "video":
            continue
        info["w"] = int(s.get("width") or 0)
        info["h"] = int(s.get("height") or 0)
        rate = s.get("avg_frame_rate") or s.get("r_frame_rate") or "0/1"
        try:
            num, den = rate.split("/")
            info["fps"] = float(num) / float(den) if float(den) else 0.0
        except Exception:
            info["fps"] = 0.0
        break
    if is_image(path):
        info["kind"] = "image"
        info["fps"] = 0.0
    return info


def target_size(info: dict, aspect: str, height: str) -> tuple[int, int]:
    """Resolve output frame size from aspect + height, keeping source as fallback."""
    src_w, src_h = max(1, info["w"]), max(1, info["h"])
    if aspect == "source":
        ar = src_w / src_h
    else:
        aw, ah = ASPECTS[aspect]
        ar = aw / ah
    if height == "source":
        base = src_h if aspect == "source" else min(src_w, src_h)
        if aspect == "source":
            base = max(src_w, src_h)
        w = base * ar
    else:
        w = int(height) * ar
    w = max(2, int(round(w / 2)) * 2)
    h = max(2, int(round(w / ar / 2)) * 2)
    cap = 3840
    if w > cap:
        w = cap
        h = max(2, int(round(w / ar / 2)) * 2)
    return w, h


def sub_style(args) -> str:
    font = (args.sub_font or "Arial").replace(",", "")
    colour = (args.sub_color or "#FFFFFF").lstrip("#").upper()
    alpha = "00" if args.sub_color.lower().endswith("ffffff") else "10"
    return (f"FontName={font},FontSize={args.sub_size},"
            f"Outline={args.sub_outline},Shadow=0,"
            f"MarginV={args.sub_margin_v},"
            f"PrimaryColour=&H{alpha}{colour}")


def extract_frames(video: Path, interval: float, frames_dir: Path) -> list[Path]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    run([_tool("ffmpeg"), "-y", "-i", str(video), "-vf", f"fps=1/{interval}",
         str(frames_dir / "frame_%04d.jpg")])
    return sorted(frames_dir.glob("*.jpg"))


def detect_language(video: Path) -> str | None:
    wav = video.parent / "_detect.wav"
    try:
        run([_tool("ffmpeg"), "-y", "-i", str(video), "-t", "30", "-vn",
             "-ac", "1", "-ar", "16000", str(wav)])
    except RuntimeError:
        return None
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        _segments, info = model.transcribe(str(wav), vad_filter=False)
        if info.language_probability < 0.5:
            return None
        return info.language
    except Exception as e:
        print(f"  lang detect failed: {e}")
        return None
    finally:
        wav.unlink(missing_ok=True)


def caption_frames(frames: list[Path]) -> list[str]:
    from transformers import BlipForConditionalGeneration, BlipProcessor

    print("Loading BLIP...")
    processor = BlipProcessor.from_pretrained(BLIP_MODEL)
    model = BlipForConditionalGeneration.from_pretrained(BLIP_MODEL)
    captions = []
    for i, f in enumerate(frames, 1):
        image = Image.open(f).convert("RGB")
        inputs = processor(image, return_tensors="pt")
        out = model.generate(**inputs, max_new_tokens=60)
        cap = processor.decode(out[0], skip_special_tokens=True)
        if not captions or difflib.SequenceMatcher(None, cap.lower(), captions[-1].lower()).ratio() < 0.8:
            captions.append(cap)
        if i % 5 == 0 or i == len(frames):
            print(f"  captioned {i}/{len(frames)} frames ({len(captions)} unique)")
    return captions


def build_narration(captions: list[str], lang: str, rewrite: bool = True) -> list[str]:
    if not rewrite:
        return captions
    import os

    from google import genai

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  no GOOGLE_API_KEY / GEMINI_API_KEY - using raw captions")
        return captions
    lang_name = "Arabic" if lang == "ar" else "English"
    prompt = (
        f"You are writing voice-over narration for a video. Below are captions of "
        f"video frames in chronological order. Write natural spoken {lang_name} "
        f"voice-over narration covering what is shown. 3 to 8 short sentences, "
        f"chronological, factual, based ONLY on the captions. "
        f'Reply with a JSON array of strings, nothing else.\n\nCaptions:\n'
        + "\n".join(f"- {c}" for c in captions)
    )
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        segments = json.loads(resp.text)
        segments = [s.strip() for s in segments if isinstance(s, str) and s.strip()]
        if segments:
            return segments
    except Exception as e:
        print(f"  Gemini narration failed: {e}")
    return captions


async def _tts_one(text: str, voice: str, path: Path, rate: str, pitch: str) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(path))


def tts(segments: list[str], lang: str, voice: str | None, work: Path,
        rate: str = "+0%", pitch: str = "+0Hz") -> list[Path]:
    voice = voice or VOICES.get(lang, VOICES["en"])
    print(f"TTS with {voice} (rate {rate})...")

    async def all_segs():
        paths = []
        for i, seg in enumerate(segments):
            p = work / f"seg_{i:03d}.mp3"
            await _tts_one(seg, voice, p, rate, pitch)
            paths.append(p)
        return paths

    return asyncio.run(all_segs())


def concat_audio(seg_paths: list[Path], work: Path, gap: float = GAP) -> Path:
    g = work / "gap.mp3"
    run([_tool("ffmpeg"), "-y", "-f", "lavfi", "-t", str(gap), "-i",
         "anullsrc=r=44100:cl=stereo", "-c:a", "libmp3lame", "-q:a", "9", str(g)])
    lines = []
    for i, p in enumerate(seg_paths):
        if i:
            lines.append(f"file '{g.name}'")
        lines.append(f"file '{p.name}'")
    lst = work / "concat.txt"
    lst.write_text("\n".join(lines), encoding="utf-8")
    out = work / "voice.mp3"
    run([_tool("ffmpeg"), "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt",
         "-c:a", "libmp3lame", "-q:a", "2", "voice.mp3"], cwd=work)
    return out


def segment_times(seg_paths: list[Path], gap: float = GAP) -> list[tuple[float, float]]:
    times = []
    t = 0.0
    for i, p in enumerate(seg_paths):
        d = duration_of(p)
        times.append((t, t + d))
        t += d + (gap if i < len(seg_paths) - 1 else 0)
    return times


def make_srt(segments: list[str], times: list[tuple[float, float]], work: Path) -> Path:
    def fmt(s: float) -> str:
        ms = int(round(max(0.0, s) * 1000))
        return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d},{ms % 1000:03d}"

    lines = []
    for i, ((start, end), text) in enumerate(zip(times, segments), 1):
        lines += [str(i), f"{fmt(start)} --> {fmt(end)}", text, ""]
    srt = work / "sub.srt"
    srt.write_text("\n".join(lines), encoding="utf-8")
    return srt


def sub_filter(enabled: bool, style: str) -> str:
    if not enabled:
        return ""
    return f"subtitles=sub.srt:force_style='{style}'"


def mux(video: Path, voice: Path, video_dur: float, audio_dur: float,
        args, work: Path, out: Path) -> None:
    extend = max(0.0, audio_dur - video_dur)
    pad = max(0.0, video_dur - audio_dur)
    out_dur = max(video_dur, audio_dur)

    v = "[0:v]"
    if extend > 0.05:
        v += f"tpad=stop_mode=clone:stop_duration={extend:.3f},"
    s = sub_filter(not args.no_subtitles, sub_style(args))
    if s:
        v += f"{s}[vout]"
    else:
        v += "null[vout]"

    cmd = [_tool("ffmpeg"), "-y", "-i", str(video), "-i", str(voice)]
    if pad > 0.05:
        cmd += ["-f", "lavfi", "-t", f"{pad:.3f}", "-i", "anullsrc=r=44100:cl=stereo"]
        ac = "[1:a][2:a]concat=n=2:v=0:a=1[aout]"
    else:
        ac = "[1:a]anull[aout]"
    crf, preset = QUALITY[args.quality]
    cmd += ["-filter_complex", f"{v};{ac}",
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-t", f"{out_dur:.3f}", str(out)]
    run(cmd, cwd=work)


MOTION_AMP = 0.18


def _zoompan(motion: str, sw: int, sh: int, frames: int,
             fx: float, fy: float) -> str:
    """zoompan segment anchored on the focal point. Consumes one frame, emits `frames`."""
    n = max(2, frames)
    span = max(1, n - 1)
    fx_s, fy_s = f"{fx:.4f}", f"{fy:.4f}"
    amp = MOTION_AMP
    if motion == "zoom-in":
        z = f"1+{amp}*on/{span}"
    elif motion == "zoom-out":
        z = f"{1 + amp}-{amp}*on/{span}"
    else:  # pan
        z = f"{1 + amp}"
    if motion == "pan-right":
        x = f"(iw-iw/zoom)*on/{span}"
    elif motion == "pan-left":
        x = f"(iw-iw/zoom)*(1-on/{span})"
    else:
        x = f"(iw-iw/zoom)*{fx_s}"
    y = f"(ih-ih/zoom)*{fy_s}"
    return (f"zoompan=z='{z}':x='{x}':y='{y}':"
            f"d={n}:s={sw}x{sh}:fps={FPS}")


def image_filter(w: int, h: int, fit: str, zoom: float, fx: float, fy: float,
                 motion: str, frames: int) -> tuple[str, bool]:
    """Filter chain for a still image. Returns (chain, needs_single_frame)."""
    zoom = max(1.0, zoom)
    animate = motion in ("zoom-in", "zoom-out", "pan-left", "pan-right")
    # work big so motion has pixels to move through
    sw = int(w * max(zoom, 1 + MOTION_AMP) * 1.15) // 2 * 2
    sh = int(h * max(zoom, 1 + MOTION_AMP) * 1.15) // 2 * 2
    sw, sh = max(sw, w), max(sh, h)

    def source_chain(src: str = "0:v") -> str:
        steps = [f"scale={sw}:{sh}:force_original_aspect_ratio=increase"]
        if animate:
            steps.append(_zoompan(motion, sw, sh, frames, fx, fy))
        return f"[{src}]{','.join(steps)}[zo]"

    if fit == "blur":
        chain = (
            "[0:v]split=2[bgs][fgs];"
            f"[bgs]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},boxblur=24:2[bg];"
            + source_chain("fgs")
            + f";[zo]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v0]"
        )
    elif fit == "contain":
        chain = (
            source_chain("z")
            + f";[zo]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black[v0]"
        )
    else:  # cover
        chain = (
            source_chain("z")
            + f";[zo]crop={w}:{h}:(iw-{w})*{fx:.4f}:(ih-{h})*{fy:.4f}[v0]"
        )
    return chain, animate


def mux_image(image: Path, voice: Path, audio_dur: float, args, work: Path, out: Path) -> None:
    w, h = args._out_w, args._out_h
    out_dur = max(audio_dur, args.min_duration)
    frames = max(2, int(round(out_dur * FPS)))
    chain, animate = image_filter(w, h, args.fit, args.zoom, args.fx, args.fy,
                                  args.motion, frames)
    s = sub_filter(not args.no_subtitles, sub_style(args))
    if s:
        chain += f";[v0]{s}[vout]"
    else:
        chain += ";[v0]null[vout]"

    crf, preset = QUALITY[args.quality]
    img_in = ["-i", str(image)] if animate else ["-loop", "1", "-framerate", str(FPS), "-i", str(image)]
    cmd = [_tool("ffmpeg"), "-y"] + img_in + ["-i", str(voice),
           "-filter_complex", f"{chain};[1:a]anull[aout]",
           "-map", "[vout]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
           "-c:a", "aac", "-b:a", "160k", "-pix_fmt", "yuv420p",
           "-r", str(FPS), "-t", f"{out_dur:.3f}", str(out)]
    run(cmd, cwd=work)




def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Video or image -> BLIP -> narration -> voice + subtitles")
    ap.add_argument("media", help="video file, image file, or folder of them")
    ap.add_argument("--interval", type=float, default=2.0, help="video: seconds per frame")
    ap.add_argument("--max-frames", type=int, default=0, help="video: cap frame count (0 = all)")
    ap.add_argument("--lang", choices=["auto", "ar", "en"], default="auto")
    ap.add_argument("--voice", help="override edge-tts voice, e.g. ar-EG-ShakirNeural")
    ap.add_argument("--rate", default="+0%", help="speech rate, e.g. +10%%")
    ap.add_argument("--pitch", default="+0Hz", help="speech pitch, e.g. +5Hz")
    ap.add_argument("--caption", default="", help="use this narration text, skip BLIP")
    ap.add_argument("--raw-captions", action="store_true",
                    help="speak BLIP captions verbatim, skip Gemini rewrite")
    ap.add_argument("--no-subtitles", action="store_true")

    g = ap.add_argument_group("frame (images)")
    g.add_argument("--aspect", choices=list(ASPECTS), default="source")
    g.add_argument("--height", choices=list(HEIGHTS), default="source")
    g.add_argument("--fit", choices=FITS, default="cover",
                   help="cover=crop to fill, contain=letterbox, blur=blurred backdrop")
    g.add_argument("--zoom", type=float, default=1.0, help="frame zoom, 1.0-2.0")
    g.add_argument("--fx", type=float, default=0.5, help="focal point x 0-1")
    g.add_argument("--fy", type=float, default=0.5, help="focal point y 0-1")
    g.add_argument("--motion", choices=MOTIONS, default="none", help="Ken Burns motion")
    g.add_argument("--min-duration", type=float, default=0.0,
                   help="pad image clip to at least N seconds")

    s = ap.add_argument_group("subtitles")
    s.add_argument("--sub-font", default="Arial")
    s.add_argument("--sub-size", type=int, default=18)
    s.add_argument("--sub-outline", type=int, default=2)
    s.add_argument("--sub-margin-v", type=int, default=28)
    s.add_argument("--sub-color", default="#FFFFFF")

    o = ap.add_argument_group("output")
    o.add_argument("--quality", choices=list(QUALITY), default="good")
    o.add_argument("--keep", action="store_true", help="keep work files")
    return ap


def main():
    ap = build_parser()
    args = ap.parse_args()
    for name, lo, hi in (("zoom", 1.0, 2.5), ("fx", 0.0, 1.0), ("fy", 0.0, 1.0)):
        setattr(args, name, max(lo, min(hi, getattr(args, name))))

    src = Path(args.media)
    if src.is_dir():
        items = sorted(p for p in src.iterdir()
                       if p.suffix.lower() in VID_EXTS | IMG_EXTS)
    elif src.is_file():
        items = [src]
    else:
        sys.exit(f"Not found: {src}")
    if not items:
        sys.exit("No videos or images found.")

    for item in items:
        item = item.resolve()
        img = is_image(item)
        kind = "image" if img else "video"
        print(f"\n=== {item.name} ===")
        work = BASE / "work" / item.stem
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)

        info = media_info(item)
        if info["w"] and info["h"]:
            print(f"source: {info['w']}x{info['h']}"
                  + (f"  {info['dur']:.1f}s" if info["dur"] else ""))
        args._out_w, args._out_h = target_size(info, args.aspect, args.height)

        vid_dur = 0.0 if img else (info["dur"] or duration_of(item))
        if not img:
            print(f"duration: {vid_dur:.1f}s")

        if args.lang == "auto":
            if img:
                lang = "en"
                print("image input, default language: en (use --lang ar for Arabic)")
            else:
                lang = detect_language(item) or "en"
                print(f"detected language: {lang}")
        else:
            lang = args.lang

        if img:
            print(f"frame: {args._out_w}x{args._out_h}  fit={args.fit} "
                  f"zoom={args.zoom:.2f} focus=({args.fx:.2f},{args.fy:.2f}) "
                  f"motion={args.motion}")
            frames = [item]
        else:
            frames = extract_frames(item, args.interval, work / "frames")
            if args.max_frames:
                frames = frames[:args.max_frames]
            print(f"frames: {len(frames)} ({kind})")

        if args.caption:
            captions = [s.strip() for s in args.caption.split("|") if s.strip()]
            print("narration: manual text")
        else:
            captions = caption_frames(frames)
            print("captions:")
            for c in captions:
                print(f"  - {c}")

        segments = build_narration(captions, lang, rewrite=not args.raw_captions)
        print("narration segments:")
        for s in segments:
            print(f"  - {s}")

        seg_paths = tts(segments, lang, args.voice, work, args.rate, args.pitch)
        voice = concat_audio(seg_paths, work)
        audio_dur = duration_of(voice)
        print(f"audio: {audio_dur:.1f}s" + ("" if img else f" (video {vid_dur:.1f}s)"))

        if not args.no_subtitles:
            times = segment_times(seg_paths)
            make_srt(segments, times, work)

        out = BASE / "output" / f"{item.stem}_voiceover_{lang}.mp4"
        out.parent.mkdir(exist_ok=True)
        if img:
            print(f"render: {args._out_w}x{args._out_h} "
                  f"{max(audio_dur, args.min_duration):.1f}s")
            mux_image(item, voice, audio_dur, args, work, out)
        else:
            mux(item, voice, vid_dur, audio_dur, args, work, out)
        print(f"OUTPUT: {out}")

        if not args.keep:
            shutil.rmtree(work, ignore_errors=True)

    print("\ndone.")


if __name__ == "__main__":
    main()
