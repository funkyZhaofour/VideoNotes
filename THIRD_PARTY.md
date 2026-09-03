# Third-party components

The MIT license in this repository covers VideoNotes source code and its generated icon. Dependencies and models keep their own licenses. They are downloaded separately during setup and are not bundled in this repository or its source ZIP.

- **PySide6 / Qt**: LGPLv3 / GPLv3 / commercial; [Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html).
- **FFmpeg**: [upstream licensing](https://ffmpeg.org/legal.html). Windows setup downloads the separately distributed [Gyan Essentials build](https://www.gyan.dev/ffmpeg/builds/) (GPLv3), verifies its publisher-provided SHA-256, and keeps available license/README files. See that distributor for build configuration and corresponding source.
- **Apple Vision**: provided by macOS; [Apple documentation](https://developer.apple.com/documentation/vision).
- **RapidOCR / bundled OCR models**: [RapidOCR](https://github.com/RapidAI/RapidOCR), Apache-2.0; Windows uses `rapidocr-onnxruntime==1.4.4`, whose wheel includes OCR model files.
- **sherpa-onnx**: [project](https://github.com/k2-fsa/sherpa-onnx), Apache-2.0.
- **SenseVoice speech model**: [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) and the license/reference included with its sherpa-onnx export. Model downloads are not relicensed by this repository.
- **Silero VAD model**: [project](https://github.com/snakers4/silero-vad), MIT.
- **python-docx** (MIT), **openpyxl** (MIT), **ReportLab** (BSD), **Pillow** (MIT-CMU), **NumPy** (BSD), **pysubs2** (MIT), **portalocker** (BSD), **ONNX Runtime** (MIT), and their dependencies retain their package licenses.

Pinned speech-model checksums in `download_assets.py` are recorded checksums for reproducibility, not independent publisher signatures. Windows FFmpeg checksums are fetched from the same publisher as the archive. Do not treat them as proof of origin independent of the download host.

Continuous integration downloads a public speech fixture from the sherpa-onnx project. Test videos are generated from simple shapes and text; no user videos or personal evidence records are included.
