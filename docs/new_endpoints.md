# Extended MTA API Endpoints

This document describes the new endpoints added to support LIRR, MNR, outages, alerts, and route planning.

## LIRR Endpoints

### Get LIRR Routes
- **URL:** `/lirr/routes`
- **Method:** GET
- **Description:** Returns all available LIRR routes
- **Response:** List of route IDs with update timestamp

### Get LIRR Stops
- **URL:** `/lirr/stops`  
- **Method:** GET
- **Description:** Returns all LIRR stops with real-time train data
- **Response:** Array of stop objects with trains, locations, etc.

### Get LIRR Stops by Route
- **URL:** `/lirr/by-route/<route_id>`
- **Method:** GET
- **Description:** Returns all stops for a specific LIRR route
- **Parameters:** `route_id` - LIRR route identifier (1-12)
- **Response:** Array of stops on the specified route

### Get LIRR Stop by ID
- **URL:** `/lirr/by-id/<stop_id>`
- **Method:** GET
- **Description:** Returns specific LIRR stop information
- **Parameters:** `stop_id` - LIRR stop identifier
- **Response:** Stop data with real-time arrivals

### Search LIRR Stops
- **URL:** `/lirr/search?q=<query>`
- **Method:** GET
- **Description:** Search LIRR stops by name
- **Parameters:** `q` - Search query string
- **Response:** Array of matching stops

### Get LIRR Stops by Location
- **URL:** `/lirr/by-location?lat=<lat>&lon=<lon>`
- **Method:** GET
- **Description:** Find nearest LIRR stops to coordinates
- **Parameters:** `lat`, `lon` - GPS coordinates
- **Response:** Array of nearby stops sorted by distance

## MNR Endpoints

### Get MNR Routes
- **URL:** `/mnr/routes`
- **Method:** GET
- **Description:** Returns all available Metro-North routes
- **Response:** List of route IDs with update timestamp

### Get MNR Stops
- **URL:** `/mnr/stops`
- **Method:** GET  
- **Description:** Returns all MNR stops with real-time train data
- **Response:** Array of stop objects with trains, locations, etc.

### Get MNR Stops by Route
- **URL:** `/mnr/by-route/<route_id>`
- **Method:** GET
- **Description:** Returns all stops for a specific MNR route
- **Parameters:** `route_id` - MNR route identifier
- **Response:** Array of stops on the specified route

### Get MNR Stop by ID
- **URL:** `/mnr/by-id/<stop_id>`
- **Method:** GET
- **Description:** Returns specific MNR stop information
- **Parameters:** `stop_id` - MNR stop identifier
- **Response:** Stop data with real-time arrivals

### Search MNR Stops
- **URL:** `/mnr/search?q=<query>`
- **Method:** GET
- **Description:** Search MNR stops by name
- **Parameters:** `q` - Search query string
- **Response:** Array of matching stops

### Get MNR Stops by Location  
- **URL:** `/mnr/by-location?lat=<lat>&lon=<lon>`
- **Method:** GET
- **Description:** Find nearest MNR stops to coordinates
- **Parameters:** `lat`, `lon` - GPS coordinates
- **Response:** Array of nearby stops sorted by distance

## Outage Endpoints

### Search Elevator/Escalator Outages
- **URL:** `/outages/search?station=<station_name>`
- **Method:** GET
- **Description:** Find current and upcoming elevator/escalator outages at a station
- **Parameters:** `station` - Station name (partial match supported)
- **Response:** Object with current_outages, upcoming_outages arrays and metadata

Example response:
```json
{
  "station": "union square",
  "current_outages": [
    {
      "equipment": "ES123",
      "type": "ES",
      "serving": "Platform to mezzanine",
      "outage_date": "01/15/2024 09:00:00 AM",
      "estimated_return": "02/01/2024 11:59:00 PM", 
      "reason": "Capital Replacement",
      "ada_accessible": false
    }
  ],
  "upcoming_outages": [],
  "last_updated": "2024-01-20T10:30:00"
}
```

## Alert Endpoints

### Search Service Alerts
- **URL:** `/alerts/search?q=<query>&service=<service_type>`
- **Method:** GET
- **Description:** Search service alerts across subway, LIRR, and MNR
- **Parameters:** 
  - `q` - Search query (required)
  - `service` - Filter by service type: 'all', 'subway', 'lirr', 'mnr' (optional, defaults to 'all')
- **Response:** Object with matching alerts

Example response:
```json
{
  "query": "delay",
  "service_type": "all",
  "alerts": [
    {
      "service": "subway",
      "header": "Service Change: A trains delayed",
      "description": "A trains are delayed due to signal problems...",
      "active_period": [...],
      "informed_entity": [...]
    }
  ],
  "last_updated": "2024-01-20T10:30:00"
}
```

## Route Planning Endpoint

### Multi-Modal Route Planning
- **URL:** `/route-plan?from_lat=<lat>&from_lon=<lon>&to_lat=<lat>&to_lon=<lon>`
- **Method:** GET
- **Description:** Basic multi-modal trip planning across subway, LIRR, and MNR
- **Parameters:** 
  - `from_lat`, `from_lon` - Origin coordinates
  - `to_lat`, `to_lon` - Destination coordinates
- **Response:** Object with nearest stops for each service type

Example response:
```json
{
  "from_point": [40.7589, -73.9851],
  "to_point": [40.6892, -73.9442],
  "options": {
    "subway": {
      "from_stations": [...],
      "to_stations": [...]
    },
    "lirr": {
      "from_stations": [...], 
      "to_stations": [...]
    },
    "mnr": {
      "from_stations": [...],
      "to_stations": [...]
    }
  },
  "note": "This is a basic proximity-based route suggestion. For detailed routing, use dedicated trip planning services."
}
```

## Data Sources

- **LIRR Real-time:** `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/lirr%2Fgtfs-lirr`
- **MNR Real-time:** `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/mnr%2Fgtfs-mnr`
- **Outages:** 
  - Current: `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene.json`
  - Upcoming: `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene_upcoming.json`
  - Equipment: `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fnyct_ene_equipments.json`
- **Alerts:**
  - Subway: `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts.json`
  - LIRR: `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Flirr-alerts.json`
  - MNR: `https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fmnr-alerts.json`

## Cache Policy

- Real-time data (trains, outages, alerts): 5 minutes default
- Static data (stops, routes): Loaded at startup
- API responses include `updated` timestamp when applicable

## Error Responses

All endpoints return appropriate HTTP status codes:
- 400: Bad Request (missing/invalid parameters)
- 404: Not Found (invalid stop/route ID)  
- 500: Internal Server Error

Error responses include JSON with `error` field describing the issue.