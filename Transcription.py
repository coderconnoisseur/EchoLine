from vosk import KaldiRecognizer,Model
import json 
import queue

class Transcription:
    def process_audio(self):
            """Process audio stream and update captions"""
            rec = KaldiRecognizer(self.model, self.samplerate)
            last_text = ""  # Keep track of the last text to prevent duplicate updates

            while True:
                try:
                    data = self.q.get(timeout=1.0)  # Add timeout to prevent hanging
                    if len(data) == 0:
                        break
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        if result.get("text", "") and result["text"] != last_text:
                            last_text = result["text"]
                            self.update_caption(result["text"])
                    else:
                        # Handle partial results
                        partial = json.loads(rec.PartialResult())
                        if partial.get("partial", "") and partial["partial"] != last_text:
                            last_text = partial["partial"]
                            self.update_caption(partial["partial"], is_partial=True)
                except queue.Empty:
                    continue  # No data available, try again
                except Exception as e:
                    print(f"Error processing audio: {e}")
                    continue
    # Remove this method as we're using the one from Overlay class
    # def update_caption(self, text, is_partial=False):
    #     """Update the caption text in the overlay"""
    #     if is_partial:
    #         text = f"{text}..."
    # 
    #     try:
    #         self.label.config(text=text)
    #         self.root.update()
    # 
    #         # Auto-scroll to the bottom
    #         self.canvas.yview_moveto(1.0)
    #     except:
    #         pass
