"""
Database setup script
Creates the database and initializes the schema
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_database(db_name: str, user: str, password: str, host: str = 'localhost', port: str = '5432'):
    """
    Create a new PostgreSQL database
    
    Args:
        db_name: Name of the database to create
        user: Database user
        password: User password
        host: Database host
        port: Database port
    """
    try:
        # Connect to default 'postgres' database
        conn = psycopg2.connect(
            dbname='postgres',
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        
        if cur.fetchone():
            print(f"Database '{db_name}' already exists")
        else:
            # Create database
            cur.execute(sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(db_name)
            ))
            print(f"Database '{db_name}' created successfully")
        
        cur.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Error creating database: {e}")
        sys.exit(1)


def setup_schema(db_name: str, user: str, password: str, host: str = 'localhost', port: str = '5432', schema_file: str = 'docs/database_schema.sql'):
    """
    Set up database schema from SQL file
    
    Args:
        db_name: Database name
        user: Database user
        password: User password
        host: Database host
        port: Database port
        schema_file: Path to SQL schema file
    """
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname=db_name,
            user=user,
            password=password,
            host=host,
            port=port
        )
        cur = conn.cursor()
        
        # Read and execute schema file
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        cur.execute(schema_sql)
        conn.commit()
        
        print(f"Schema setup completed successfully")
        
        # Verify tables were created
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """)
        
        tables = cur.fetchall()
        print(f"\nCreated tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        cur.close()
        conn.close()
        
    except FileNotFoundError:
        print(f"Error: Schema file '{schema_file}' not found")
        sys.exit(1)
    except psycopg2.Error as e:
        print(f"Error setting up schema: {e}")
        sys.exit(1)


def test_connection(db_name: str, user: str, password: str, host: str = 'localhost', port: str = '5432'):
    """
    Test database connection
    
    Args:
        db_name: Database name
        user: Database user
        password: User password
        host: Database host
        port: Database port
        
    Returns:
        True if connection successful, False otherwise
    """
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=user,
            password=password,
            host=host,
            port=port
        )
        
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"\nPostgreSQL version: {version[0]}")
        
        cur.close()
        conn.close()
        
        print("✓ Database connection successful")
        return True
        
    except psycopg2.Error as e:
        print(f"✗ Database connection failed: {e}")
        return False


def main():
    """Main setup function"""
    print("=" * 60)
    print("Cyprus Real Estate Database Setup")
    print("=" * 60)
    
    # Get database configuration from environment variables
    db_config = {
        'db_name': os.getenv('DB_NAME', 'cyprus_real_estate'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432')
    }
    
    print(f"\nDatabase Configuration:")
    print(f"  Host: {db_config['host']}:{db_config['port']}")
    print(f"  Database: {db_config['db_name']}")
    print(f"  User: {db_config['user']}")
    
    if not db_config['password']:
        print("\n⚠️  Warning: DB_PASSWORD not set in .env file")
        db_config['password'] = input("Enter database password: ")
    
    print("\n" + "-" * 60)
    print("Step 1: Creating database")
    print("-" * 60)
    create_database(**db_config)
    
    print("\n" + "-" * 60)
    print("Step 2: Setting up schema")
    print("-" * 60)
    setup_schema(**db_config)
    
    print("\n" + "-" * 60)
    print("Step 3: Testing connection")
    print("-" * 60)
    test_connection(**db_config)
    
    print("\n" + "=" * 60)
    print("Database setup completed successfully! 🎉")
    print("=" * 60)
    print("\nYou can now:")
    print("  1. Run the scrapers: python src/scrapers/bazaraki_scraper.py")
    print("  2. Clean the data: python src/utils/data_cleaning.py")
    print("  3. Explore the data: jupyter notebook notebooks/")
    print("=" * 60)


if __name__ == "__main__":
    main()
