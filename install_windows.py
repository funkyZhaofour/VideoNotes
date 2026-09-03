"""Create a desktop shortcut through Windows' own Desktop-folder resolver."""
import os
import subprocess
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parent


def main():
    if os.name!="nt": raise SystemExit("Run this installer on Windows.")
    icon=ROOT/"icon.ico"
    Image.open(ROOT/"icon.png").save(icon,format="ICO")
    env=dict(os.environ,VIDEONOTES_ROOT=str(ROOT))
    script=r'''
$ErrorActionPreference = 'Stop'
$root = $env:VIDEONOTES_ROOT
$shell = New-Object -ComObject WScript.Shell
$desktop = $shell.SpecialFolders.Item('Desktop')
$path = Join-Path $desktop 'VideoNotes.lnk'
$python = Join-Path $root '.venv\Scripts\pythonw.exe'
if (Test-Path $path) {
  $existing = $shell.CreateShortcut($path)
  if ($existing.TargetPath -ne $python) { throw 'A different VideoNotes shortcut already exists. It was not overwritten.' }
}
$shortcut = $shell.CreateShortcut($path)
$shortcut.TargetPath = $python
$shortcut.Arguments = '"' + (Join-Path $root 'app.py') + '"'
$shortcut.WorkingDirectory = $root
$shortcut.IconLocation = Join-Path $root 'icon.ico'
$shortcut.Description = 'VideoNotes - local video to Word, PDF and Excel'
$shortcut.Save()
Write-Output ('Installed: ' + $path)
'''
    subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",script],env=env,check=True)


if __name__=="__main__": main()
