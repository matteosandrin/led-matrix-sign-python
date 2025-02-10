from datetime import datetime
import requests
from typing import Dict, List, Optional, TypedDict
from pprint import pprint
import json
import os

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))

class TrainTime(TypedDict):
    route_id: str
    direction_id: str
    long_name: str
    stop_headsign: str
    time: int
    trip_id: Optional[str]
    is_express: bool

class Stations(TypedDict):
    stop_id: str
    stop_name: str
    latitude: float
    longitude: float
    north_direction_label: str
    south_direction_label: str
    routes: List[str]

stations: List[Stations] = json.load(open(os.path.join(CURRENT_FOLDER, "stations.json")))

# Complex stations mapping
complex_stations: Dict[str, List[str]] = {
    "127": ["127", "R16", "902", "725"],  # Times Sq-42 St ! check for all lines
    "222": ["222", "415"],  # 149 St - Grand Concourse
    "232": ["232", "423"],  # Borough Hall
    "235": ["235", "D24"],  # Atlantic Av - Barclays Ctr (2,3,4,5,Q,B)
    "631": ["631", "723", "901"],  # Grand Central - 42 St
    "719": ["719", "G22"],  # Court Sq
    "A12": ["A12", "D13"],  # 145 St
    "A24": ["A24", "125"],  # 59 St - Columbus Circle
    "A32": ["A32", "D20"],  # W 4 St
    "A38": ["A38", "M22"],  # Fulton St
    "A41": ["A41", "R29"],  # Jay St - MetroTech
    "D11": ["D11", "414"],  # 161 St - Yankee Stadium
    "J27": ["J27", "L22", "A51"],  # Broadway Jct
    "L17": ["L17", "M08"],  # Myrtle - Wyckoff Avs
    "M18": ["M18", "F15"],  # Delancey St
    "Q01": ["M20", "639"],  # Canal St - (4,5,6,J,Z)
    "R23": ["Q01", "R23", "M20", "639"],  # Canal St - (R,W,N,Q)
    "R09": ["R09", "718"],  # Queensboro Plaza
    "R17": ["R17", "D17"],  # 34 St Herald Sq
    "R20": ["R20", "L03", "635"],  # Union Sq - 14 St
}


def calculate_arrival_time_in_seconds(
        arrival_fmt: str, current_time_ms: Optional[int] = None) -> int:
    if current_time_ms is None:
        current_time_ms = int(datetime.now().timestamp() * 1000)
    arrival_time_ms = int(datetime.fromisoformat(
        arrival_fmt.replace('Z', '+00:00')).timestamp() * 1000)
    time_to_arrival_ms = arrival_time_ms - current_time_ms
    return round(time_to_arrival_ms / 1000)


def combine_complex_ids(complex_ids: List[str]) -> str:
    return ','.join(f"MTASBWY:{stop_id}" for stop_id in complex_ids)


def check_for_complex_stop_ids(stop_id: str) -> str:
    return combine_complex_ids(complex_stations[stop_id]) if stop_id in complex_stations else f"MTASBWY:{stop_id}"


class MTA():
    def __init__(self, api_key: str):
        self.domain = 'https://otp-mta-prod.camsys-apps.com/otp/routers/default'
        self.api_key = api_key

    def get_predictions(self, stop_id: str) -> Optional[List[TrainTime]]:
        try:
            response = requests.get(f"{self.domain}/nearby", params={
                'stops': check_for_complex_stop_ids(stop_id),
                'apikey': self.api_key,
                'groupByParent': 'true',
                'routes': '',
                'timeRange': 60 * 60
            })
            status_per_station = response.json()
            train_times: List[TrainTime] = []
            for station in status_per_station:
                groups = station['groups']
                groups = [g for g in groups if g['times']]
                for route_entry in groups:
                    route_id = route_entry['route']['id'].replace(
                        'MTASBWY:', '')
                    for train in route_entry['times']:
                        # Handle terminal station edge cases
                        arrival_time = (
                            train.get('arrivalFmt') or train.get('departureFmt')
                            if not train.get('scheduledArrival') and
                            not train.get('realtimeArrival') else train.get(
                                'departureFmt'))
                        time = calculate_arrival_time_in_seconds(arrival_time)
                        if time >= 0:
                            train_times.append({
                                'route_id': route_id,
                                'direction_id': train['directionId'],
                                'long_name': train['tripHeadsign'],
                                'stop_headsign': route_entry['headsign'],
                                'time': time,
                                'trip_id': train.get('tripId', '').replace('MTASBWY:', ''),
                                'is_express': 'express' in route_entry['route']['longName'].lower()
                            })
            return sorted(train_times, key=lambda x: x['time'])
        except Exception as err:
            print('unable to fetch nearby api', err)
            return None
