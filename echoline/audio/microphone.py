from .wasapi import WasapiSource, windows_default_input_id


class MicrophoneSource(WasapiSource):
    """Captures the default microphone."""

    name = "Microphone"
    fills_silence = False         # microphones deliver audio continuously
    missing_status = "no-microphone"

    @staticmethod
    def default_device_id_function():
        return windows_default_input_id

    def _lookup_device(self, audio):
        index = audio.get_host_api_info_by_type(self._pyaudio.paWASAPI)["defaultInputDevice"]
        if index < 0:
            raise OSError("no default microphone")
        return audio.get_device_info_by_index(index)
