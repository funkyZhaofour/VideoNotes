"""Public synthetic fixtures; no private videos, browser accounts or microphones."""
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw,ImageFont
from docx import Document
from engine import ROOT,Options,Segment,process,run,executable,write_srt,Cancelled
from compat import folder_name


def prepare():
    folder=ROOT/"tests/fixtures"
    folder.mkdir(exist_ok=True)
    candidates=[Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts/arial.ttf",
                Path("/System/Library/Fonts/Supplemental/Arial.ttf"),Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    font_path=next((x for x in candidates if x.is_file()),None)
    font=ImageFont.truetype(str(font_path),38) if font_path else ImageFont.load_default(size=38)
    for i,text in enumerate(["Save 10 pictures","Save 11 pictures","Video Notes complete"]):
        image=Image.new("RGB",(960,540),"#e5f0ed")
        draw=ImageDraw.Draw(image)
        draw.text((70,80),"Video Notes / test slide",font=font,fill="#153e39")
        draw.rectangle((0,410,960,540),fill="#142b34")
        draw.text((130,450),text,font=font,fill="white")
        image.save(folder/f"portable{i}.png")
    (folder/"portable.txt").write_text("".join(f"file 'portable{i}.png'\nduration 2\n" for i in range(3))+"file 'portable2.png'\n",encoding="utf-8")
    run([executable("ffmpeg"),"-v","error","-y","-f","concat","-safe","0","-i",folder/"portable.txt","-t","6","-r","25","-c:v","libx264","-pix_fmt","yuv420p",folder/"burned.mp4"])
    return folder


class Portable(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.fixtures=prepare()

    def test_ocr_custom_folder_and_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            opt=Options(str(self.fixtures/"burned.mp4"),td,word_source="subtitles",visual_changes=False,result_name="我的取证 001")
            path,report=process(opt)
            self.assertEqual(path.name,"我的取证 001")
            self.assertEqual(report["screenshots"],3)
            self.assertIn("10",report["segments"][0]["text"])
            self.assertIn("11",report["segments"][1]["text"])
            self.assertTrue((path/"文字稿.docx").exists())
            self.assertTrue((path/"取证信息.xlsx").exists())
            with self.assertRaises(ValueError): process(opt)
            self.assertTrue((path/"文字稿.docx").exists())

    def test_folder_names(self):
        self.assertEqual(folder_name("证据编号 001"),"证据编号 001")
        for name in ("../outside","a/b","a\\b","CON","nul.txt","a:","ending."," space"):
            with self.assertRaises(ValueError): folder_name(name)

    def test_cancel_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            stop=threading.Event()
            def progress(value,text):
                if value>8: stop.set()
            with self.assertRaises(Cancelled):
                process(Options(str(self.fixtures/"burned.mp4"),td),stop,progress)
            self.assertFalse(list(Path(td).iterdir()))

    def test_speech_sample(self):
        sample=os.environ.get("VIDEONOTES_TEST_AUDIO")
        if not sample: self.skipTest("Set VIDEONOTES_TEST_AUDIO to the documented public speech sample")
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            video=root/"speech.mp4"
            run([executable("ffmpeg"),"-v","error","-y","-i",self.fixtures/"burned.mp4","-i",sample,"-map","0:v","-map","1:a","-t","5.8","-c:v","copy","-c:a","aac",video])
            path,report=process(Options(str(video),str(root/"out"),mode="speech",language="zh",visual_changes=False))
            self.assertEqual(report["word_source"],"音频自动转写")
            self.assertGreater(report["transcript_segments"],0)
            text="\n".join(p.text for p in Document(path/"文字稿.docx").paragraphs)
            self.assertNotIn("Save 10 pictures",text)
            print("Speech transcription produced",report["transcript_segments"],"segments")


if __name__=="__main__": unittest.main()
