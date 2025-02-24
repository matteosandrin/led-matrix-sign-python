from enum import Enum
from PIL import Image, ImageFont
from pathlib import Path

CURRENT_FOLDER = Path(__file__).parent
fonts_dir = CURRENT_FOLDER.parent / 'fonts'
img_dir = CURRENT_FOLDER.parent / 'img'


class SignMode(Enum):
    TEST = 0
    CLOCK = 1
    MBTA = 2
    MTA = 3
    MUSIC = 4
    WIDGET = 5


class UIMessageType(Enum):
    TEST = 0
    MODE_SHIFT = 1
    MODE_CHANGE = 2
    MBTA_CHANGE_STATION = 3
    MBTA_TEST_BANNER = 4
    MTA_CHANGE_STATION = 5
    MTA_ALERT = 6


class RenderMessageType(Enum):
    CLEAR = 0
    FRAME = 1
    SWAP = 2
    TEXT = 3
    CLOCK = 4
    MBTA = 5
    MBTA_BANNER = 6
    MTA = 7
    MTA_ALERT = 8
    MUSIC = 9


class ClockType(Enum):
    DEFAULT = 0
    MBTA = 1
    MTA = 2


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
    MBTA = ImageFont.truetype(str(fonts_dir / 'MBTASans-Regular.otf'), 8)
    SILKSCREEN = ImageFont.truetype(
        str(fonts_dir / 'Silkscreen-Normal.ttf'), 8)
    PICOPIXEL = ImageFont.truetype(str(fonts_dir / 'Picopixel.ttf'), 7)
    LCD = ImageFont.truetype(str(fonts_dir / 'LCD.ttf'), 8)
    MTA = ImageFont.truetype(str(fonts_dir / 'MTASans-Medium.otf'), 10)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


class Colors:
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    MBTA_AMBER = (255, 191, 0)
    SPOTIFY_GREEN = (29, 185, 84)
    MTA_GREEN = hex_to_rgb("#D0FF00")
    MTA_RED_AMBER = hex_to_rgb("#E25822")


class Images:
    ARROW_UP = Image.open(img_dir / 'arrow-up.png')
    ARROW_DOWN = Image.open(img_dir / 'arrow-down.png')
    DEG_SYMBOL = Image.open(img_dir / 'deg-symbol.png')
