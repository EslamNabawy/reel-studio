import argparse
import asyncio
import difflib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from transformers import BlipForConditionalGeneration, BlipProcessor

FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    BASE = Path(sys.executable).resolve().parent
    os.environ.setdefault("HF_HOME", str(BASE / "models"))
else:
    BASE = Path(__file__).resolve().parent
    load_dotenv(BASE / ".env")
    load_dotenv(BASE.parent / ".env")
if FROZEN:
    load_dotenv(BASE / ".env")

for _stream in (sys.stdout, sys.stderr, sys.stdin):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BLIP_MODEL = "Salesforce/blip-image-captioning-base"
WHISPER_MODEL = "tiny"
VOICES = {"en": "en-US-AndrewNeural", "ar": "ar-EG-SalmaNeural"}
GAP = 0.3
VID_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


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


def build_narration(captions: list[str], lang: str) -> list[str]:
    import os

    from google import genai

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("  no GOOGLE_API_KEY - using raw captions")
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


async def _tts_one(text: str, voice: str, path: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice).save(str(path))


def tts(segments: list[str], lang: str, voice: str | None, work: Path) -> list[Path]:
    voice = voice or VOICES.get(lang, VOICES["en"])
    print(f"TTS with {voice}...")

    async def all_segs():
        paths = []
        for i, seg in enumerate(segments):
            p = work / f"seg_{i:03d}.mp3"
            await _tts_one(seg, voice, p)
            paths.append(p)
        return paths

    return asyncio.run(all_segs())


def concat_audio(seg_paths: list[Path], work: Path) -> Path:
    gap = work / "gap.mp3"
    run([_tool("ffmpeg"), "-y", "-f", "lavfi", "-t", str(GAP), "-i",
         "anullsrc=r=44100:cl=stereo", "-c:a", "libmp3lame", "-q:a", "9", str(gap)])
    lines = []
    for i, p in enumerate(seg_paths):
        if i:
            lines.append(f"file '{gap.name}'")
        lines.append(f"file '{p.name}'")
    lst = work / "concat.txt"
    lst.write_text("\n".join(lines), encoding="utf-8")
    out = work / "voice.mp3"
    run([_tool("ffmpeg"), "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt",
         "-c:a", "libmp3lame", "-q:a", "2", "voice.mp3"], cwd=work)
    return out


def segment_times(seg_paths: list[Path]) -> list[tuple[float, float]]:
    times = []
    t = 0.0
    for i, p in enumerate(seg_paths):
        d = duration_of(p)
        times.append((t, t + d))
        t += d + (GAP if i < len(seg_paths) - 1 else 0)
    return times


def make_srt(segments: list[str], times: list[tuple[float, float]], work: Path) -> Path:
    def fmt(s: float) -> str:
        ms = int(round(s * 1000))
        return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d},{ms % 1000:03d}"

    lines = []
    for i, ((start, end), text) in enumerate(zip(times, segments), 1):
        lines += [str(i), f"{fmt(start)} --> {fmt(end)}", text, ""]
    srt = work / "sub.srt"
    srt.write_text("\n".join(lines), encoding="utf-8")
    return srt


def mux(video: Path, voice: Path, srt: Path, video_dur: float,
        audio_dur: float, work: Path, out: Path) -> None:
    extend = max(0.0, audio_dur - video_dur)
    pad = max(0.0, video_dur - audio_dur)
    out_dur = max(video_dur, audio_dur)

    v = "[0:v]"
    if extend > 0.05:
        v += f"tpad=stop_mode=clone:stop_duration={extend:.3f},"
    v += "subtitles=sub.srt:force_style='FontName=Arial,FontSize=18,Outline=1,MarginV=18'[vout]"

    cmd = [_tool("ffmpeg"), "-y", "-i", str(video), "-i", str(voice)]
    if pad > 0.05:
        cmd += ["-f", "lavfi", "-t", f"{pad:.3f}", "-i", "anullsrc=r=44100:cl=stereo"]
        ac = "[1:a][2:a]concat=n=2:v=0:a=1[aout]"
    else:
        ac = "[1:a]anull[aout]"
    cmd += ["-filter_complex", f"{v};{ac}",
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "160k", "-t", f"{out_dur:.3f}", str(out)]
    run(cmd, cwd=work)


def mux_image(image: Path, voice: Path, srt: Path, audio_dur: float,
              work: Path, out: Path) -> None:
    v = ("[0:v]scale=trunc(iw/2)*2:trunc(ih/2)*2,"
         "subtitles=sub.srt:force_style='FontName=Arial,FontSize=18,Outline=1,MarginV=18'[vout]")
    cmd = [_tool("ffmpeg"), "-y", "-loop", "1", "-framerate", "25",
           "-i", str(image), "-i", str(voice),
           "-filter_complex", f"{v};[1:a]anull[aout]",
           "-map", "[vout]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
           "-c:a", "aac", "-b:a", "160k", "-pix_fmt", "yuv420p",
           "-t", f"{audio_dur:.3f}", str(out)]
    run(cmd, cwd=work)


def main():
    ap = argparse.ArgumentParser(description="Video or image -> BLIP -> voice-over + subtitles")
    ap.add_argument("media", help="video file, image file, or folder of them")
    ap.add_argument("--interval", type=float, default=2.0, help="seconds per frame (default 2)")
    ap.add_argument("--lang", choices=["auto", "ar", "en"], default="auto")
    ap.add_argument("--voice", help="override edge-tts voice, e.g. ar-EG-ShakirNeural")
    ap.add_argument("--keep", action="store_true", help="keep work files")
    args = ap.parse_args()

    src = Path(args.media)
    if src.is_dir():
        videos = sorted(p for p in src.iterdir()
                        if p.suffix.lower() in VID_EXTS | IMG_EXTS)
    elif src.is_file():
        videos = [src]
    else:
        sys.exit(f"Not found: {src}")
    if not videos:
        sys.exit("No videos or images found.")

    for video in videos:
        video = video.resolve()
        img = is_image(video)
        kind = "image" if img else "video"
        print(f"\n=== {video.name} ===")
        work = BASE / "work" / video.stem
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)

        vid_dur = 0.0 if img else duration_of(video)
        if not img:
            print(f"duration: {vid_dur:.1f}s")

        if args.lang == "auto":
            if img:
                lang = "en"
                print("image input, default language: en (use --lang ar for Arabic)")
            else:
                lang = detect_language(video) or "en"
                print(f"detected language: {lang}")
        else:
            lang = args.lang

        if img:
            frames = [video]
        else:
            frames = extract_frames(video, args.interval, work / "frames")
        print(f"frames: {len(frames)} ({kind})")

        captions = caption_frames(frames)
        print("captions:")
        for c in captions:
            print(f"  - {c}")

        segments = build_narration(captions, lang)
        print("narration segments:")
        for s in segments:
            print(f"  - {s}")

        seg_paths = tts(segments, lang, args.voice, work)
        voice = concat_audio(seg_paths, work)
        audio_dur = duration_of(voice)
        print(f"audio: {audio_dur:.1f}s" + ("" if img else f" (video {vid_dur:.1f}s)"))

        times = segment_times(seg_paths)
        srt = make_srt(segments, times, work)

        out = BASE / "output" / f"{video.stem}_voiceover_{lang}.mp4"
        out.parent.mkdir(exist_ok=True)
        if img:
            mux_image(video, voice, srt, audio_dur, work, out)
        else:
            mux(video, voice, srt, vid_dur, audio_dur, work, out)
        print(f"OUTPUT: {out}")

        if not args.keep:
            shutil.rmtree(work, ignore_errors=True)

    print("\ndone.")


if __name__ == "__main__":
    main()
