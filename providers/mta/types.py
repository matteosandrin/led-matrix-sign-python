from dataclasses import dataclass
from typing import Optional, List


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