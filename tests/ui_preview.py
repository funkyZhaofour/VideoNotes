import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import *

app = QApplication([])
app.setStyle("Fusion")
app.setStyleSheet(STYLE)
window = Window()
window.load_video(str(ROOT / "tests/fixtures/burned.mp4"))
window.show()
app.processEvents()
window.grab().save(str(ROOT / "界面预览.png"))
assert window.generate.isEnabled()
assert not window.preview.pixmap.isNull()
window.trial_range()
assert 0 < window.end.value() <= 9
window.reset_roi()
assert window.preview.roi == (0.,.72,1.,.26)
print("UI preview and import controls passed", window.size())
window.close()
