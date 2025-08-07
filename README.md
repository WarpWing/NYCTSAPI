g MTA API - Multi-Modal Realtime Transit Data

MTAPI is a comprehensive HTTP server that provides realtime transit data for NYC Subway, LIRR (Long Island Rail Road), and Metro-North Railroad (MNR). The API converts MTA's Protocol Buffer feeds to JSON, now with MNR and LIRR search, outages, alerts and more!

**Massive credit and thanks to [Jon Thornton](https://github.com/jonthornton) for the original MTAPI project.** This fork builds upon his excellent foundation to add multi-modal support and advanced search features. Original project: https://github.com/jonthornton/MTAPI


## Prerequisites

Before installing, ensure you have:

- Python 3.7 or higher
- pip (Python package installer)
- Git (for cloning the repository)

### System Dependencies

Install required system packages:

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git
```

**macOS:**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python3 git
```

**Windows:**
- Download Python 3.7+ from https://python.org/downloads/
- Install Git from https://git-scm.com/download/win

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/MTAPI.git
cd MTAPI
```

### 2. Set Up Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Download Required Data Files

The API requires GTFS data files for LIRR and MNR. Download these files:

**LIRR Data:**
```bash
mkdir -p data/lirr
cd data/lirr
curl -O https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/lirr%2Fgtfs.zip
unzip gtfs.zip
cd ../..
```

**MNR Data:**
```bash
mkdir -p data/mnr  
cd data/mnr
curl -O https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/mnr%2Fgtfs.zip
unzip gtfs.zip
cd ../..
```

### 5. Generate Station Files

Generate station JSON files for all systems:

```bash
# Generate MNR stations
python3 scripts/make_mnr_stations.py > data/mnr-stations.json

# Generate LIRR stations
python3 scripts/make_lirr_stations.py > data/lirr-stations.json

# Generate subway stations (if you don't have stations.json)
python3 scripts/make_stations_csv.py data/gtfs/stops.txt data/gtfs/transfers.txt > data/stations.csv
python3 scripts/make_stations_json.py data/stations.csv > data/stations.json
```

### 6. Configuration

Create a `settings.cfg` file (copy from `settings.cfg.sample`):

```ini
MTA_KEY = your_mta_api_key_here
STATIONS_FILE = data/stations.json
DEBUG = False
THREADED = True
MAX_TRAINS = 10
MAX_MINUTES = 30
CACHE_SECONDS = 60
```

Get your MTA API key from: https://api.mta.info/

## Running the Server

### Development
```bash
python app.py
```
The API will be available at http://localhost:5000

### Production

For production deployment, use a WSGI server:

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## API Documentation

### Core Endpoints

**Search Stations (Multi-System)**
```
GET /search?q=grand+central&system=all
```
- `q`: Search query (supports multiple keywords)
- `system`: Filter by `all`, `subway`, `lirr`, `mnr`

**Find Stations by Location**
```
GET /by-location?lat=40.7589&lon=-73.9851&system=all&limit=5
```
- `lat`, `lon`: GPS coordinates
- `system`: System filter
- `limit`: Max results
- `radius`: Search radius in degrees

**Get Station by ID**
```
GET /by-id/125,A24
```
Returns stations by comma-separated IDs (supports parent ID lookup)

### System-Specific Endpoints

**Subway**
- `/routes` - List routes
- `/by-route/6` - Stations on route 6

**LIRR**
- `/lirr/routes` - LIRR routes
- `/lirr/stops` - All LIRR stops
- `/lirr/by-route/1` - Stops on LIRR route
- `/lirr/search?q=jamaica` - Search LIRR stops

**Metro-North**
- `/mnr/routes` - MNR routes
- `/mnr/stops` - All MNR stops
- `/mnr/by-route/1` - Stops on MNR route
- `/mnr/search?q=stamford` - Search MNR stops

### Utility Endpoints

**Outages**
```
GET /outages/search?station=union+square
```

**Service Alerts**
```
GET /alerts/search?q=delay&service=all
```

**Route Planning**
```
GET /route-plan?from_lat=40.7589&from_lon=-73.9851&to_lat=40.6892&to_lon=-73.9442
```

## OpenAPI Specification

Generate API documentation:

```bash
python3 generate_openapi.py
```

This creates `openapi.json` and `openapi.yaml` files compatible with Swagger UI and other OpenAPI tools.

## Configuration Options

- **MTA_KEY**: Your MTA API key (required)
- **STATIONS_FILE**: Path to subway stations JSON file (required)
- **CROSS_ORIGIN**: CORS headers (`*` for development)
- **MAX_TRAINS**: Maximum trains per station (default: 10)
- **MAX_MINUTES**: How far ahead to show arrivals (default: 30)
- **CACHE_SECONDS**: Data refresh interval (default: 60)
- **THREADED**: Enable background refresh (default: True)
- **DEBUG**: Flask debug mode (default: False)

## Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Download and process GTFS data
RUN ./scripts/setup-data.sh

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## Development

### Adding New Features

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Submit a pull request

### Testing

```bash
python -m pytest tests/
```

## Data Sources

- **Subway Real-time**: MTA GTFS-Realtime feeds
- **LIRR Real-time**: `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/lirr%2Fgtfs-lirr`
- **MNR Real-time**: `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/mnr%2Fgtfs-mnr`
- **Outages**: MTA Elevator/Escalator status feeds
- **Alerts**: MTA Service alert feeds

## Performance Considerations

- API responses are cached for 60 seconds by default
- Multi-system searches may take slightly longer than single-system
- Use the `limit` parameter to control response sizes
- Enable `THREADED` mode for production to prevent blocking

## Contributing

Contributions are welcome! Please read the contributing guidelines and submit pull requests to improve the API.

### Areas for Improvement

- Additional transit systems (buses, ferry)
- GraphQL support
- WebSocket real-time updates


## Acknowledgments

- **Jon Thornton**: Original MTAPI creator and maintainer (https://github.com/jonthornton/MTAPI)
- **MTA**: For providing comprehensive real-time transit data APIs
- **GTFS Community**: For transit data standards and tools
- **Contributors**: Everyone who has contributed to making transit data more accessible

