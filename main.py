import argparse
from recorder import Recorder
from llm import generate_agent_code
import sys
import os
import signal

def main():
    parser = argparse.ArgumentParser(description="Screencast to Playwright Agent Generator")
    parser.add_argument("action", choices=["record", "generate"], help="Action to perform: 'record' screen or 'generate' agent.")
    parser.add_argument("--output", default="recording.mp4", help="Output file name for the video (default: recording.mp4)")
    args = parser.parse_args()

    if args.action == "record":
        recorder = Recorder(output_file=args.output)
        recorder.start()
        
        try:
            print("Press Enter or Ctrl+C to stop recording...")
            input()
        except KeyboardInterrupt:
            pass # Caught Ctrl+C
            
        recorder.stop()
        print(f"Saved recording. Run 'python main.py generate --output {args.output}' to build your agent.")

    elif args.action == "generate":
        if not os.path.exists(args.output):
            print(f"Error: Screen recording file '{args.output}' not found. Please record first.")
            sys.exit(1)
            
        generate_agent_code(args.output)

if __name__ == "__main__":
    main()
