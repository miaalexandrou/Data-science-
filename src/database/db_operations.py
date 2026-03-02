"""
Database operations module for Cyprus Real Estate project
Handles connection, data insertion, and queries for PostgreSQL database
"""

import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from typing import List, Dict, Optional, Tuple
import os
from datetime import datetime
import json


class DatabaseManager:
    """
    Manages database connections and operations for the real estate project
    """
    
    def __init__(self, db_config: Optional[Dict] = None):
        """
        Initialize database manager
        
        Args:
            db_config: Database configuration dictionary
                      If None, reads from environment variables
        """
        if db_config is None:
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'cyprus_real_estate'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', '')
            }
        
        self.db_config = db_config
        self.conn = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            print("Database connection established successfully")
            return self.conn
        except psycopg2.Error as e:
            print(f"Error connecting to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("Database connection closed")
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> Optional[List]:
        """
        Execute a query and return results
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Query results as list of dictionaries
        """
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if cur.description:  # Has results
                    return cur.fetchall()
                self.conn.commit()
                return None
        except psycopg2.Error as e:
            self.conn.rollback()
            print(f"Error executing query: {e}")
            raise
    
    def insert_property(self, property_data: Dict) -> Optional[int]:
        """
        Insert a new property into the database
        
        Args:
            property_data: Dictionary containing property information
            
        Returns:
            Property ID if successful, None otherwise
        """
        query = """
        INSERT INTO properties (
            source, external_id, url, title, description,
            price, city, district, area, latitude, longitude,
            property_type, size_sqm, bedrooms, bathrooms,
            year_built, floor_level, has_parking, has_pool, has_garden,
            energy_rating, listing_date, photos_count, first_scraped_date
        ) VALUES (
            %(source)s, %(external_id)s, %(url)s, %(title)s, %(description)s,
            %(price)s, %(city)s, %(district)s, %(area)s, %(latitude)s, %(longitude)s,
            %(property_type)s, %(size_sqm)s, %(bedrooms)s, %(bathrooms)s,
            %(year_built)s, %(floor_level)s, %(has_parking)s, %(has_pool)s, %(has_garden)s,
            %(energy_rating)s, %(listing_date)s, %(photos_count)s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (source, external_id) 
        DO UPDATE SET
            price = EXCLUDED.price,
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            last_updated = CURRENT_TIMESTAMP,
            is_active = TRUE
        RETURNING property_id;
        """
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, property_data)
                property_id = cur.fetchone()[0]
                self.conn.commit()
                return property_id
        except psycopg2.Error as e:
            self.conn.rollback()
            print(f"Error inserting property: {e}")
            return None
    
    def batch_insert_properties(self, properties: List[Dict]) -> Tuple[int, int]:
        """
        Insert multiple properties efficiently
        
        Args:
            properties: List of property dictionaries
            
        Returns:
            Tuple of (inserted_count, updated_count)
        """
        inserted = 0
        updated = 0
        
        for prop in properties:
            prop_id = self.insert_property(prop)
            if prop_id:
                inserted += 1
        
        return inserted, updated
    
    def get_properties(
        self,
        city: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        property_type: Optional[str] = None,
        bedrooms: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Query properties with filters
        
        Args:
            city: Filter by city
            min_price: Minimum price
            max_price: Maximum price
            property_type: Filter by property type
            bedrooms: Filter by number of bedrooms
            limit: Maximum number of results
            
        Returns:
            List of property dictionaries
        """
        conditions = ["is_active = TRUE"]
        params = []
        
        if city:
            conditions.append("city = %s")
            params.append(city)
        
        if min_price:
            conditions.append("price >= %s")
            params.append(min_price)
        
        if max_price:
            conditions.append("price <= %s")
            params.append(max_price)
        
        if property_type:
            conditions.append("property_type = %s")
            params.append(property_type)
        
        if bedrooms:
            conditions.append("bedrooms = %s")
            params.append(bedrooms)
        
        where_clause = " AND ".join(conditions)
        params.append(limit)
        
        query = f"""
        SELECT * FROM properties
        WHERE {where_clause}
        ORDER BY last_updated DESC
        LIMIT %s;
        """
        
        return self.execute_query(query, tuple(params))
    
    def get_price_history(self, property_id: int) -> List[Dict]:
        """
        Get price history for a property
        
        Args:
            property_id: Property ID
            
        Returns:
            List of price history entries
        """
        query = """
        SELECT price, recorded_date
        FROM price_history
        WHERE property_id = %s
        ORDER BY recorded_date ASC;
        """
        return self.execute_query(query, (property_id,))
    
    def get_market_statistics(self, city: Optional[str] = None) -> Dict:
        """
        Get market statistics
        
        Args:
            city: Filter by city (optional)
            
        Returns:
            Dictionary with market statistics
        """
        where_clause = "WHERE is_active = TRUE"
        params = []
        
        if city:
            where_clause += " AND city = %s"
            params.append(city)
        
        query = f"""
        SELECT 
            COUNT(*) as total_properties,
            AVG(price) as avg_price,
            MIN(price) as min_price,
            MAX(price) as max_price,
            AVG(price / NULLIF(size_sqm, 0)) as avg_price_per_sqm,
            COUNT(DISTINCT property_type) as property_types_count
        FROM properties
        {where_clause};
        """
        
        result = self.execute_query(query, tuple(params))
        return dict(result[0]) if result else {}
    
    def log_scraping_session(
        self,
        source: str,
        scrape_type: str,
        status: str,
        properties_found: int = 0,
        properties_new: int = 0,
        properties_updated: int = 0,
        errors_count: int = 0,
        duration_seconds: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> int:
        """
        Log a scraping session
        
        Args:
            source: Data source name
            scrape_type: Type of scrape (full, incremental, details)
            status: Scraping status
            properties_found: Number of properties found
            properties_new: Number of new properties
            properties_updated: Number of updated properties
            errors_count: Number of errors encountered
            duration_seconds: Duration of scraping session
            error_message: Error message if failed
            
        Returns:
            Log ID
        """
        query = """
        INSERT INTO scraping_logs (
            source, scrape_type, status,
            properties_found, properties_new, properties_updated,
            errors_count, duration_seconds, error_message
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING log_id;
        """
        
        params = (
            source, scrape_type, status,
            properties_found, properties_new, properties_updated,
            errors_count, duration_seconds, error_message
        )
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                log_id = cur.fetchone()[0]
                self.conn.commit()
                return log_id
        except psycopg2.Error as e:
            self.conn.rollback()
            print(f"Error logging scraping session: {e}")
            return -1
    
    def deactivate_old_listings(self, days: int = 90) -> int:
        """
        Deactivate listings that haven't been updated in X days
        
        Args:
            days: Number of days threshold
            
        Returns:
            Number of properties deactivated
        """
        query = """
        UPDATE properties
        SET is_active = FALSE
        WHERE is_active = TRUE
          AND last_updated < CURRENT_DATE - INTERVAL '%s days'
        RETURNING property_id;
        """
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, (days,))
                count = cur.rowcount
                self.conn.commit()
                return count
        except psycopg2.Error as e:
            self.conn.rollback()
            print(f"Error deactivating listings: {e}")
            return 0


# Context manager support
class DatabaseConnection:
    """Context manager for database connections"""
    
    def __init__(self, db_config: Optional[Dict] = None):
        self.db_manager = DatabaseManager(db_config)
    
    def __enter__(self):
        self.db_manager.connect()
        return self.db_manager
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db_manager.disconnect()


def main():
    """Example usage"""
    # Example: Connect and query properties
    with DatabaseConnection() as db:
        # Get properties in Nicosia
        properties = db.get_properties(city='Nicosia', limit=10)
        print(f"Found {len(properties)} properties in Nicosia")
        
        # Get market statistics
        stats = db.get_market_statistics(city='Limassol')
        print(f"Market statistics for Limassol: {stats}")


if __name__ == "__main__":
    main()
