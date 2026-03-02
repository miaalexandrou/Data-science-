-- ============================================================
-- DataScience Database Schema
-- Source: bazaraki_properties.json
-- ============================================================

CREATE DATABASE IF NOT EXISTS DataScience_data
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE DataScience_data;

-- ------------------------------------------------------------
-- Table: properties
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS properties (
    id                  INT             UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source              VARCHAR(50)     NOT NULL,
    reference_number    VARCHAR(50)     NOT NULL,
    external_id         VARCHAR(50)     NOT NULL,
    url                 TEXT            NOT NULL,
    title               VARCHAR(255)    NOT NULL,
    price               DECIMAL(12, 2)  NOT NULL,
    city                VARCHAR(100)    NOT NULL,
    district            VARCHAR(100)    NOT NULL,
    area                VARCHAR(100)    NULL,
    bedrooms            TINYINT         UNSIGNED NULL,
    bathrooms           TINYINT         UNSIGNED NULL,
    property_area_sqm   INT             UNSIGNED NULL,
    plot_area_sqm       INT             UNSIGNED NULL,
    property_type       VARCHAR(100)    NOT NULL,
    parking             VARCHAR(100)    NULL,
    `condition`         VARCHAR(100)    NULL,
    furnishing          VARCHAR(100)    NULL,
    included            TEXT            NULL,
    postal_code         VARCHAR(20)     NULL,
    construction_year   SMALLINT        UNSIGNED NULL,
    online_viewing      VARCHAR(10)     NULL,
    air_conditioning    VARCHAR(100)    NULL,
    energy_efficiency   VARCHAR(50)     NULL,
    price_per_sqm       DECIMAL(10, 3)  NULL,
    scraped_date        DATETIME        NOT NULL,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    -- Avoid duplicate listings from the same source
    UNIQUE KEY uq_source_external (source, external_id),

    -- Common query indexes
    INDEX idx_city          (city),
    INDEX idx_district      (district),
    INDEX idx_property_type (property_type),
    INDEX idx_price         (price),
    INDEX idx_bedrooms      (bedrooms),
    INDEX idx_scraped_date  (scraped_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
