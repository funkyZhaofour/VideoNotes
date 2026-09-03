"""One-time source installation for Windows x64 and macOS."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    if not (3,11)<=sys.version_info[:2]<(3,13):
        raise SystemExit("Please install Python 3.11 or 3.12 (64-bit), then run setup again.")
    if sys.platform not in {"darwin","win32"}:
        raise SystemExit("This installer supports macOS and Windows.")
    if sys.platform=="darwin" and not shutil.which("ffmpeg"):
        raise SystemExit("FFmpeg is required. Install Homebrew, then run: brew install ffmpeg")
    venv=ROOT/".venv"
    if not venv.exists(): subprocess.run([sys.executable,"-m","venv",str(venv)],check=True)
    python=venv/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    subprocess.run([str(python),"-m","pip","install","-r",str(ROOT/"requirements.txt")],check=True)
    subprocess.run([str(python),str(ROOT/"download_assets.py")],check=True)
    if sys.platform=="darwin":
        (ROOT/"bin").mkdir(exist_ok=True)
        cache=str(Path(tempfile.gettempdir())/"videonotes-swift-cache")
        subprocess.run(["swiftc","-O","-module-cache-path",cache,str(ROOT/"ocr.swift"),"-o",str(ROOT/"bin/subtitle-ocr"),"-framework","Vision","-framework","Foundation"],check=True)
        subprocess.run([str(python),str(ROOT/"build_app.py")],check=True)
        subprocess.run([str(python),str(ROOT/"install_desktop.py")],check=True)
    else:
        subprocess.run([str(python),str(ROOT/"install_windows.py")],check=True)
    print("Ready. Open VideoNotes from your Desktop. / 安装完成，请打开桌面上的视频成册。")


if __name__=="__main__": main()
