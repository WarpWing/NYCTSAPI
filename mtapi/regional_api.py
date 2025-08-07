import json
import csv
import datetime
import os
from collections import defaultdict
from itertools import islice
import threading
import logging
import urllib.request, urllib.error, contextlib
import google.protobuf.message
from mtaproto.feedresponse import FeedResponse, Trip, TripStop, TZ
from operator import itemgetter

logger = logging.getLogger(__name__)

def distance(p1, p2):
    import math
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

def format_time_readable(dt):
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    return dt.strftime('%I:%M %p')

class RegionalAPI:
    
    def __init__(self, key, gtfs_dir, feed_url, expires_seconds=60, max_trains=10, max_minutes=30):
        self._KEY = key
        self._GTFS_DIR = gtfs_dir
        self._FEED_URL = feed_url
        self._MAX_TRAINS = max_trains
        self._MAX_MINUTES = max_minutes
        self._EXPIRES_SECONDS = expires_seconds
        self._read_lock = threading.RLock()
        
        self._routes = {}
        self._stops = {}
        self._trips = {}
        self._stop_times = {}
        self._last_update = None
        
        self._load_static_data()
    
    def _load_static_data(self):
        routes_file = os.path.join(self._GTFS_DIR, 'routes.txt')
        if os.path.exists(routes_file):
            with open(routes_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self._routes[row['route_id']] = row
        
        stops_file = os.path.join(self._GTFS_DIR, 'stops.txt')
        if os.path.exists(stops_file):
            with open(stops_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self._stops[row['stop_id']] = {
                        'id': row['stop_id'],
                        'name': row['stop_name'],
                        'location': [float(row['stop_lat']), float(row['stop_lon'])],
                        'url': row.get('stop_url', ''),
                        'code': row.get('stop_code', ''),
                        'wheelchair_boarding': row.get('wheelchair_boarding', '0')
                    }
        
        trips_file = os.path.join(self._GTFS_DIR, 'trips.txt')
        if os.path.exists(trips_file):
            with open(trips_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self._trips[row['trip_id']] = row
        
        logger.info(f"Loaded {len(self._routes)} routes, {len(self._stops)} stops, {len(self._trips)} trips")
    
    def _load_feed(self):
        try:
            request = urllib.request.Request(self._FEED_URL)
            if self._KEY and self._KEY != 'your-mta-key-here':
                request.add_header('x-api-key', self._KEY)
            with contextlib.closing(urllib.request.urlopen(request)) as r:
                data = r.read()
                return FeedResponse(data)
        except (urllib.error.URLError, google.protobuf.message.DecodeError, ConnectionResetError) as e:
            logger.error(f'Couldn\'t connect to feed: {str(e)}')
            return None
    
    def _update(self):
        logger.info('updating regional feed...')
        self._last_update = datetime.datetime.now(TZ)
        
        for stop_id in self._stops:
            self._stops[stop_id]['trains'] = {'N': [], 'S': []}
            self._stops[stop_id]['last_update'] = None
        
        feed_data = self._load_feed()
        if not feed_data:
            return
        
        max_time = self._last_update + datetime.timedelta(minutes=self._MAX_MINUTES)
        
        for entity in feed_data.entity:
            if not entity.HasField('trip_update'):
                continue
                
            trip = Trip(entity)
            if not trip.is_valid():
                continue
            
            trip_id = entity.trip_update.trip.trip_id
                
            route_id = self._trips.get(trip_id, {}).get('route_id', 'Unknown')
            
            if route_id == 'Unknown' and hasattr(entity.trip_update.trip, 'route_id'):
                route_id = entity.trip_update.trip.route_id
            
            if route_id in self._routes:
                route_name = self._routes[route_id].get('route_long_name', route_id)
            else:
                route_name = route_id
            
            all_stops_in_trip = []
            for update in entity.trip_update.stop_time_update:
                all_stops_in_trip.append(update.stop_id)
            
            trip_stops = {}
            for update in entity.trip_update.stop_time_update:
                stop_id = update.stop_id
                departure_time = None
                arrival_time = None
                
                if update.HasField('departure'):
                    departure_time = datetime.datetime.fromtimestamp(update.departure.time, TZ)
                if update.HasField('arrival'):
                    arrival_time = datetime.datetime.fromtimestamp(update.arrival.time, TZ)
                
                trip_stops[stop_id] = {
                    'departure_time': departure_time,
                    'arrival_time': arrival_time
                }
            
            for update in entity.trip_update.stop_time_update:
                stop_id = update.stop_id
                
                if stop_id not in self._stops:
                    continue
                
                departure_time = None
                arrival_time = None
                
                if update.HasField('departure'):
                    departure_time = datetime.datetime.fromtimestamp(update.departure.time, TZ)
                if update.HasField('arrival'):
                    arrival_time = datetime.datetime.fromtimestamp(update.arrival.time, TZ)
                
                train_time = departure_time or arrival_time
                if not train_time or train_time < self._last_update or train_time > max_time:
                    continue
                
                direction = self._determine_direction(stop_id, all_stops_in_trip)
                
                if 'trains' not in self._stops[stop_id]:
                    self._stops[stop_id]['trains'] = {'N': [], 'S': []}
                
                train_data = {
                    'route': route_id,
                    'route_name': route_name,
                    'time': train_time,
                    'trip_id': trip_id
                }
                
                if departure_time:
                    train_data['departure_time'] = departure_time
                    train_data['departure_time_formatted'] = format_time_readable(departure_time)
                if arrival_time:
                    train_data['arrival_time'] = arrival_time
                    train_data['arrival_time_formatted'] = format_time_readable(arrival_time)
                
                if '1' in trip_stops:
                    gc_times = trip_stops['1']
                    if gc_times['departure_time']:
                        train_data['origin_departure'] = gc_times['departure_time']
                        train_data['origin_departure_formatted'] = format_time_readable(gc_times['departure_time'])
                        train_data['origin_station'] = 'Grand Central'
                
                if '4' in trip_stops:
                    harlem_times = trip_stops['4']
                    if harlem_times['departure_time']:
                        train_data['harlem_departure'] = harlem_times['departure_time']
                        train_data['harlem_departure_formatted'] = format_time_readable(harlem_times['departure_time'])
                        train_data['harlem_station'] = 'Harlem-125 St'
                
                self._stops[stop_id]['trains'][direction].append(train_data)
                self._stops[stop_id]['last_update'] = feed_data.timestamp
        
        for stop_id in self._stops:
            if 'trains' in self._stops[stop_id]:
                for direction in ['N', 'S']:
                    trains = self._stops[stop_id]['trains'][direction]
                    trains.sort(key=lambda x: x['time'])
                    self._stops[stop_id]['trains'][direction] = trains[:self._MAX_TRAINS]
    
    def _determine_direction(self, current_stop, all_stops):
        if '1' in all_stops:
            try:
                current_idx = all_stops.index(current_stop)
                gc_idx = all_stops.index('1')
                if gc_idx > current_idx:
                    return 'S'
                else:
                    return 'N'
            except ValueError:
                pass
        return 'N'
    
    def is_expired(self):
        if not self._last_update:
            return True
        if self._EXPIRES_SECONDS:
            age = datetime.datetime.now(TZ) - self._last_update
            return age.total_seconds() > self._EXPIRES_SECONDS
        return False
    
    def get_routes(self):
        return list(self._routes.keys())
    
    def get_stops(self):
        return list(self._stops.values())
    
    def get_stop_by_id(self, stop_id):
        if self.is_expired():
            self._update()
        
        with self._read_lock:
            if stop_id in self._stops:
                stop_data = self._stops[stop_id].copy()
                return stop_data
        return None
    
    def get_stops_by_route(self, route_id):
        if self.is_expired():
            self._update()
        
        with self._read_lock:
            route_stops = []
            for stop_id, stop_data in self._stops.items():
                if 'trains' in stop_data:
                    for direction in ['N', 'S']:
                        for train in stop_data['trains'][direction]:
                            if train['route'] == route_id:
                                if stop_data not in route_stops:
                                    route_stops.append(stop_data)
                                break
            return sorted(route_stops, key=lambda x: x['name'])
    
    def search_stops(self, query):
        query = query.lower().strip()
        if not query:
            return []
        
        matches = []
        for stop_id, stop_data in self._stops.items():
            if query in stop_data['name'].lower():
                matches.append({
                    'id': stop_data['id'],
                    'name': stop_data['name'],
                    'location': stop_data['location'],
                    'code': stop_data.get('code', '')
                })
        
        return sorted(matches, key=lambda x: x['name'])
    
    def get_by_location(self, point, limit=5):
        if self.is_expired():
            self._update()
        
        with self._read_lock:
            stops_with_distance = []
            for stop_data in self._stops.values():
                dist = distance(stop_data['location'], point)
                stops_with_distance.append((stop_data, dist))
            
            stops_with_distance.sort(key=lambda x: x[1])
            return [stop[0] for stop in stops_with_distance[:limit]]
    
    def last_update(self):
        return self._last_update


class LIRRApi(RegionalAPI):
    
    def __init__(self, key, expires_seconds=60, max_trains=10, max_minutes=30):
        super().__init__(
            key=key,
            gtfs_dir='data/lirr',
            feed_url='https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/lirr%2Fgtfs-lirr',
            expires_seconds=expires_seconds,
            max_trains=max_trains,
            max_minutes=max_minutes
        )


class MNRApi(RegionalAPI):
    
    def __init__(self, key, expires_seconds=60, max_trains=10, max_minutes=30):
        super().__init__(
            key=key,
            gtfs_dir='data/mnr',
            feed_url='https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/mnr%2Fgtfs-mnr',
            expires_seconds=expires_seconds,
            max_trains=max_trains,
            max_minutes=max_minutes
        )


class OutageAPI:
    
    def __init__(self, data_dir='data/outages'):
        self._data_dir = data_dir
        self._outages = []
        self._equipment = []
        self._upcoming = []
        self._last_update = None
        
    def _load_outage_data(self):
        try:
            outages_file = os.path.join(self._data_dir, 'nyct_ene.json')
            if os.path.exists(outages_file):
                with open(outages_file, 'r') as f:
                    self._outages = json.load(f)
            
            equipment_file = os.path.join(self._data_dir, 'nyct_ene_equipments.json')
            if os.path.exists(equipment_file):
                with open(equipment_file, 'r') as f:
                    self._equipment = json.load(f)
            
            upcoming_file = os.path.join(self._data_dir, 'nyct_ene_upcoming.json')
            if os.path.exists(upcoming_file):
                with open(upcoming_file, 'r') as f:
                    self._upcoming = json.load(f)
            
            self._last_update = datetime.datetime.now()
            logger.info(f"Loaded {len(self._outages)} outages, {len(self._equipment)} equipment, {len(self._upcoming)} upcoming")
            
        except Exception as e:
            logger.error(f"Error loading outage data: {e}")
    
    def search_outages(self, station_name):
        if not self._last_update or (datetime.datetime.now() - self._last_update).total_seconds() > 300:
            self._load_outage_data()
        
        station_name = station_name.lower()
        results = {
            'station': station_name,
            'current_outages': [],
            'upcoming_outages': [],
            'last_updated': self._last_update.isoformat() if self._last_update else None
        }
        
        for outage in self._outages:
            if station_name in outage.get('station', '').lower():
                results['current_outages'].append({
                    'equipment': outage.get('equipment', ''),
                    'type': outage.get('equipmenttype', ''),
                    'serving': outage.get('serving', ''),
                    'outage_date': outage.get('outagedate', ''),
                    'estimated_return': outage.get('estimatedreturntoservice', ''),
                    'reason': outage.get('reason', ''),
                    'ada_accessible': outage.get('ADA', 'N') == 'Y'
                })
        
        for outage in self._upcoming:
            if station_name in outage.get('station', '').lower():
                results['upcoming_outages'].append({
                    'equipment': outage.get('equipment', ''),
                    'type': outage.get('equipmenttype', ''),
                    'serving': outage.get('serving', ''),
                    'outage_date': outage.get('outagedate', ''),
                    'estimated_return': outage.get('estimatedreturntoservice', ''),
                    'reason': outage.get('reason', ''),
                    'ada_accessible': outage.get('ADA', 'N') == 'Y'
                })
        
        return results


class AlertAPI:
    
    def __init__(self, data_dir='data/alerts'):
        self._data_dir = data_dir
        self._subway_alerts = []
        self._lirr_alerts = []
        self._mnr_alerts = []
        self._last_update = None
    
    def _load_alert_data(self):
        try:
            subway_file = os.path.join(self._data_dir, 'subway-alerts.json')
            if os.path.exists(subway_file):
                with open(subway_file, 'r') as f:
                    data = json.load(f)
                    self._subway_alerts = data.get('entity', [])
            
            lirr_file = os.path.join(self._data_dir, 'lirr-alerts.json')
            if os.path.exists(lirr_file):
                with open(lirr_file, 'r') as f:
                    data = json.load(f)
                    self._lirr_alerts = data.get('entity', [])
            
            mnr_file = os.path.join(self._data_dir, 'mnr-alerts.json')  
            if os.path.exists(mnr_file):
                with open(mnr_file, 'r') as f:
                    data = json.load(f)
                    self._mnr_alerts = data.get('entity', [])
            
            self._last_update = datetime.datetime.now()
            logger.info(f"Loaded {len(self._subway_alerts)} subway, {len(self._lirr_alerts)} LIRR, {len(self._mnr_alerts)} MNR alerts")
            
        except Exception as e:
            logger.error(f"Error loading alert data: {e}")
    
    def search_alerts(self, query, service_type='all'):
        if not self._last_update or (datetime.datetime.now() - self._last_update).total_seconds() > 300:
            self._load_alert_data()
        
        query = query.lower()
        results = {
            'query': query,
            'service_type': service_type,
            'alerts': [],
            'last_updated': self._last_update.isoformat() if self._last_update else None
        }
        
        alerts_to_search = []
        if service_type == 'all' or service_type == 'subway':
            alerts_to_search.extend([('subway', alert) for alert in self._subway_alerts])
        if service_type == 'all' or service_type == 'lirr':
            alerts_to_search.extend([('lirr', alert) for alert in self._lirr_alerts])
        if service_type == 'all' or service_type == 'mnr':
            alerts_to_search.extend([('mnr', alert) for alert in self._mnr_alerts])
        
        for service, alert in alerts_to_search:
            if 'alert' in alert:
                alert_data = alert['alert']
                header = alert_data.get('header_text', {}).get('translation', [{}])[0].get('text', '')
                description = alert_data.get('description_text', {}).get('translation', [{}])[0].get('text', '')
                
                if query in header.lower() or query in description.lower():
                    results['alerts'].append({
                        'service': service,
                        'header': header,
                        'description': description,
                        'active_period': alert_data.get('active_period', []),
                        'informed_entity': alert_data.get('informed_entity', [])
                    })
        
        return results