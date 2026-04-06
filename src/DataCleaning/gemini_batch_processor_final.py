import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=API_KEY)

# Use new directories for the 'properties_final' table
INPUT_DIR = "data/llm_batches_final"
OUTPUT_DIR = "data/llm_extracted_final"
PROMPT_FILE = "prompts-for-feature-extraction.txt"

def process_single_batch(filename, system_instruction):
    input_path = os.path.join(INPUT_DIR, filename)
    output_path = os.path.join(OUTPUT_DIR, filename.replace('.json', '_extracted.json'))
    
    if os.path.exists(output_path):
        return f"⏩ Skipped {filename} (Already processed)"

    with open(input_path, 'r', encoding='utf-8') as f:
        batch_data = f.read()

    max_retries = 3
    for attempt in range(max_retries):
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
            
            raw_text = response.text.replace('```json', '').replace('```', '').strip()
            extracted_json = json.loads(raw_text)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(extracted_json, f, indent=2, ensure_ascii=False)
                
            return f"✅ Successfully saved: {output_path}"
            
        except Exception as e:
            if attempt == max_retries - 1:
                return f"❌ Error processing {filename} entirely: {e}"
            time.sleep(2)
            
    return f"❌ Failed {filename}"

def process_batches_parallel():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        system_instruction = f.read()

    batch_files = sorted([f for f in os.listdir(INPUT_DIR) if f.startswith("batch_") and f.endswith(".json")])
    print(f"Found {len(batch_files)} batches to process for properties_final.")
    print("🚀 Firing up parallel processing...")

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_single_batch, filename, system_instruction): filename for filename in batch_files}
        for future in as_completed(futures):
            try:
                result = future.result()
                print(result)
            except Exception as exc:
                print(f"Batch generated an exception: {exc}")

if __name__ == "__main__":
    process_batches_parallel()