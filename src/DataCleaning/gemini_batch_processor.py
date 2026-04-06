import os
import json
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=API_KEY)

INPUT_DIR = "data/llm_batches"
OUTPUT_DIR = "data/llm_extracted"
PROMPT_FILE = "prompts-for-feature-extraction.txt"

def process_batches():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        system_instruction = f.read()

    batch_files = sorted([f for f in os.listdir(INPUT_DIR) if f.startswith("batch_") and f.endswith(".json")])
    print(f"Found {len(batch_files)} batches to process.")

    for filename in batch_files:
        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename.replace('.json', '_extracted.json'))
        
        if os.path.exists(output_path):
            print(f"Skipping {filename} - already processed.")
            continue

        print(f"Sending {filename} to Gemini...")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            batch_data = f.read()
            
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=batch_data,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            
            extracted_json = json.loads(response.text)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(extracted_json, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Successfully saved: {output_path}")
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Response was: {response.text}")
            print("Retrying in 15 seconds...")
            time.sleep(15) # Wait out the rate limit and retry instead of breaking
            continue # Try this batch again
            
        time.sleep(7) # Increased sleep to prevent rate limiting

if __name__ == "__main__":
    process_batches()