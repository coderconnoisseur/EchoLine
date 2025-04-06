#this window will contain the overlay logic (tkinter)
import tkinter as tk

class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Live Captions")
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha',0.8) 
        self.root.geometry("800x100+100+100") 
        self.root.overrideredirect(True) 
        self.root.configure(background='black')
        self.subtitle_label = tk.Label(self.root, text="", font=("Arial", 24), bg="white", fg="black")
        self.subtitle_label.pack(expand=True, fill='both')
    def update_subtitle(self,text):
        self.subtitle_label.config(text=text)
    def run(self): 
        self.root.mainloop()


if __name__ == "__main__":
    overlay = Overlay()
    overlay.update_subtitle("This is a test subtitle.")
    overlay.run()
        