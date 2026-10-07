import argparse
import os
import sys
from pathlib import Path

# Must run before PySide6 is imported: moonshine.dll cannot initialise once Qt is loaded.
from .engine.moonshine_engine import preload_native_library

preload_native_library()

from PySide6.QtWidgets import QApplication  # noqa: E402


def log_to_file_when_frozen(path=None):
    """The packaged exe has no console: keep prints and tracebacks in a log people can send us."""
    if not getattr(sys, "frozen", False):
        return None
    path = path or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "EchoLine" / "echoline.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    sys.stdout = sys.stderr = open(path, "w", encoding="utf-8", buffering=1)    # one run per log
    import faulthandler

    faulthandler.enable(sys.stderr)          # native crashes too, not just Python errors
    print(machine_report(), flush=True)
    return path


def machine_report():
    """What a tester's log needs to say about their PC."""
    import ctypes
    import platform
    import winreg

    from . import __version__
    from .models import models_dir

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    except OSError:
        cpu = platform.processor()
    # x64 apps run emulated on ARM PCs (Snapdragon); only IsWow64Process2 tells.
    native = ctypes.c_ushort(0)
    process = ctypes.c_ushort(0)
    try:
        kernel32 = ctypes.WinDLL("kernel32")
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p      # a handle, not a C int
        kernel32.IsWow64Process2(ctypes.c_void_p(kernel32.GetCurrentProcess()),
                                 ctypes.byref(process), ctypes.byref(native))
    except (AttributeError, OSError):
        pass
    arch = {0xAA64: "ARM64 (running x64 emulated)", 0x8664: "x64"}.get(native.value, platform.machine())
    return "\n".join([f"EchoLine {__version__}",
                      f"Windows {platform.version()} ({platform.win32_edition()})",
                      f"CPU {cpu}, {os.cpu_count()} threads",
                      f"Architecture {arch}",
                      f"Models {models_dir()}", ""])


def startup_mode(settings, model, is_downloaded):
    """run: captions now; setup: full onboarding; repair: re-fetch a missing model."""
    if not settings.onboarded:
        return "setup"
    if model and is_downloaded(model):
        return "run"
    return "repair" if model else "setup"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="echoline", description="Live captions for anything playing on your PC.")
    parser.add_argument("--model", choices=["tiny", "small", "medium"], default=None,
                        help="use this model for this run (default: the one chosen at setup)")
    parser.add_argument("--show-latency", action="store_true", help="show p50/p95 caption latency")
    args = parser.parse_args(argv)
    log_to_file_when_frozen()

    qt_app = QApplication(sys.argv[:1])
    qt_app.setQuitOnLastWindowClosed(False)   # hiding captions or closing settings must not quit
    qt_app.setApplicationName("EchoLine")

    from .instance import InstanceServer, notify_running, server_name
    if notify_running(server_name()):
        return 0                               # the running copy shows itself
    instance = InstanceServer(server_name())

    from .ui.style import use_fluent_style
    use_fluent_style()

    from . import models
    from .app import EchoLineApp
    from .audio.loopback import LoopbackSource
    from .audio.microphone import MicrophoneSource
    from .engine.moonshine_engine import MoonshineEngine
    from .settings.model import default_settings_path, load_settings
    from .settings.store import SettingsStore

    settings, was_reset = load_settings(default_settings_path())
    store = SettingsStore(settings, default_settings_path())

    def chosen_model():
        # ponytail: --model also wins after a switch in Settings; it is a developer flag.
        return args.model or store.settings.model

    def make_source(kind):
        return MicrophoneSource() if kind == "microphone" else LoopbackSource()

    def make_engine():
        return MoonshineEngine.load(models.arch(chosen_model()), cache_root=models.models_dir())

    echoline = EchoLineApp(make_source, make_engine, store,
                           show_latency=args.show_latency, settings_reset=was_reset)
    instance.shown.connect(echoline.bring_to_front)
    mode = startup_mode(store.settings, chosen_model(), models.is_downloaded)
    if mode == "run":
        echoline.start()
    else:
        echoline.run_setup(chosen_model() if mode == "repair" else None)
    try:
        return qt_app.exec()
    finally:
        echoline.shutdown()
        instance.close()


if __name__ == "__main__":
    sys.exit(main())
