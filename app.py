from __future__ import annotations

import os
import sys
import tempfile
import threading
import json
import hashlib
import re
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QRectF, QUrl
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFileDialog, QComboBox, QDoubleSpinBox,
    QProgressBar, QMessageBox, QSlider, QFrame, QGroupBox, QLineEdit, QScrollArea, QTabWidget, QCheckBox, QBoxLayout, QInputDialog)

from engine import ROOT, Options, process, probe, frame, timestamp, Cancelled
from evidence_ui import EvidenceForm
import evidence
from compat import folder_name


class Preview(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.pixmap = QPixmap()
        self.roi = (0., .72, 1., .26)
        self.origin = None
        self.box = QRectF()
        self.setMinimumSize(300, 180)
        self.setMaximumHeight(340)
        self.setCursor(Qt.CrossCursor)

    def image_rect(self):
        if self.pixmap.isNull():
            return QRectF(self.rect())
        size = self.pixmap.size().scaled(self.size(), Qt.KeepAspectRatio)
        return QRectF((self.width()-size.width())/2, (self.height()-size.height())/2, size.width(), size.height())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#152c35"))
        if self.pixmap.isNull():
            p.setPen(QColor("#c4d5da"))
            p.drawText(self.rect(), Qt.AlignCenter, "拖入一段视频，开始整理\n\nMP4 · MOV · MKV · AVI · WebM")
            return
        r = self.image_rect()
        p.drawPixmap(r.toRect(), self.pixmap)
        x, y, w, h = self.roi
        roi = QRectF(r.x()+x*r.width(), r.y()+y*r.height(), w*r.width(), h*r.height())
        p.fillRect(roi, QColor(37, 200, 166, 36))
        p.setPen(QPen(QColor("#31dfb5"), 2))
        p.drawRect(roi)
        p.fillRect(QRectF(roi.x(), max(r.y(), roi.y()-23), 100, 23), QColor("#137a66"))
        p.setPen(Qt.white)
        p.drawText(QRectF(roi.x()+6, max(r.y(), roi.y()-23), 90, 23), Qt.AlignVCenter, "字幕识别区域")

    def mousePressEvent(self, event):
        if not self.pixmap.isNull() and self.image_rect().contains(event.position()):
            self.origin = event.position()

    def mouseMoveEvent(self, event):
        if self.origin is None:
            return
        r = self.image_rect()
        selected = QRectF(self.origin, event.position()).normalized().intersected(r)
        if selected.width() > 12 and selected.height() > 8:
            self.roi = ((selected.x()-r.x())/r.width(), (selected.y()-r.y())/r.height(), selected.width()/r.width(), selected.height()/r.height())
            self.update()

    def mouseReleaseEvent(self, event):
        self.mouseMoveEvent(event)
        self.origin = None
        self.changed.emit()


class Worker(QThread):
    progress = Signal(float, str)
    complete = Signal(str, object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, options):
        super().__init__()
        self.options = options
        self.stop = threading.Event()

    def run(self):
        try:
            folder, report = process(self.options, self.stop, self.progress.emit)
            self.complete.emit(str(folder), report)
        except Cancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(str(error))


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video = ""
        self.duration = 0
        self.worker = None
        self.result = ""
        self.temp = tempfile.TemporaryDirectory(prefix="video-notes-preview-")
        self.setWindowTitle("视频成册 2.1 · 画面与取证记录")
        self.resize(1040, 740)
        self.setMinimumSize(640, 440)
        self.setAcceptDrops(True)
        if (ROOT / "icon.png").exists():
            self.setWindowIcon(QIcon(str(ROOT / "icon.png")))
        base = QWidget()
        self.setCentralWidget(base)
        layout = QVBoxLayout(base)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(8)
        heading = QHBoxLayout()
        title = QLabel("视频成册")
        title.setObjectName("title")
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(QLabel("界面缩放"))
        self.zoom=QComboBox()
        self.zoom.addItems(["80%","90%","100%","110%","125%"])
        self.zoom.setCurrentText("100%")
        self.zoom.currentTextChanged.connect(self.apply_zoom)
        heading.addWidget(self.zoom)
        badge = QLabel("本地处理  ·  无需账号")
        badge.setObjectName("badge")
        heading.addWidget(badge)
        layout.addLayout(heading)
        subtitle = QLabel("字幕与画面一起记录，来源信息保存到 Excel。")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        self.controls = QWidget()
        body = QVBoxLayout(self.controls)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(12)
        row = QHBoxLayout()
        self.choose = QPushButton("＋  导入视频")
        self.choose.setObjectName("primary")
        self.choose.clicked.connect(self.pick_video)
        row.addWidget(self.choose)
        self.filename = QLabel("选择本机视频，或将视频拖到窗口里")
        self.filename.setWordWrap(True)
        row.addWidget(self.filename, 1)
        body.addLayout(row)

        middle = QHBoxLayout()
        self.middle=middle
        left = QVBoxLayout()
        self.preview = Preview()
        left.addWidget(self.preview, 1)
        seekrow = QHBoxLayout()
        self.seek = QSlider(Qt.Horizontal)
        self.seek.setRange(0, 1000)
        self.seek.setEnabled(False)
        self.seek.sliderReleased.connect(self.update_preview)
        self.seek.valueChanged.connect(self.update_clock)
        seekrow.addWidget(self.seek)
        self.clock = QLabel("00:00:00")
        seekrow.addWidget(self.clock)
        left.addLayout(seekrow)
        hintrow = QHBoxLayout()
        hint = QLabel("拖动进度条找到有字幕的画面，再用鼠标框住字幕。")
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        hintrow.addWidget(hint, 1)
        reset = QPushButton("重置字幕框")
        reset.clicked.connect(self.reset_roi)
        hintrow.addWidget(reset)
        left.addLayout(hintrow)
        middle.addLayout(left, 3)

        settings = QGroupBox("生成方式")
        grid = QVBoxLayout(settings)
        grid.setSpacing(8)
        grid.addWidget(QLabel("PDF 截图依据"))
        self.mode = QComboBox()
        self.mode.addItem("自动：内置字幕 → 画面字幕 → 语音", "auto")
        self.mode.addItem("识别画面里的字幕", "ocr")
        self.mode.addItem("视频无字幕，按语音分段", "speech")
        grid.addWidget(self.mode)
        self.visual_changes=QCheckBox("同时检测画面 / 动作变化")
        self.visual_changes.setChecked(True)
        grid.addWidget(self.visual_changes)
        self.visual_sensitivity=QComboBox()
        for name,value in [("灵敏度：高 · 小动作 / 小表情包","high"),("灵敏度：标准 · 推荐","normal"),("灵敏度：低 · 主要画面变化","low")]:
            self.visual_sensitivity.addItem(name,value)
        self.visual_sensitivity.setCurrentIndex(1)
        grid.addWidget(self.visual_sensitivity)
        self.visual_gap=QComboBox()
        for name,value in [("画面截图间隔 ≥ 0.4 秒",.4),("画面截图间隔 ≥ 0.2 秒",.2),("画面截图间隔 ≥ 1 秒",1.)]:
            self.visual_gap.addItem(name,value)
        grid.addWidget(self.visual_gap)
        grid.addWidget(QLabel("Word 文字来源"))
        self.word_source = QComboBox()
        self.word_source.addItem("从音频识别文字（推荐）", "audio")
        self.word_source.addItem("使用截图对应的字幕文字", "subtitles")
        grid.addWidget(self.word_source)
        grid.addWidget(QLabel("语音语言"))
        self.language = QComboBox()
        for name, value in [("自动识别", "auto"), ("中文普通话", "zh"), ("英语", "en"), ("粤语", "yue"), ("日语", "ja"), ("韩语", "ko")]:
            self.language.addItem(name, value)
        grid.addWidget(self.language)
        grid.addWidget(QLabel("检查字幕与画面的间隔"))
        self.interval = QComboBox()
        for name, value in [("0.5 秒 · 日常使用", .5), ("0.2 秒 · 快速切换字幕", .2), ("1 秒 · 更快，可能漏短字幕", 1.)]:
            self.interval.addItem(name, value)
        grid.addWidget(self.interval)
        grid.addWidget(QLabel("PDF 排版"))
        self.pages = QComboBox()
        self.pages.addItem("每页 2 张 · 便于连续阅读", 2)
        self.pages.addItem("每页 1 张 · 画面更大", 1)
        grid.addWidget(self.pages)
        grid.addStretch()
        middle.addWidget(settings, 2)
        body.addLayout(middle, 1)

        extras = QGridLayout()
        extras.addWidget(QLabel("字幕文件（可选）"), 0, 0)
        self.subtitle = QLineEdit()
        self.subtitle.setPlaceholderText("SRT / VTT / ASS；选择后优先按该文件截图")
        extras.addWidget(self.subtitle, 0, 1)
        subbutton = QPushButton("选择字幕…")
        subbutton.clicked.connect(self.pick_subtitle)
        extras.addWidget(subbutton, 0, 2)
        extras.addWidget(QLabel("保存位置"), 1, 0)
        self.output = QLineEdit(str(Path.home() / "Documents" / "视频成册"))
        extras.addWidget(self.output, 1, 1)
        outbutton = QPushButton("选择文件夹…")
        outbutton.clicked.connect(self.pick_output)
        extras.addWidget(outbutton, 1, 2)
        extras.addWidget(QLabel("本次结果文件夹名"),2,0)
        self.result_name=QLineEdit()
        self.result_name.setPlaceholderText("自行命名；留空则按视频名和时间自动命名")
        extras.addWidget(self.result_name,2,1)
        create=QPushButton("新建文件夹…")
        create.clicked.connect(self.new_result_folder)
        extras.addWidget(create,2,2)
        self.destination_hint=QLabel()
        self.destination_hint.setWordWrap(True)
        self.destination_hint.setObjectName("hint")
        extras.addWidget(self.destination_hint,3,0,1,3)
        self.output.textChanged.connect(self.update_destination_hint)
        self.result_name.textChanged.connect(self.update_destination_hint)
        self.update_destination_hint()
        body.addLayout(extras)
        range_row = QGridLayout()
        range_row.addWidget(QLabel("处理范围"),0,0)
        self.start = QDoubleSpinBox()
        self.end = QDoubleSpinBox()
        for spin in (self.start, self.end):
            spin.setDecimals(1)
            spin.setRange(0, 999999)
            spin.setSuffix(" 秒")
            spin.setMinimumWidth(120)
        self.end.setSpecialValueText("直到视频结束")
        range_row.addWidget(self.start,0,1)
        range_row.addWidget(QLabel("至"),0,2)
        range_row.addWidget(self.end,0,3)
        trial = QPushButton("先试前 1 分钟")
        trial.clicked.connect(self.trial_range)
        range_row.addWidget(trial,1,1)
        entire = QPushButton("整个视频")
        entire.clicked.connect(lambda: (self.start.setValue(0), self.end.setValue(0)))
        range_row.addWidget(entire,1,3)
        range_row.setColumnStretch(4,1)
        body.addLayout(range_row)
        self.tabs=QTabWidget()
        self.video_scroll=QScrollArea()
        self.video_scroll.setWidgetResizable(True)
        self.video_scroll.setFrameShape(QFrame.NoFrame)
        self.video_scroll.setWidget(self.controls)
        self.tabs.addTab(self.video_scroll,"视频与截图")
        self.evidence_form=EvidenceForm()
        self.evidence_form.save_requested.connect(self.save_evidence_only)
        self.evidence_form.open_requested.connect(self.open_ledger)
        evidence_scroll=QScrollArea()
        evidence_scroll.setWidgetResizable(True)
        evidence_scroll.setFrameShape(QFrame.NoFrame)
        evidence_scroll.setWidget(self.evidence_form)
        self.tabs.addTab(evidence_scroll,"取证信息与附件")
        layout.addWidget(self.tabs,1)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #dce5e4;")
        layout.addWidget(divider)
        self.status = QLabel("就绪 · 将生成 Word 文字稿、截图 PDF，以及可单独使用的图片和字幕。")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(9)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        bottom = QHBoxLayout()
        self.open_result = QPushButton("打开结果文件夹")
        self.open_result.setEnabled(False)
        self.open_result.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.result)))
        bottom.addWidget(self.open_result)
        self.open_pdf = QPushButton("查看 PDF")
        self.open_pdf.setEnabled(False)
        self.open_pdf.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.result) / "字幕截图.pdf"))))
        bottom.addWidget(self.open_pdf)
        bottom.addStretch()
        self.cancel = QPushButton("取消")
        self.cancel.setEnabled(False)
        self.cancel.clicked.connect(self.cancel_work)
        bottom.addWidget(self.cancel)
        self.generate = QPushButton("生成文档 + 取证表")
        self.generate.setObjectName("primary")
        self.generate.setMinimumWidth(150)
        self.generate.setEnabled(False)
        self.generate.clicked.connect(self.begin)
        bottom.addWidget(self.generate)
        layout.addLayout(bottom)
        note = QLabel("短于采样间隔的变化可能遗漏；提高灵敏度会增加图片。可先试 1 分钟。")
        note.setObjectName("hint")
        note.setWordWrap(True)
        layout.addWidget(note)
        screen=QApplication.primaryScreen()
        if screen:
            available=screen.availableGeometry()
            self.resize(min(1040,available.width()-40),min(740,available.height()-70))
            self.move(available.x()+(available.width()-self.width())//2,available.y()+25)

    def apply_zoom(self,text):
        factor=int(text.rstrip("%"))/100
        scaled=re.sub(r"(font-size:\s*)(\d+)px",lambda m:m[1]+str(round(int(m[2])*factor))+"px",STYLE)
        self.setStyleSheet(scaled)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,"middle"):
            desired=QBoxLayout.TopToBottom if self.width()<900 else QBoxLayout.LeftToRight
            if self.middle.direction()!=desired:
                self.middle.setDirection(desired)

    def draft_path(self):
        key=hashlib.sha256(self.video.encode()).hexdigest()[:24]
        return ROOT/"草稿"/(key+".json")

    def save_draft(self):
        path=self.draft_path()
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"fields":self.evidence_form.data(),"attachments":self.evidence_form.attachments},ensure_ascii=False),encoding="utf-8")

    def open_ledger(self):
        path=Path(self.output.text()).expanduser()/"取证台账.xlsx"
        if path.exists(): QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        else: QMessageBox.information(self,"暂无台账","生成文档或保存取证信息后，这里会出现累计 Excel 台账。保存位置可在“视频与截图”页修改。")

    def save_evidence_only(self):
        try:
            if not self.output.text().strip(): raise ValueError("请先在视频页选择保存文件夹。")
            record=evidence.make_record(self.evidence_form.data(),export_finished_at=evidence.local_time(),original_file=self.video,
                                       attachment_names="\n".join(self.evidence_form.attachments),generated_files="仅保存信息，未生成取证文件或复制附件")
            path=evidence.append_ledger(record,Path(self.output.text()).expanduser())
            self.save_draft()
            self.status.setText("已追加一条取证记录到台账（仅保存信息）。")
        except Exception as error:
            QMessageBox.warning(self,"取证记录未保存",str(error))

    def update_clock(self):
        self.clock.setText(timestamp(self.duration*self.seek.value()/1000).split(".")[0])

    def update_preview(self):
        if not self.video:
            return
        try:
            at = min(self.duration-.05, self.duration*self.seek.value()/1000)
            path = Path(self.temp.name) / "preview.jpg"
            frame(self.video, max(0, at), path, width=1280)
            self.preview.pixmap = QPixmap(str(path))
            self.preview.update()
        except Exception as error:
            self.status.setText("预览失败：" + str(error))

    def reset_roi(self):
        self.preview.roi = (0., .72, 1., .26)
        self.preview.update()

    def pick_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入视频", str(Path.home()), "视频 (*.mp4 *.mov *.mkv *.m4v *.avi *.webm *.wmv *.flv *.ts);;所有文件 (*)")
        if path:
            self.load_video(path)

    def load_video(self, path):
        if self.worker and self.worker.isRunning():
            return
        try:
            _, duration = probe(path)
        except Exception as error:
            QMessageBox.warning(self, "无法导入视频", str(error))
            return
        old_video=self.video
        if old_video: self.save_draft()
        self.video, self.duration = str(Path(path).resolve()), duration
        if self.draft_path().exists():
            try:
                draft=json.loads(self.draft_path().read_text(encoding="utf-8"))
                self.evidence_form.set_data(draft["fields"],draft.get("attachments",[]))
            except (ValueError,KeyError):
                self.evidence_form.set_data({})
        elif old_video and old_video!=self.video:
            self.evidence_form.set_data({})
        self.filename.setText(f"{Path(path).name}\n时长 {timestamp(duration).split('.')[0]}")
        self.filename.setToolTip(str(path))
        self.seek.setEnabled(True)
        self.seek.setValue(min(1000, round(5000/duration)))
        self.start.setValue(0)
        self.end.setValue(0)
        self.subtitle.clear()
        for ext in (".srt", ".vtt", ".ass"):
            candidate = Path(path).with_suffix(ext)
            if candidate.exists():
                self.subtitle.setText(str(candidate))
                break
        self.update_preview()
        self.generate.setEnabled(True)
        self.status.setText("视频已导入 · 请确认绿色框覆盖字幕，或选择“视频无字幕，按语音分段”。")

    def pick_subtitle(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择字幕文件", str(Path(self.video).parent) if self.video else str(Path.home()), "字幕 (*.srt *.vtt *.ass *.ssa);;所有文件 (*)")
        if path:
            self.subtitle.setText(path)

    def pick_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存文件夹", self.output.text())
        if path:
            self.output.setText(path)

    def new_result_folder(self):
        name,ok=QInputDialog.getText(self,"新建结果文件夹","输入本次结果文件夹名称（开始处理时创建）：",text=self.result_name.text())
        if ok and name:
            try:
                folder_name(name)
                target=Path(self.output.text()).expanduser()/name
                if target.exists(): raise ValueError("该文件夹已存在，请换一个名称。")
                self.result_name.setText(name)
            except ValueError as error:
                QMessageBox.warning(self,"名称不可用",str(error))

    def update_destination_hint(self):
        name=self.result_name.text() or "〈按视频名和时间自动新建〉"
        self.destination_hint.setText("实际保存到："+str(Path(self.output.text()).expanduser()/name))

    def trial_range(self):
        self.start.setValue(0)
        self.end.setValue(min(60, self.duration) if self.duration else 60)

    def begin(self):
        if not self.output.text().strip():
            QMessageBox.warning(self, "请选择保存位置", "请先选择保存文件夹。")
            return
        try:
            name=folder_name(self.result_name.text())
            if name and (Path(self.output.text()).expanduser()/name).exists():
                raise ValueError("本次结果文件夹已存在，请更换名称。")
        except ValueError as error:
            QMessageBox.warning(self,"结果文件夹名称不可用",str(error))
            return
        subtitle = self.subtitle.text().strip()
        if subtitle and not Path(subtitle).is_file():
            QMessageBox.warning(self, "字幕文件不存在", "请重新选择字幕文件，或清空字幕文件栏。")
            return
        if self.start.value() >= self.duration or (self.end.value() > 0 and self.end.value() <= self.start.value()):
            QMessageBox.warning(self, "处理范围不正确", "结束时间应晚于开始时间，开始时间应位于视频内。")
            return
        opt = Options(video=self.video, output=self.output.text().strip(), subtitle=subtitle,
                      mode=self.mode.currentData(), word_source=self.word_source.currentData(),
                      language=self.language.currentData(), roi=self.preview.roi, interval=self.interval.currentData(),
                      per_page=self.pages.currentData(), start=self.start.value(), end=self.end.value(),
                      visual_changes=self.visual_changes.isChecked(),visual_sensitivity=self.visual_sensitivity.currentData(),
                      visual_gap=self.visual_gap.currentData(),evidence=self.evidence_form.data(),attachments=list(self.evidence_form.attachments),result_name=name)
        self.save_draft()
        self.evidence_form.setEnabled(False)
        self.controls.setEnabled(False)
        self.generate.setEnabled(False)
        self.cancel.setEnabled(True)
        self.open_result.setEnabled(False)
        self.open_pdf.setEnabled(False)
        self.progress.setValue(0)
        self.worker = Worker(opt)
        self.worker.progress.connect(self.show_progress)
        self.worker.complete.connect(self.completed)
        self.worker.failed.connect(self.failed)
        self.worker.cancelled.connect(self.cancelled)
        self.worker.finished.connect(self.reenable)
        self.worker.start()

    def show_progress(self, value, text):
        self.progress.setValue(max(self.progress.value(), round(value)))
        self.status.setText(text)

    def reenable(self):
        self.evidence_form.setEnabled(True)
        self.controls.setEnabled(True)
        self.generate.setEnabled(bool(self.video))
        self.cancel.setEnabled(False)

    def completed(self, folder, report):
        self.result = folder
        self.open_result.setEnabled(True)
        self.open_pdf.setEnabled(True)
        self.status.setText(f"已完成 · {report['screenshots']} 张截图 ｜ Word：{report['word_source']} ｜ PDF：{report['screenshot_source']}")
        if report["warnings"]:
            self.status.setToolTip("\n".join(report["warnings"]))
        if report.get("ledger_error"):
            QMessageBox.warning(self,"文档已保存，累计台账未追加",report["ledger_error"]+"\n本次结果文件夹里仍有取证信息.xlsx，可以单独查看或手动合并。")

    def failed(self, message):
        self.status.setText("未完成 · 请查看原因后重试。")
        QMessageBox.warning(self, "处理未完成", message)

    def cancelled(self):
        self.status.setText("已取消 · 本次临时文件已清理。")
        self.progress.setValue(0)

    def cancel_work(self):
        if self.worker:
            self.worker.stop.set()
            self.cancel.setEnabled(False)
            self.status.setText("正在取消并清理临时文件…")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and not (self.worker and self.worker.isRunning()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.load_video(urls[0].toLocalFile())

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.cancel_work()
            self.status.setText("正在取消。清理结束后即可关闭窗口。")
            event.ignore()
            return
        self.save_draft()
        self.temp.cleanup()
        event.accept()


STYLE = """
QMainWindow { background: #f5f8f7; }
QWidget { color: #203b43; font-size: 13px; font-family: 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', 'Helvetica Neue'; }
QLabel#title { font-size: 30px; font-weight: 650; }
QLabel#subtitle { font-size: 14px; color: #687d82; padding-bottom: 3px; }
QLabel#hint { font-size: 11px; color: #77868a; }
QLabel#badge { color: #187b68; background: #e2f2eb; border-radius: 12px; padding: 7px 14px; font-size: 11px; }
QPushButton { background: white; border: 1px solid #d6e1de; border-radius: 7px; padding: 8px 13px; }
QPushButton:hover { background: #eaf4ef; border-color: #9ac7b8; }
QPushButton:disabled { color: #9aa9a5; background: #eef1ef; border-color: #e0e7e3; }
QPushButton#primary { color: white; background: #147c67; border-color: #147c67; font-weight: 600; padding: 10px 17px; }
QPushButton#primary:hover { background: #09624f; }
QPushButton#primary:disabled { background: #a8c8bd; border-color: #a8c8bd; }
QGroupBox { background: #ffffff; border: 1px solid #dce6e1; border-radius: 10px; margin-top: 13px; padding: 14px; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 5px; font-weight: 600; }
QComboBox, QLineEdit, QDoubleSpinBox { background: white; border: 1px solid #d6e1de; border-radius: 5px; padding: 7px; min-height: 17px; }
QComboBox { padding-right: 20px; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: white; selection-background-color: #d2e9de; color: #203b43; }
QProgressBar { background: #dfeae5; border: none; border-radius: 4px; }
QProgressBar::chunk { background: #199479; border-radius: 4px; }
QSlider::groove:horizontal { height: 4px; background: #d9e5df; border-radius: 2px; }
QSlider::handle:horizontal { width: 13px; margin: -5px 0; background: #147c67; border-radius: 6px; }
QTabWidget::pane { border: 1px solid #dce6e1; border-radius: 6px; }
QTabBar::tab { padding: 9px 18px; background: #e8f0ed; }
QTabBar::tab:selected { background: white; color: #137b66; font-weight: 600; }
QPlainTextEdit, QListWidget { background: white; border: 1px solid #d6e1de; border-radius: 5px; padding: 5px; }
"""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("视频成册")
    app.setOrganizationName("Local Tools")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = Window()
    window.show()
    if len(sys.argv) > 1 and Path(sys.argv[1]).is_file():
        window.load_video(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
