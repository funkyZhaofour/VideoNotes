#!/bin/zsh
set -eu
cd -- "${0:A:h}"
if command -v python3.11 >/dev/null; then
  python3.11 setup.py
elif command -v python3.12 >/dev/null; then
  python3.12 setup.py
else
  echo 'Install Python 3.11 or 3.12, and FFmpeg, before setup.'
  echo 'With Homebrew: brew install python@3.11 ffmpeg'
  read -r
  exit 1
fi
read -r '?Installation finished. Press Return to close.'
