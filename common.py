try:
    from config import config
except ImportError:
    print("ERROR: Config file not found. Please create a config/config.py file.")
    print("       Start by copying config/config.example.py to config/config.py")
    exit(1)
from enum import Enum
from PIL import ImageFont
import os

__all__ = ["config", "SignMode", "UIMessageType", "Fonts", "Colors"]

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))


class SignMode(Enum):
    TEST = 0
    MBTA = 1
    CLOCK = 2
    MUSIC = 3
    WIDGET = 4


class UIMessageType(Enum):
    TEST = 0
    MODE_SHIFT = 1
    MODE_CHANGE = 2
    MBTA_CHANGE_STATION = 3
    MBTA_TEST_BANNER = 4


class RenderMessageType(Enum):
    CLEAR = 0
    TEXT = 1
    MBTA = 2
    MBTA_BANNER = 3
    MUSIC = 4
    FRAME = 5
    SWAP = 6


class Rect:
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def to_tuple(self):
        return (self.x, self.y, self.w, self.h)
    
    def to_crop_tuple(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)


class Fonts:
    MBTA = ImageFont.truetype(os.path.join(
        CURRENT_FOLDER, "fonts/MBTASans-Regular.otf"), 8)
    SILKSCREEN = ImageFont.truetype(os.path.join(
        CURRENT_FOLDER, "fonts/Silkscreen-Normal.ttf"), 8)
    PICOPIXEL = ImageFont.truetype(os.path.join(
        CURRENT_FOLDER, "fonts/Picopixel.ttf"), 7)


class Colors:
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    MBTA_AMBER = (255, 191, 0)
    SPOTIFY_GREEN = (29, 185, 84)
