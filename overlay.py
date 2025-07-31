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
        
        # Create the main window
        self.root = tk.Tk()
        self.root.attributes('-topmost', True)  # Always on top
        self.root.attributes('-alpha', 0.85)    # Slightly more opaque for better readability
        self.root.overrideredirect(True)        # No borders
        self.root.configure(background='#1a1a1a')  # Dark gray instead of pure black
        
        # Create main container with rounded corners effect
        self.main_container = tk.Frame(
            self.root, 
            bg='#1a1a1a', 
            bd=0, 
            highlightthickness=2,
            highlightbackground='#333333',
            highlightcolor='#555555'
        )
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create header frame for controls (initially hidden)
        self.header_frame = tk.Frame(
            self.main_container,
            bg='#2d2d2d',
            height=30,
            bd=0
        )
        self.header_frame.pack(fill=tk.X, padx=2, pady=(2, 0))
        self.header_frame.pack_propagate(False)
        
        # Close button (initially hidden)
        self.close_btn = tk.Button(
            self.header_frame,
            text="✕",
            font=("Arial", 12, "bold"),
            bg='#ff4444',
            fg='white',
            activebackground='#ff6666',
            activeforeground='white',
            bd=0,
            relief='flat',
            width=3,
            height=1,
            cursor='hand2',
            command=self.close_app
        )
        self.close_btn.pack(side=tk.RIGHT, padx=5, pady=3)
        
        # Add hover effects for close button
        self.close_btn.bind("<Enter>", lambda e: self.close_btn.configure(bg='#ff6666'))
        self.close_btn.bind("<Leave>", lambda e: self.close_btn.configure(bg='#ff4444'))
        
        # App title (initially hidden)
        self.title_label = tk.Label(
            self.header_frame,
            text="EchoLine - Live Captions",
            font=("Arial", 10, "bold"),
            bg='#2d2d2d',
            fg='#cccccc'
        )
        self.title_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Hide header initially
        self.header_frame.pack_forget()
        
        # Create content area
        self.content_frame = tk.Frame(
            self.main_container,
            bg='#1a1a1a',
            bd=0
        )
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Create canvas for scrollable content
        self.canvas = tk.Canvas(
            self.content_frame, 
            background='#1a1a1a', 
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Create frame for text content
        self.frame = tk.Frame(self.canvas, bg='#1a1a1a')
        self.canvas.create_window((0, 0), window=self.frame, anchor='nw')
        
        # Create scrollbar (styled)
        style = ttk.Style()
        style.configure('Custom.Vertical.TScrollbar',
                       background='#333333',
                       troughcolor='#1a1a1a',
                       borderwidth=0,
                       arrowcolor='#666666',
                       darkcolor='#333333',
                       lightcolor='#555555')
        
        self.scrollbar = ttk.Scrollbar(
            self.content_frame, 
            orient="vertical", 
            command=self.canvas.yview,
            style='Custom.Vertical.TScrollbar'
        )
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.frame.bind("<Configure>", self.on_frame_configure)
        
        # Create the main text label with improved styling
        self.label = tk.Label(
            self.frame,
            text="Ready for live captions...",
            font=("Segoe UI", 16, "normal"),  # More modern font
            background='#1a1a1a',
            foreground='#ffffff',
            wraplength=380,
            justify='left',
            pady=10,
            padx=15
        )
        self.label.pack(pady=15, padx=15, anchor='w')
        
        # Set window position and size
        self.root.geometry(f"420x120+{self.root.winfo_screenwidth()//2 - 210}+{self.root.winfo_screenheight() - 170}")
        
        # Bind mouse events for moving and hover effects
        self.bind_events()
        
        # Initialize variables
        self._offset_x = 0
        self._offset_y = 0
        self.is_hovered = False
        self.transition_alpha = 0.85
        self.transition_job = None
        self.pulse_job = None
        
        # Start subtle pulse animation when not hovered
        self.start_pulse_animation()
        
    def bind_events(self):
        """Bind all mouse events for interaction"""
        # Movement events
        self.root.bind("<ButtonPress-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        self.root.bind("<ButtonRelease-1>", self.stop_move)
        
        # Hover events - bind to root window for better detection
        self.root.bind("<Enter>", self.on_hover_enter)
        self.root.bind("<Leave>", self.on_hover_leave)
        
        # Also bind to main container and content for better coverage
        self.main_container.bind("<Enter>", self.on_hover_enter)
        self.main_container.bind("<Leave>", self.on_hover_leave)
        
    def animate_alpha(self, target_alpha, current_step=0, total_steps=10):
        """Smoothly animate the alpha transparency"""
        if self.transition_job:
            self.root.after_cancel(self.transition_job)
        
        if current_step <= total_steps:
            # Calculate current alpha using easing
            progress = current_step / total_steps
            # Ease-out function for smoother animation
            eased_progress = 1 - (1 - progress) ** 2
            current_alpha = self.transition_alpha + (target_alpha - self.transition_alpha) * eased_progress
            
            self.root.attributes('-alpha', current_alpha)
            
            if current_step < total_steps:
                self.transition_job = self.root.after(20, lambda: self.animate_alpha(target_alpha, current_step + 1, total_steps))
            else:
                self.transition_alpha = target_alpha
    
    def on_hover_enter(self, event=None):
        """Handle mouse enter (hover start) with smooth animation"""
        if not self.is_hovered:
            self.is_hovered = True
            # Stop pulse animation
            if self.pulse_job:
                self.root.after_cancel(self.pulse_job)
                self.pulse_job = None
            # Show header with close button
            self.header_frame.pack(fill=tk.X, padx=2, pady=(2, 0), before=self.content_frame)
            # Smooth alpha transition
            self.animate_alpha(0.98)
            # Add glow effect
            self.main_container.configure(highlightbackground='#0078d4', highlightthickness=2)
    
    def on_hover_leave(self, event=None):
        """Handle mouse leave (hover end) with smooth animation"""
        # Delay the hide action to prevent flickering
        self.root.after(100, self._delayed_hover_leave)
    
    def _delayed_hover_leave(self):
        """Delayed hover leave to check if mouse is really outside"""
        try:
            # Get current mouse position relative to window
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            wx = self.root.winfo_rootx()
            wy = self.root.winfo_rooty()
            ww = self.root.winfo_width()
            wh = self.root.winfo_height()
            
            # Add some margin to prevent premature hiding
            margin = 10
            
            if not (wx - margin <= x <= wx + ww + margin and 
                    wy - margin <= y <= wy + wh + margin):
                self.is_hovered = False
                # Hide header with smooth animation
                self.animate_alpha(0.85)
                # Remove glow effect
                self.main_container.configure(highlightbackground='#333333', highlightthickness=2)
                # Hide header after animation
                self.root.after(200, lambda: self.header_frame.pack_forget() if not self.is_hovered else None)
                # Restart pulse animation
                self.root.after(300, self.start_pulse_animation)
                
        except tk.TclError:
            # Window might be destroyed, ignore
            pass
    
    def start_pulse_animation(self):
        """Start a subtle pulse animation when not hovered"""
        if not self.is_hovered:
            self.pulse_animation(0)
    
    def pulse_animation(self, step):
        """Subtle pulse animation for the border"""
        if not self.is_hovered:
            # Create a subtle pulse effect with the border color
            import math
            intensity = 0.3 + 0.2 * math.sin(step * 0.1)  # Gentle sine wave
            
            # Convert intensity to hex color
            base_color = 0x33
            pulse_color = int(base_color + (0x66 - base_color) * intensity)
            color_hex = f"#{pulse_color:02x}{pulse_color:02x}{pulse_color:02x}"
            
            try:
                self.main_container.configure(highlightbackground=color_hex)
                self.pulse_job = self.root.after(100, lambda: self.pulse_animation(step + 1))
            except tk.TclError:
                # Window destroyed
                pass
        else:
            # Stop pulse when hovered
            if self.pulse_job:
                self.root.after_cancel(self.pulse_job)
                self.pulse_job = None
    
    def close_app(self):
        """Close the application gracefully"""
        try:
            self.stop_capture()
        except:
            pass
        self.root.destroy()
        sys.exit(0)
    def on_frame_configure(self, event):
        """Update the scroll region when frame size changes"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def run(self): 
        """Start the tkinter main loop"""
        self.root.mainloop()

    def start_move(self, event):
        """Record the initial position of the mouse for window dragging"""
        self._offset_x = event.x
        self._offset_y = event.y

    def do_move(self, event):
        """Move the window to follow the mouse during drag"""
        x = self.root.winfo_pointerx() - self._offset_x
        y = self.root.winfo_pointery() - self._offset_y
        self.root.geometry(f"+{x}+{y}")

    def stop_move(self, event):
        """Stop moving the window and reset offset"""
        self._offset_x = 0
        self._offset_y = 0

    def update_caption(self, text, is_partial=False):
        """Update the caption text in the overlay with enhanced styling"""
        if is_partial:
            text = f"{text}..."
        
        try:
            if not self.root.winfo_exists():
                return
            
            self._current_text = text
            
            def update_label():
                if hasattr(self, '_current_text'):
                    # Update text with improved formatting
                    if self._current_text.strip():
                        self.label.config(
                            text=self._current_text,
                            foreground='#ffffff' if not is_partial else '#cccccc'
                        )
                    else:
                        self.label.config(
                            text="Listening for audio...",
                            foreground='#888888'
                        )
                # Auto-scroll to bottom
                self.canvas.yview_moveto(1.0)
            
            self.root.after(0, update_label)
        except Exception as e:
            print(f"Error updating caption: {e}")

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