try:
    from config import config
except ImportError:
    print("ERROR: Config file not found. Please create a config/config.py file.")
    print("       Start by copying config/config.example.py to config/config.py")
    exit(1)
from enum import Enum
from PIL import ImageFont
import os

__all__ = ["config","SignMode", "UIMessageType", "Fonts", "Colors"]

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))

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
    MBTA_BANNER = 2
    MUSIC = 3
    IMAGE = 4

class Rect:
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

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