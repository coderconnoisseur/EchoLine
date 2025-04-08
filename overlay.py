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
        self.subtitle_label = tk.Label(self.root, text="", font=("Arial", 24), bg="white", fg="black") #white bg black font
        self.subtitle_label.pack(expand=True, fill='both')      #will adjust to fit space 
        #canvas setup
        self.canvas=tk.Canvas(self.root,background='black',highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH,expand=True)
        self.frame=tk.Frame(self.canvas,bg='black')
        self.canvas.create_window((0,0),window=self.frame,anchor='nw')
        
        #scroll bar setup  
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.frame.bind("<Configure>", self.on_frame_configure)
        self.label = ttk.Label(
            self.frame,
            text="",
            font=("Arial", 16),
            background='black',
            foreground='white',
            wraplength=380,
            justify='left'
        )
        self.label.pack(pady=10, padx=10, anchor='w')
        self.root.geometry(f"400x100+{self.root.winfo_screenwidth()//2 - 200}+{self.root.winfo_screenheight() - 150}")
        #the subtitle overlay will be at bottom and will be of size 400*100(i might add resize later)
    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        #updates the scroll region 
    def update_subtitle(self,text):
        self.subtitle_label.config(text=text)
        #core subtitle updation 
    def run(self): 
        self.root.mainloop()
        #keeps tkinter running 


if __name__ == "__main__":
    overlay = Overlay()
    overlay.start_capture()

        