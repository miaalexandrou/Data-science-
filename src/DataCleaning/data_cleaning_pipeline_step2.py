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
    Fetch all property records from the source database (properties_semifinal table).
    
    Returns
    -------
    List[Dict]
        List of property records from the source database.
    """
    try:
        requested_count = int(input("\n How many lines do you want to fetch from properties_semifinal? (enter 1 for all) "))
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
                    cursor.execute("SELECT * FROM properties_semifinal")
                else:
                    cursor.execute("SELECT * FROM properties_semifinal LIMIT %s", (requested_count,))
                results = cursor.fetchall()
        print(f"[FETCH] Retrieved {len(results)} records from properties_semifinal table")
        return results
    except Exception as e:
        print(f"[FETCH] Error fetching data: {e}")
        return []



def clean_data(raw_data: List[Dict]) -> List[Dict]:
    """
    Clean and normalize property data.
    """
    cleaned_data = apply_targeted_imputations(raw_data)
    cleaned_data = remove_rows_with_null_city(cleaned_data)
    
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
                    
                    sql = f"INSERT INTO properties_final ({columns}) VALUES ({placeholders})"
                    cursor.execute(sql, values)
            
            db._conn.commit()
            inserted_count = len(cleaned_data)
            print(f"[INSERT] Inserted {inserted_count} records into properties_final table")
            return inserted_count
    except Exception as e:
        print(f"[INSERT] Error inserting data: {e}")
        return 0

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
    updated_rows: List[Dict] = [dict(row) for row in data]
    districts_imputed = 0

    for row in updated_rows:
        district = row.get("district")
        area = row.get("area")

        district_missing = district is None or (isinstance(district, str) and district.strip() == "")
        area_available = area is not None and (not isinstance(area, str) or area.strip() != "")

        if district_missing and area_available:
            row["district"] = area
            districts_imputed += 1

    print(f"[IMPUTE] Districts imputed from area: {districts_imputed}")
    return updated_rows


def remove_rows_with_null_city(data: List[Dict]) -> List[Dict]:
    rows_with_null_values = []
    remaining_rows = []
    city_removed = 0
    district_removed = 0
    property_area_sqm_removed = 0
    property_type_removed = 0

    for row in data:
        city = row.get("city")
        district = row.get("district")
        property_area_sqm = row.get("property_area_sqm")
        property_type = row.get("property_type")
        city_missing = city is None or (isinstance(city, str) and city.strip() == "")
        district_missing = district is None or (isinstance(district, str) and district.strip() == "")
        property_area_sqm_missing = property_area_sqm is None or (
            isinstance(property_area_sqm, str) and property_area_sqm.strip() == ""
        )
        property_type_missing = property_type is None or (
            isinstance(property_type, str) and property_type.strip() == ""
        )

        if city_missing or district_missing or property_area_sqm_missing or property_type_missing:
            rows_with_null_values.append(row)
            if city_missing:
                city_removed += 1
            if district_missing:
                district_removed += 1
            if property_area_sqm_missing:
                property_area_sqm_removed += 1
            if property_type_missing:
                property_type_removed += 1
        else:
            remaining_rows.append(row)

    if not rows_with_null_values:
        print("[CLEAN] No rows found with null city, district, property_area_sqm, or property_type values.")
        return data

    print(f"[CLEAN] Found {len(rows_with_null_values)} rows with null city, district, property_area_sqm, or property_type values.")
    print(f"[CLEAN] city missing: {city_removed}")
    print(f"[CLEAN] district missing: {district_removed}")
    print(f"[CLEAN] property_area_sqm missing: {property_area_sqm_removed}")
    print(f"[CLEAN] property_type missing: {property_type_removed}")
    print(f"[CLEAN] Deleted {len(rows_with_null_values)} rows with null city, district, property_area_sqm, or property_type values.")
    return remaining_rows



# ──────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
