"""Small platform boundaries shared by the desktop app and workers."""
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def process_options():
    return {"creationflags":0x08000000} if os.name=="nt" else {}


def ocr_command():
    if sys.platform=="darwin" and os.environ.get("VIDEONOTES_OCR")!="rapidocr":
        return [str(ROOT/"bin/subtitle-ocr")]
    python=Path(sys.executable)
    # A console Python child gives reliable redirected stdio under pythonw.exe.
    if python.name.lower()=="pythonw.exe": python=python.with_name("python.exe")
    return [str(python),"-u",str(ROOT/"ocr_rapid.py")]


def folder_name(value):
    if not value:
        return ""
    if value!=value.strip() or any(ord(c)<32 or c in '<>:"/\\|?*' for c in value) or value in {".",".."} or value.endswith(("."," ")):
        raise ValueError('文件夹名称不能包含 / \\ : * ? " < > |，也不能以空格或点结尾。')
    if value.split('.')[0].upper() in {"CON","PRN","AUX","NUL",*(f"COM{i}" for i in range(1,10)),*(f"LPT{i}" for i in range(1,10))}:
        raise ValueError("这个名称被 Windows 保留，请换一个文件夹名称。")
    if len(value)>120:
        raise ValueError("文件夹名称请控制在 120 个字符以内。")
    return value
