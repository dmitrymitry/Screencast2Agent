import os
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()

def generate_agent_code(video_path: str, logger=None):
    logger = logger or print
    logger("Preparing to upload video to Gemini...")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger("Error: GEMINI_API_KEY environment variable is missing. Please add it in Settings.")
        return

    client = genai.Client(api_key=api_key)

    logger(f"Uploading '{video_path}'...")
    try:
        video_file = client.files.upload(file=video_path)
    except Exception as e:
        logger(f"Failed to upload video: {e}")
        return

    logger("Transcoding and analyzing video on Google servers. Please wait...")
    # Wait for the file to be processed
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        logger("\nFailed to process video on Google servers.")
        return

    logger("\nVideo is ready! Sending prompt to Gemini 2.5 Flash... This might take 10-30 seconds.")
    
    prompt = """
    Watch this screencast carefully and listen to the audio narration.
    The user is demonstrating a specific task in a web browser.
    
    1. First, provide a step-by-step generic algorithm in Markdown format explaining exactly what actions they take (clicks, typing, conditionals).
    2. Then, step by step, create a list of instructions as a prompt, this should outline the task to be passed to an agent. 
    3. Then, provide a complete, working Python Playwright script that automates this exact process.
    4. Provide the Python code inside standard markdown python block (```python ... ```).
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[video_file, prompt]
        )
        logger("Received response from Gemini.")
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        logger(f"Error during generation: {err_msg}")
        return
    finally:
        # Always try to delete the file from Google servers to save quota
        try:
            client.files.delete(name=video_file.name)
        except Exception:
            pass

    # Save outputs
    logger("Saving algorithm notes to algorithm.md...")
    with open("algorithm.md", "w") as f:
        f.write(response.text)
        
    logger("Extracting generated Python code...")
    lines = response.text.split('\n')
    in_code_block = False
    code_lines = []
    
    for line in lines:
        if line.strip() == "```python" or line.strip() == "```py":
            in_code_block = True
            continue
        elif line.strip() == "```" and in_code_block:
            in_code_block = False
            break
        
        if in_code_block:
            code_lines.append(line)
            
    if code_lines:
        with open("generated_agent.py", "w") as f:
            f.write("\n".join(code_lines))
        logger("Agent code successfully saved to generated_agent.py.")
    else:
        logger("Warning: Could not extract specific Playwright code block. Please check algorithm.md for the RAW output.")
