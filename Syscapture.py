import sounddevice as sd
import numpy as np
import Transcription
import threading
class Syscapture:
    def audio_callback(self, indata, frames, time, status):
                """Callback function for audio stream"""
                if status:
                    print(status)
                self.q.put(bytes(indata))

    def start_capture(self):
        """Start audio capture from Stereo Mix"""
        try:
            # Find Stereo Mix device
            devices = sd.query_devices()
            stereo_mix_device = None
            
            print("Available audio devices:")
            for i, device in enumerate(devices):
                print(f"{i}: {device['name']}")
                if 'Stereo Mix' in device['name']:
                    stereo_mix_device = i
                    break
            
            if stereo_mix_device is None:
                print("Stereo Mix not found. Make sure it's enabled in your sound settings.")
                return

            print(f"Using Stereo Mix device: {devices[stereo_mix_device]['name']}")

            # Start audio processing thread
            threading.Thread(target=self.process_audio, daemon=True).start()

            # Start recording from Stereo Mix
            with sd.InputStream(device=stereo_mix_device,
                            channels=1,
                            samplerate=self.samplerate,
                            callback=self.audio_callback,
                            dtype=np.int16):
                print("Started capturing system audio...")
                self.root.mainloop()

        except Exception as e:
            print(f"Error starting capture: {e}")
            print("Full error details:", str(e))
