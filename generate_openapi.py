#!/usr/bin/env python3
"""
Generate OpenAPI 3.0 specification for MTAPI
"""

import json
import yaml
from datetime import datetime

def create_openapi_spec():
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "MTA API",
            "description": "Real-time NYC MTA subway, LIRR, and Metro-North data API with unified search capabilities",
            "version": "2.1.0",
            "contact": {
                "name": "MTAPI",
                "url": "https://github.com/jonthornton/MTAPI"
            },
            "license": {
                "name": "BSD",
                "url": "https://github.com/jonthornton/MTAPI/blob/master/LICENSE"
            }
        },
        "servers": [
            {
                "url": "https://api.example.com",
                "description": "Production server"
            }
        ],
        "paths": {},
        "components": {
            "schemas": {
                "Station": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Station ID"},
                        "name": {"type": "string", "description": "Station name"},
                        "location": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "Station coordinates [latitude, longitude]"
                        },
                        "system": {
                            "type": "string",
                            "enum": ["subway", "lirr", "mnr"],
                            "description": "Transit system"
                        },
                        "routes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Routes serving this station"
                        },
                        "stops": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2
                            },
                            "description": "Individual platform/stop coordinates"
                        },
                        "N": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Train"},
                            "description": "Northbound trains"
                        },
                        "S": {
                            "type": "array", 
                            "items": {"$ref": "#/components/schemas/Train"},
                            "description": "Southbound trains"
                        },
                        "hasData": {
                            "type": "boolean",
                            "description": "Whether station has real-time data"
                        },
                        "last_update": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Last update timestamp"
                        }
                    }
                },
                "SearchResult": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Station ID"},
                        "name": {"type": "string", "description": "Station name"},
                        "location": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                            "description": "Station coordinates [latitude, longitude]"
                        },
                        "system": {
                            "type": "string",
                            "enum": ["subway", "lirr", "mnr"],
                            "description": "Transit system"
                        },
                        "distance": {
                            "type": "number",
                            "description": "Distance from search point (location searches only)"
                        }
                    }
                },
                "Train": {
                    "type": "object",
                    "properties": {
                        "route": {"type": "string", "description": "Train route"},
                        "time": {
                            "type": "string",
                            "format": "date-time",
                            "description": "Expected arrival time"
                        }
                    }
                },
                "DataEnvelope": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Station"}
                        },
                        "updated": {
                            "type": "string",
                            "format": "date-time",
                            "nullable": True,
                            "description": "Last update timestamp"
                        }
                    }
                },
                "SearchEnvelope": {
                    "type": "object", 
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/SearchResult"}
                        },
                        "updated": {
                            "type": "string",
                            "format": "date-time",
                            "nullable": True,
                            "description": "Last update timestamp"
                        }
                    }
                },
                "RoutesResponse": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "updated": {
                            "type": "string",
                            "format": "date-time"
                        }
                    }
                },
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string", "description": "Error message"}
                    }
                },
                "OutageResponse": {
                    "type": "object",
                    "properties": {
                        "station": {"type": "string"},
                        "current_outages": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Outage"}
                        },
                        "upcoming_outages": {
                            "type": "array", 
                            "items": {"$ref": "#/components/schemas/Outage"}
                        },
                        "last_updated": {"type": "string", "format": "date-time"}
                    }
                },
                "Outage": {
                    "type": "object",
                    "properties": {
                        "equipment": {"type": "string"},
                        "type": {"type": "string"},
                        "serving": {"type": "string"},
                        "outage_date": {"type": "string"},
                        "estimated_return": {"type": "string"},
                        "reason": {"type": "string"},
                        "ada_accessible": {"type": "boolean"}
                    }
                },
                "AlertResponse": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "service_type": {"type": "string"},
                        "alerts": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Alert"}
                        },
                        "last_updated": {"type": "string", "format": "date-time"}
                    }
                },
                "Alert": {
                    "type": "object",
                    "properties": {
                        "service": {"type": "string"},
                        "header": {"type": "string"},
                        "description": {"type": "string"},
                        "active_period": {"type": "array", "items": {"type": "object"}},
                        "informed_entity": {"type": "array", "items": {"type": "object"}}
                    }
                },
                "RoutePlanResponse": {
                    "type": "object",
                    "properties": {
                        "from_point": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2
                        },
                        "to_point": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2
                        },
                        "options": {
                            "type": "object",
                            "properties": {
                                "subway": {"$ref": "#/components/schemas/RouteOption"},
                                "lirr": {"$ref": "#/components/schemas/RouteOption"},
                                "mnr": {"$ref": "#/components/schemas/RouteOption"}
                            }
                        },
                        "note": {"type": "string"}
                    }
                },
                "RouteOption": {
                    "type": "object",
                    "properties": {
                        "from_stations": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Station"}
                        },
                        "to_stations": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Station"}
                        }
                    }
                }
            },
            "parameters": {
                "SystemFilter": {
                    "name": "system",
                    "in": "query",
                    "description": "Filter by transit system",
                    "required": False,
                    "schema": {
                        "type": "string",
                        "enum": ["all", "subway", "lirr", "mnr"],
                        "default": "all"
                    }
                },
                "SearchQuery": {
                    "name": "q",
                    "in": "query",
                    "description": "Search query - supports multiple keywords",
                    "required": True,
                    "schema": {"type": "string"},
                    "example": "grand central"
                },
                "Latitude": {
                    "name": "lat",
                    "in": "query",
                    "description": "Latitude coordinate",
                    "required": True,
                    "schema": {"type": "number", "format": "double"},
                    "example": 40.7589
                },
                "Longitude": {
                    "name": "lon",
                    "in": "query", 
                    "description": "Longitude coordinate",
                    "required": True,
                    "schema": {"type": "number", "format": "double"},
                    "example": -73.9851
                }
            }
        }
    }

    # Add paths
    spec["paths"] = {
        "/": {
            "get": {
                "summary": "API Information",
                "description": "Get basic API information",
                "responses": {
                    "200": {
                        "description": "API information",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "readme": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/search": {
            "get": {
                "summary": "Search Stations",
                "description": "Search for stations by name with keyword support across multiple transit systems",
                "parameters": [
                    {"$ref": "#/components/parameters/SearchQuery"},
                    {"$ref": "#/components/parameters/SystemFilter"}
                ],
                "responses": {
                    "200": {
                        "description": "Search results",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SearchEnvelope"}
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        },
        "/by-location": {
            "get": {
                "summary": "Find Stations by Location",
                "description": "Find stations near the provided coordinates",
                "parameters": [
                    {"$ref": "#/components/parameters/Latitude"},
                    {"$ref": "#/components/parameters/Longitude"},
                    {
                        "name": "system",
                        "in": "query",
                        "description": "Filter by transit system",
                        "schema": {
                            "type": "string",
                            "enum": ["all", "subway", "lirr", "mnr"],
                            "default": "subway"
                        }
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "description": "Maximum number of results",
                        "schema": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50}
                    },
                    {
                        "name": "radius",
                        "in": "query",
                        "description": "Search radius in degrees",
                        "schema": {"type": "number", "format": "double", "default": 0.01, "minimum": 0.001}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Nearby stations",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DataEnvelope"}
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        },
        "/by-route/{route}": {
            "get": {
                "summary": "Get Stations by Route",
                "description": "Get all stations on the provided train route",
                "parameters": [
                    {
                        "name": "route",
                        "in": "path",
                        "required": True,
                        "description": "Route identifier",
                        "schema": {"type": "string"},
                        "example": "6"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Stations on route",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DataEnvelope"}
                            }
                        }
                    },
                    "404": {
                        "description": "Route not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        },
        "/by-id/{ids}": {
            "get": {
                "summary": "Get Stations by ID",
                "description": "Get stations by their IDs (comma-separated)",
                "parameters": [
                    {
                        "name": "ids",
                        "in": "path",
                        "required": True,
                        "description": "Comma-separated station IDs",
                        "schema": {"type": "string"},
                        "example": "125,A24"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Station data",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DataEnvelope"}
                            }
                        }
                    },
                    "404": {
                        "description": "Station not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        },
        "/routes": {
            "get": {
                "summary": "List Available Routes",
                "description": "Get list of all available subway routes",
                "responses": {
                    "200": {
                        "description": "Available routes",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/RoutesResponse"}
                            }
                        }
                    }
                }
            }
        }
    }

    # Add LIRR endpoints
    lirr_paths = {
        "/lirr/routes": {
            "get": {
                "summary": "Get LIRR Routes",
                "description": "Get all available LIRR routes",
                "tags": ["LIRR"],
                "responses": {
                    "200": {
                        "description": "LIRR routes",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/RoutesResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/lirr/stops": {
            "get": {
                "summary": "Get All LIRR Stops",
                "description": "Get all LIRR stops with real-time data",
                "tags": ["LIRR"],
                "responses": {
                    "200": {
                        "description": "All LIRR stops",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DataEnvelope"}
                            }
                        }
                    }
                }
            }
        },
        "/lirr/by-route/{route}": {
            "get": {
                "summary": "Get LIRR Stops by Route",
                "description": "Get all stops for a specific LIRR route",
                "tags": ["LIRR"],
                "parameters": [
                    {
                        "name": "route",
                        "in": "path",
                        "required": True,
                        "description": "LIRR route identifier",
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "LIRR stops on route",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DataEnvelope"}
                            }
                        }
                    },
                    "404": {
                        "description": "Route not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        },
        "/lirr/by-id/{stop_id}": {
            "get": {
                "summary": "Get LIRR Stop by ID",
                "description": "Get specific LIRR stop information",
                "tags": ["LIRR"],
                "parameters": [
                    {
                        "name": "stop_id",
                        "in": "path",
                        "required": True,
                        "description": "LIRR stop identifier",
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "LIRR stop data",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DataEnvelope"}
                            }
                        }
                    },
                    "404": {
                        "description": "Stop not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        },
        "/lirr/search": {
            "get": {
                "summary": "Search LIRR Stops",
                "description": "Search LIRR stops by name",
                "tags": ["LIRR"],
                "parameters": [
                    {"$ref": "#/components/parameters/SearchQuery"}
                ],
                "responses": {
                    "200": {
                        "description": "LIRR search results",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SearchEnvelope"}
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        },
        "/lirr/by-location": {
            "get": {
                "summary": "Find LIRR Stops by Location",
                "description": "Find nearest LIRR stops to coordinates",
                "tags": ["LIRR"],
                "parameters": [
                    {"$ref": "#/components/parameters/Latitude"},
                    {"$ref": "#/components/parameters/Longitude"}
                ],
                "responses": {
                    "200": {
                        "description": "Nearby LIRR stops",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DataEnvelope"}
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        }
    }

    # Add MNR endpoints (similar structure to LIRR)
    mnr_paths = {
        "/mnr/routes": {
            "get": {
                "summary": "Get MNR Routes",
                "description": "Get all available Metro-North routes",
                "tags": ["MNR"],
                "responses": {
                    "200": {
                        "description": "MNR routes",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/RoutesResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/mnr/stops": {
            "get": {
                "summary": "Get All MNR Stops",
                "description": "Get all Metro-North stops with real-time data",
                "tags": ["MNR"],
                "responses": {
                    "200": {
                        "description": "All MNR stops",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DataEnvelope"}
                            }
                        }
                    }
                }
            }
        },
        "/mnr/by-route/{route}": {
            "get": {
                "summary": "Get MNR Stops by Route",
                "description": "Get all stops for a specific Metro-North route",
                "tags": ["MNR"],
                "parameters": [
                    {
                        "name": "route",
                        "in": "path",
                        "required": True,
                        "description": "MNR route identifier",
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "MNR stops on route",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DataEnvelope"}
                            }
                        }
                    },
                    "404": {
                        "description": "Route not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        },
        "/mnr/by-id/{stop_id}": {
            "get": {
                "summary": "Get MNR Stop by ID",
                "description": "Get specific Metro-North stop information",
                "tags": ["MNR"],
                "parameters": [
                    {
                        "name": "stop_id",
                        "in": "path",
                        "required": True,
                        "description": "MNR stop identifier",
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "MNR stop data",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DataEnvelope"}
                            }
                        }
                    },
                    "404": {
                        "description": "Stop not found",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        },
        "/mnr/search": {
            "get": {
                "summary": "Search MNR Stops",
                "description": "Search Metro-North stops by name",
                "tags": ["MNR"],
                "parameters": [
                    {"$ref": "#/components/parameters/SearchQuery"}
                ],
                "responses": {
                    "200": {
                        "description": "MNR search results",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SearchEnvelope"}
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        },
        "/mnr/by-location": {
            "get": {
                "summary": "Find MNR Stops by Location",
                "description": "Find nearest Metro-North stops to coordinates",
                "tags": ["MNR"],
                "parameters": [
                    {"$ref": "#/components/parameters/Latitude"},
                    {"$ref": "#/components/parameters/Longitude"}
                ],
                "responses": {
                    "200": {
                        "description": "Nearby MNR stops",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DataEnvelope"}
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        }
    }

    # Add utility endpoints
    utility_paths = {
        "/outages/search": {
            "get": {
                "summary": "Search Elevator/Escalator Outages",
                "description": "Find current and upcoming elevator/escalator outages",
                "tags": ["Outages"],
                "parameters": [
                    {
                        "name": "station",
                        "in": "query",
                        "required": True,
                        "description": "Station name (partial match supported)",
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Outage information",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/OutageResponse"}
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        },
        "/alerts/search": {
            "get": {
                "summary": "Search Service Alerts",
                "description": "Search service alerts across transit systems",
                "tags": ["Alerts"],
                "parameters": [
                    {"$ref": "#/components/parameters/SearchQuery"},
                    {
                        "name": "service",
                        "in": "query",
                        "description": "Filter by service type",
                        "schema": {
                            "type": "string",
                            "enum": ["all", "subway", "lirr", "mnr"],
                            "default": "all"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Service alerts",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AlertResponse"}
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        },
        "/route-plan": {
            "get": {
                "summary": "Multi-Modal Route Planning",
                "description": "Basic multi-modal trip planning across subway, LIRR, and MNR",
                "tags": ["Route Planning"],
                "parameters": [
                    {
                        "name": "from_lat",
                        "in": "query",
                        "required": True,
                        "description": "Origin latitude",
                        "schema": {"type": "number", "format": "double"}
                    },
                    {
                        "name": "from_lon",
                        "in": "query",
                        "required": True,
                        "description": "Origin longitude",
                        "schema": {"type": "number", "format": "double"}
                    },
                    {
                        "name": "to_lat",
                        "in": "query",
                        "required": True,
                        "description": "Destination latitude",
                        "schema": {"type": "number", "format": "double"}
                    },
                    {
                        "name": "to_lon",
                        "in": "query",
                        "required": True,
                        "description": "Destination longitude",
                        "schema": {"type": "number", "format": "double"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Route planning suggestions",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/RoutePlanResponse"}
                            }
                        }
                    },
                    "400": {
                        "description": "Bad request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Error"}
                            }
                        }
                    }
                }
            }
        }
    }

    # Merge all paths
    spec["paths"].update(lirr_paths)
    spec["paths"].update(mnr_paths)
    spec["paths"].update(utility_paths)

    # Add tags
    spec["tags"] = [
        {"name": "Subway", "description": "NYC Subway endpoints"},
        {"name": "LIRR", "description": "Long Island Rail Road endpoints"},
        {"name": "MNR", "description": "Metro-North Railroad endpoints"},
        {"name": "Outages", "description": "Elevator and escalator outage information"},
        {"name": "Alerts", "description": "Service alerts and disruptions"},
        {"name": "Route Planning", "description": "Multi-modal trip planning"}
    ]

    return spec

def main():
    spec = create_openapi_spec()
    
    # Generate JSON
    with open('openapi.json', 'w') as f:
        json.dump(spec, f, indent=2, separators=(',', ': '))
    
    # Generate YAML
    with open('openapi.yaml', 'w') as f:
        yaml.dump(spec, f, default_flow_style=False, sort_keys=False)
    
    print("Generated OpenAPI specification:")
    print("- openapi.json")
    print("- openapi.yaml")
    print(f"\nAPI Version: {spec['info']['version']}")
    print(f"Total endpoints: {len(spec['paths'])}")

if __name__ == "__main__":
    main()