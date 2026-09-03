"""Build a normal double-clickable macOS launcher, with no Terminal window."""
from pathlib import Path
import plistlib
import subprocess
import tempfile
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
bundle = ROOT / "视频成册.app"
contents = bundle / "Contents"
for folder in (contents / "MacOS", contents / "Resources"):
    folder.mkdir(parents=True, exist_ok=True)
image = Image.new("RGBA", (1024, 1024))
d = ImageDraw.Draw(image)
d.rounded_rectangle((50,50,974,974), radius=220, fill="#137b66")
d.rounded_rectangle((237,209,812,810), radius=48, fill="#93cdb7")
d.rounded_rectangle((188,166,762,768), radius=48, fill="#f5faf7")
d.rounded_rectangle((248,236,702,499), radius=25, fill="#203e45")
d.polygon([(424,293),(424,445),(552,369)], fill="#5cdec0")
d.rounded_rectangle((248,553,641,581), radius=14, fill="#b5d5c8")
d.rounded_rectangle((248,623,544,651), radius=14, fill="#b5d5c8")
image.save(ROOT / "icon.png")
image.save(contents / "Resources/AppIcon.icns", format="ICNS")
plist = {"CFBundleName": "视频成册", "CFBundleDisplayName": "视频成册",
         "CFBundleIdentifier": "local.videonotes.desktop", "CFBundleVersion": "220",
         "CFBundleShortVersionString": "2.2.0", "CFBundlePackageType": "APPL",
         "CFBundleExecutable": "VideoNotes", "CFBundleIconFile": "AppIcon",
         "LSMinimumSystemVersion": "14.0", "LSUIElement": True,
         "NSHighResolutionCapable": True, "VideoNotesRoot": str(ROOT)}
with (contents / "Info.plist").open("wb") as f:
    plistlib.dump(plist, f)
subprocess.run(["swiftc", "-O", "-module-cache-path", str(Path(tempfile.gettempdir())/"videonotes-swift-cache"),
                str(ROOT/"launcher.swift"), "-o", str(contents/"MacOS/VideoNotes"), "-framework", "AppKit"], check=True)
subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", str(bundle)], check=True)
print(bundle)
