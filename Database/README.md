# DataScience Database Setup

This folder contains the Docker configuration for running a MariaDB database for the data science project.

## Prerequisites

- **Docker**: [Install Docker](https://www.docker.com/products/docker-desktop)
- **Docker Compose**: Included with Docker Desktop

Verify installation:
```bash
docker --version
docker-compose --version
```

## Quick Start

### 1. Start the Database

From this directory (Database/), run:

```bash
docker-compose -f db.yaml up -d
```

The `-d` flag runs the container in the background (detached mode).

### 2. Verify the Container is Running

```bash
docker ps | grep DataScience-mysql-db
```

You should see:
```
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
    host='localhost',
    user='DataScience-user',
    password='DataScience_pass_2025',
    database='DataScience',
    port=3306
)
```

#### Option C: Using your favorite SQL client
- Host: `localhost`
- Port: `3306`
- Database: `DataScience`
- User: `DataScience-user`
- Password: `DataScience_pass_2025`

## Database Credentials

| Credential | Value |
|---|---|
| **Host** | localhost |
| **Port** | 3306 |
| **Root User** | root |
| **Root Password** | DataScience_root_2025 |
| **Database** | DataScience |
| **App User** | DataScience-user |
| **App Password** | DataScience_pass_2025 |

## Container Management

### View Logs
```bash
docker logs DataScience-mysql-db
```

### Stop the Container
```bash
docker-compose -f db.yaml down
```

### Remove the Container and Data
```bash
docker-compose -f db.yaml down -v
```
⚠️ This deletes all data! Use only if you want a fresh start.

### Restart the Container
```bash
docker-compose -f db.yaml restart
```

## Health Check

The container includes an automatic health check that:
- Runs every 10 seconds
- Times out after 5 seconds
- Retries up to 5 times before marking as unhealthy

View health status:
```bash
docker ps
```

## Data Persistence

Database data is stored in the `mysql_data` volume, so it persists even if the container is stopped.

To see all volumes:
```bash
docker volume ls | grep mysql_data
```

## Troubleshooting

### Port 3306 Already in Use
If you get "port is already allocated", find and stop the conflicting container:
```bash
# Find what's using port 3306
lsof -i :3306

# Or stop all MySQL/MariaDB containers
docker ps | grep -E "mysql|mariadb"
docker stop <container_id>
```

### Connection Refused
Wait a few seconds for the container to fully start. Check logs:
```bash
docker logs DataScience-mysql-db
```

### Container Won't Start
Clean up and restart:
```bash
docker-compose -f db.yaml down
docker volume rm data-science-_mysql_data
docker-compose -f db.yaml up -d
```

## Next Steps

1. ✅ Container is running
2. 📊 [Load your scraped data](../data/raw/bazaraki_properties.json) into the database
3. 🔍 Run queries and analysis
