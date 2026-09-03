"""One disclaimer source, shared by the app and future exported folders."""
from pathlib import Path

VERSION="2026-09-03"
SHORT_NOTICE="自动识别结果需人工核对。本工具不提供公证、司法鉴定或可信时间戳，不保证材料被采纳。"


def disclaimer_text():
    return (Path(__file__).resolve().parent/"DISCLAIMER.md").read_text(encoding="utf-8")


def export_notice(folder):
    path=Path(folder)/"免责声明与使用边界.txt"
    path.write_text(disclaimer_text(),encoding="utf-8")
    return path
