import time

from PySide6.QtGui import QGuiApplication

from echoline.settings.model import Settings
from echoline.settings.store import SettingsStore
from echoline.ui.onboarding import Setup

app = QGuiApplication.instance()


def wait_until(condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


class FakeStatus:
    notice = ""

    def set_notice(self, text, ms=6000):
        self.notice = text


class FakeApp:
    def __init__(self, tmp_path, **settings):
        self.settings_store = SettingsStore(Settings(**settings), tmp_path / "settings.json")
        self.status = FakeStatus()
        self.calls = []

    def __getattr__(self, name):          # start, set_visible, reload_engine, close_onboarding, quit
        return lambda *args: self.calls.append((name, *args))


class Downloads:
    def __init__(self, fail=False):
        self.fail, self.names = fail, []

    def __call__(self, name, on_progress):
        self.names.append(name)
        on_progress(0.5)
        if self.fail:
            raise OSError("offline")
        return "path"


def make(tmp_path, downloads=None, choice="tiny", downloaded=False, **settings):
    fake = FakeApp(tmp_path, **settings)
    setup = Setup(fake, download=downloads or Downloads(), check_hardware=lambda: choice,
                  is_downloaded=lambda name: downloaded)
    return fake, setup


def test_first_run_downloads_tiny_checks_and_starts(tmp_path):
    fake, setup = make(tmp_path)
    setup.begin()
    assert wait_until(lambda: setup.property("phase") == "ready")
    assert fake.settings_store.settings.model == "tiny"
    assert ("start",) in fake.calls
    assert setup.property("progress") == 0.5


def test_fast_pc_also_downloads_small(tmp_path):
    downloads = Downloads()
    fake, setup = make(tmp_path, downloads, choice="small")
    setup.begin()
    assert wait_until(lambda: setup.property("phase") == "ready")
    assert downloads.names == ["tiny", "small"]
    assert fake.settings_store.settings.model == "small"


def test_failed_download_shows_error_and_retry_restarts(tmp_path):
    downloads = Downloads(fail=True)
    fake, setup = make(tmp_path, downloads)
    setup.begin()
    assert wait_until(lambda: setup.property("phase") == "error")
    downloads.fail = False
    setup.retry()
    assert wait_until(lambda: setup.property("phase") == "ready")
    assert downloads.names == ["tiny", "tiny"]


def test_steps_advance_only_once_ready_and_show_captions(tmp_path):
    fake, setup = make(tmp_path)
    setup.begin()
    setup.nextStep()
    assert setup.property("step") == 0          # still downloading
    assert wait_until(lambda: setup.property("phase") == "ready")
    setup.nextStep()
    assert setup.property("step") == 1 and ("set_visible", True) in fake.calls
    setup.nextStep()
    assert setup.property("step") == 2


def test_finish_saves_onboarded_and_closes(tmp_path):
    fake, setup = make(tmp_path)
    setup.finish()
    assert fake.settings_store.settings.onboarded is True
    assert (tmp_path / "settings.json").exists()
    assert ("close_onboarding",) in fake.calls
    setup.windowClosed()                         # the close that finish() caused
    assert ("quit",) not in fake.calls


def test_closing_before_ready_quits(tmp_path):
    fake, setup = make(tmp_path, Downloads(fail=True))
    setup.begin()
    assert wait_until(lambda: setup.property("phase") == "error")
    setup.windowClosed()
    assert ("quit",) in fake.calls


def test_closing_after_ready_counts_as_finish(tmp_path):
    fake, setup = make(tmp_path)
    setup.begin()
    assert wait_until(lambda: setup.property("phase") == "ready")
    setup.windowClosed()
    assert fake.settings_store.settings.onboarded is True and ("quit",) not in fake.calls


def test_repair_downloads_the_named_model_then_closes_and_starts(tmp_path):
    downloads = Downloads()
    fake, setup = make(tmp_path, downloads, onboarded=True, model="small")
    setup.begin(repair_model="small")
    assert setup.property("repair") is True
    assert wait_until(lambda: ("start",) in fake.calls)
    assert downloads.names == ["small"]
    assert ("close_onboarding",) in fake.calls and ("set_visible", True) in fake.calls


def test_choose_downloaded_model_switches_at_once(tmp_path):
    fake, setup = make(tmp_path, downloaded=True, onboarded=True, model="tiny")
    setup.chooseModel("small")
    assert fake.settings_store.settings.model == "small"
    assert ("reload_engine",) in fake.calls


def test_choose_missing_model_downloads_first(tmp_path):
    downloads = Downloads()
    fake, setup = make(tmp_path, downloads, onboarded=True, model="tiny")
    setup.chooseModel("small")
    assert fake.settings_store.settings.model == "tiny"       # not until the files are here
    assert wait_until(lambda: ("reload_engine",) in fake.calls)
    assert fake.settings_store.settings.model == "small" and setup.property("phase") == "idle"


def test_failed_switch_keeps_the_old_model_and_says_why(tmp_path):
    fake, setup = make(tmp_path, Downloads(fail=True), onboarded=True, model="tiny")
    setup.chooseModel("small")
    assert wait_until(lambda: setup.property("phase") == "idle" and fake.status.notice)
    assert fake.settings_store.settings.model == "tiny"
    assert ("reload_engine",) not in fake.calls


def test_closing_after_ready_shows_the_captions(tmp_path):
    fake, setup = make(tmp_path)
    setup.begin()
    assert wait_until(lambda: setup.property("phase") == "ready")
    setup.windowClosed()                         # skipped Next on step 0
    assert ("set_visible", True) in fake.calls


def test_failed_hardware_check_falls_back_to_tiny(tmp_path):
    fake = FakeApp(tmp_path)

    def broken_check():
        raise RuntimeError("native error")

    setup = Setup(fake, download=Downloads(), check_hardware=broken_check, is_downloaded=lambda name: False)
    setup.begin()
    assert wait_until(lambda: setup.property("phase") in ("ready", "error"))
    assert setup.property("phase") == "ready" and fake.settings_store.settings.model == "tiny"
