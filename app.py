# coding: utf-8
"""
    mta-api-sanity
    ~~~~~~

    Expose the MTA's real-time subway feed as a json api

    :copyright: (c) 2014 by Jon Thornton.
    :license: BSD, see LICENSE for more details.
"""

from mtapi.mtapi import Mtapi
from mtapi.regional_api import LIRRApi, MNRApi, OutageAPI, AlertAPI
from mtapi.unified_search import UnifiedStationSearch
from flask import Flask, request, Response, render_template, abort, redirect
import json
from datetime import datetime
from functools import wraps, reduce
import logging
import os

app = Flask(__name__)
app.config.update(
    MAX_TRAINS=10,
    MAX_MINUTES=30,
    CACHE_SECONDS=60,
    THREADED=True
)

_SETTINGS_ENV_VAR = 'MTAPI_SETTINGS'
_SETTINGS_DEFAULT_PATH = './settings.cfg'
if _SETTINGS_ENV_VAR in os.environ:
    app.config.from_envvar(_SETTINGS_ENV_VAR)
elif os.path.isfile(_SETTINGS_DEFAULT_PATH):
    app.config.from_pyfile(_SETTINGS_DEFAULT_PATH)
else:
    raise Exception('No configuration found! Create a settings.cfg file or set MTAPI_SETTINGS env variable.')

# set debug logging
if app.debug:
    logging.basicConfig(level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, datetime):
                return obj.isoformat()
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)

mta = Mtapi(
    app.config['MTA_KEY'],
    app.config['STATIONS_FILE'],
    max_trains=app.config['MAX_TRAINS'],
    max_minutes=app.config['MAX_MINUTES'],
    expires_seconds=app.config['CACHE_SECONDS'],
    threaded=app.config['THREADED'])

# Initialize regional APIs
lirr = LIRRApi(
    app.config['MTA_KEY'],
    expires_seconds=app.config['CACHE_SECONDS'],
    max_trains=app.config['MAX_TRAINS'],
    max_minutes=240)

mnr = MNRApi(
    app.config['MTA_KEY'],
    expires_seconds=app.config['CACHE_SECONDS'],
    max_trains=app.config['MAX_TRAINS'],
    max_minutes=240)

# Initialize outage and alert APIs
outage_api = OutageAPI()
alert_api = AlertAPI()

# Initialize unified station search
unified_search = UnifiedStationSearch(
    app.config['STATIONS_FILE'],
    '/home/ubuntu/misc/mrnlirr/MTAPI/data/mnr-stations.json',
    '/home/ubuntu/misc/mrnlirr/MTAPI/data/lirr-stations.json'
)

def response_wrapper(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        resp = f(*args, **kwargs)

        if not isinstance(resp, Response):
            # custom JSON encoder; this is important
            resp = Response(
                response=json.dumps(resp, cls=CustomJSONEncoder),
                status=200,
                mimetype="application/json"
            )

        add_cors_header(resp)

        return resp

    return decorated_function

def add_cors_header(resp):
    if app.config['DEBUG']:
        resp.headers['Access-Control-Allow-Origin'] = '*'
    elif 'CROSS_ORIGIN' in app.config:
        resp.headers['Access-Control-Allow-Origin'] = app.config['CROSS_ORIGIN']

    return resp

@app.route('/')
@response_wrapper
def index():
    return {
        'title': 'MTAPI',
        'readme': 'Visit https://github.com/jonthornton/MTAPI for more info'
        }

@app.route('/by-location', methods=['GET'])
@response_wrapper
def by_location():
    try:
        lat = float(request.args['lat'])
        lon = float(request.args['lon'])
        system_filter = request.args.get('system', 'subway')  # default to subway for backward compatibility
        limit = int(request.args.get('limit', '5'))
        radius = float(request.args.get('radius', '0.01'))
    except (KeyError, ValueError) as e:
        print(e)
        resp = Response(
            response=json.dumps({'error': 'Missing or invalid lat/lon parameter'}),
            status=400,
            mimetype="application/json"
        )
        return add_cors_header(resp)

    if system_filter == 'subway':
        # Use original subway search for backward compatibility
        data = mta.get_by_point((lat, lon), limit)
        return _make_envelope(data)
    elif system_filter == 'all':
        # Use unified search for all systems
        data = unified_search.search_by_location(lat, lon, radius, limit)
        return {
            'data': data,
            'updated': None
        }
    else:
        # Filter by specific system using unified search
        data = unified_search.search_by_location(lat, lon, radius, limit * 3)  # Get more, then filter
        filtered_data = [station for station in data if station.get('system') == system_filter][:limit]
        return {
            'data': filtered_data,
            'updated': None
        }

@app.route('/by-route/<route>', methods=['GET'])
@response_wrapper
def by_route(route):

    if route.islower():
        return redirect(request.host_url + 'by-route/' + route.upper(), code=301)

    try:
        data = mta.get_by_route(route)
        return _make_envelope(data)
    except KeyError as e:
        resp = Response(
            response=json.dumps({'error': 'Station not found'}),
            status=404,
            mimetype="application/json"
        )

        return add_cors_header(resp)

@app.route('/by-id/<id_string>', methods=['GET'])
@response_wrapper
def by_index(id_string):
    ids = id_string.split(',')
    try:
        data = mta.get_by_id(ids)
        return _make_envelope(data)
    except KeyError as e:
        resp = Response(
            response=json.dumps({'error': 'Station not found'}),
            status=404,
            mimetype="application/json"
        )

        return add_cors_header(resp)

@app.route('/routes', methods=['GET'])
@response_wrapper
def routes():
    return {
        'data': sorted(mta.get_routes()),
        'updated': mta.last_update()
        }

@app.route('/search', methods=['GET'])
@response_wrapper
def search_stations():
    try:
        query = request.args['q']
        system_filter = request.args.get('system', 'all')  # all, subway, mnr, lirr
    except KeyError as e:
        resp = Response(
            response=json.dumps({'error': 'Missing q parameter'}),
            status=400,
            mimetype="application/json"
        )
        return add_cors_header(resp)

    if system_filter == 'subway' or system_filter == 'all':
        # Use original subway search for subway-only or include subway in unified search
        if system_filter == 'subway':
            data = mta.search_stations(query)
            return {
                'data': data,
                'updated': mta.last_update()
            }
    
    # Use unified search for multi-system search
    data = unified_search.search_stations(query, system_filter)
    return {
        'data': data,
        'updated': None  # Unified search doesn't have a last_update timestamp
    }

def _envelope_reduce(a, b):
    if a['last_update'] and b['last_update']:
        return a if a['last_update'] < b['last_update'] else b
    elif a['last_update']:
        return a
    else:
        return b

def _make_envelope(data):
    time = None
    if data:
        time = reduce(_envelope_reduce, data)['last_update']

    return {
        'data': data,
        'updated': time
    }

# LIRR endpoints
@app.route('/lirr/routes', methods=['GET'])
@response_wrapper
def lirr_routes():
    return {
        'data': sorted(lirr.get_routes()),
        'updated': lirr.last_update()
    }

@app.route('/lirr/stops', methods=['GET'])
@response_wrapper
def lirr_stops():
    return {
        'data': lirr.get_stops(),
        'updated': lirr.last_update()
    }

@app.route('/lirr/by-route/<route>', methods=['GET'])
@response_wrapper
def lirr_by_route(route):
    try:
        data = lirr.get_stops_by_route(route)
        return {
            'data': data,
            'updated': lirr.last_update()
        }
    except Exception as e:
        resp = Response(
            response=json.dumps({'error': 'Route not found'}),
            status=404,
            mimetype="application/json"
        )
        return add_cors_header(resp)

@app.route('/lirr/by-id/<stop_id>', methods=['GET'])
@response_wrapper
def lirr_by_id(stop_id):
    try:
        data = lirr.get_stop_by_id(stop_id)
        if data:
            return {
                'data': [data],
                'updated': lirr.last_update()
            }
        else:
            resp = Response(
                response=json.dumps({'error': 'Stop not found'}),
                status=404,
                mimetype="application/json"
            )
            return add_cors_header(resp)
    except Exception as e:
        resp = Response(
            response=json.dumps({'error': 'Stop not found'}),
            status=404,
            mimetype="application/json"
        )
        return add_cors_header(resp)

@app.route('/lirr/search', methods=['GET'])
@response_wrapper
def lirr_search():
    try:
        query = request.args['q']
    except KeyError as e:
        resp = Response(
            response=json.dumps({'error': 'Missing q parameter'}),
            status=400,
            mimetype="application/json"
        )
        return add_cors_header(resp)
    
    data = lirr.search_stops(query)
    return {
        'data': data,
        'updated': lirr.last_update()
    }

@app.route('/lirr/by-location', methods=['GET'])
@response_wrapper
def lirr_by_location():
    try:
        location = (float(request.args['lat']), float(request.args['lon']))
    except KeyError as e:
        resp = Response(
            response=json.dumps({'error': 'Missing lat/lon parameter'}),
            status=400,
            mimetype="application/json"
        )
        return add_cors_header(resp)
    
    data = lirr.get_by_location(location, 5)
    return {
        'data': data,
        'updated': lirr.last_update()
    }

# MNR endpoints
@app.route('/mnr/routes', methods=['GET'])
@response_wrapper
def mnr_routes():
    return {
        'data': sorted(mnr.get_routes()),
        'updated': mnr.last_update()
    }

@app.route('/mnr/stops', methods=['GET'])
@response_wrapper
def mnr_stops():
    return {
        'data': mnr.get_stops(),
        'updated': mnr.last_update()
    }

@app.route('/mnr/by-route/<route>', methods=['GET'])
@response_wrapper
def mnr_by_route(route):
    try:
        data = mnr.get_stops_by_route(route)
        return {
            'data': data,
            'updated': mnr.last_update()
        }
    except Exception as e:
        resp = Response(
            response=json.dumps({'error': 'Route not found'}),
            status=404,
            mimetype="application/json"
        )
        return add_cors_header(resp)

@app.route('/mnr/by-id/<stop_id>', methods=['GET'])
@response_wrapper
def mnr_by_id(stop_id):
    try:
        data = mnr.get_stop_by_id(stop_id)
        if data:
            return {
                'data': [data],
                'updated': mnr.last_update()
            }
        else:
            resp = Response(
                response=json.dumps({'error': 'Stop not found'}),
                status=404,
                mimetype="application/json"
            )
            return add_cors_header(resp)
    except Exception as e:
        resp = Response(
            response=json.dumps({'error': 'Stop not found'}),
            status=404,
            mimetype="application/json"
        )
        return add_cors_header(resp)

@app.route('/mnr/search', methods=['GET'])
@response_wrapper
def mnr_search():
    try:
        query = request.args['q']
    except KeyError as e:
        resp = Response(
            response=json.dumps({'error': 'Missing q parameter'}),
            status=400,
            mimetype="application/json"
        )
        return add_cors_header(resp)
    
    data = mnr.search_stops(query)
    return {
        'data': data,
        'updated': mnr.last_update()
    }

@app.route('/mnr/by-location', methods=['GET'])
@response_wrapper
def mnr_by_location():
    try:
        location = (float(request.args['lat']), float(request.args['lon']))
    except KeyError as e:
        resp = Response(
            response=json.dumps({'error': 'Missing lat/lon parameter'}),
            status=400,
            mimetype="application/json"
        )
        return add_cors_header(resp)
    
    data = mnr.get_by_location(location, 5)
    return {
        'data': data,
        'updated': mnr.last_update()
    }

# Outage endpoints
@app.route('/outages/search', methods=['GET'])
@response_wrapper
def search_outages():
    try:
        station = request.args['station']
    except KeyError as e:
        resp = Response(
            response=json.dumps({'error': 'Missing station parameter'}),
            status=400,
            mimetype="application/json"
        )
        return add_cors_header(resp)
    
    data = outage_api.search_outages(station)
    return data

# Alert endpoints
@app.route('/alerts/search', methods=['GET'])
@response_wrapper
def search_alerts():
    try:
        query = request.args['q']
        service_type = request.args.get('service', 'all')
    except KeyError as e:
        resp = Response(
            response=json.dumps({'error': 'Missing q parameter'}),
            status=400,
            mimetype="application/json"
        )
        return add_cors_header(resp)
    
    data = alert_api.search_alerts(query, service_type)
    return data

# Route planning endpoint
@app.route('/route-plan', methods=['GET'])
@response_wrapper
def route_plan():
    try:
        from_lat = float(request.args['from_lat'])
        from_lon = float(request.args['from_lon'])
        to_lat = float(request.args['to_lat'])
        to_lon = float(request.args['to_lon'])
    except (KeyError, ValueError) as e:
        resp = Response(
            response=json.dumps({'error': 'Missing or invalid from_lat, from_lon, to_lat, to_lon parameters'}),
            status=400,
            mimetype="application/json"
        )
        return add_cors_header(resp)
    
    from_point = (from_lat, from_lon)
    to_point = (to_lat, to_lon)
    
    # Simple multi-modal routing - find nearest subway, LIRR, and MNR stops
    subway_from = mta.get_by_point(from_point, 3)
    subway_to = mta.get_by_point(to_point, 3)
    lirr_from = lirr.get_by_location(from_point, 3)
    lirr_to = lirr.get_by_location(to_point, 3)
    mnr_from = mnr.get_by_location(from_point, 3)
    mnr_to = mnr.get_by_location(to_point, 3)
    
    return {
        'from_point': from_point,
        'to_point': to_point,
        'options': {
            'subway': {
                'from_stations': subway_from,
                'to_stations': subway_to
            },
            'lirr': {
                'from_stations': lirr_from,
                'to_stations': lirr_to
            },
            'mnr': {
                'from_stations': mnr_from,
                'to_stations': mnr_to
            }
        },
        'note': 'This is a basic proximity-based route suggestion. For detailed routing, use dedicated trip planning services.'
    }

if __name__ == '__main__':
    app.run(use_reloader=True)
