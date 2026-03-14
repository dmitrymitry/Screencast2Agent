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
    The user is demonstrating a specific task.
    Even if it's not a browser, try your best to write a Playwright/PyAutoGUI script.
    
    You MUST output your response in EXACTLY three sections separated by these exact headers:
    
    === ALGORITHM ===
    [Provide a step-by-step generic algorithm in Markdown explaining exactly what actions they take]
    
    === PROMPT ===
    [Create a list of instructions as a prompt outlining the task to be passed to an agent]
    
    === CODE ===
    [Provide the complete, working Python script inside a standard python markdown block]
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

    # Parse outputs
    logger("Extracting sections into separate files...")
    text = response.text
    
    # Simple extraction using string splits
    algorithm_text = ""
    prompt_text = ""
    code_text = ""
    
    if "=== ALGORITHM ===" in text and "=== PROMPT ===" in text:
        parts = text.split("=== ALGORITHM ===")
        if len(parts) > 1:
            sub = parts[1].split("=== PROMPT ===")
            algorithm_text = sub[0].strip()
            if len(sub) > 1:
                sub2 = sub[1].split("=== CODE ===")
                prompt_text = sub2[0].strip()
                if len(sub2) > 1:
                    code_text = sub2[1].strip()
    else:
        # Fallback if AI didn't follow formatting strictly
        algorithm_text = text

    # Save Algorithm
    with open("algorithm.md", "w") as f:
        f.write(algorithm_text)
        
    # Save Prompt
    if prompt_text:
        with open("prompt.md", "w") as f:
            f.write(prompt_text)
        logger("Saved agent instructions to prompt.md.")

    # Save Code
    if code_text:
        # Clean markdown wrappers from code if present
        lines = code_text.split('\n')
        clean_lines = []
        in_code = False
        
        for line in lines:
            if line.strip().startswith("```python") or line.strip().startswith("```py"):
                in_code = True
                continue
            elif line.strip().startswith("```"):
                if in_code:
                    break
                else:
                    continue # Skip general markdown block starts
            
            # If not wrapped in markdown, just add it, or if inside python block
            if in_code or not code_text.startswith("```"):
                clean_lines.append(line)
                
        final_code = "\n".join(clean_lines).strip()
        if final_code:
            with open("generated_agent.py", "w") as f:
                f.write(final_code)
            logger("Agent code safely saved to generated_agent.py.")
        else:
            logger("Warning: No Python code was found in the output.")
    else:
        logger("Detailed parsing failed. Wrote raw output to algorithm.md.")
