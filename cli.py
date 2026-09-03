import argparse
import threading
from engine import Options, process, Cancelled

parser = argparse.ArgumentParser(description="将本地视频转换为 Word 文字稿及字幕截图 PDF")
parser.add_argument("video")
parser.add_argument("--output", required=True)
parser.add_argument("--subtitle", default="")
parser.add_argument("--mode", choices=["auto", "ocr", "speech"], default="auto")
parser.add_argument("--word-source", choices=["audio", "subtitles"], default="audio")
parser.add_argument("--language", choices=["auto", "zh", "en", "yue", "ja", "ko"], default="auto")
parser.add_argument("--interval", type=float, default=.5)
parser.add_argument("--per-page", type=int, choices=[1,2], default=2)
parser.add_argument("--start", type=float, default=0)
parser.add_argument("--end", type=float, default=0)
parser.add_argument("--result-name",default="",help="本次结果子文件夹名称；留空自动命名")
parser.add_argument("--no-visual-changes",dest="visual_changes",action="store_false",help="仅按字幕 / 语音分段截图")
parser.add_argument("--visual-sensitivity",choices=["high","normal","low"],default="normal")
parser.add_argument("--visual-gap",type=float,default=.4)
args = parser.parse_args()
folder, report = process(Options(**vars(args)), progress=lambda p,t: print(f"{p:5.1f}% {t}", flush=True))
print(f"保存到：{folder}")
