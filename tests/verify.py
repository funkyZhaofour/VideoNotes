"""End-to-end fixtures for distinct subtitle changes and separate audio text."""
import json
import os
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import *

FIX = ROOT / "tests/fixtures"
OUT = ROOT / "tests/results"


def fixtures():
    from PIL import ImageDraw, ImageFont
    FIX.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    font_path = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
    title_font = ImageFont.truetype(font_path, 44)
    sub_font = ImageFont.truetype(font_path, 36)
    cues = ["第一步：导入视频", "第二步：保存 10 张图片", "第二步：保存 11 张图片"]
    for i, text in enumerate(cues):
        im = Image.new("RGB", (1280, 720), "#eef5f3")
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((60, 60, 1220, 545), radius=22, fill="#ffffff", outline="#d2e3dc", width=3)
        d.text((105, 100), "视频成册 · 演示课程", font=title_font, fill="#173e39")
        d.text((105, 240), "画面保持不变，字幕逐段切换", font=sub_font, fill="#52736d")
        d.rectangle((0, 590, 1280, 720), fill="#172e35")
        box = d.textbbox((0, 0), text, font=sub_font)
        d.text(((1280-box[2])/2, 625), text, font=sub_font, fill="white")
        im.save(FIX / f"slide{i}.png")
    concat = "".join(f"file 'slide{i}.png'\nduration 3\n" for i in range(3)) + "file 'slide2.png'\n"
    (FIX / "frames.txt").write_text(concat)
    run([executable("ffmpeg"), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", FIX / "frames.txt",
         "-t", "9", "-r", "25", "-c:v", "libx264", "-pix_fmt", "yuv420p", FIX / "burned.mp4"])
    write_srt([Segment(i*3,(i+1)*3,t) for i,t in enumerate(cues)], FIX / "timed.srt")
    run(["/usr/bin/say", "-v", "Tingting", "-r", "160", "-o", FIX / "speech.aiff",
         "这是一段测试录音。我们正在把视频转换成文字。最后保存为文档。"])
    run([executable("ffmpeg"), "-v", "error", "-y", "-i", FIX / "burned.mp4", "-i", FIX / "speech.aiff",
         "-map", "0:v", "-map", "1:a", "-t", "9", "-c:v", "copy", "-c:a", "aac", FIX / "spoken.mp4"])
    run([executable("ffmpeg"), "-v", "error", "-y", "-i", FIX / "spoken.mp4", "-i", FIX / "timed.srt",
         "-map", "0", "-map", "1", "-c", "copy", "-c:s", "mov_text", FIX / "embedded.mp4"])


class EndToEnd(unittest.TestCase):
    def test_ocr_changes(self):
        path, report = process(Options(str(FIX / "burned.mp4"), str(OUT), mode="ocr", word_source="subtitles", visual_changes=False),
                               progress=lambda p,t: print(t, flush=True) if p > 75 else None)
        print("OCR", json.dumps(report["segments"], ensure_ascii=False), flush=True)
        self.assertEqual(report["screenshots"], 3)
        self.assertIn("10", report["segments"][1]["text"])
        self.assertIn("11", report["segments"][2]["text"])
        self.assertTrue((path / "字幕截图.pdf").stat().st_size > 10000)
        self.assertEqual(len(list((path/"截图").glob("*.jpg"))), 3)

    def test_audio_and_embedded(self):
        path, report = process(Options(str(FIX / "embedded.mp4"), str(OUT), language="zh", visual_changes=False))
        self.assertEqual(report["screenshot_source"], "视频内置字幕")
        self.assertEqual(report["word_source"], "音频自动转写")
        text = (path / "文字稿.txt").read_text()
        print("ASR", text, flush=True)
        self.assertTrue("测试" in text or "录音" in text)
        self.assertNotIn("第二步", text)
        self.assertEqual(report["screenshots"], 3)

    def test_speech_mode(self):
        path, report = process(Options(str(FIX/"spoken.mp4"), str(OUT), mode="speech", language="zh", per_page=1, visual_changes=False))
        self.assertIn("语音分段", report["screenshot_source"])
        self.assertGreater(report["screenshots"], 0)

    def test_clip_and_silent_fallback(self):
        path, report = process(Options(str(FIX/"burned.mp4"), str(OUT), subtitle=str(FIX/"timed.srt"), start=3.5, end=6.5, visual_changes=False))
        self.assertEqual(report["screenshots"], 2)
        self.assertEqual(report["segments"][0]["start"], 3.5)
        self.assertEqual(report["segments"][-1]["end"], 6.5)
        self.assertEqual(report["word_source"], "字幕文件")

    def test_cancel_removes_partial(self):
        stop = threading.Event()
        before = set(OUT.iterdir())
        def progress(p, text):
            if p > 8:
                stop.set()
        with self.assertRaises(Cancelled):
            process(Options(str(FIX/"burned.mp4"), str(OUT), mode="ocr"), stop, progress)
        self.assertEqual(before, set(OUT.iterdir()))

    def test_repeated_caption_after_gap(self):
        rows = group_observations([(0,"测试"),(.5,"测试"),(1,""),(1.5,"测试"),(2,"改变")], .5, 2.5)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].end, 1)
        self.assertEqual(rows[1].start, 1.5)

    def test_overlapping_subtitles(self):
        file = FIX/"overlap.srt"
        write_srt([Segment(0,3,"中文"), Segment(1,2,"English")], file)
        rows = load_subtitles(file, 0, 3)
        self.assertEqual([r.text for r in rows], ["中文", "中文\nEnglish", "中文"])


if __name__ == "__main__":
    fixtures()
    unittest.main()
