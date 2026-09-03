from pathlib import Path
import json
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QFormLayout,QHBoxLayout,QLineEdit,QPlainTextEdit,
    QComboBox,QPushButton,QLabel,QFileDialog,QListWidget)
from evidence import FIELDS,local_time,new_evidence_id


class EvidenceForm(QWidget):
    save_requested=Signal()
    open_requested=Signal()
    def __init__(self):
        super().__init__()
        self.inputs={}
        self.attachments=[]
        layout=QVBoxLayout(self)
        hint=QLabel("来源信息按原页面填写；未知数据留空。本机导出时间、权利卫士取证时间和可信时间戳签发时间是三类不同信息。")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        actions=QHBoxLayout()
        save=QPushButton("追加一条信息到台账")
        save.clicked.connect(self.save_requested.emit)
        actions.addWidget(save)
        open_button=QPushButton("打开累计台账")
        open_button.clicked.connect(self.open_requested.emit)
        actions.addWidget(open_button)
        actions.addStretch()
        layout.addLayout(actions)
        form=QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        choices={"collected":["待核对","是","否","部分取证"],
                 "rights_guard_used":["","是","否","待核对"],
                 "trusted_timestamp_used":["","是","否","待核对"],
                 "platform":["","哔哩哔哩 / B站","小红书","抖音","微博","快手","微信视频号","其他"],
                 "account_type":["","个人","企业 / 品牌","机构","媒体","其他"],
                 "platform_status":["","未投诉","已提交 / 待处理","处理中","已删除 / 下架","已限制传播","未处理 / 驳回","其他"]}
        long={"description","issue","platform_details","notes"}
        sections={"evidence_id":"来源与证据基本信息", "rights_guard_used":"权利卫士与可信时间戳",
                  "views":"传播数据", "platform_status":"平台处理情况"}
        for key,label in FIELDS:
            if key in sections:
                heading=QLabel("<b>"+sections[key]+"</b>")
                heading.setStyleSheet("margin-top: 10px; color: #147c67;")
                form.addRow(heading)
            if key in choices:
                widget=QComboBox()
                widget.setEditable(True)
                widget.addItems(choices[key])
            elif key in long:
                widget=QPlainTextEdit()
                widget.setFixedHeight(76)
                widget.setPlaceholderText("按实际情况填写，可留空")
            else:
                widget=QLineEdit()
                widget.setPlaceholderText("未知 / 不可见请留空")
            if key in {"rights_guard_capture_at","timestamp_issued_at"}:
                widget.setPlaceholderText("按权利卫士页面或证书原样填写，不自动填入")
            self.inputs[key]=widget
            if key in {"capture_at","metrics_at"}:
                row=QHBoxLayout()
                row.addWidget(widget)
                now=QPushButton("填入现在")
                now.clicked.connect(lambda checked=False,w=widget:w.setText(local_time()))
                row.addWidget(now)
                form.addRow(label,row)
            else:
                form.addRow(label,widget)
        layout.addLayout(form)
        attachrow=QHBoxLayout()
        attachrow.addWidget(QLabel("评论区、网页截图、第三方证书等附件"))
        add=QPushButton("添加截图或文件…")
        add.clicked.connect(self.add_attachments)
        attachrow.addWidget(add)
        remove=QPushButton("移除选中")
        remove.clicked.connect(self.remove_attachment)
        attachrow.addWidget(remove)
        layout.addLayout(attachrow)
        self.files=QListWidget()
        self.files.setFixedHeight(110)
        layout.addWidget(self.files)
        note=QLabel("附件会复制到本次结果文件夹并记录文件名，不会自动读取或验证。每次导出或保存只在累计台账末尾追加一条新记录，旧行不会被替换。")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.set_data({})

    def data(self):
        result={}
        for key,w in self.inputs.items():
            result[key]=(w.toPlainText() if isinstance(w,QPlainTextEdit) else w.currentText() if isinstance(w,QComboBox) else w.text()).strip()
        return result

    def set_data(self,data,attachments=None):
        for key,w in self.inputs.items():
            text=data.get(key,"")
            if key=="evidence_id": text=text or new_evidence_id()
            if key=="collected": text=text or "待核对"
            if isinstance(w,QPlainTextEdit): w.setPlainText(text)
            elif isinstance(w,QComboBox): w.setCurrentText(text)
            else: w.setText(text)
        self.attachments=list(attachments or [])
        self.refresh_files()

    def refresh_files(self):
        self.files.clear()
        self.files.addItems(self.attachments)

    def add_attachments(self):
        paths,_=QFileDialog.getOpenFileNames(self,"添加截图、证书或其他附件","","截图和文件 (*)")
        self.attachments=list(dict.fromkeys(self.attachments+paths))
        self.refresh_files()

    def remove_attachment(self):
        index=self.files.currentRow()
        if index>=0:
            self.attachments.pop(index)
            self.refresh_files()
