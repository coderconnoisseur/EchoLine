import sounddevice as sd
import numpy as np
import Transcription
import threading
import queue

class Syscapture:
    def audio_callback(self, indata, frames, time, status):
        """Callback function for audio stream"""
        if status:
            print(f"Audio status: {status}")
        try:
            # Put data in queue with timeout to prevent blocking
            self.q.put(bytes(indata), timeout=0.1)
        except queue.Full:
            # If queue is full, clear it and try again
            try:
                while not self.q.empty():
                    self.q.get_nowait()
                self.q.put(bytes(indata), timeout=0.1)
            except Exception as e:
                print(f"Error in audio callback: {e}")
        except Exception as e:
            print(f"Error in audio callback: {e}")

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

    def stop_capture(self):
        """Stop audio capture and cleanup"""
        try:
            # Signal to stop processing
            self.q.put(b'')
            
            # Clear the labels
            self.update_caption("")
            
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.quit()
        except Exception as e:
            print(f"Error during shutdown: {e}")

    # Remove this method as we're using the one from Overlay class
    # def update_caption(self, text, is_partial=False):
    #     """Update the caption text in the overlay"""
    #     if is_partial:
    #         text = f"{text}..."
    #     
    #     try:
    #         # Ensure we're updating from the main thread
    #         if not self.root.winfo_exists():
    #             return
    #         
    #         # Update both labels with the same text
    #         def update_labels():
    #             self.label.config(text=text)
    #             self.subtitle_label.config(text=text)
    #             self.canvas.yview_moveto(1.0)
    #         
    #         # Schedule the update on the main thread
    #         self.root.after(0, update_labels)
    #     except Exception as e:
    #         print(f"Error updating caption: {e}")
