import subprocess
import signal
import os
import time

class Recorder:
    def __init__(self, output_file="recording.mp4", logger=None):
        self.output_file = output_file
        self.process = None
        self.logger = logger or print

    def start(self):
        if self.process is not None:
            self.logger("Recording is already in progress.")
            return

        self.logger(f"Starting recording to {self.output_file}...")
        
        # Determine the first screen and the default audio input for Mac
        # You can use `ffmpeg -f avfoundation -list_devices true -i ""` to see devices.
        # Often "1:0" means Screen 1, Audio 0 (default mic)
        # Note: Mac might require accessibility permissions for terminal to capture screen
        command = [
            'ffmpeg',
            '-y', # Overwrite output files without asking
            '-f', 'avfoundation',
            '-framerate', '30',
            '-i', '3:1', # Screen 3 (Capture screen 0) and Audio 1 (Microphone MacBook Air)
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-pix_fmt', 'yuv420p',
            self.output_file
        ]
        
        # Start ffmpeg silently
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.logger("Recording started. In CLI: Press 'Ctrl+C' to stop. In GUI: Click 'Stop'.")

    def stop(self):
        if self.process is None:
            self.logger("No recording in progress.")
            return

        self.logger("Stopping recording...")
        # Send SIGINT to gracefully stop ffmpeg and save the file properly
        self.process.send_signal(signal.SIGINT)
        self.process.wait()
        self.process = None
        self.logger(f"Recording saved to {self.output_file}")
