import json
import os
import random
import requests
import config
from common.broadcaster import StatusBroadcaster
from dataclasses import dataclass
from datetime import datetime
from pprint import pprint
from typing import Dict, List, Optional, TypedDict
import logging

logger = logging.getLogger("led-matrix-sign")

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MTA_STATION = "121"  # 86 St 1,2,3 station
if hasattr(config, 'DEFAULT_MTA_STATION'):
    DEFAULT_MTA_STATION = config.DEFAULT_MTA_STATION
MAX_NUM_PREDICTIONS = 6


@dataclass
class TrainTime:
    route_id: str
    direction_id: str
    long_name: str
    stop_headsign: str
    time: int
    trip_id: Optional[str]
    is_express: bool
    display_order: int


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


def get_second_train(predictions: List[TrainTime], last_second_train: TrainTime) -> TrainTime:
    """
    The second train slot on the board rotates between the next couple of
    trains. This function returns the next train in the rotation. It always
    skips the first train in the rotation, since that is already shown in the
    first slot.
    """
    if (predictions is None) or (len(predictions) < 2):
        return None
    if last_second_train is None:
        return predictions[1]
    for i, train in enumerate(predictions):
        if train.display_order == last_second_train.display_order:
            next_id = i + 1
            if next_id >= len(predictions):
                next_id = 1
            return predictions[next_id]
    return predictions[1]


def print_predictions(predictions: List[TrainTime]):
    for train in predictions:
        logger.info(f"{train.display_order+1}. ({train.route_id}) {train.long_name} {int(round(train.time / 60.0))}min ({train.time}s) {train.trip_id}")
    logger.info("")


def combine_complex_ids(complex_ids: List[str]) -> str:
    return ','.join(f"MTASBWY:{stop_id}" for stop_id in complex_ids)


def check_for_complex_stop_ids(stop_id: str) -> str:
    return combine_complex_ids(complex_stations[stop_id]) if stop_id in complex_stations else f"MTASBWY:{stop_id}"


class MTA():
    def __init__(self, api_key: str):
        self.domain = 'https://otp-mta-prod.camsys-apps.com/otp/routers/default'
        self.api_key = api_key
        self.station_broadcaster = StatusBroadcaster()
        self.station_broadcaster.set_status(DEFAULT_MTA_STATION)
        # The last train to be shown in the second slot on the board.
        self.last_second_train = None

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
                                    ['longName'].lower(),
                                    display_order=0))
            train_times = sorted(train_times, key=lambda x: x.time)
            for i, train in enumerate(train_times):
                train.display_order = i
            return train_times[:MAX_NUM_PREDICTIONS]
        except Exception as err:
            logger.error('unable to fetch nearby api', exc_info=err)
            return None

    def get_fake_predictions(self) -> List[TrainTime]:
        return [
            TrainTime(
                route_id="1",
                direction_id="1",
                long_name="South Ferry",
                stop_headsign="Downtown",
                time=80,
                trip_id="893",
                is_express=False,
                display_order=0
            ),
            TrainTime(
                route_id="2",
                direction_id="0",
                long_name="Van Cortlandt Park",
                stop_headsign="Uptown & The Bronx",
                time=200,
                trip_id="894",
                is_express=False,
                display_order=1
            ),
            TrainTime(
                route_id="F",
                direction_id="0",
                long_name="Ozone Park",
                stop_headsign="Uptown & The Bronx",
                time=360,
                trip_id="895",
                is_express=False,
                display_order=2
            ),
            TrainTime(
                route_id="3",
                direction_id="0",
                long_name="Van Cortlandt Park",
                stop_headsign="Uptown & The Bronx",
                time=470,
                trip_id="896",
                is_express=False,
                display_order=3
            )
        ]

    def get_current_station(self) -> Optional[str]:
        return self.station_broadcaster.get_status()

    def set_current_station(self, station: str):
        self.clear()
        self.station_broadcaster.set_status(station)

    def clear(self):
        self.last_second_train = None


class AlertMessages:
    def __init__(self):
        self.available_messages = alert_messages.copy()
        self.used_messages = []
        self.last_message = None

    def next(self) -> str:
        # Every message is shown once per cycle. The same message is never shown
        # twice in a row.
        if len(self.available_messages) == 0:
            self.available_messages = [
                m for m in self.used_messages if m != self.last_message]
            self.used_messages = []
            if self.last_message:
                self.used_messages.append(self.last_message)
        message = random.choice(self.available_messages)
        self.available_messages.remove(message)
        self.used_messages.append(message)
        self.last_message = message
        return message

    @classmethod
    def random(cls) -> str:
        return random.choice(alert_messages)
