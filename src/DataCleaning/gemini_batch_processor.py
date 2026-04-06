import os
import json
import time

from google import genai
from google.genai import types

API_KEY = "AIzaSyBgweJ1sYv42HhuvOVcglJnETo2R1oduCw"  
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
            if 'response' in locals():
                print(f"Response was: {response.text}")
            break
            
        time.sleep(5)

if __name__ == "__main__":
    process_batches()