"""Download public models/tools at setup time, never while processing a video."""
import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BASE="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
ASR="sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2"
ASR_HASH="7d1efa2138a65b0b488df37f8b89e3d91a60676e416f515b952358d83dfd347e"
HASHES={"sensevoice.int8.onnx":"c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51",
        "tokens.txt":"f449eb28dc567533d7fa59be34e2abca8784f771850c78a47fb731a31429a1dc",
        "silero_vad.onnx":"9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6"}


def digest(path):
    sha=hashlib.sha256()
    with Path(path).open("rb") as file:
        while chunk:=file.read(4*1024*1024): sha.update(chunk)
    return sha.hexdigest()


def download(url,path,expected=None):
    path=Path(path)
    tmp=path.with_suffix(path.suffix+".download")
    print("Downloading:",url,flush=True)
    try:
        request=urllib.request.Request(url,headers={"User-Agent":"VideoNotes/2.1"})
        with urllib.request.urlopen(request,timeout=120) as source,tmp.open("wb") as target:
            shutil.copyfileobj(source,target)
        if expected and digest(tmp)!=expected:
            raise RuntimeError("Download checksum mismatch: "+url)
        tmp.replace(path)
    finally: tmp.unlink(missing_ok=True)


def models():
    folder=ROOT/"models"
    folder.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        archive=Path(td)/ASR
        if any(not (folder/n).exists() or digest(folder/n)!=HASHES[n] for n in ("sensevoice.int8.onnx","tokens.txt")):
            download(BASE+ASR,archive,ASR_HASH)
            names={"model.int8.onnx":"sensevoice.int8.onnx","tokens.txt":"tokens.txt","LICENSE":"sensevoice-LICENSE"}
            with tarfile.open(archive,"r:bz2") as source:
                for item in source:
                    name=Path(item.name).name
                    if item.isfile() and name in names:
                        # Copy only explicitly named regular files, not paths/symlinks.
                        stream=source.extractfile(item)
                        if stream:
                            with (folder/names[name]).open("wb") as target: shutil.copyfileobj(stream,target)
        vad=folder/"silero_vad.onnx"
        if not vad.exists() or digest(vad)!=HASHES[vad.name]:
            download(BASE+vad.name,vad,HASHES[vad.name])
    for name,expected in HASHES.items():
        if not (folder/name).is_file() or digest(folder/name)!=expected: raise RuntimeError("Model verification failed: "+name)
    records=[{"file":n,"sha256":h,"url":BASE+(n if n=="silero_vad.onnx" else ASR)} for n,h in HASHES.items()]
    (folder/"sources.json").write_text(json.dumps(records,indent=2),encoding="utf-8")
    print("Speech models ready.",flush=True)


def windows_ffmpeg():
    if sys.platform!="win32": return
    folder=ROOT/"bin"
    folder.mkdir(exist_ok=True)
    if all((folder/n).exists() or shutil.which(n) for n in ("ffmpeg.exe","ffprobe.exe")): return
    base="https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    with tempfile.TemporaryDirectory() as td:
        archive=Path(td)/"ffmpeg.zip"
        checksum=Path(td)/"checksum.txt"
        download(base+".sha256",checksum)
        expected=checksum.read_text().split()[0]
        if len(expected)!=64 or any(c not in "0123456789abcdefABCDEF" for c in expected): raise RuntimeError("Invalid FFmpeg checksum")
        download(base,archive,expected.lower())
        with zipfile.ZipFile(archive) as source:
            for item in source.infolist():
                name=Path(item.filename).name
                if name in {"ffmpeg.exe","ffprobe.exe","LICENSE","README.txt"}:
                    with source.open(item) as src,(folder/name).open("wb") as dst: shutil.copyfileobj(src,dst)
    if not all((folder/n).is_file() for n in ("ffmpeg.exe","ffprobe.exe")): raise RuntimeError("FFmpeg archive missing executable files")
    (folder/"download-source.json").write_text(json.dumps({"url":base,"sha256":expected,"upstream":"https://ffmpeg.org/download.html"},indent=2),encoding="utf-8")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--ffmpeg-only",action="store_true")
    args=parser.parse_args()
    if not args.ffmpeg_only: models()
    windows_ffmpeg()
