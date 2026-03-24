# Cyprus Real Estate – Best Value Search Engine 

**CSE 473/525 Data Science Group Project – Phase A**  
**Team DataVision**  
**Semester 8, Spring 2026**

---

##  Project Overview

The **Cyprus Real Estate Best Value Search Engine** is a data science project that identifies undervalued residential properties in Cyprus by analyzing listing data from multiple sources. The system scrapes, stores, and analyzes real estate listings to highlight the best value-for-money properties.

### Research Question
**Can we identify undervalued residential properties in Cyprus by analyzing listing data from multiple sources?**

### Target Users
- First-time home buyers looking for affordable properties
- Real estate investors seeking undervalued opportunities
- Real estate agents wanting market intelligence
- Property sellers wanting to price competitively

---

##  Project Goals

1. **Data Collection**: Scrape property listings from Bazaraki.com
2. **Data Storage**: Store structured data in a relational database
3. **Data Analysis**: Analyze price trends and property characteristics
4. **ML Modeling**: Predict fair market value and identify undervalued properties
5. **Visualization**: Create an interactive dashboard for exploring properties

---

##  Database Service (Database/)

The `Database/` folder contains the Docker configuration for running a MariaDB database used by this project.

### Prerequisites

- **Docker**: [Install Docker](https://www.docker.com/products/docker-desktop)
- **Docker Compose**: Included with Docker Desktop

Verify installation:
```bash
docker --version
docker-compose --version
```

### 1. Start the Database

From the `Database/` directory, run:
```bash
docker-compose -f db.yaml up -d
```
The `-d` flag runs the container in the background (detached mode).

### 2. Verify the Container is Running

```bash
docker ps | grep DataScience-mysql-db
```
You should see something similar to:
```text
DataScience-mysql-db   mariadb:10.2.32   Up (health: starting)   0.0.0.0:3306->3306/tcp
```

### 3. Connect to the Database

#### Option A: Using MySQL CLI
```bash
mysql -h localhost -u DataScience-user -p DataScience
# Password: DataScience_pass_2025
```

#### Option B: Using Python
```python
import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="DataScience-user",
    password="DataScience_pass_2025",
    database="DataScience",
    port=3306,
)
```

#### Option C: Using a SQL client
- Host: `localhost`
- Port: `3306`
- Database: `DataScience`
- User: `DataScience-user`
- Password: `DataScience_pass_2025`

### Database Credentials

| Credential        | Value                   |
|-------------------|-------------------------|
| **Host**          | localhost               |
| **Port**          | 3306                    |
| **Root User**     | root                    |
| **Root Password** | DataScience_root_2025   |
| **Database**      | DataScience             |
| **App User**      | DataScience-user        |
| **App Password**  | DataScience_pass_2025   |

### Container Management

View logs:
```bash
docker logs DataScience-mysql-db
```

Stop the container:
```bash
docker-compose -f db.yaml down
```

Remove the container and data (⚠️ deletes all data):
```bash
docker-compose -f db.yaml down -v
```

Restart the container:
```bash
docker-compose -f db.yaml restart
```

### Health Check

The container includes an automatic health check that:
- Runs every 10 seconds
- Times out after 5 seconds
- Retries up to 5 times before marking the container as unhealthy

View health status:
```bash
docker ps
```

### Data Persistence

Database data is stored in the `mysql_data` volume, so it persists even if the container is stopped.

List volumes:
```bash
docker volume ls | grep mysql_data
```

### Troubleshooting

**Port 3306 already in use**
```bash
# Find what's using port 3306
lsof -i :3306

# Or stop MySQL/MariaDB containers
docker ps | grep -E "mysql|mariadb"
docker stop <container_id>
```

**Connection refused**
Wait a few seconds for the container to fully start, then check logs:
```bash
docker logs DataScience-mysql-db
```

**Container won't start**
```bash
docker-compose -f db.yaml down
docker volume rm data-science-_mysql_data
docker-compose -f db.yaml up -d
```

---

##  Next Steps

1. Ensure the database container is running.
2. Run the property scraper script, for example:
   ```bash
   python bazaraki_scraper.py
   ```
3. When prompted, choose how much data you want to scrape.

