import threading
import traceback

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot

from .. import models

GETTING_READY, SOUND_TEST, THEME = range(3)
DOWNLOAD_FAILED = "Couldn't download — check your internet connection"


class Setup(QObject):
    """First-run setup and model switching: fetch a model with progress, then start captions."""

    changed = Signal()
    _phase_from_worker = Signal(str)
    _progress_from_worker = Signal(float)
    _succeeded = Signal(str)
    _failed = Signal()

    def __init__(self, app, download=None, check_hardware=None, is_downloaded=None):
        super().__init__()
        self._app = app
        self._download = download or models.download
        self._check_hardware = check_hardware or models.check_hardware
        self._is_downloaded = is_downloaded or models.is_downloaded
        self._step, self._phase, self._progress = GETTING_READY, "idle", 0.0
        self._mode = None            # "setup" | "repair" | "switch"
        self._finished = False
        self._repair_model = None
        self._phase_from_worker.connect(self._set_phase, Qt.QueuedConnection)
        self._progress_from_worker.connect(self._set_progress, Qt.QueuedConnection)
        self._succeeded.connect(self._on_ready, Qt.QueuedConnection)
        self._failed.connect(self._on_failed, Qt.QueuedConnection)

    step = Property(int, lambda self: self._step, notify=changed)
    phase = Property(str, lambda self: self._phase, notify=changed)
    progress = Property(float, lambda self: self._progress, notify=changed)
    repair = Property(bool, lambda self: self._mode == "repair", notify=changed)

    @Slot(str)
    def _set_phase(self, phase):
        self._phase = phase
        self.changed.emit()

    @Slot(float)
    def _set_progress(self, fraction):
        self._progress = fraction
        self.changed.emit()

    def _run(self, job):
        self._progress = 0.0
        self._set_phase("downloading")

        def work():
            try:
                self._succeeded.emit(job())
            except Exception:
                traceback.print_exc()
                self._failed.emit()

        threading.Thread(target=work, name="model-setup", daemon=True).start()

    def _fetch(self, name):
        self._download(name, self._progress_from_worker.emit)
        return name

    def _first_run(self):
        self._fetch("tiny")
        self._phase_from_worker.emit("checking")
        model = self._check_hardware()
        if model != "tiny":
            self._progress_from_worker.emit(0.0)
            self._phase_from_worker.emit("downloading")
            self._fetch(model)
        return model

    def begin(self, repair_model=None):
        """Start first-run setup, or (repair_model) re-fetch a missing model."""
        self._mode = "repair" if repair_model else "setup"
        self._repair_model = repair_model
        self._run(lambda: self._fetch(repair_model) if repair_model else self._first_run())

    @Slot(str)
    def _on_ready(self, model):
        self._app.settings_store.setValue("model", model)
        if self._mode == "switch":
            self._set_phase("idle")
            self._app.reload_engine()
            return
        self._set_phase("ready")
        if self._mode == "repair":
            self._finished = True
            self._app.close_onboarding()
            self._app.set_visible(True)
        self._app.start()

    @Slot()
    def _on_failed(self):
        if self._mode == "switch":
            self._set_phase("idle")
            self._app.status.set_notice(DOWNLOAD_FAILED)
        else:
            self._set_phase("error")

    @Slot()
    def retry(self):
        if self._phase == "error":
            self.begin(self._repair_model)

    @Slot()
    def nextStep(self):
        if self._step == GETTING_READY and self._phase != "ready":
            return
        if self._step == GETTING_READY:
            self._app.set_visible(True)          # the sound test uses the real overlay
        self._step = min(self._step + 1, THEME)
        self.changed.emit()

    @Slot()
    def finish(self):
        if self._finished:
            return
        self._finished = True
        self._app.settings_store.setValue("onboarded", True)
        self._app.settings_store.save_now()
        self._app.close_onboarding()

    @Slot()
    def windowClosed(self):
        if self._finished:
            return
        if self._mode == "setup" and self._phase == "ready":
            self.finish()
        else:
            self._app.quit()                     # nothing to caption with yet

    @Slot(str)
    def chooseModel(self, name):
        busy = self._phase in ("downloading", "checking")
        onboarding = self._mode in ("setup", "repair") and not self._finished
        if busy or onboarding or name == self._app.settings_store.settings.model:
            return
        if self._is_downloaded(name):
            self._app.settings_store.setValue("model", name)
            self._app.reload_engine()
            return
        self._mode = "switch"
        self._run(lambda: self._fetch(name))
