import os
import json
import pymysql
import decimal
import datetime

EXTRACTED_DIR = "data/llm_extracted"
OUTPUT_FILE = "data/xgboost_training_data.json"

def get_llm_features():
    llm_features_dict = {}
    print(f"Loading extracted JSON files from {EXTRACTED_DIR}...")
    
    # get all extracted json files
    extracted_files = [f for f in os.listdir(EXTRACTED_DIR) if f.endswith("_extracted.json")]
    
    for filename in extracted_files:
        filepath = os.path.join(EXTRACTED_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
                
                # map features by property_id
                for prop in batch_data:
                    prop_id = str(prop.get("property_id"))
                    if prop_id:
                        llm_features_dict[prop_id] = prop
        except Exception as e:
            print(f"⚠️ Warning: Could not read {filename}: {e}")
            
    print(f"Successfully loaded {len(llm_features_dict)} unique properties from LLM extraction.")
    return llm_features_dict

def prepare_for_xgboost():
    llm_features = get_llm_features()
    
    print("\nConnecting to the database...")
    try:
        connection = pymysql.connect(
            host='localhost',
            port=3307,
            user='root',
            password='DataScience_root_2025',
            database='DataScience_data',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return

    final_dataset = []
    
    try:
        with connection.cursor() as cursor:
            # fetch base records from db
            print("Fetching base records from properties_processed table...")
            cursor.execute("SELECT * FROM properties_processed")
            db_records = cursor.fetchall()
            
            print(f"Found {len(db_records)} records in the database. Merging with LLM features...")
            
            for record in db_records:
                prop_id = str(record.get('external_id'))
                
                # get llm features for this property
                extracted_data = llm_features.get(prop_id, {})
                
                # combine db record with llm features
                merged_record = {**record, **extracted_data}
                
                # convert decimal and datetime for json serialization
                for key, value in merged_record.items():
                    if isinstance(value, decimal.Decimal):
                        merged_record[key] = float(value)
                    elif isinstance(value, (datetime.date, datetime.datetime)):
                        merged_record[key] = value.isoformat()
                        
                final_dataset.append(merged_record)
                
        # export to json
        print(f"\nSaving final merged dataset to {OUTPUT_FILE}...")
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_dataset, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Success! {len(final_dataset)} completely merged records are ready for XGBoost training at: {OUTPUT_FILE}")

    except Exception as e:
        print(f"❌ Error during merge: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    prepare_for_xgboost()