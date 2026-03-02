-- Cyprus Real Estate Database Schema
-- PostgreSQL Database Setup for Best Value Real Estate Search Engine

-- Drop existing tables if they exist
DROP TABLE IF EXISTS price_history CASCADE;
DROP TABLE IF EXISTS scraping_logs CASCADE;
DROP TABLE IF EXISTS properties CASCADE;

-- Create properties table
CREATE TABLE properties (
    property_id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL CHECK (source IN ('bazaraki', 'spitogatos')),
    external_id VARCHAR(100) NOT NULL,
    url TEXT,
    title VARCHAR(255),
    description TEXT,
    
    -- Pricing
    price DECIMAL(10, 2) CHECK (price > 0),
    price_per_sqm DECIMAL(8, 2),
    
    -- Location
    city VARCHAR(100),
    district VARCHAR(100),
    area VARCHAR(100),
    latitude DECIMAL(9, 6),
    longitude DECIMAL(9, 6),
    
    -- Property characteristics
    property_type VARCHAR(50) CHECK (property_type IN ('house', 'apartment', 'villa', 'penthouse', 'bungalow', 'studio', 'maisonette', 'other')),
    size_sqm INTEGER CHECK (size_sqm > 0),
    plot_size_sqm INTEGER,
    bedrooms INTEGER CHECK (bedrooms >= 0),
    bathrooms INTEGER CHECK (bathrooms >= 0),
    year_built INTEGER CHECK (year_built >= 1900 AND year_built <= EXTRACT(YEAR FROM CURRENT_DATE) + 2),
    floor_level INTEGER,
    total_floors INTEGER,
    
    -- Amenities & Features (boolean flags)
    has_parking BOOLEAN DEFAULT FALSE,
    has_pool BOOLEAN DEFAULT FALSE,
    has_garden BOOLEAN DEFAULT FALSE,
    has_balcony BOOLEAN DEFAULT FALSE,
    has_elevator BOOLEAN DEFAULT FALSE,
    has_air_conditioning BOOLEAN DEFAULT FALSE,
    has_heating BOOLEAN DEFAULT FALSE,
    is_furnished BOOLEAN DEFAULT FALSE,
    
    -- Energy & Condition
    energy_rating VARCHAR(10),  -- A+, A, B, C, D, E, F, G
    condition VARCHAR(50),  -- new, excellent, good, needs renovation
    
    -- Listing metadata
    listing_date DATE,
    photos_count INTEGER DEFAULT 0,
    
    -- Data management
    first_scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Unique constraint on source and external_id combination
    CONSTRAINT unique_property UNIQUE(source, external_id)
);

-- Create indexes for better query performance
CREATE INDEX idx_properties_city ON properties(city);
CREATE INDEX idx_properties_price ON properties(price);
CREATE INDEX idx_properties_type ON properties(property_type);
CREATE INDEX idx_properties_bedrooms ON properties(bedrooms);
CREATE INDEX idx_properties_active ON properties(is_active);
CREATE INDEX idx_properties_location ON properties(city, district);
CREATE INDEX idx_properties_price_range ON properties(price) WHERE is_active = TRUE;

-- Create GiST index for geospatial queries (requires PostGIS extension)
-- CREATE INDEX idx_properties_geo ON properties USING GIST(ll_to_earth(latitude, longitude));

-- Create price history table
CREATE TABLE price_history (
    history_id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL REFERENCES properties(property_id) ON DELETE CASCADE,
    price DECIMAL(10, 2) NOT NULL CHECK (price > 0),
    recorded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Index for efficient time series queries
    CONSTRAINT fk_property FOREIGN KEY (property_id) REFERENCES properties(property_id)
);

CREATE INDEX idx_price_history_property ON price_history(property_id);
CREATE INDEX idx_price_history_date ON price_history(recorded_date);

-- Create scraping logs table
CREATE TABLE scraping_logs (
    log_id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    scrape_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scrape_type VARCHAR(50),  -- 'full', 'incremental', 'details'
    
    -- Statistics
    properties_found INTEGER DEFAULT 0,
    properties_new INTEGER DEFAULT 0,
    properties_updated INTEGER DEFAULT 0,
    properties_deactivated INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    
    -- Status
    status VARCHAR(50) CHECK (status IN ('started', 'completed', 'failed', 'partial')),
    error_message TEXT,
    duration_seconds INTEGER,
    
    -- Metadata
    config JSONB  -- Store scraping configuration as JSON
);

CREATE INDEX idx_scraping_logs_source ON scraping_logs(source);
CREATE INDEX idx_scraping_logs_date ON scraping_logs(scrape_date);
CREATE INDEX idx_scraping_logs_status ON scraping_logs(status);

-- Create view for active properties with derived features
CREATE VIEW active_properties_view AS
SELECT 
    p.*,
    ROUND(p.price / NULLIF(p.size_sqm, 0), 2) as calculated_price_per_sqm,
    EXTRACT(YEAR FROM CURRENT_DATE) - p.year_built as property_age,
    CURRENT_DATE - p.listing_date as days_on_market,
    (SELECT COUNT(*) FROM price_history ph WHERE ph.property_id = p.property_id) as price_changes_count,
    (SELECT MIN(ph.price) FROM price_history ph WHERE ph.property_id = p.property_id) as lowest_price,
    (SELECT MAX(ph.price) FROM price_history ph WHERE ph.property_id = p.property_id) as highest_price
FROM properties p
WHERE p.is_active = TRUE;

-- Create view for price trends
CREATE VIEW price_trends_view AS
SELECT 
    city,
    property_type,
    COUNT(*) as property_count,
    AVG(price) as avg_price,
    AVG(price_per_sqm) as avg_price_per_sqm,
    MIN(price) as min_price,
    MAX(price) as max_price,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) as median_price
FROM properties
WHERE is_active = TRUE
GROUP BY city, property_type;

-- Function to update last_updated timestamp
CREATE OR REPLACE FUNCTION update_last_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update last_updated
CREATE TRIGGER trigger_update_last_updated
BEFORE UPDATE ON properties
FOR EACH ROW
EXECUTE FUNCTION update_last_updated();

-- Function to archive price changes
CREATE OR REPLACE FUNCTION archive_price_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (NEW.price IS DISTINCT FROM OLD.price) THEN
        INSERT INTO price_history (property_id, price)
        VALUES (NEW.property_id, NEW.price);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to log price changes
CREATE TRIGGER trigger_archive_price
AFTER UPDATE ON properties
FOR EACH ROW
WHEN (OLD.price IS DISTINCT FROM NEW.price)
EXECUTE FUNCTION archive_price_change();

-- Insert sample data for testing (optional)
-- You can comment this out for production

-- Sample properties
INSERT INTO properties (
    source, external_id, title, price, city, district, 
    property_type, size_sqm, bedrooms, bathrooms,
    has_parking, has_pool, listing_date
) VALUES 
    ('bazaraki', 'BAZ001', '3 Bedroom Apartment in Nicosia Center', 180000, 'Nicosia', 'Center', 'apartment', 120, 3, 2, TRUE, FALSE, CURRENT_DATE - INTERVAL '10 days'),
    ('spitogatos', 'SPT001', 'Luxury Villa with Pool in Limassol', 650000, 'Limassol', 'Agios Athanasios', 'villa', 250, 4, 3, TRUE, TRUE, CURRENT_DATE - INTERVAL '5 days'),
    ('bazaraki', 'BAZ002', 'Studio Apartment near University', 85000, 'Nicosia', 'Engomi', 'studio', 45, 1, 1, FALSE, FALSE, CURRENT_DATE - INTERVAL '2 days');

-- Grant permissions (adjust user as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_user;

-- Display table information
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
ORDER BY table_name;
