#!/usr/bin/env python3
import csv
import json
import sys

def main():
    stations = {}
    
    # Read LIRR stops and create stations
    with open('/home/ubuntu/misc/mrnlirr/MTAPI/data/lirr/stops.txt', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stop_id = row['stop_id']
            stations[stop_id] = {
                'id': stop_id,
                'name': row['stop_name'],
                'location': [float(row['stop_lat']), float(row['stop_lon'])],
                'stops': {
                    stop_id: [float(row['stop_lat']), float(row['stop_lon'])]
                },
                'system': 'lirr'
            }
    
    json.dump(stations, sys.stdout, sort_keys=True, indent=4, separators=(',', ': '))

if __name__ == '__main__':
    main()