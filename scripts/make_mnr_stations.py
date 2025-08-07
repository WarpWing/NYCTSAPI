#!/usr/bin/env python3
import csv
import json
import sys

def main():
    stations = {}
    
    # Read MNR stops and create stations
    with open('/home/ubuntu/misc/mrnlirr/MTAPI/data/mnr/stops.txt', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip non-station entries (location_type != 0 means it's not a stop/platform)
            if row.get('location_type', '0') != '0':
                continue
                
            stop_id = row['stop_id']
            stations[stop_id] = {
                'id': stop_id,
                'name': row['stop_name'],
                'location': [float(row['stop_lat']), float(row['stop_lon'])],
                'stops': {
                    stop_id: [float(row['stop_lat']), float(row['stop_lon'])]
                },
                'system': 'mnr'
            }
    
    json.dump(stations, sys.stdout, sort_keys=True, indent=4, separators=(',', ': '))

if __name__ == '__main__':
    main()