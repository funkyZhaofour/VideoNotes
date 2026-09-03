import sys
import unittest
import tempfile
import threading
import json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw
from openpyxl import load_workbook
from engine import ROOT,Options,Segment,process,run,executable,write_srt
from evidence import make_record,append_ledger,fingerprint
from visual import Detector
import numpy as np


class Upgrade(unittest.TestCase):
    def test_gesture_overlay_scene_and_spreadsheet(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for i in range(8):
                im=Image.new("RGB",(640,360),"#c5d7d0")
                draw=ImageDraw.Draw(im)
                draw.rectangle((70,60,170,200),fill="#383333")
                if i in (1,2):
                    draw.rectangle((170,80,260+i*25,115),fill="#383333")
                if i==3: im=Image.new("RGB",(640,360),"#913994")
                if i==5: draw.rectangle((390,65,455,130),fill="#ff2400")
                im.save(root/f"{i}.png")
            (root/"frames.txt").write_text("".join(f"file '{i}.png'\nduration 0.5\n" for i in range(8))+"file '7.png'\n")
            video=root/"motion.mp4"
            run([executable("ffmpeg"),"-v","error","-y","-f","concat","-safe","0","-i",root/"frames.txt","-t","4","-r","25","-c:v","libx264","-pix_fmt","yuv420p",video])
            write_srt([Segment(0,4,"字幕始终不变")],root/"same.srt")
            fields={"evidence_id":"EV-DEMO-001","uid":"00001234567890123456789","description":"=1+1","views":"","likes":"1.2万","platform":"B站","collected":"否","capture_at":"2026-09-03 10:15 +08:00","title":"人物动作与插入表情包测试"}
            output,report=process(Options(str(video),str(root/"out"),subtitle=str(root/"same.srt"),word_source="subtitles",interval=.2,
                evidence=fields,attachments=[str(root/"5.png")]))
            times=[r["capture"] for r in report["segments"] if "画面" in r["reason"]]
            print("Visual changes:",times)
            self.assertTrue(any(.4<=t<=.8 for t in times),"gesture missed")
            self.assertTrue(any(1.4<=t<=1.8 for t in times),"cut missed")
            self.assertTrue(any(2.4<=t<=2.8 for t in times),"small overlay missed")
            self.assertGreaterEqual(len(times),6)
            self.assertEqual(report["transcript_segments"],1)
            record=report["evidence"]
            self.assertEqual(record["sha256"],fingerprint(video))
            self.assertEqual(record["collected"],"否")
            self.assertEqual(record["capture_at"],fields["capture_at"])
            self.assertTrue((output/"评论区等附件/001_5.png").is_file())
            for file in (output/"取证信息.xlsx",root/"out/取证台账.xlsx"):
                book=load_workbook(file)
                sheet=book["取证台账"]
                head={sheet.cell(1,c).value:c for c in range(1,sheet.max_column+1)}
                self.assertEqual(sheet.cell(2,head["账号 ID / UID"]).value,fields["uid"])
                self.assertEqual(sheet.cell(2,head["视频文案"]).data_type,"s")
                self.assertIsNone(sheet.cell(2,head["浏览量"]).value)
                book.close()
            # Silent, text-free footage still produces a visual PDF.
            silent,report2=process(Options(str(video),str(root/"out"),mode="speech",interval=.2))
            self.assertEqual(report2["word_source"],"无可用语音或字幕")
            self.assertGreater(report2["screenshots"],1)
            book=load_workbook(root/"out/取证台账.xlsx")
            self.assertEqual(book["取证台账"].max_row,3)
            book.close()
            import shutil
            sample=ROOT/"tests/v2-demo"
            sample.mkdir(exist_ok=True)
            for name in ("字幕截图.pdf","取证信息.xlsx","取证信息.json","处理记录.json"):
                shutil.copy2(output/name,sample/name)
            shutil.copy2(root/"out/取证台账.xlsx",sample/"取证台账.xlsx")

    def test_noise_vs_small_change(self):
        frame=np.zeros((180,320,3),np.uint8)+100
        detector=Detector()
        self.assertTrue(detector.accept(0,frame))
        self.assertFalse(detector.accept(.5,frame+1))
        changed=frame.copy()
        changed[30:55,50:80]=255
        self.assertTrue(detector.accept(1,changed))

    def test_ledger_preserves_manual_edit(self):
        with tempfile.TemporaryDirectory() as td:
            path=append_ledger(make_record({"title":"第一条"}),td)
            book=load_workbook(path)
            book["取证台账"]["A2"]="手工修改的编号"
            book.save(path)
            book.close()
            append_ledger(make_record({"title":"第二条"}),td)
            book=load_workbook(path)
            self.assertEqual(book["取证台账"]["A2"].value,"手工修改的编号")
            self.assertEqual(book["取证台账"].max_row,3)
            book.close()


if __name__=="__main__": unittest.main()
