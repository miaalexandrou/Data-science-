# Cyprus Real Estate - Best Value Search Engine   🏠

**CSE 473/525 Data Science Group Project - Phase A**  
**Team DataVision**  
**Semester 8, Spring 2026**

---

## 📋 Project Overview

The **Cyprus Real Estate Best Value Search Engine** is a data science project that aims to identify undervalued residential properties in Cyprus by analyzing listing data from multiple sources. The system scrapes, processes, and analyzes real estate data to help buyers find the best value-for-money properties.

### Research Question
**Can we identify undervalued residential properties in Cyprus by analyzing listing data from multiple sources?**

### Target Users
- First-time home buyers looking for affordable properties
- Real estate investors seeking undervalued opportunities
- Real estate agents wanting market intelligence
- Property sellers wanting to price competitively

---

## 🎯 Project Goals

1. **Data Collection**: Scrape property listings from Bazaraki.com and Spitogatos.com.cy
2. **Data Storage**: Store structured data in PostgreSQL database
3. **Data Analysis**: Analyze price trends and property characteristics
4. **ML Modeling**: Predict fair market value and identify undervalued properties
5. **Visualization**: Create interactive dashboard for exploring properties

---

## 🏗️ Project Structure

```
cyprus-real-estate/
├── README.md                   # Project documentation
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore file
│
├── src/                       # Source code
│   ├── scrapers/              # Web scraping modules
│   │   ├── bazaraki_scraper.py
│   │   └── spitogatos_scraper.py
│   ├── database/              # Database operations
│   │   ├── db_setup.py
│   │   └── db_operations.py
│   ├── models/                # ML models
│   │   └── price_predictor.py
│   └── utils/                 # Utility functions
│       └── data_cleaning.py
│
├── data/                      # Data storage
│   ├── raw/                   # Raw scraped data
│   └── processed/             # Cleaned data
│
├── notebooks/                 # Jupyter notebooks
│   └── exploratory_analysis.ipynb
│
├── docs/                      # Documentation
│   ├── phase_a_report.md      # Phase A report
│   └── database_schema.sql    # Database schema
│
└── app/                       # Web application (Phase B)
    └── streamlit_app.py
```

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 13+ (or SQLite for local testing)
- pip package manager

### Step 1: Clone Repository
```bash
git clone <repository-url>
cd Data-science-
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Database Setup
1. Create PostgreSQL database:
```bash
createdb cyprus_real_estate
```

2. Run schema setup:
```bash
psql -d cyprus_real_estate -f docs/database_schema.sql
```

### Step 4: Environment Configuration
1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` with your database credentials:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cyprus_real_estate
DB_USER=your_username
DB_PASSWORD=your_password
```

---

## 📊 Usage

### 1. Run Web Scrapers

**Scrape Bazaraki:**
```bash
python src/scrapers/bazaraki_scraper.py
```

**Scrape Spitogatos:**
```bash
python src/scrapers/spitogatos_scraper.py
```

### 2. Process Data
```bash
python src/utils/data_cleaning.py
```

### 3. Run Analysis (Jupyter Notebook)
```bash
jupyter notebook notebooks/exploratory_analysis.ipynb
```

### 4. Launch Dashboard (Phase B)
```bash
streamlit run app/streamlit_app.py
```

---

## 📈 Data Sources

### 1. Bazaraki.com
- Cyprus's largest classified ads platform
- Categories: Residential properties for sale
- Data: Price, location, size, features

### 2. Spitogatos.com.cy
- Specialized real estate platform
- Data: Price, area, property type, amenities

---

## 🗄️ Database Schema

### Main Tables
- **properties**: Core property information
- **price_history**: Track price changes over time
- **scraping_logs**: Monitor scraping activities

### Key Features
- ACID compliance with PostgreSQL
- Price change tracking with triggers
- Efficient indexing for queries
- Support for geospatial data

See [database_schema.sql](docs/database_schema.sql) for full schema.

---

## 🤖 Machine Learning (Phase B)

### Planned Models

1. **Price Prediction Model** (Regression)
   - Random Forest Regressor
   - Gradient Boosting (XGBoost)
   - Features: location, size, bedrooms, amenities
   - Target: Fair market value

2. **Value Score Calculation**
   - Value Score = Predicted Price / Actual Price
   - Score > 1.1 = Undervalued
   - Score 0.9-1.1 = Fair value
   - Score < 0.9 = Overvalued

3. **Property Clustering**
   - K-Means clustering
   - Identify market segments

---

## 📅 Project Timeline

### Phase A (Due: March 30, 2026)
- [x] Project setup and planning
- [x] Database schema design
- [x] Web scrapers development
- [ ] Initial data collection
- [ ] Exploratory data analysis
- [ ] Phase A report and presentation

### Phase B (Due: April 27, 2026)
- [ ] Complete data pipeline
- [ ] ML model development
- [ ] Dashboard development
- [ ] Model monitoring
- [ ] Final report and presentation

---

## 🛡️ Ethical Considerations

### Data Collection Ethics
- ✅ Only scraping publicly available data
- ✅ Respecting robots.txt directives
- ✅ Rate limiting to avoid server overload
- ✅ No collection of personal information
- ✅ GDPR compliance

### Responsible AI
- Transparent about model limitations
- Predictions are estimates, not guarantees
- Users should verify with professionals
- No market manipulation intent

---

## 👥 Team Roles

| Role | Responsibilities |
|------|------------------|
| **Project Manager** | Coordination, timeline, reporting |
| **Data Engineer** | Scrapers, database, data pipeline |
| **Data Scientist** | Modeling, feature engineering, analysis |
| **Frontend Developer** | Dashboard development, UX |

---

## 📚 Technology Stack

### Backend
- **Language**: Python 3.9+
- **Database**: PostgreSQL
- **Web Scraping**: BeautifulSoup, Selenium
- **Data Processing**: Pandas, NumPy

### Machine Learning
- **Framework**: scikit-learn, XGBoost
- **Evaluation**: cross-validation, MAE, R²

### Frontend (Phase B)
- **Dashboard**: Streamlit
- **Visualization**: Plotly, Folium
- **Maps**: Folium for geospatial visualization

### DevOps
- **Version Control**: Git/GitHub
- **Deployment**: Streamlit Cloud (free tier)

---

## 📖 Documentation

- [Phase A Report](docs/phase_a_report.md)
- [Database Schema](docs/database_schema.sql)
- [API Documentation](docs/api_docs.md) (Phase B)

---

## 🐛 Known Issues & Limitations

1. **Website Structure Changes**: Scrapers may break if websites update their HTML
2. **Data Completeness**: Some properties have missing information
3. **Sampling Bias**: Only properties listed online are included
4. **Model Accuracy**: Predictions depend on data quality and features

---

## 🔮 Future Enhancements

- [ ] Real-time notifications for new undervalued properties
- [ ] Mobile application
- [ ] Integration with more data sources
- [ ] Property price prediction API
- [ ] User authentication and saved searches
- [ ] Email alerts for price drops

---

## 📝 License

This project is created for educational purposes as part of CSE 473/525 Data Science course.

---

## 📧 Contact

**Team DataVision**  
CSE 473/525 Data Science  
Instructor: Σίμος Γερασίμου  

For questions or feedback, please contact via Moodle.

---

## 🙏 Acknowledgments

- Course Instructor: Σίμος Γερασίμου
- Data Sources: Bazaraki.com, Spitogatos.com.cy
- Cyprus Statistical Service

---

**Last Updated**: March 2, 2026
