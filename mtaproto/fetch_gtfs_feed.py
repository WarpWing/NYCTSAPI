#!/usr/bin/env python3

import requests
import json
import csv
import argparse
from datetime import datetime
from mtaproto.gtfs_realtime_pb2 import FeedMessage

def fetch_gtfs_feed(url):
    """Fetch GTFS-RT feed from MTA API endpoint"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        print(f"Error fetching feed: {e}")
        return None

def parse_feed_to_dict(feed_data):
    """Parse protobuf feed data to dictionary"""
    feed = FeedMessage()
    feed.ParseFromString(feed_data)
    
    feed_dict = {
        'header': {
            'gtfs_realtime_version': feed.header.gtfs_realtime_version,
            'incrementality': feed.header.incrementality,
            'timestamp': feed.header.timestamp
        },
        'entities': []
    }
    
    for entity in feed.entity:
        entity_dict = {'id': entity.id}
        
        if entity.HasField('trip_update'):
            trip_update = entity.trip_update
            entity_dict['trip_update'] = {
                'trip': {
                    'trip_id': trip_update.trip.trip_id,
                    'route_id': trip_update.trip.route_id,
                    'direction_id': trip_update.trip.direction_id,
                    'start_time': trip_update.trip.start_time,
                    'start_date': trip_update.trip.start_date
                },
                'stop_time_updates': []
            }
            
            for stu in trip_update.stop_time_update:
                stu_dict = {
                    'stop_sequence': stu.stop_sequence,
                    'stop_id': stu.stop_id
                }
                if stu.HasField('arrival'):
                    stu_dict['arrival_time'] = stu.arrival.time
                    stu_dict['arrival_delay'] = stu.arrival.delay
                if stu.HasField('departure'):
                    stu_dict['departure_time'] = stu.departure.time
                    stu_dict['departure_delay'] = stu.departure.delay
                
                entity_dict['trip_update']['stop_time_updates'].append(stu_dict)
        
        if entity.HasField('vehicle'):
            vehicle = entity.vehicle
            entity_dict['vehicle'] = {
                'trip': {
                    'trip_id': vehicle.trip.trip_id,
                    'route_id': vehicle.trip.route_id,
                    'direction_id': vehicle.trip.direction_id,
                    'start_time': vehicle.trip.start_time,
                    'start_date': vehicle.trip.start_date
                },
                'position': {
                    'latitude': vehicle.position.latitude,
                    'longitude': vehicle.position.longitude,
                    'bearing': vehicle.position.bearing,
                    'speed': vehicle.position.speed
                },
                'current_stop_sequence': vehicle.current_stop_sequence,
                'stop_id': vehicle.stop_id,
                'current_status': vehicle.current_status,
                'timestamp': vehicle.timestamp,
                'congestion_level': vehicle.congestion_level,
                'occupancy_status': vehicle.occupancy_status
            }
        
        if entity.HasField('alert'):
            alert = entity.alert
            entity_dict['alert'] = {
                'active_period': [{'start': ap.start, 'end': ap.end} for ap in alert.active_period],
                'informed_entity': [{'route_id': ie.route_id, 'stop_id': ie.stop_id} for ie in alert.informed_entity],
                'cause': alert.cause,
                'effect': alert.effect,
                'url': [{'translation': [{'text': t.text, 'language': t.language} for t in url.translation]} for url in alert.url.translation] if alert.url else [],
                'header_text': [{'translation': [{'text': t.text, 'language': t.language} for t in ht.translation]} for ht in alert.header_text],
                'description_text': [{'translation': [{'text': t.text, 'language': t.language} for t in dt.translation]} for dt in alert.description_text]
            }
        
        feed_dict['entities'].append(entity_dict)
    
    return feed_dict

def save_to_json(data, filename):
    """Save data to JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Data saved to {filename}")

def save_to_csv(data, filename):
    """Save data to CSV file (flattened structure)"""
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write header info
        writer.writerow(['Feed Header Info'])
        writer.writerow(['GTFS Realtime Version', data['header']['gtfs_realtime_version']])
        writer.writerow(['Incrementality', data['header']['incrementality']])
        writer.writerow(['Timestamp', datetime.fromtimestamp(data['header']['timestamp']).isoformat()])
        writer.writerow([])
        
        # Write entities
        writer.writerow(['Entity ID', 'Type', 'Trip ID', 'Route ID', 'Stop ID', 'Arrival Time', 'Departure Time', 'Latitude', 'Longitude', 'Additional Info'])
        
        for entity in data['entities']:
            entity_id = entity['id']
            
            if 'trip_update' in entity:
                trip = entity['trip_update']['trip']
                for stu in entity['trip_update']['stop_time_updates']:
                    arrival_time = datetime.fromtimestamp(stu['arrival_time']).isoformat() if 'arrival_time' in stu else ''
                    departure_time = datetime.fromtimestamp(stu['departure_time']).isoformat() if 'departure_time' in stu else ''
                    writer.writerow([
                        entity_id, 'trip_update', trip['trip_id'], trip['route_id'], 
                        stu['stop_id'], arrival_time, departure_time, '', '', 
                        f"Stop Sequence: {stu['stop_sequence']}"
                    ])
            
            if 'vehicle' in entity:
                vehicle = entity['vehicle']
                writer.writerow([
                    entity_id, 'vehicle', vehicle['trip']['trip_id'], vehicle['trip']['route_id'],
                    vehicle['stop_id'], '', '', vehicle['position']['latitude'], 
                    vehicle['position']['longitude'], f"Status: {vehicle['current_status']}"
                ])
            
            if 'alert' in entity:
                alert = entity['alert']
                writer.writerow([
                    entity_id, 'alert', '', '', '', '', '', '', '', 
                    f"Cause: {alert['cause']}, Effect: {alert['effect']}"
                ])
    
    print(f"Data saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Fetch MTA GTFS-RT feed and export to CSV or JSON')
    parser.add_argument('--format', choices=['json', 'csv', 'both'], default='both', 
                       help='Output format (default: both)')
    parser.add_argument('--output', default='mta_feed', 
                       help='Output filename prefix (default: mta_feed)')
    parser.add_argument('--url', default='https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/mnr%2Fgtfs-mnr',
                       help='GTFS-RT feed URL')
    
    args = parser.parse_args()
    
    print(f"Fetching GTFS-RT feed from: {args.url}")
    feed_data = fetch_gtfs_feed(args.url)
    
    if not feed_data:
        print("Failed to fetch feed data")
        return
    
    print("Parsing feed data...")
    parsed_data = parse_feed_to_dict(feed_data)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if args.format in ['json', 'both']:
        json_filename = f"{args.output}_{timestamp}.json"
        save_to_json(parsed_data, json_filename)
    
    if args.format in ['csv', 'both']:
        csv_filename = f"{args.output}_{timestamp}.csv"
        save_to_csv(parsed_data, csv_filename)
    
    print(f"Feed contains {len(parsed_data['entities'])} entities")

if __name__ == '__main__':
    main()