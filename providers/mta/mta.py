from datetime import datetime
import requests
from typing import Dict, List, Optional, TypedDict
from pprint import pprint
import json
import os
from common.broadcaster import StatusBroadcaster
from dataclasses import dataclass

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))


@dataclass
class TrainTime:
    route_id: str
    direction_id: str
    long_name: str
    stop_headsign: str
    time: int
    trip_id: Optional[str]
    is_express: bool


@dataclass
class Station:
    stop_id: str
    stop_name: str
    latitude: float
    longitude: float
    north_direction_label: str
    south_direction_label: str
    routes: List[str]


station_data = json.load(
    open(os.path.join(CURRENT_FOLDER, "stations.json")))
stations: List[Station] = [Station(**s) for s in station_data]

# Complex stations mapping
complex_stations: Dict[str, List[str]] = {
    # Times Sq-42 St ! check for all lines
    "127": ["127", "R16", "902", "725"],
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

alert_messages: List[str] = [
    "This is an important message from the New York City Police Department. Keep your belongings in your sight at all times. Protect yourself.",
    "Backpacks and other large containers are subject to random search by the police. Thank you for your cooperation.",
    "Please be careful. Do not put your hand or your bag in a train door that is closing.",
    "The next train to arrive on the uptown local track is not in service. Please stand away from the platform edge.",
    "Please help us keep trains moving. Let customers leave the train before you enter the train; please do not hold train doors open."]


def stations_by_route() -> Dict[str, List[Station]]:
    stations_by_route = {}
    for station in stations:
        for route in station.routes:
            if route not in stations_by_route:
                stations_by_route[route] = []
            stations_by_route[route].append(station)
    return stations_by_route


def station_by_id(stop_id: str) -> Optional[Station]:
    for station in stations:
        if station.stop_id == stop_id:
            return station
    return None


def train_station_to_str(station: str) -> str:
    for s in stations:
        if s.stop_id == station:
            return s.stop_name
    return ""


def combine_complex_ids(complex_ids: List[str]) -> str:
    return ','.join(f"MTASBWY:{stop_id}" for stop_id in complex_ids)


def check_for_complex_stop_ids(stop_id: str) -> str:
    return combine_complex_ids(complex_stations[stop_id]) if stop_id in complex_stations else f"MTASBWY:{stop_id}"


class MTA():
    def __init__(self, api_key: str):
        self.domain = 'https://otp-mta-prod.camsys-apps.com/otp/routers/default'
        self.api_key = api_key
        self.station_broadcaster = StatusBroadcaster()
        self.station_broadcaster.set_status("121")  # 116th st station

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
                        wait_time = train['realtimeArrival'] - \
                            (train['timestamp'] - train['serviceDay'])
                        if wait_time >= 0:
                            train_times.append(
                                TrainTime(
                                    route_id=route_id,
                                    direction_id=train['directionId'],
                                    long_name=train['tripHeadsign'],
                                    stop_headsign=route_entry['headsign'],
                                    time=wait_time, trip_id=train.get(
                                        'tripId', '').replace(
                                        'MTASBWY:', ''),
                                    is_express='express'
                                    in route_entry['route']
                                    ['longName'].lower()))
            return sorted(train_times, key=lambda x: x.time)
        except Exception as err:
            print('unable to fetch nearby api', err)
            return None

    def get_fake_predictions(self) -> List[TrainTime]:
        return [
            TrainTime(
                route_id="1",
                direction_id="1",
                long_name="South Ferry",
                stop_headsign="Downtown",
                time=780,
                trip_id="893",
                is_express=False
            ),
            TrainTime(
                route_id="2",
                direction_id="0",
                long_name="Van Cortlandt Park",
                stop_headsign="Uptown & The Bronx",
                time=240,
                trip_id="893",
                is_express=False
            )
        ]

    def get_current_station(self) -> Optional[str]:
        return self.station_broadcaster.get_status()

    def set_current_station(self, station: str):
        self.station_broadcaster.set_status(station)
