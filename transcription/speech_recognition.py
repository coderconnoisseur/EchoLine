import os
import json
import numpy as np
from vosk import KaldiRecognizer, Model

class SpeechRecognizer:
    """Handles speech recognition using Vosk"""
    
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.model = None
        self.recognizer = None
        self.initialize_model()
    
    def initialize_model(self):
        """Initialize the Vosk model"""
        try:
            # Use a relative path or environment variable instead of hardcoded user path
            model_path = os.path.join(os.path.expanduser("~"), ".cache", "vosk", "vosk-model-small-en-us-0.15")
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            return True
        except Exception as e:
            print(f"Error loading Vosk model: {e}")
            self.model = None
            self.recognizer = None
            return False
    
    def process_audio_data(self, audio_data):
        """Process audio data and return transcription results"""
        if not self.recognizer:
            return None, False
            
        # Convert to numpy array if needed
        if not isinstance(audio_data, np.ndarray):
            audio_data = np.frombuffer(audio_data, dtype=np.int16)
        
        if self.recognizer.AcceptWaveform(audio_data.tobytes()):
            result = json.loads(self.recognizer.Result())
            return result.get('text', ''), False  # Final text
        else:
            partial = json.loads(self.recognizer.PartialResult())
            return partial.get('partial', ''), True  # Partial text