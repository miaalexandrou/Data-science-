# Phase A Report: Best Value Real Estate Search Engine for Cyprus

**Team DataVision**  
**CSE 473/525: Data Science**  
**Date:** March 2026

---

## 1. Project Domain & Research Question

### 1.1 Domain
Real Estate Market Analysis - Cyprus

### 1.2 Problem Statement
The Cyprus real estate market lacks transparency in pricing, making it difficult for buyers to identify properties that offer the best value for money. Many properties may be overpriced or undervalued based on location, features, and market trends.

### 1.3 Research Questions
1. **Primary Question**: Can we identify undervalued residential properties in Cyprus by analyzing listing data from multiple sources?
2. **Secondary Questions**:
   - What factors contribute most to property value in different regions of Cyprus?
   - How do property prices vary across cities (Nicosia, Limassol, Larnaca, Paphos, Famagusta)?
   - Can we predict fair market value based on property characteristics?
   - Which properties offer the best value relative to their predicted price?

### 1.4 Target Users
- First-time home buyers looking for affordable properties
- Real estate investors seeking undervalued opportunities
- Real estate agents wanting market intelligence
- Property sellers wanting to price competitively

---

## 2. Data Collection Strategy

### 2.1 Data Sources
We will collect property listing data from two major Cyprus real estate platforms:

1. **Bazaraki.com** - Cyprus's largest classified ads platform
   - Categories: Residential properties for sale
   - Data points: Price, location, size, bedrooms, bathrooms, features
   
2. **Spitogatos.com.cy** - Specialized real estate platform
   - Categories: Houses and apartments for sale
   - Data points: Price, area, property type, amenities, year built

### 2.2 Web Scraping Approach
- **Method**: Python-based web scraping using BeautifulSoup and Selenium
- **Frequency**: Daily updates to capture new listings and price changes
- **Data Volume**: Expected ~5,000-10,000 active listings
- **Ethical Considerations**:
  - Respect robots.txt
  - Implement rate limiting to avoid server overload
  - Only collect publicly available information
  - No personal data collection (phone numbers, names)

### 2.3 Features to Extract
- Property ID (unique identifier)
- Price (EUR)
- Location (city, district, area)
- Property type (house, apartment, villa)
- Size (square meters)
- Number of bedrooms
- Number of bathrooms
- Year built
- Floor level (for apartments)
- Parking availability
- Swimming pool
- Garden
- Energy efficiency rating
- Listing date
- Description text
- Number of photos
- Source website

---

## 3. Data Storage Design

### 3.1 Database Choice
**PostgreSQL** - Selected for:
- Structured relational data
- ACID compliance for data integrity
- Strong support for geospatial queries (PostGIS extension)
- Excellent performance for analytics queries

### 3.2 Database Schema (Preliminary)

#### Table: properties
```sql
CREATE TABLE properties (
    property_id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    external_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(255),
    description TEXT,
    price DECIMAL(10, 2),
    city VARCHAR(100),
    district VARCHAR(100),
    area VARCHAR(100),
    latitude DECIMAL(9, 6),
    longitude DECIMAL(9, 6),
    property_type VARCHAR(50),
    size_sqm INTEGER,
    bedrooms INTEGER,
    bathrooms INTEGER,
    year_built INTEGER,
    floor_level INTEGER,
    has_parking BOOLEAN,
    has_pool BOOLEAN,
    has_garden BOOLEAN,
    energy_rating VARCHAR(10),
    listing_date DATE,
    first_scraped_date TIMESTAMP,
    last_updated TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT check_price CHECK (price > 0),
    CONSTRAINT check_size CHECK (size_sqm > 0)
);
```

#### Table: price_history
```sql
CREATE TABLE price_history (
    history_id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(property_id),
    price DECIMAL(10, 2),
    recorded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Table: scraping_logs
```sql
CREATE TABLE scraping_logs (
    log_id SERIAL PRIMARY KEY,
    source VARCHAR(50),
    scrape_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    properties_found INTEGER,
    properties_new INTEGER,
    properties_updated INTEGER,
    errors_count INTEGER,
    status VARCHAR(50)
);
```

### 3.3 Entity-Relationship Diagram
```
[Properties] 1---* [Price History]
     |
     |
[Scraping Logs]
```

---

## 4. Data Processing Pipeline (Planned)

### 4.1 Data Cleaning
- Remove duplicate listings (same property on both sites)
- Standardize location names
- Handle missing values (imputation or removal)
- Convert units to consistent format
- Remove outliers (extreme prices or sizes)

### 4.2 Feature Engineering
- Price per square meter
- Distance to city center
- Distance to amenities (beaches, schools, hospitals)
- Age of property (current year - year_built)
- Listing age (days on market)
- Text features from description (TF-IDF)

### 4.3 Data Quality Measures
- Validation rules for price ranges
- Geolocation validation
- Completeness checks (minimum required fields)
- Consistency checks across updates

---

## 5. Modeling Approach (Planned for Phase B)

### 5.1 Predictive Models
1. **Price Prediction Model** (Regression)
   - Random Forest Regressor
   - Gradient Boosting (XGBoost)
   - Features: location, size, bedrooms, amenities
   - Target: Fair market value

2. **Value Score Model**
   - Calculate: Value Score = Predicted Price / Actual Price
   - Score > 1.1 = Undervalued (potential bargain)
   - Score 0.9-1.1 = Fair value
   - Score < 0.9 = Overvalued

3. **Clustering Model** (Unsupervised)
   - K-Means clustering to group similar properties
   - Identify market segments

### 5.2 Evaluation Metrics
- Mean Absolute Error (MAE)
- Mean Absolute Percentage Error (MAPE)
- R² Score
- Cross-validation (5-fold)

---

## 6. Prototype Design

### 6.1 Application Type
**Web Dashboard** using Streamlit

### 6.2 User Interface Features

#### Home Page
- Search filters: location, price range, bedrooms, property type
- Map view of properties
- List view with key details

#### Property Details Page
- Full property information
- Price history chart
- Value score indicator (color-coded)
- Similar properties comparison
- Predicted fair value

#### Analytics Dashboard
- Market overview statistics
- Price trends by region
- Best value recommendations (top 20)
- Interactive visualizations (Plotly)

#### Admin Panel (Phase B)
- Scraping status and logs
- Data quality metrics
- Model performance monitoring

### 6.3 Technology Stack
- **Frontend**: Streamlit
- **Backend**: Python (Flask/FastAPI for API endpoints)
- **Database**: PostgreSQL
- **Data Processing**: Pandas, NumPy
- **Modeling**: scikit-learn, XGBoost
- **Visualization**: Plotly, Folium (maps)
- **Web Scraping**: BeautifulSoup, Selenium
- **Deployment**: Streamlit Cloud (free tier)

---

## 7. Project Timeline (Phase A)

| Week | Tasks |
|------|-------|
| Week 1 (Mar 3-9) | Project setup, scrapers development |
| Week 2 (Mar 10-16) | Database implementation, initial data collection |
| Week 3 (Mar 17-23) | Data cleaning, EDA, UI mockups |
| Week 4 (Mar 24-30) | Basic prototype, report writing, presentation prep |

---

## 8. Ethical Considerations

### 8.1 Data Privacy
- No scraping of personal information (contact details)
- Only publicly available listing data
- Compliance with GDPR regulations

### 8.2 Web Scraping Ethics
- Respect robots.txt directives
- Rate limiting (1 request per 2 seconds)
- User-agent identification
- No disruption to website services

### 8.3 Bias Considerations
- Acknowledge potential sampling bias (online listings only)
- Properties not listed online won't be included
- Luxury properties may be underrepresented
- Document data limitations in final report

### 8.4 Responsible Use
- Tool designed to help buyers, not manipulate markets
- Predictions are estimates, not guarantees
- Users should verify with professionals
- Transparent about model limitations

---

## 9. Team Roles

| Role | Name | Responsibilities |
|------|------|------------------|
| Project Manager | [TBD] | Coordination, timeline, reporting |
| Data Engineer | [TBD] | Scrapers, database, data pipeline |
| Data Scientist | [TBD] | Modeling, feature engineering, analysis |
| Frontend Developer | [TBD] | Dashboard development, UX |

---

## 10. GitHub Repository

**Repository**: [GitHub Link - TBD]

### Repository Structure
```
cyprus-real-estate/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   ├── scrapers/
│   │   ├── bazaraki_scraper.py
│   │   └── spitogatos_scraper.py
│   ├── database/
│   │   ├── db_setup.py
│   │   └── db_operations.py
│   ├── models/
│   │   └── price_predictor.py
│   └── utils/
│       └── data_cleaning.py
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
│   └── exploratory_analysis.ipynb
├── docs/
│   ├── phase_a_report.md
│   └── database_schema.sql
└── app/
    └── streamlit_app.py
```

---

## 11. Current Progress (Phase A)

### Completed
- [x] Project domain and research question defined
- [x] Data sources identified
- [x] Database schema designed
- [x] Project structure created

### In Progress
- [ ] Web scrapers implementation
- [ ] Database setup
- [ ] Initial data collection

### Planned
- [ ] Data cleaning pipeline
- [ ] Exploratory data analysis
- [ ] UI mockups and basic prototype
- [ ] Phase A presentation

---

## 12. Expected Challenges & Mitigation

| Challenge | Mitigation Strategy |
|-----------|---------------------|
| Website structure changes | Modular scraper design, regular monitoring |
| Incomplete data | Imputation strategies, minimum completeness thresholds |
| Duplicate listings | Fuzzy matching algorithm for deduplication |
| Data volume | Efficient database indexing, incremental processing |
| Deployment costs | Use free tiers (Streamlit Cloud, render.com) |
| Model accuracy | Multiple models, ensemble methods, continuous validation |

---

## 13. Next Steps for Phase B

1. Complete all data collection and processing stages
2. Implement and evaluate ML models
3. Develop full-featured web dashboard
4. Implement monitoring and drift detection
5. Conduct user testing
6. Prepare final presentation and demonstration

---

## References

- Bazaraki.com - Property listings platform
- Spitogatos.com.cy - Real estate platform
- Cyprus Statistical Service - Housing market data
- Course materials - CSE 473/525 Data Science

---

**Last Updated**: March 2, 2026
