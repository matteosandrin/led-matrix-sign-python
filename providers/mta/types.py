from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

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

class DayType(Enum):
    WEEKDAY = "weekday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

@dataclass
class HistoricalTrainTime:
    route_id: str
    direction_id: str
    long_name: str
    departure_time: str
    trip_id: str
    day_type: DayType