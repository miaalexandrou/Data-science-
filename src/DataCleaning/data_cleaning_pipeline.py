"""
Data Cleaning Pipeline
Fetches property data from the source database,
cleans it, and inserts it into the cleaning database.
"""

import sys
import os
from statistics import median
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
        requested_count = int(input("How many lines do you want to fetch from properties? (enter 1 for all) "))
    except ValueError:
        print("[FETCH] Invalid number entered.")
        return []

    if requested_count <= 0:
        print("[FETCH] Number of lines must be greater than 0.")
        return []

    fetch_all = requested_count == 1

    try:
        with DBConnectionCleaning() as db:
            with db._conn.cursor() as cursor:
                if fetch_all:
                    cursor.execute("SELECT * FROM properties")
                else:
                    cursor.execute("SELECT * FROM properties LIMIT %s", (requested_count,))
                results = cursor.fetchall()
        print(f"[FETCH] Retrieved {len(results)} records from properties table")
        return results
    except Exception as e:
        print(f"[FETCH] Error fetching data: {e}")
        return []



def clean_data(raw_data: List[Dict]) -> List[Dict]:
    """
    Clean and normalize property data.
    """
    # Remove duplicate rows
    cleaned_data = deduplicate(raw_data)
    
    # Handle null values
    cleaned_data = handle_nulls(cleaned_data)
    # Add data when possible 
    cleaned_data = apply_targeted_imputations(cleaned_data)
    
    return cleaned_data


def insert_cleaned_data(cleaned_data: List[Dict]) -> int:
    if not cleaned_data:
        return 0
    
    try:
        with DBConnectionCleaning() as db:
            with db._conn.cursor() as cursor:
                for record in cleaned_data:
                    # Build column names and placeholders dynamically
                    row = dict(record)
                    row.pop("id", None)

                    columns = ", ".join(f"`{column}`" for column in row.keys())
                    placeholders = ", ".join(["%s"] * len(row))
                    values = tuple(row.values())
                    
                    sql = f"INSERT INTO properties_processed ({columns}) VALUES ({placeholders})"
                    cursor.execute(sql, values)
            
            db._conn.commit()
            inserted_count = len(cleaned_data)
            print(f"[INSERT] Inserted {inserted_count} records into properties_processed table")
            return inserted_count
    except Exception as e:
        print(f"[INSERT] Error inserting data: {e}")
        return 0

def deduplicate(raw_data: List[Dict]) -> List[Dict]:

    """
    Remove identical rows from the dataset.
    
    Web crawlers often hit the same information twice.
    This function identifies and removes duplicate rows.
    
    Parameters
    ----------
    raw_data : List[Dict]
        Raw property records that may contain duplicates.
    
    Returns
    -------
    List[Dict]
        Deduplicated property records.
    """
    seen_urls = set()
    deduplicated = []
    duplicates_removed = 0
    
    for row in raw_data:
        url = row.get("url")

        # Fall back to external_id only if a URL is missing
        dedupe_key = url or row.get("external_id")

        if dedupe_key not in seen_urls:
            seen_urls.add(dedupe_key)
            deduplicated.append(row)
        else:
            duplicates_removed += 1
    
    print(f"[DEDUPLICATE] Removed {duplicates_removed} duplicate records")
    return deduplicated


def handle_nulls(data: List[Dict]) -> List[Dict]:
    """
    Handle null/None values in the dataset.
    
    Parameters
    ----------
    data : List[Dict]
        Property records that may contain null values.
    
    Returns
    -------
    List[Dict]
        Cleaned property records with nulls handled.
    """
    data = convert_pseudo_nulls_to_null(data)
    return data


def convert_pseudo_nulls_to_null(data: List[Dict]) -> List[Dict]:
    """
    Step 1: Convert pseudo-null tokens (e.g. '', 'N/A', '??') to SQL NULL.

    Note: In Python, SQL NULL is represented as None for DB drivers.
    """
    pseudo_null_tokens = {
        "",
        "-",
        "--",
        "n/a",
        "na",
        "n.a.",
        "not available",
        "not_applicable",
        "null",
        "none",
        "unknown",
        "?",
        "??",
    }
    cleaned_rows: List[Dict] = []

    for row in data:
        updated_row = dict(row)
        for key, value in updated_row.items():
            if isinstance(value, str):
                normalized = " ".join(value.strip().split())
                if normalized.lower() in pseudo_null_tokens:
                    updated_row[key] = None
                else:
                    updated_row[key] = normalized
        cleaned_rows.append(updated_row)

    return cleaned_rows


def apply_targeted_imputations(data: List[Dict]) -> List[Dict]:
    """ Apply safe imputations: price_per_sqm and optional grouped bathrooms."""

    updated_rows: List[Dict] = [dict(row) for row in data]

    # Recompute price_per_sqm only when enough information exists.
    for row in updated_rows:
        price = row.get("price")
        property_area = row.get("property_area_sqm")
        if row.get("price_per_sqm") is None and price is not None and property_area not in (None, 0):
            row["price_per_sqm"] = round(float(price) / float(property_area), 3)

    # Optional bathrooms imputation by (property_type, bedrooms) group medians.
    grouped_bathrooms: Dict = {}
    for row in updated_rows:
        bathrooms = row.get("bathrooms")
        if bathrooms is None:
            continue
        group_key = (row.get("property_type"), row.get("bedrooms"))
        grouped_bathrooms.setdefault(group_key, []).append(float(bathrooms))

    group_medians = {key: median(values) for key, values in grouped_bathrooms.items() if values}

    bathrooms_imputed = 0
    for row in updated_rows:
        if row.get("bathrooms") is not None:
            continue
        group_key = (row.get("property_type"), row.get("bedrooms"))
        if group_key in group_medians:
            row["bathrooms"] = int(round(group_medians[group_key]))
            bathrooms_imputed += 1

    print(f"[IMPUTE] Bathrooms imputed: {bathrooms_imputed}")
    return updated_rows



# ──────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
