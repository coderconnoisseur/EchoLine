import queue
import threading
import numpy as np
import sounddevice as sd

class AudioCapture:
    """Handles audio capture from system audio"""
    
    def __init__(self, sample_rate=16000, callback=None):
        self.sample_rate = sample_rate
        self.callback = callback
        self.is_capturing = False
        self.q = queue.Queue()
        self.capture_thread = None
    
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
    
    def process_audio_queue(self):
        """Process audio data from the queue"""
        while self.is_capturing:
            try:
                data = self.q.get(timeout=1.0)
                if data == b'':  # Stop signal
                    break
                
                if self.callback:
                    self.callback(data)
                    
            except queue.Empty:
                continue
            except Exception as e:
                if self.is_capturing:  # Only log if we're still supposed to be capturing
                    print(f"Error processing audio: {e}")
                continue
    
    def start(self):
        """Start audio capture from Stereo Mix"""
        if self.is_capturing:
            return
            
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
                return False

            print(f"Using Stereo Mix device: {devices[stereo_mix_device]['name']}")

            # Set capturing flag
            self.is_capturing = True
            
            # Start audio processing thread
            self.capture_thread = threading.Thread(target=self.process_audio_queue, daemon=True)
            self.capture_thread.start()

            # Start recording from Stereo Mix
            self.stream = sd.InputStream(
                device=stereo_mix_device,
                channels=1,
                samplerate=self.sample_rate,
                callback=self.audio_callback,
                dtype=np.int16
            )
            self.stream.start()
            
            print("Started capturing system audio...")
            return True

        except Exception as e:
            print(f"Error starting capture: {e}")
            print("Full error details:", str(e))
            self.is_capturing = False
            return False
    
    def stop(self):
        """Stop audio capture and cleanup"""
        try:
            print("Stopping audio capture...")
            self.is_capturing = False
            
            # Signal to stop processing
            self.q.put(b'')
            
            # Stop the stream if it exists
            if hasattr(self, 'stream') and self.stream.active:
                self.stream.stop()
                self.stream.close()
            
            return True
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
            return False