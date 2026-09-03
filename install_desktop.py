from pathlib import Path
import plistlib
import shutil

root = Path(__file__).resolve().parent
source = root / "视频成册.app"
destination = Path.home() / "Desktop" / "视频成册.app"
if destination.exists():
    with (destination/"Contents/Info.plist").open("rb") as file:
        existing=plistlib.load(file)
    if existing.get("VideoNotesRoot")==str(root):
        print(f"桌面入口已存在并指向本项目：{destination}")
        raise SystemExit(0)
    raise SystemExit(f"桌面已有其他位置的同名应用，未覆盖。请使用本项目的 Start-Mac.command：{destination}")
shutil.copytree(source, destination)
print(f"已安装：{destination}")
