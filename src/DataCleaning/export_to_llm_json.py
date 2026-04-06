import json
import pymysql
import os

BATCH_SIZE = 50
OUTPUT_DIR = "data/llm_batches"

def export_database_to_json_batches():
    # Create the output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Connect to your Database
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
        print(f"Error connecting to the database: {e}")
        return

    print("Successfully connected to the database.")

    try:
        with connection.cursor() as cursor:
            # Query the target columns
            query = """
                SELECT 
                    external_id as property_id,
                    description, 
                    parking, 
                    furnishing, 
                    air_conditioning, 
                    energy_efficiency
                FROM properties_processed
            """
            cursor.execute(query)
            records = cursor.fetchall()
            
            total_records = len(records)
            print(f"Found {total_records} records to process.")

            # Process in batches
            batch = []
            batch_num = 1
            
            for i, record in enumerate(records):
                # Create the clean JSON object for the prompt mapping your desired fields
                input_json = {
                    "property_id": record.get('property_id'),
                    "Description": record.get('description', ''),
                    "Parking": record.get('parking', ''),
                    "Furnished": record.get('furnishing', ''),
                    "AirConditioning": record.get('air_conditioning', ''),
                    "Energy Efficient": record.get('energy_efficiency', '')
                }
                
                batch.append(input_json)
                
                # If we've hit the BATCH_SIZE or the end of the records, save the file
                if len(batch) >= BATCH_SIZE or i == total_records - 1:
                    output_file = os.path.join(OUTPUT_DIR, f"batch_{batch_num:03d}.json")
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(batch, f, indent=2, ensure_ascii=False)
                    
                    print(f"Saved {output_file} ({len(batch)} records)")
                    
                    # Reset the batch and increment the batch number
                    batch = []
                    batch_num += 1

    except Exception as e:
         print(f"Error fetching data: {e}")
    finally:
        connection.close()
        print("Done exporting batches.")

if __name__ == "__main__":
    export_database_to_json_batches()
