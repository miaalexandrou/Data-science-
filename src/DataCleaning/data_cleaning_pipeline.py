"""
Data Cleaning Pipeline
Fetches property data from the source database,
cleans it, and inserts it into the cleaning database.
"""

import sys
import os
from typing import List, Dict

# Add src directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)
sys.path.insert(0, src_dir)

from databaseconection.db_connectionCleaning import DBConnection as DBConnectionCleaning


# ──────────────────────────────────────────────────────────────────────────
# MAIN ORCHESTRATION FUNCTION
# ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("[PIPELINE] Starting data cleaning pipeline...")
    
    # Fetch data from source
    print("[PIPELINE] Fetching data from database...")
    raw_data = fetch_data_from_source()
    
    # Clean data
    print(f"[PIPELINE] Cleaning {len(raw_data)} records...")
    cleaned_data = clean_data(raw_data)
    
    # Insert into database
    print("[PIPELINE] Inserting cleaned data into database...")
    inserted_count = insert_cleaned_data(cleaned_data)
    
    print(f"[PIPELINE] Pipeline complete. Inserted {inserted_count} records.")


# ──────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────

def fetch_data_from_source() -> List[Dict]:
    """
    Fetch all property records from the source database (properties table).
    
    Returns
    -------
    List[Dict]
        List of property records from the source database.
    """
    try:
        with DBConnectionCleaning() as db:
            with db._conn.cursor() as cursor:
                cursor.execute("SELECT * FROM properties")
                results = cursor.fetchall()
        print(f"[FETCH] Retrieved {len(results)} records from properties table")
        return results
    except Exception as e:
        print(f"[FETCH] Error fetching data: {e}")
        return []


def clean_data(raw_data: List[Dict]) -> List[Dict]:
    """
    Clean and normalize property data.
    
    Parameters
    ----------
    raw_data : List[Dict]
        Raw property records from the source database.
    
    Returns
    -------
    List[Dict]
        Cleaned property records ready for insertion.
    """
    pass


def insert_cleaned_data(cleaned_data: List[Dict]) -> int:
    """
    Insert cleaned data into the cleaning database.
    
    Parameters
    ----------
    cleaned_data : List[Dict]
        Cleaned property records.
    
    Returns
    -------
    int
        Number of records inserted.
    """
    pass


# ──────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
