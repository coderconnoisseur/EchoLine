#this window will contain the overlay logic (tkinter)
import queue
import sys
import tkinter as tk
from tkinter import ttk
from Syscapture import Syscapture
from Transcription import Transcription,Model
class Overlay(Syscapture,Transcription):
    def __init__(self):
        
        try:
            self.model = Model("C:\\Users\\Acer\\.cache\\vosk\\vosk-model-small-en-us-0.15")
        except Exception as e:
            print("Error loading Vosk model. Please download the model from https://alphacephei.com/vosk/models")
            sys.exit(1)

        # Audio settings
        self.samplerate = 16000
        self.q = queue.Queue()
        
        
        self.root = tk.Tk()     #creates the tkinter window (init)
        # self.root.title("Live Captions")
        #Use the line 7 if window title is needed , 
        #but my project is an overlay so i'll just comment it out
        self.root.attributes('-topmost', True)  #overlay feat.
        self.root.attributes('-alpha',0.8)      #opacity/Transparency
        self.root.overrideredirect(True)        #NO BORDERS 
        self.root.configure(background='black') #self explanatory 
        
        # Remove the subtitle_label and keep only the main label
        self.canvas = tk.Canvas(self.root, background='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.frame = tk.Frame(self.canvas, bg='black')
        self.canvas.create_window((0,0), window=self.frame, anchor='nw')
        
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.frame.bind("<Configure>", self.on_frame_configure)
        
        self.label = ttk.Label(
            self.frame,
            text="",
            font=("Arial", 18),  # Decreased font size
            background='black',
            foreground='white',
            wraplength=380,
            justify='left'
        )
        self.label.pack(pady=10, padx=10, anchor='w')
        self.root.geometry(f"400x100+{self.root.winfo_screenwidth()//2 - 200}+{self.root.winfo_screenheight() - 150}")
        #the subtitle overlay will be at bottom and will be of size 400*100(i might add resize later)

        # Bind mouse events for moving the window
        self.root.bind("<ButtonPress-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        self.root.bind("<ButtonRelease-1>", self.stop_move)

        # Initialize variables to track mouse position
        self._offset_x = 0
        self._offset_y = 0

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        #updates the scroll region 
    def update_subtitle(self,text):
        self.subtitle_label.config(text=text)
        #core subtitle updation 
    def run(self): 
        self.root.mainloop()
        #keeps tkinter running 

    def start_move(self, event):
        """Record the initial position of the mouse."""
        self._offset_x = event.x
        self._offset_y = event.y

    def do_move(self, event):
        """Move the window to follow the mouse."""
        x = self.root.winfo_pointerx() - self._offset_x
        y = self.root.winfo_pointery() - self._offset_y
        self.root.geometry(f"+{x}+{y}")

    def stop_move(self, event):
        """Stop moving the window."""
        self._offset_x = 0
        self._offset_y = 0

    def update_caption(self, text, is_partial=False):
        """Update the caption text in the overlay"""
        if is_partial:
            text = f"{text}..."
        
        try:
            if not self.root.winfo_exists():
                return
            
            self._current_text = text
            
            def update_label():
                if hasattr(self, '_current_text'):
                    self.label.config(text=self._current_text)
                self.canvas.yview_moveto(1.0)
            
            self.root.after(0, update_label)
        except Exception as e:
            print(f"Error updating caption: {e}")

    # Remove the update_subtitle method as it's no longer needed




        