import customtkinter as ctk
from tkinter import filedialog
import threading
import os
from dotenv import load_dotenv

from recorder import Recorder
from llm import generate_agent_code

# Load existing environment variables
load_dotenv()

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Screencast2Agent")
        self.geometry("600x600")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Global Exception Handlers
        import traceback
        self.report_callback_exception = self.handle_tk_exception

        # State
        self.is_recording = False
        self.current_video_path = "recording.mp4"
        
        # Fetch available devices for Mac
        self.video_devices_map, self.audio_devices_map = Recorder.get_avfoundation_devices()
        
        # Default device indices (fallback if fetching fails: '3' for screen 0, '1' for mic)
        self.selected_video_device = "3"
        self.selected_audio_device = "1"
        
        # Initialize recorder with defaults
        self.recorder = Recorder(output_file=self.current_video_path, logger=self.log, 
                                 video_device=self.selected_video_device, audio_device=self.selected_audio_device)

        # UI Elements
        self.create_widgets()
        
        # Load API key if present
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key:
            self.api_key_entry.insert(0, api_key)
            self.log("Loaded API Key from .env")

    def create_widgets(self):
        # Top Frame for Settings
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.settings_frame.grid_columnconfigure(1, weight=1)

        self.api_key_label = ctk.CTkLabel(self.settings_frame, text="Gemini API Key:")
        self.api_key_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.api_key_entry = ctk.CTkEntry(self.settings_frame, show="*", placeholder_text="AIzaSy...")
        self.api_key_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        self.save_key_btn = ctk.CTkButton(self.settings_frame, text="Save Key", width=80, command=self.save_api_key)
        self.save_key_btn.grid(row=0, column=2, padx=10, pady=10)

        # Video Device Dropdown
        self.video_label = ctk.CTkLabel(self.settings_frame, text="Screen:")
        self.video_label.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")
        
        video_options = list(self.video_devices_map.keys()) if self.video_devices_map else ["Default Screen"]
        self.video_dropdown = ctk.CTkOptionMenu(self.settings_frame, values=video_options, command=self.change_video_device)
        self.video_dropdown.grid(row=1, column=1, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        # Audio Device Dropdown
        self.audio_label = ctk.CTkLabel(self.settings_frame, text="Microphone:")
        self.audio_label.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")
        
        audio_options = list(self.audio_devices_map.keys()) if self.audio_devices_map else ["Default Mic"]
        self.audio_dropdown = ctk.CTkOptionMenu(self.settings_frame, values=audio_options, command=self.change_audio_device)
        self.audio_dropdown.grid(row=2, column=1, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        # Middle Frame for Actions
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=1, column=0, padx=20, pady=0, sticky="ew")
        self.action_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.record_btn = ctk.CTkButton(self.action_frame, text="Start Recording", height=50, 
                                       command=self.toggle_recording, fg_color="#C0392B", hover_color="#922B21")
        self.record_btn.grid(row=0, column=0, padx=10, pady=15, sticky="ew")

        self.load_btn = ctk.CTkButton(self.action_frame, text="Load Video", height=50, 
                                     command=self.load_video, fg_color="#2980B9", hover_color="#1F618D")
        self.load_btn.grid(row=0, column=1, padx=10, pady=15, sticky="ew")

        self.generate_btn = ctk.CTkButton(self.action_frame, text="Generate Agent", height=50, 
                                         command=self.start_generation, state="disabled")
        self.generate_btn.grid(row=0, column=2, padx=10, pady=15, sticky="ew")
        
        # Progress Bar for Generation
        self.progress_bar = ctk.CTkProgressBar(self.action_frame, mode="indeterminate")
        self.progress_bar.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 15), sticky="ew")
        self.progress_bar.set(0) # Hide visually when not spinning

        # Bottom Frame for Logs
        self.log_textbox = ctk.CTkTextbox(self, font=("Courier", 12))
        self.log_textbox.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        self.log_textbox.insert("0.0", "Welcome to Screencast2Agent!\nReady to record your browser flow.\n")
        # To make it read-only but copyable:
        def prevent_typing(event):
            # Allow Command-C (Mac) and Ctrl-C (Windows)
            if event.state & 0x0004 or event.state & 0x0008: 
                return None
            # Allow arrow keys for navigation
            if event.keysym in ("Up", "Down", "Left", "Right"):
                return None
            return "break"
            
        self.log_textbox.bind("<Key>", prevent_typing)
        
        # Add Right-Click Copy Menu
        import tkinter as tk
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_selection)
        
        # Bind right-click for Mac (<Button-2>) and Windows/Linux (<Button-3>)
        self.log_textbox.bind("<Button-2>", self.show_context_menu)
        self.log_textbox.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_selection(self):
        try:
            # Get selected text from the inner text widget
            selected_text = self.log_textbox.get("sel.first", "sel.last")
            # Clear clipboard and append
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self.update() # Keeps the clipboard populated
        except Exception:
            # Nothing selected
            pass

    def log(self, message):
        """Thread-safe logging to the text box"""
        self.after(0, self._log_internal, message)
        
    def _log_internal(self, message):
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")

    def handle_tk_exception(self, exc, val, tb):
        """Catch all uncaught Tkinter/UI exceptions and print them in the app log."""
        import traceback
        import sys
        err_msg = "".join(traceback.format_exception(exc, val, tb))
        self.log(f"💥 Application Error:\n{err_msg}")
        
        # Write to stderr so auto_healer catches it!
        sys.stderr.write(f"Traceback (most recent call last):\n{err_msg}\n")
        sys.stderr.flush()

    def save_api_key(self):
        key = self.api_key_entry.get().strip()
        if key:
            os.environ["GEMINI_API_KEY"] = key
            with open(".env", "w") as f:
                f.write(f"GEMINI_API_KEY=\"{key}\"\n")
            self.log("API Key saved to .env file and loaded into session.")
        else:
            self.log("Please enter a valid API Key.")

    def change_video_device(self, choice):
        if choice in self.video_devices_map:
            self.selected_video_device = self.video_devices_map[choice]
            self.log(f"Selected Screen: {choice} (Index {self.selected_video_device})")

    def change_audio_device(self, choice):
        if choice in self.audio_devices_map:
            self.selected_audio_device = self.audio_devices_map[choice]
            self.log(f"Selected Microphone: {choice} (Index {self.selected_audio_device})")

    def toggle_recording(self):
        if not self.is_recording:
            # Recreate recorder with selected devices
            self.recorder = Recorder(output_file=self.current_video_path, logger=self.log, 
                                     video_device=self.selected_video_device, 
                                     audio_device=self.selected_audio_device)
            # Start Recording
            self.recorder.start()
            self.is_recording = True
            
            # Update UI
            self.record_btn.configure(text="Stop Recording", fg_color="#27AE60", hover_color="#1E8449")
            self.generate_btn.configure(state="disabled")
            self.api_key_entry.configure(state="disabled")
            self.save_key_btn.configure(state="disabled")
        else:
            # Stop Recording
            self.recorder.stop()
            self.is_recording = False
            self.current_video_path = "recording.mp4"
            
            # Update UI
            self.record_btn.configure(text="Start Recording", fg_color="#C0392B", hover_color="#922B21")
            self.generate_btn.configure(state="normal")
            self.load_btn.configure(state="normal")
            
            self.api_key_entry.configure(state="normal")
            self.save_key_btn.configure(state="normal")
            
            # Check if file exists
            if os.path.exists(self.current_video_path):
                self.log(f"Recording successfully saved to {self.current_video_path}. Ready to generate agent.")
            else:
                self.log(f"Error: {self.current_video_path} not found. Ffmpeg might have failed.")

    def load_video(self):
        file_path = filedialog.askopenfilename(
            title="Select a Video File",
            filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv"), ("All files", "*.*")]
        )
        if file_path:
            self.current_video_path = file_path
            self.log(f"Loaded video: {self.current_video_path}")
            self.generate_btn.configure(state="normal")

    def start_generation(self):
        self.log("-" * 40)
        self.log(f"Starting Generation Process for {self.current_video_path}...")
        self.generate_btn.configure(state="disabled")
        self.record_btn.configure(state="disabled")
        self.load_btn.configure(state="disabled")
        
        # Start Progress Bar
        self.progress_bar.start()
        
        # Run in thread to not freeze UI
        threading.Thread(target=self._run_generation, daemon=True).start()
        
    def _run_generation(self):
        try:
            generate_agent_code(self.current_video_path, logger=self.log)
        except Exception as e:
            import traceback
            import sys
            err_msg = traceback.format_exc()
            self.log(f"💥 Critical error during generation:\n{err_msg}")
            sys.stderr.write(f"Traceback (most recent call last):\n{err_msg}\n")
            sys.stderr.flush()
        finally:
            self.after(0, self._reset_ui_after_generation)
            
    def _reset_ui_after_generation(self):
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.generate_btn.configure(state="normal")
        self.record_btn.configure(state="normal")
        self.load_btn.configure(state="normal")
        self.log("Generation process finished.")
        self.log("-" * 40)


if __name__ == "__main__":
    app = App()
    app.mainloop()
