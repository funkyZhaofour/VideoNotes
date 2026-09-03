# Contributing

Bug reports and pull requests are welcome. Describe your OS, Python version, selected mode, sampling interval, and the error message. Use a short synthetic or public test video if possible; never attach private evidence records, account credentials, transcripts, or personal videos.

Install with Python 3.11 or 3.12. Platform-specific code is kept in `compat.py`, OCR helpers and setup scripts. The application does not access websites or upload video during normal processing.

Validation commands:

```text
python tests/test_portable.py
python tests/verify_v2.py
python tests/ui_v2.py
```

The speech test is optional locally: set `VIDEONOTES_TEST_AUDIO` to a local speech WAV. CI uses the documented public sherpa-onnx fixture. Tests generate outputs under `tests/`, which are ignored by Git. On macOS, `VIDEONOTES_OCR=rapidocr` exercises the Windows OCR backend if its dependencies are installed.

Generated output, models, virtual environments and drafts must remain untracked. Preserve literal account IDs and unknown metrics in Excel exports, and never replace an existing result directory.
