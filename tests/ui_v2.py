import os,sys,time,tempfile
os.environ["QT_QPA_PLATFORM"]="offscreen"
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import *
from evidence import workbook_for,make_record

app=QApplication([])
app.setStyle("Fusion")
app.setStyleSheet(STYLE)
w=Window()
w.load_video(str(ROOT/"tests/fixtures/burned.mp4"))
w.show()
app.processEvents()
for zoom in ("80%","100%","125%"):
    w.zoom.setCurrentText(zoom)
    w.resize(660,510)
    app.processEvents()
    assert w.height()<=510
    assert w.generate.mapTo(w,w.generate.rect().bottomRight()).y()<w.height()
    assert w.middle.direction()==QBoxLayout.TopToBottom
w.zoom.setCurrentText("100%")
w.grab().save(str(ROOT/"新版小窗口.png"))
w.tabs.setCurrentIndex(1)
app.processEvents()
w.grab().save(str(ROOT/"取证信息界面.png"))
# Exercise the real worker signals and UI completion state without OCR services.
with tempfile.TemporaryDirectory() as out:
    w.output.setText(out)
    w.mode.setCurrentIndex(w.mode.findData("speech"))
    w.evidence_form.set_data({"evidence_id":"EV-UI-TEST","platform":"界面测试"})
    failures=[]
    w.begin()
    w.worker.failed.connect(failures.append)
    limit=time.monotonic()+30
    while w.worker.isRunning() and time.monotonic()<limit:
        app.processEvents()
        time.sleep(.02)
    app.processEvents()
    assert not w.worker.isRunning()
    assert not failures,failures
    assert w.open_result.isEnabled() and w.generate.isEnabled()
    assert (Path(out)/"取证台账.xlsx").exists()
w.evidence_form.set_data({})
w.close()
book=workbook_for(make_record({}))
book["取证台账"].delete_rows(2)
book.save(ROOT/"取证台账模板.xlsx")
print("Responsive layout, zoom, threaded export, and Excel completion passed")
