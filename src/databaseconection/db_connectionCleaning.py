"""
Database Connection Module
Handles MariaDB connections and inserts for the DataScience project.
Connection settings are read from environment variables with sensible defaults
that match Database/db.yaml.
"""

import os
import json
import re
import pymysql
import pymysql.cursors
from typing import Dict, List, Optional


# ──────────────────────────────────────────────
# Connection defaults (override via env vars)
# ──────────────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = int(os.getenv("DB_PORT", "3307"))
DB_USER     = os.getenv("DB_USER",     "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "DataScience_root_2025")
DB_NAME     = os.getenv("DB_NAME",     "DataScience")


class DBConnection:
    """
    Manages a single MariaDB/MySQL connection for the DataScience project.

    Usage
    -----
    db = DBConnection()
    db.connect()
    inserted = db.insert_properties(properties)
    db.disconnect()

    Or use as a context manager:
    with DBConnection() as db:
        db.insert_properties(properties)
    """

    def __init__(
        self,
        host: str     = DB_HOST,
        port: int     = DB_PORT,
        user: str     = DB_USER,
        password: str = DB_PASSWORD,
        database: str = DB_NAME,
    ):
        self.host     = host
        self.port     = port
        self.user     = user
        self.password = password
        self.database = database
        self._conn: Optional[pymysql.connections.Connection] = None

    # ── context manager support ───────────────────────────────────────────
    def __enter__(self) -> "DBConnection":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    # ── connection management ─────────────────────────────────────────────
    def connect(self) -> None:
        """Open the database connection."""
        try:
            self._conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
            )
            print(f"[DB] Connected to {self.database} on {self.host}:{self.port}")
        except pymysql.Error as e:
            print(f"[DB] Connection failed: {e}")
            raise

    def disconnect(self) -> None:
        """Close the database connection."""
        if self._conn:
            try:
                self._conn.close()
                print("[DB] Connection closed.")
            except pymysql.Error:
                pass
            finally:
                self._conn = None

    def is_connected(self) -> bool:
        """Return True if the connection is open and alive."""
        if not self._conn:
            return False
        try:
            self._conn.ping(reconnect=True)
            return True
        except pymysql.Error:
            return False

    def commit(self) -> None:
        """Commit current transaction."""
        if not self.is_connected():
            raise RuntimeError("[DB] Not connected. Call connect() first.")
        self._conn.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        if not self.is_connected():
            raise RuntimeError("[DB] Not connected. Call connect() first.")
        self._conn.rollback()

    def _validate_table_name(self, table_name: str) -> str:
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', table_name or ''):
            raise ValueError(f"Invalid table name: {table_name}")
        return table_name

    def fetch_rows_with_missing_locations(
        self,
        table_name: str = "properties_processed",
        max_rows: Optional[int] = None,
    ) -> List[Dict]:
        """Fetch rows where city/district/area is missing or unknown-like."""
        if not self.is_connected():
            raise RuntimeError("[DB] Not connected. Call connect() first.")

        safe_table = self._validate_table_name(table_name)
        query = f"""
            SELECT id, url, city, district, area
            FROM {safe_table}
            WHERE
                city IS NULL OR TRIM(city) = '' OR LOWER(TRIM(city)) IN ('unknown', 'n/a', 'na', 'none', 'null', '?', '??') OR
                district IS NULL OR TRIM(district) = '' OR LOWER(TRIM(district)) IN ('unknown', 'n/a', 'na', 'none', 'null', '?', '??') OR
                area IS NULL OR TRIM(area) = '' OR LOWER(TRIM(area)) IN ('unknown', 'n/a', 'na', 'none', 'null', '?', '??')
            ORDER BY id ASC
        """
        params = ()
        if max_rows and max_rows > 0:
            query += " LIMIT %s"
            params = (max_rows,)

        with self._conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def update_location_fields_by_id(
        self,
        row_id: int,
        city: Optional[str] = None,
        district: Optional[str] = None,
        area: Optional[str] = None,
        table_name: str = "properties_processed",
        commit: bool = False,
    ) -> bool:
        """Update provided non-null location fields for a specific row id."""
        if not self.is_connected():
            raise RuntimeError("[DB] Not connected. Call connect() first.")

        safe_table = self._validate_table_name(table_name)
        updates: Dict[str, str] = {}
        if city is not None:
            updates['city'] = city
        if district is not None:
            updates['district'] = district
        if area is not None:
            updates['area'] = area

        if not updates:
            return False

        set_clause = ", ".join([f"`{k}` = %s" for k in updates.keys()])
        sql = f"UPDATE {safe_table} SET {set_clause} WHERE id = %s"
        params = tuple(updates.values()) + (row_id,)

        try:
            with self._conn.cursor() as cursor:
                cursor.execute(sql, params)
                affected = cursor.rowcount > 0
            if commit:
                self._conn.commit()
            return affected
        except pymysql.Error:
            self._conn.rollback()
            raise

    # ── insert helpers ────────────────────────────────────────────────────
    def insert_property(self, property_data: Dict) -> bool:
        """
        Insert a single property record.

        Returns True if a new row was inserted, False if it was a duplicate.
        """
        if not self.is_connected():
            raise RuntimeError("[DB] Not connected. Call connect() first.")

        sql = """
            INSERT INTO properties (
                source, reference_number, external_id, url, title, price,
                city, district, area,
                bedrooms, bathrooms,
                property_area_sqm, plot_area_sqm,
                property_type, parking, `condition`, furnishing,
                included, postal_code, construction_year,
                online_viewing, air_conditioning, energy_efficiency,
                price_per_sqm, description, scraped_date
            ) VALUES (
                %(source)s, %(reference_number)s, %(external_id)s,
                %(url)s, %(title)s, %(price)s,
                %(city)s, %(district)s, %(area)s,
                %(bedrooms)s, %(bathrooms)s,
                %(property_area_sqm)s, %(plot_area_sqm)s,
                %(property_type)s, %(parking)s, %(condition)s, %(furnishing)s,
                %(included)s, %(postal_code)s, %(construction_year)s,
                %(online_viewing)s, %(air_conditioning)s, %(energy_efficiency)s,
                %(price_per_sqm)s, %(description)s, %(scraped_date)s
            )
        """
        # Normalize data
        row = dict(property_data)
        
        # Remove must_haves if present
        row.pop("must_haves", None)
        
        # Convert list fields to JSON strings
        if isinstance(row.get("included"), list):
            row["included"] = json.dumps(row["included"], ensure_ascii=False) if row["included"] else None
        
        # Handle condition field
        row.setdefault("condition", row.pop("condition", None))

        try:
            with self._conn.cursor() as cursor:
                cursor.execute(sql, row)
            self._conn.commit()
            return cursor.rowcount == 1
        except pymysql.Error as e:
            self._conn.rollback()
            print(f"[DB] Insert error for {row.get('external_id')}: {e}")
            return False

    def insert_properties(self, properties: List[Dict]) -> int:
        """
        Bulk-insert a list of property dicts.

        Returns the number of newly inserted rows (duplicates are skipped).
        """
        if not properties:
            return 0

        inserted = 0
        skipped  = 0

        for prop in properties:
            if self.insert_property(prop):
                inserted += 1
            else:
                skipped += 1

        print(f"[DB] Inserted {inserted} new row(s), skipped {skipped} duplicate(s).")
        return inserted
