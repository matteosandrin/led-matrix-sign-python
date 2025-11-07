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
    GAME_OF_LIFE = 6

# These modes will not be cycled through, but will be available to be selected
# manually from the web interface
DISABLED_MODES = [SignMode.TEST, SignMode.WIDGET]

class UIMessageType(Enum):
    TEST = 0
    MODE_SHIFT = 1
    MODE_CHANGE = 2
    MBTA_CHANGE_STATION = 3
    MBTA_TEST_BANNER = 4
    MTA_CHANGE_STATION = 5
    MTA_CHANGE_DIRECTION = 6
    MTA_ALERT = 7
    SHUTDOWN = 8


class ClockType(Enum):
    DEFAULT = 0
    MBTA = 1
    MTA = 2


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
    MTA_RED_AMBER = hex_to_rgb("#E28522")


class Images:
    ARROW_UP = Image.open(img_dir / 'arrow-up.png')
    ARROW_DOWN = Image.open(img_dir / 'arrow-down.png')
    DEG_SYMBOL = Image.open(img_dir / 'deg-symbol.png')

def get_next_mode(current_mode: SignMode) -> SignMode:
    modes = list(SignMode)
    current_index = modes.index(current_mode)
    next_index = (current_index + 1) % len(modes)
    next_mode = modes[next_index]
    if next_mode in DISABLED_MODES:
        return get_next_mode(next_mode)
    return next_mode
