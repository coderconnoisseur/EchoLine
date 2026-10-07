# Build: python -m PyInstaller packaging/echoline.spec --noconfirm   (output: dist/EchoLine/)
from pathlib import Path

import moonshine_voice

ROOT = Path(SPECPATH).parent
MOONSHINE = Path(moonshine_voice.__file__).parent

a = Analysis(
    [str(ROOT / "packaging" / "echoline_app.py")],
    pathex=[str(ROOT)],
    # moonshine_api loads its DLLs from its own package folder, so keep them there.
    binaries=[(str(MOONSHINE / "moonshine.dll"), "moonshine_voice"),
              (str(MOONSHINE / "onnxruntime.dll"), "moonshine_voice")],
    datas=[(str(ROOT / "echoline" / "ui" / "qml"), "echoline/ui/qml"),
           # the hardware check times Tiny on this clip
           (str(MOONSHINE / "assets" / "two_cities.wav"), "moonshine_voice/assets")],
    hiddenimports=["pycaw.pycaw", "comtypes.stream"],
    # Benchmark/metrics tooling, not used by the app.
    excludes=["vosk", "matplotlib", "librosa", "metrics", "pyarrow", "pandas", "scipy", "tkinter", "pytest"],
)

# PyInstaller's QML hook ships every Qt module; EchoLine only uses Qt Quick, Controls,
# Layouts and Effects. Dropping the rest (QtWebEngine alone is ~200 MB) keeps the
# install small. Any QML import that goes missing fails loudly at startup.
UNUSED = ("WebEngine", "WebChannel", "WebSockets", "WebView", "Qt3D", "3D", "Quick3D", "Pdf", "Charts",
          "DataVisualization", "Graphs", "Multimedia", "Location", "Positioning", "Sensors", "TextToSpeech",
          "RemoteObjects", "Scxml", "VirtualKeyboard", "Qt5Compat", "QtTest", "Qt6Test", "SpatialAudio",
          "Scene2D", "Scene3D", "Particles", "Timeline", "Lottie")


def wanted(entry):
    dest = entry[0].replace("\\", "/")
    return not any(part in dest for part in UNUSED) and "/translations/qtwebengine" not in dest


a.binaries = [b for b in a.binaries if wanted(b)]
a.datas = [d for d in a.datas if wanted(d)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="EchoLine",
    console=False,
    icon=str(ROOT / "packaging" / "echoline.ico"),
)
coll = COLLECT(exe, a.binaries, a.datas, name="EchoLine")
