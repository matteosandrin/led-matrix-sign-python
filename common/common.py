from enum import Enum
from PIL import Image, ImageFont
from pathlib import Path

CURRENT_FOLDER = Path(__file__).parent
fonts_dir = CURRENT_FOLDER.parent / 'fonts'
img_dir = CURRENT_FOLDER.parent / 'img'


class SignMode(Enum):
    TEST = 0
    MBTA = 1
    CLOCK = 2
    MUSIC = 3
    WIDGET = 4
    MTA = 5

class UIMessageType(Enum):
    TEST = 0
    MODE_SHIFT = 1
    MODE_CHANGE = 2
    MBTA_CHANGE_STATION = 3
    MBTA_TEST_BANNER = 4
    MTA_CHANGE_STATION = 5


class RenderMessageType(Enum):
    CLEAR = 0
    TEXT = 1
    MBTA = 2
    MBTA_BANNER = 3
    MUSIC = 4
    FRAME = 5
    SWAP = 6
    MTA = 7


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
    SILKSCREEN = ImageFont.truetype(str(fonts_dir / 'Silkscreen-Normal.ttf'), 8)
    PICOPIXEL = ImageFont.truetype(str(fonts_dir / 'Picopixel.ttf'), 7)
    LCD = ImageFont.truetype(str(fonts_dir / 'LCD.ttf'), 8)
    MTA = ImageFont.truetype(str(fonts_dir / 'MTASans-Medium.otf'), 10)


class Colors:
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    MBTA_AMBER = (255, 191, 0)
    SPOTIFY_GREEN = (29, 185, 84)

class Images:
    ARROW_UP = Image.open(img_dir / 'arrow-up.png')
    ARROW_DOWN = Image.open(img_dir / 'arrow-down.png')
    DEG_SYMBOL = Image.open(img_dir / 'deg-symbol.png')
