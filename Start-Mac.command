#!/bin/zsh
set -eu
cd -- "${0:A:h}"
export PYTHONDONTWRITEBYTECODE=1
if [[ ! -x .venv/bin/python ]]; then
  echo 'Run Setup-Mac.command first.'
  read -r
  exit 1
fi
exec .venv/bin/python app.py
