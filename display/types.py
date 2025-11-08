from dataclasses import dataclass
from PIL import Image
from common import ClockType
from typing import List, Optional, Tuple
from datetime import datetime
import providers.mbta.types as mbta
import providers.mta.types as mta
import providers.music.types as music
import numpy as np


class Rect:
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def to_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)

    def to_crop_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)

AnimationFrame = Tuple[Rect, Image.Image]

@dataclass
class BaseRenderMessage:
    pass


class RenderMessage:

    @dataclass
    class Clear(BaseRenderMessage):
        pass

    @dataclass
    class Frame(BaseRenderMessage):
        bbox: Rect
        frame: Image.Image
        z_index: int = 0

    @dataclass
    class Swap(BaseRenderMessage):
        pass

    @dataclass
    class Text(BaseRenderMessage):
        text: str
        z_index: int = 0

    @dataclass
    class Clock(BaseRenderMessage):
        clock_type: ClockType
        time: datetime
        z_index: int = 0

    @dataclass
    class MBTA(BaseRenderMessage):
        status: mbta.PredictionStatus
        predictions: List[mbta.Prediction]
        z_index: int = 0

    @dataclass
    class MBTABanner(BaseRenderMessage):
        lines: List[str]
        z_index: int = 0

    @dataclass
    class MTA(BaseRenderMessage):
        predictions: List[mta.TrainTime]
        z_index: int = 0

    @dataclass
    class MTAAlert(BaseRenderMessage):
        text: str
        z_index: int = 0
    
    @dataclass
    class MTATestImages(BaseRenderMessage):
        pass

    @dataclass
    class MTAStartup(BaseRenderMessage):
        pass

    @dataclass
    class MTAStationBanner(BaseRenderMessage):
        station_name: str
        routes: List[str]

    @dataclass
    class Music(BaseRenderMessage):
        status: str
        song: Optional[music.Song]
        z_index: int = 0

    @dataclass
    class GameOfLife(BaseRenderMessage):
        grid: np.ndarray
        generation: int
        z_index: int = 0
