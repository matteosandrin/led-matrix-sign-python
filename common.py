try:
    from config import config
except ImportError:
    print("ERROR: Config file not found. Please create a config/config.py file.")
    print("       Start by copying config/config.example.py to config/config.py")
    exit(1)
from enum import Enum

__all__ = ["config","SignMode", "UIMessageType"]

class SignMode(Enum):
    TEST = 0
    MBTA = 1
    CLOCK = 2
    MUSIC = 3

class UIMessageType(Enum):
    TEST = 0
    MODE_SHIFT = 1
    MODE_CHANGE = 2
    MBTA_CHANGE_STATION = 3

class RenderMessageType(Enum):
    TEXT = 0
    MBTA = 1
    MUSIC = 2
