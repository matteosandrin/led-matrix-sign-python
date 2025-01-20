from enum import Enum


class SignMode(Enum):
    TEST = 0
    MBTA = 1
    CLOCK = 2
    MUSIC = 3

class UIMessageType(Enum):
    MODE_SHIFT = 0
    MODE_CHANGE = 1
    MBTA_CHANGE_STATION = 2
