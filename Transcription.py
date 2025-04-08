from vosk import KaldiRecognizer,Model
import json 
class Transcription:
    def process_audio(self):
            """Process audio stream and update captions"""
            rec = KaldiRecognizer(self.model, self.samplerate)

            while True:
                data = self.q.get()
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if result.get("text", ""):
                        self.update_caption(result["text"])  # Update with complete results
                else:
                    # Handle partial results
                    partial = json.loads(rec.PartialResult())
                    if partial.get("partial", ""):
                        self.update_caption(partial["partial"], is_partial=True)
    def update_caption(self, text, is_partial=False):
            """Update the caption text in the overlay"""
            if is_partial:
                text = f"{text}..."
        
            try:
                self.label.config(text=text)
                self.root.update()
            
                # Auto-scroll to the bottom
                self.canvas.yview_moveto(1.0)
            except:
                pass
