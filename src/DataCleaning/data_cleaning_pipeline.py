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
        requested_count = int(input("\n How many lines do you want to fetch from properties? (enter 1 for all) "))
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

    enable_targeted_imputations = 1  # Set to 0 to disable this function's imputations.
    if enable_targeted_imputations == 0:
        print("[IMPUTE] Targeted imputations disabled")
        return [dict(row) for row in data]

    updated_rows: List[Dict] = [dict(row) for row in data]

    """Recompute missing price_per_sqm from price and area when possible."""
    recompute_price_per_sqm(updated_rows)

    """Fill missing price from property_area_sqm and price_per_sqm."""
    prices_imputed = impute_missing_prices(updated_rows)

    """Detect bathroom outliers with IQR and impute missing/outlier values by median."""
    bathrooms_imputed, bathrooms_outliers_fixed = fix_and_impute_bathrooms(updated_rows)

    print(f"[IMPUTE] Prices imputed: {prices_imputed}")
    print(f"[IMPUTE] Bathrooms imputed: {bathrooms_imputed}")
    print(f"[IMPUTE] Bathrooms outliers fixed: {bathrooms_outliers_fixed}")
    return updated_rows


def recompute_price_per_sqm(rows: List[Dict]) -> None:
    """Recompute missing price_per_sqm from price and area when possible."""
    for row in rows:
        price = row.get("price")
        property_area = row.get("property_area_sqm")
        if row.get("price_per_sqm") is None and price is not None and property_area not in (None, 0):
            row["price_per_sqm"] = round(float(price) / float(property_area), 3)


def impute_missing_prices(rows: List[Dict]) -> int:
    """Fill missing price from property_area_sqm and price_per_sqm."""
    prices_imputed = 0
    for row in rows:
        if row.get("price") is not None:
            continue
        property_area = row.get("property_area_sqm")
        price_per_sqm = row.get("price_per_sqm")
        if property_area is None or price_per_sqm is None:
            continue
        row["price"] = round(float(property_area) * float(price_per_sqm), 2)
        prices_imputed += 1
    return prices_imputed


def fix_and_impute_bathrooms(rows: List[Dict]) -> tuple[int, int]:
    """Detect bathroom outliers with IQR and impute missing/outlier values by median."""
    numeric_bathrooms = []
    for row in rows:
        bathrooms = row.get("bathrooms")
        if bathrooms is None:
            continue
        try:
            value = float(bathrooms)
        except (TypeError, ValueError):
            continue
        if value > 0:
            numeric_bathrooms.append(value)

    def percentile(sorted_values: List[float], p: float) -> float:
        if not sorted_values:
            return 0.0
        if len(sorted_values) == 1:
            return sorted_values[0]
        position = (len(sorted_values) - 1) * p
        lower_index = int(position)
        upper_index = min(lower_index + 1, len(sorted_values) - 1)
        fraction = position - lower_index
        return sorted_values[lower_index] + (sorted_values[upper_index] - sorted_values[lower_index]) * fraction

    lower_bound = 0.0
    upper_bound = float("inf")
    global_bathrooms_median = None
    if numeric_bathrooms:
        sorted_bathrooms = sorted(numeric_bathrooms)
        q1 = percentile(sorted_bathrooms, 0.25)
        q3 = percentile(sorted_bathrooms, 0.75)
        iqr = q3 - q1
        lower_bound = max(0.0, q1 - 1.5 * iqr)
        upper_bound = q3 + 1.5 * iqr
        global_bathrooms_median = median(sorted_bathrooms)

    outlier_indices = set()
    for idx, row in enumerate(rows):
        bathrooms = row.get("bathrooms")
        if bathrooms is None:
            continue
        try:
            value = float(bathrooms)
        except (TypeError, ValueError):
            continue
        if value < lower_bound or value > upper_bound:
            row["bathrooms"] = None
            outlier_indices.add(idx)

    grouped_bathrooms: Dict = {}
    for row in rows:
        bathrooms = row.get("bathrooms")
        if bathrooms is None:
            continue
        group_key = (row.get("property_type"), row.get("bedrooms"))
        grouped_bathrooms.setdefault(group_key, []).append(float(bathrooms))

    group_medians = {key: median(values) for key, values in grouped_bathrooms.items() if values}

    bathrooms_imputed = 0
    bathrooms_outliers_fixed = 0
    for idx, row in enumerate(rows):
        if row.get("bathrooms") is not None:
            continue

        group_key = (row.get("property_type"), row.get("bedrooms"))
        replacement = group_medians.get(group_key, global_bathrooms_median)
        if replacement is None:
            continue

        row["bathrooms"] = int(round(replacement))
        if idx in outlier_indices:
            bathrooms_outliers_fixed += 1
        else:
            bathrooms_imputed += 1

    return bathrooms_imputed, bathrooms_outliers_fixed



# ──────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
