import json
import re
from typing import List, Dict, Any

class UnifiedStationSearch:
    def __init__(self, subway_stations_file: str, mnr_stations_file: str, lirr_stations_file: str):
        self.stations = {}
        self._load_stations(subway_stations_file, 'subway')
        self._load_stations(mnr_stations_file, 'mnr')
        self._load_stations(lirr_stations_file, 'lirr')
        
    def _load_stations(self, stations_file: str, system: str):
        try:
            with open(stations_file, 'r') as f:
                data = json.load(f)
                for station_id, station_data in data.items():
                    # Make a copy to avoid modifying the original
                    station_copy = dict(station_data)
                    # Ensure system is set
                    station_copy['system'] = system
                    # Create a unique key by prefixing with system
                    key = f"{system}:{station_id}"
                    self.stations[key] = station_copy
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load {stations_file} for {system}: {e}")
    
    def search_stations(self, query: str, system_filter: str = 'all') -> List[Dict[str, Any]]:
        query = query.lower().strip()
        if not query:
            return []
        
        # Split query into keywords for more flexible matching
        keywords = query.split()
        matches = []
        
        for station_key, station in self.stations.items():
            # Skip if system filter is applied and doesn't match
            if system_filter != 'all' and station.get('system', 'subway') != system_filter:
                continue
                
            station_name = station['name'].lower()
            
            # Check for exact substring match (existing behavior)
            if query in station_name:
                matches.append(self._format_station_result(station))
                continue
            
            # Check for keyword matching - all keywords must match
            if len(keywords) > 1:
                if all(keyword in station_name for keyword in keywords):
                    matches.append(self._format_station_result(station))
                    continue
            
            # Check for partial word matching (e.g., "grand" matches "Grand Central")
            words = station_name.split()
            for keyword in keywords:
                if any(word.startswith(keyword) for word in words):
                    matches.append(self._format_station_result(station))
                    break
        
        # Sort matches: exact matches first, then by name
        def sort_key(match):
            name = match['name'].lower()
            if name == query:
                return (0, name)
            elif query in name:
                return (1, name)
            else:
                return (2, name)
        
        matches.sort(key=sort_key)
        return matches[:50]  # Limit to 50 results
    
    def _format_station_result(self, station: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'id': station['id'],
            'name': station['name'],
            'location': station['location'],
            'system': station.get('system', 'subway')
        }
    
    def get_by_id(self, station_id: str, system: str = None) -> Dict[str, Any]:
        # Try different system prefixes if system is not specified
        if system:
            key = f"{system}:{station_id}"
            return self.stations.get(key)
        else:
            # Try all systems
            for sys in ['subway', 'mnr', 'lirr']:
                key = f"{sys}:{station_id}"
                if key in self.stations:
                    return self.stations[key]
        return None
    
    def search_by_location(self, lat: float, lon: float, radius: float = 0.01, limit: int = 10) -> List[Dict[str, Any]]:
        matches = []
        
        for station_key, station in self.stations.items():
            station_lat, station_lon = station['location']
            # Simple distance calculation (not great circle, but fine for small distances)
            distance = ((lat - station_lat) ** 2 + (lon - station_lon) ** 2) ** 0.5
            
            if distance <= radius:
                result = self._format_station_result(station)
                result['distance'] = distance
                matches.append(result)
        
        # Sort by distance
        matches.sort(key=lambda x: x['distance'])
        return matches[:limit]