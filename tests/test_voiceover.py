"""Pure-logic tests for video_voiceover/voiceover.py.

No models, no network, no ffmpeg: only argparse math, SRT formatting,
subtitle-style strings and filter-chain construction.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "video_voiceover"))

import voiceover as v


def _sub_args(**kw):
    base = dict(sub_font="Arial", sub_size=18, sub_outline=2,
                sub_margin_v=28, sub_color="#FFFFFF")
    base.update(kw)
    return SimpleNamespace(**base)


def test_is_image():
    assert v.is_image(Path("clip.mp4")) is False
    assert v.is_image(Path("photo.JPG")) is True
    assert v.is_image(Path("pic.webp")) is True


def test_target_size_explicit():
    assert v.target_size({"w": 640, "h": 480}, "16:9", "720") == (1280, 720)
    assert v.target_size({"w": 640, "h": 480}, "9:16", "1080") == (608, 1080)


def test_target_size_even_and_capped():
    w, h = v.target_size({"w": 100, "h": 100}, "1:1", "1080")
    assert (w, h) == (1080, 1080)
    assert w % 2 == 0 and h % 2 == 0


def test_sub_style_white_opaque():
    s = v.sub_style(_sub_args())
    assert s == ("FontName=Arial,FontSize=18,Outline=2,Shadow=0,"
                 "MarginV=28,PrimaryColour=&H00FFFFFF")


def test_sub_style_tinted():
    s = v.sub_style(_sub_args(sub_color="#FFB547", sub_size=24))
    assert "FontSize=24" in s
    assert s.endswith("PrimaryColour=&H10FFB547")


def test_sub_filter():
    assert v.sub_filter(False, "FontName=Arial") == ""
    assert v.sub_filter(True, "FontName=Arial") == (
        "subtitles=sub.srt:force_style='FontName=Arial'")


def test_make_srt_format(tmp_path):
    srt = v.make_srt(["Hello world", "Second line"],
                     [(0.0, 1.5), (1.8, 3.25)], tmp_path)
    text = srt.read_text(encoding="utf-8")
    assert "1\n00:00:00,000 --> 00:00:01,500\nHello world" in text
    assert "2\n00:00:01,800 --> 00:00:03,250\nSecond line" in text


def test_image_filter_still():
    chain, animate = v.image_filter(1920, 1080, "cover", 1.0, 0.5, 0.5,
                                    "none", 50)
    assert animate is False
    assert "crop=" in chain


def test_image_filter_animated():
    chain, animate = v.image_filter(1920, 1080, "cover", 1.0, 0.5, 0.5,
                                    "zoom-in", 50)
    assert animate is True
    assert "zoompan" in chain


def test_parser_defaults():
    ap = v.build_parser()
    a = ap.parse_args(["x.mp4"])
    assert a.lang == "auto"
    assert a.quality == "good"
    assert a.sub_size == 18
    assert a.aspect == "source"
    assert a.no_subtitles is False
