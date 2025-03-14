import json
import os
import time
import config
from datetime import datetime, timezone
from enum import Enum, auto
from dataclasses import dataclass
import requests
from common.broadcaster import StatusBroadcaster
from typing import List, Dict, Optional
from .types import Prediction, PredictionStatus, Station
import logging

logger = logging.getLogger("led-matrix-sign")

# Constants
DIRECTION_SOUTHBOUND = 0
DIRECTION_NORTHBOUND = 1
MBTA_MAX_ERROR_COUNT = 3

MBTA_PREDICTIONS_URL = "https://api-v3.mbta.com/predictions"

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))

station_data = json.load(
    open(os.path.join(CURRENT_FOLDER, "stations.json")))
stations: List[Station] = [Station(**s) for s in station_data]


DEFAULT_MBTA_STATION = "place-harsq" # harvard square station
if hasattr(config, 'DEFAULT_MBTA_STATION'):
    DEFAULT_MBTA_STATION = config.DEFAULT_MBTA_STATION


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


class MBTA:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.latest_predictions = [Prediction(), Prediction()]
        self.error_count = 0
        self.station_broadcaster = StatusBroadcaster()
        self.station_broadcaster.set_status(DEFAULT_MBTA_STATION)

    @property
    def station(self):
        return self.station_broadcaster.get_status()

    def get_predictions(self, num_predictions: int, directions: List[int],
                        nth_positions: List[int]) -> tuple[PredictionStatus, List[Prediction]]:
        dst = [Prediction() for _ in range(num_predictions)]

        if self.station == "test":
            dst = self._get_placeholder_predictions()
            dst[0].value = "5 min"
            dst[1].value = "12 min"
            return PredictionStatus.OK, dst

        prediction_data = self._fetch_predictions()
        if prediction_data is None:
            self.error_count += 1
            if self.error_count <= MBTA_MAX_ERROR_COUNT:
                return PredictionStatus.ERROR_SHOW_CACHED, dst
            return PredictionStatus.ERROR, dst

        self.error_count = 0
        if len(prediction_data["data"]) == 0:
            return PredictionStatus.ERROR_EMPTY, dst

        for i in range(num_predictions):
            prediction = self._find_nth_prediction_for_direction(
                prediction_data, directions[i], nth_positions[i])
            trip = self._find_trip_for_prediction(prediction_data, prediction)
            dst[i] = self._format_prediction(prediction, trip)
        return PredictionStatus.OK, dst

    def get_predictions_both_directions(self) -> tuple[PredictionStatus,
                                                       List[Prediction]]:
        directions = [DIRECTION_SOUTHBOUND, DIRECTION_NORTHBOUND]
        nth_positions = [0, 0]
        return self.get_predictions(2, directions, nth_positions)

    def get_predictions_one_direction(self, direction: int) -> tuple[PredictionStatus, List[Prediction]]:
        directions = [direction, direction]
        nth_positions = [0, 1]
        return self.get_predictions(2, directions, nth_positions)

    def _fetch_predictions(self) -> Optional[dict]:
        try:
            routes = station_by_id(self.station).routes
            response = requests.get(MBTA_PREDICTIONS_URL, params={
                "api_key": self.api_key,
                "filter[stop]": self.station,
                "filter[route]": ','.join(routes),
                "fields[prediction]": "arrival_time,departure_time,status,direction_id",
                "include": "trip"
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching predictions: {e}")
            return None

    def _find_nth_prediction_for_direction(self, prediction_data: dict,
                                           direction: int, n: int) -> Optional[dict]:
        for prediction in prediction_data["data"]:
            attrs = prediction["attributes"]
            if attrs["direction_id"] == direction:
                if attrs["status"] is not None:
                    if n == 0:
                        return prediction
                    n -= 1
                else:
                    arr_time = attrs["arrival_time"]
                    if arr_time:
                        arr_diff = self._diff_with_local_time(arr_time)
                        if arr_diff > -30:
                            if n == 0:
                                return prediction
                            n -= 1
        return None

    def _find_trip_for_prediction(self, prediction_data: dict,
                                  prediction: Optional[dict]) -> Optional[dict]:
        if not prediction:
            return None

        trip_array = prediction_data.get("included", [])
        trip_id = prediction["relationships"]["trip"]["data"]["id"]

        for trip in trip_array:
            if trip["id"] == trip_id:
                return trip
        return None

    def _diff_with_local_time(self, timestring: str) -> int:
        """Calculate difference in seconds between given time and local time"""
        prediction_time = datetime.fromisoformat(
            timestring.replace('Z', '+00:00'))
        local_time = datetime.now(timezone.utc)
        return int((prediction_time - local_time).total_seconds())

    def _determine_display_string(
            self, arr_diff: int, dep_diff: int, status: Optional[str]) -> str:
        if status:
            status = status.lower()
            if "stopped" in status:
                return "STOP"
            return status[:6]

        if arr_diff > 0:
            if arr_diff > 60:
                minutes = int(arr_diff / 60)
                return f"{minutes} min"
            return "ARR"

        if dep_diff > 0:
            return "BRD"
        return "ERROR"

    def _format_prediction(
            self, prediction: Optional[dict],
            trip: Optional[dict]) -> Prediction:
        dst = Prediction()
        if not prediction or not trip:
            dst.label = ""
            dst.value = ""
            return dst
        attrs = prediction["attributes"]
        headsign = trip["attributes"]["headsign"]
        arr_time = attrs.get("arrival_time")
        dep_time = attrs.get("departure_time")
        status = attrs.get("status")
        # display can fit 16 chars per line
        # 10 label + 6 value
        dst.label = headsign[:10]

        if status:
            display_string = self._determine_display_string(-1, -1, status)
        elif arr_time and dep_time:
            arr_diff = self._diff_with_local_time(arr_time)
            dep_diff = self._diff_with_local_time(dep_time)
            display_string = self._determine_display_string(
                arr_diff, dep_diff, None)
        else:
            display_string = "ERROR"
        dst.value = display_string
        return dst

    def update_latest_predictions(
            self, latest: List[Prediction],
            directions: List[int]) -> None:
        if directions[0] == directions[1]:
            self.latest_predictions[directions[0]] = latest[0]
        else:
            self.latest_predictions[directions[0]] = latest[0]
            self.latest_predictions[directions[1]] = latest[1]

    def find_prediction_with_arriving_banner(
            self, predictions: [Prediction]) -> Optional[Prediction]:
        if len(predictions) < 2:
            return None
        if predictions[0].value == "ARR" and self.latest_predictions[0].value != "ARR":
            return predictions[0]
        if predictions[1].value == "ARR" and self.latest_predictions[1].value != "ARR":
            return predictions[1]
        return None

    def get_arriving_banner(self, prediction: Prediction) -> [str]:
        return [f"{prediction.label} train",
                "is now arriving."]

    def get_cached_predictions(self) -> List[Prediction]:
        return [
            Prediction(
                label=self.latest_predictions[0].label, value=self.latest_predictions[0].value),
            Prediction(
                label=self.latest_predictions[1].label, value=self.latest_predictions[1].value)
        ]

    def _get_placeholder_predictions(self) -> None:
        placeholders = [Prediction(), Prediction()]
        placeholders[0].label = "Ashmont"
        placeholders[0].value = ""
        placeholders[1].label = "Alewife"
        placeholders[1].value = ""
        return placeholders

    def set_station(self, station: str) -> None:
        self.latest_predictions = self._get_placeholder_predictions()
        self.station_broadcaster.set_status(station)
