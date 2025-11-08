from dataclasses import dataclass
from typing import List
from enum import Enum, auto


@dataclass
class Prediction:
    label: str = ""
    value: str = ""


class PredictionStatus(Enum):
    OK = auto()
    ERROR = auto()
    ERROR_SHOW_CACHED = auto()
    ERROR_EMPTY = auto()


@dataclass
class Station:
    stop_id: str
    stop_name: str
    routes: List[str]
