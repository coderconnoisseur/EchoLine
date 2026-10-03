import argparse
import sys

# Must run before PySide6 is imported: moonshine.dll cannot initialise once Qt is loaded.
from .engine.moonshine_engine import preload_native_library

preload_native_library()

from PySide6.QtGui import QGuiApplication  # noqa: E402

DEFAULT_MODEL = "tiny"   # from docs/benchmarks/2026-10-engine-bench.md


def main(argv=None):
    parser = argparse.ArgumentParser(prog="echoline", description="Live captions for anything playing on your PC.")
    parser.add_argument("--model", choices=["tiny", "small", "medium"], default=DEFAULT_MODEL)
    parser.add_argument("--show-latency", action="store_true", help="show p50/p95 caption latency")
    args = parser.parse_args(argv)

    qt_app = QGuiApplication(sys.argv[:1])
    qt_app.setApplicationName("EchoLine")

    from .ui.style import use_fluent_style
    use_fluent_style()

    from moonshine_voice import ModelArch

    from .app import EchoLineApp
    from .audio.loopback import LoopbackSource
    from .engine.moonshine_engine import MoonshineEngine

    from .settings.model import default_settings_path, load_settings
    from .settings.store import SettingsStore
    settings, was_reset = load_settings(default_settings_path())
    store = SettingsStore(settings, default_settings_path())

    arch = {"tiny": ModelArch.TINY_STREAMING, "small": ModelArch.SMALL_STREAMING,
            "medium": ModelArch.MEDIUM_STREAMING}[args.model]
    echoline = EchoLineApp(LoopbackSource(), lambda: MoonshineEngine.load(arch), store,
                           show_latency=args.show_latency, settings_reset=was_reset)
    echoline.start()
    try:
        return qt_app.exec()
    finally:
        echoline.shutdown()


if __name__ == "__main__":
    sys.exit(main())
