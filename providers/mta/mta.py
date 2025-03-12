import json
import os
import random
import requests
import config
import pickle
from common.broadcaster import StatusBroadcaster
from dataclasses import dataclass
from datetime import datetime
from pprint import pprint
from typing import Dict, List, Optional, TypedDict
from .types import TrainTime, Station, DayType, HistoricalTrainTime
import logging

logger = logging.getLogger("led-matrix-sign")

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MTA_STATION = "121"  # 86 St 1,2,3 station
if hasattr(config, 'DEFAULT_MTA_STATION'):
    DEFAULT_MTA_STATION = config.DEFAULT_MTA_STATION
MAX_NUM_PREDICTIONS = 6


station_data = json.load(
    open(os.path.join(CURRENT_FOLDER, "stations.json")))
stations: List[Station] = [Station(**s) for s in station_data]

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


def get_second_train(
        predictions: List[TrainTime],
        last_second_train: TrainTime) -> TrainTime:
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
        logger.info(
            f"{train.display_order+1}. ({train.route_id}) {train.long_name} {int(round(train.time / 60.0))}min ({train.time}s) {train.trip_id}")
    logger.info("")


def combine_stop_ids(stop_ids: List[str]) -> str:
    return ','.join(f"MTASBWY:{stop_id}" for stop_id in stop_ids)


def get_stop_ids(stop: Station) -> List[str]:
    stop_ids = [stop.stop_id]
    if stop.children:
        stop_ids += stop.children
    return stop_ids


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
            stop = station_by_id(stop_id)
            if stop is None:
                logger.error(f"Stop {stop_id} not found")
                return []
            stop_ids = get_stop_ids(stop)
            response = requests.get(f"{self.domain}/nearby", params={
                'stops': combine_stop_ids(stop_ids),
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
                        wait_time = train['realtimeDeparture'] - \
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

    def _seconds_since_midnight(self) -> int:
        now = datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return (now - midnight).total_seconds()

    def _filter_historical_train_times(
            self, train_times: List[HistoricalTrainTime]) -> List[
            HistoricalTrainTime]:
        now = datetime.now()
        day_type = DayType.WEEKDAY
        if now.weekday() == 5:
            day_type = DayType.SATURDAY
        elif now.weekday() == 6:
            day_type = DayType.SUNDAY
        seconds_since_midnight = self._seconds_since_midnight()
        train_times = [
            t for t in train_times
            if t.day_type == day_type
            and t.departure_time > seconds_since_midnight]
        train_times.sort(
            key=lambda x: x.departure_time - seconds_since_midnight)
        return train_times

    def get_fake_predictions(self, stop_id: str) -> List[TrainTime]:
        if stop_id not in self.historical_data:
            return []
        stop = station_by_id(stop_id)
        if stop is None:
            logger.error(f"Stop {stop_id} not found")
            return []
        stop_ids = get_stop_ids(stop)
        historical_train_times = []
        for stop_id in stop_ids:
            if stop_id in self.historical_data:
                historical_train_times.extend(self.historical_data[stop_id])
        historical_train_times = self._filter_historical_train_times(
            historical_train_times)
        seconds_since_midnight = self._seconds_since_midnight()
        return [TrainTime(
            route_id=t.route_id,
            direction_id=t.direction_id,
            long_name=t.long_name,
            time=int(t.departure_time - seconds_since_midnight),
            trip_id=t.trip_id,
            display_order=i,
            stop_headsign=None,
            is_express=None
        ) for i, t in enumerate(historical_train_times[:MAX_NUM_PREDICTIONS])]

    def get_current_station(self) -> Optional[str]:
        return self.station_broadcaster.get_status()

    def set_current_station(self, station: str):
        self.clear()
        self.station_broadcaster.set_status(station)

    def clear(self):
        self.last_second_train = None

    def load_historical_data(self):
        if not os.path.exists(f'{CURRENT_FOLDER}/historical_train_times.pickle'):
            logger.error(
                f"Historical train times file not found at {CURRENT_FOLDER}/historical_train_times.pickle")
            logger.error(
                "Run update-historical-train-times.py to generate this file")
            self.historical_data = {}
            return
        with open(f'{CURRENT_FOLDER}/historical_train_times.pickle', 'rb') as f:
            self.historical_data = pickle.load(f)


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
