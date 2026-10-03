from .wasapi import WasapiSource, windows_default_output_id

__all__ = ["LoopbackSource", "windows_default_output_id"]


class LoopbackSource(WasapiSource):
    """Captures whatever plays on the default output device via WASAPI loopback."""

    name = "System audio"
    fills_silence = True          # loopback sends nothing while the PC is silent
    missing_status = "no-device"

    @staticmethod
    def default_device_id_function():
        return windows_default_output_id

    def _lookup_device(self, audio):
        return audio.get_default_wasapi_loopback()
