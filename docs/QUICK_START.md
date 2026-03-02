# Quick Start Guide - Phase A

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 3. Setup Database
```bash
# Option A: Using the setup script
python src/database/db_setup.py

# Option B: Manual setup
createdb cyprus_real_estate
psql -d cyprus_real_estate -f docs/database_schema.sql
```

### 4. Run Scrapers
```bash
# Scrape Bazaraki
python src/scrapers/bazaraki_scraper.py

# Scrape Spitogatos  
python src/scrapers/spitogatos_scraper.py
```

### 5. Clean Data
```bash
python src/utils/data_cleaning.py
```

### 6. Explore Data
```bash
jupyter notebook notebooks/exploratory_analysis.ipynb
```

## Project Structure

```
Data-science-/
├── src/
│   ├── scrapers/         # Web scraping modules
│   ├── database/         # Database operations
│   ├── utils/            # Utility functions
│   └── models/           # ML models (Phase B)
├── data/
│   ├── raw/              # Raw scraped data
│   └── processed/        # Cleaned data
├── docs/                 # Documentation
├── notebooks/            # Jupyter notebooks
└── app/                  # Streamlit app (Phase B)
```

## Next Steps for Phase A

1. ✅ Project setup complete
2. ⏳ Run scrapers to collect initial data
3. ⏳ Perform exploratory data analysis
4. ⏳ Create visualizations
5. ⏳ Write Phase A report
6. ⏳ Prepare presentation

## Common Commands

```bash
# Check database connection
python -c "from src.database.db_operations import DatabaseConnection; 
with DatabaseConnection() as db: print('Connected!')"

# View scraped data
python -c "import json; 
data = json.load(open('data/raw/bazaraki_properties.json')); 
print(f'Properties: {len(data)}')"

# Generate data quality report
python -c "from src.utils.data_cleaning import DataCleaner, load_json_to_dataframe;
df = load_json_to_dataframe('data/raw/bazaraki_properties.json');
cleaner = DataCleaner();
report = cleaner.get_data_quality_report(df);
print(report)"
```

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running
- Check credentials in .env file
- Verify database exists: `psql -l`

### Scraping Issues
- Check internet connection
- Website structure may have changed
- Rate limiting - increase delay in scrapers

### Import Errors
- Ensure you're in project root directory
- Check all dependencies installed: `pip list`

## Resources

- [Phase A Report](docs/phase_a_report.md)
- [Database Schema](docs/database_schema.sql)
- [Project Brief](CSE525%20Group%20Project%20Brief.pdf)
