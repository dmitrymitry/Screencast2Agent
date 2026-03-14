import subprocess
import signal
import os
import time
import re

class Recorder:
    def __init__(self, output_file="recording.mp4", logger=None, video_device="3", audio_device="1"):
        self.output_file = output_file
        self.process = None
        self.logger = logger or print
        self.video_device = video_device
        self.audio_device = audio_device

    @staticmethod
    def get_avfoundation_devices():
        """Runs ffmpeg to get a list of AVFoundation video and audio devices."""
        video_devices = {}
        audio_devices = {}
        try:
            # ffmpeg writes the device list to stderr and exits with an error code (since input is "")
            result = subprocess.run(['ffmpeg', '-f', 'avfoundation', '-list_devices', 'true', '-i', '""'], 
                                   stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            output = result.stderr
            
            parsing_video = False
            parsing_audio = False
            
            for line in output.split('\n'):
                if "AVFoundation video devices:" in line:
                    parsing_video = True
                    parsing_audio = False
                    continue
                elif "AVFoundation audio devices:" in line:
                    parsing_video = False
                    parsing_audio = True
                    continue
                    
                # Match line format like: [AVFoundation...] [3] Capture screen 0
                match = re.search(r'\[(\d+)\]\s+(.+)$', line)
                if match:
                    idx = match.group(1)
                    name = match.group(2).strip()
                    # Skip if the name is empty or error lines
                    if name and not name.startswith('Error'):
                        if parsing_video:
                            video_devices[name] = idx
                        elif parsing_audio:
                            audio_devices[name] = idx
        except Exception as e:
            print(f"Error fetching devices: {e}")
            
        return video_devices, audio_devices

    def start(self):
        if self.process is not None:
            self.logger("Recording is already in progress.")
            return

        self.logger(f"Starting recording to {self.output_file} using devices {self.video_device}:{self.audio_device}...")
        
        command = [
            'ffmpeg',
            '-y', 
            '-f', 'avfoundation',
            '-framerate', '30',
            '-i', f'{self.video_device}:{self.audio_device}', 
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
