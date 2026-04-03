"""
Data Cleaning Pipeline
Fetches property data from the source database,
cleans it, and inserts it into the cleaning database.
"""

import sys
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert(0, "..")

from databaseconection.db_connection import DBConnection
from databaseconection.db_connectionCleaning import DBConnection as DBConnectionCleaning


# ──────────────────────────────────────────────────────────────────────────
# MAIN ORCHESTRATION FUNCTION
# ──────────────────────────────────────────────────────────────────────────

def main() -> None:
    """
    Main orchestration function:
    1. Fetch raw data from source database
    2. Clean the data
    3. Insert cleaned data into cleaning database
    """
    print("[PIPELINE] Starting data cleaning pipeline...")
    
    # Fetch data from source
    print("[PIPELINE] Fetching data from source database...")
    raw_data = fetch_data_from_source()
    
    # Clean data
    print(f"[PIPELINE] Cleaning {len(raw_data)} records...")
    cleaned_data = clean_data(raw_data)
    
    # Insert into cleaning database
    print("[PIPELINE] Inserting cleaned data into cleaning database...")
    inserted_count = insert_cleaned_data(cleaned_data)
    
    print(f"[PIPELINE] Pipeline complete. Inserted {inserted_count} records.")


# ──────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────

def fetch_data_from_source() -> List[Dict]:
    """
    Fetch all property records from the source database.
    
    Returns
    -------
    List[Dict]
        List of property records from the source database.
    """
    pass


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
