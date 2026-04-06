import os
import json
import pymysql

BATCH_SIZE = 50
OUTPUT_DIR = "data/llm_batches_final"

def export_database_to_json_batches():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
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
            # Query the new properties_final table
            query = """
                SELECT 
                    property_id,
                    description, 
                    parking, 
                    furnishing, 
                    air_conditioning, 
                    energy_efficiency
                FROM properties_final
            """
            cursor.execute(query)
            records = cursor.fetchall()
            
            total_records = len(records)
            print(f"Found {total_records} records in `properties_final` to process.")

            batch = []
            batch_num = 1
            
            for i, record in enumerate(records):
                input_json = {
                    "property_id": record.get('property_id'),
                    "Description": record.get('description', ''),
                    "Parking": record.get('parking', ''),
                    "Furnished": record.get('furnishing', ''),
                    "AirConditioning": record.get('air_conditioning', ''),
                    "Energy Efficient": record.get('energy_efficiency', '')
                }
                
                batch.append(input_json)
                
                if len(batch) >= BATCH_SIZE or i == total_records - 1:
                    output_file = os.path.join(OUTPUT_DIR, f"batch_{batch_num:03d}.json")
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(batch, f, indent=2, ensure_ascii=False)
                    
                    print(f"Saved {output_file} ({len(batch)} records)")
                    
                    batch = []
                    batch_num += 1

    except Exception as e:
         print(f"Error fetching data: {e}")
    finally:
        connection.close()
        print("Done exporting batches.")

if __name__ == "__main__":
    export_database_to_json_batches()