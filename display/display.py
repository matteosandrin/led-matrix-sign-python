import config
if config.EMULATE_RGB_MATRIX:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
else:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
import numpy as np
import providers.mbta as mbta
import providers.mta as mta
from .animation import AnimationManager
from .render_mbta import render_mbta_content, render_mbta_banner_content
from .render_mta import render_mta_content, render_mta_alert_content
from .render_music import render_music_content
from common import Fonts, Colors, Rect, ClockType, RenderMessageType
from PIL import Image, ImageDraw, ImageFont
from providers.music import Song, SpotifyResponse
from queue import Queue
from typing import List, Tuple, Any

PANEL_WIDTH = 32
PANEL_HEIGHT = 32
PANEL_COUNT = 5
SCREEN_WIDTH = PANEL_WIDTH * PANEL_COUNT
SCREEN_HEIGHT = PANEL_HEIGHT


class Display:
    def __init__(self, render_queue: Queue):
        # Configure RGB matrix
        options = RGBMatrixOptions()
        options.rows = PANEL_HEIGHT
        options.cols = PANEL_WIDTH
        options.chain_length = PANEL_COUNT
        if config.EMULATE_RGB_MATRIX:
            options.brightness = 100
        else:
            options.brightness = 50
        options.hardware_mapping = "adafruit-hat-pwm"

        options.gpio_slowdown = 3

        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()
        self.SCREEN_WIDTH = SCREEN_WIDTH
        self.SCREEN_HEIGHT = SCREEN_HEIGHT
        self.PANEL_WIDTH = PANEL_WIDTH
        self.default_font = Fonts.SILKSCREEN
        self.animation_manager = AnimationManager(render_queue)
        self.animation_manager.start()
        self.last_mbta_image = None
        self.last_mta_image = None

    def render(self, message):
        if message.get("type") == RenderMessageType.CLEAR:
            self.clear()
        if message.get("type") == RenderMessageType.FRAME:
            self.render_frame_content(message["content"])
        if message.get("type") == RenderMessageType.SWAP:
            self.swap_canvas()
        if message.get("type") == RenderMessageType.TEXT:
            self.render_text_content(message["content"])
        if message.get("type") == RenderMessageType.CLOCK:
            self.render_clock_content(message["content"])
        if message.get("type") == RenderMessageType.MBTA:
            self.render_mbta_content(message["content"])
        if message.get("type") == RenderMessageType.MBTA_BANNER:
            self.render_mbta_banner_content(message["content"])
        if message.get("type") == RenderMessageType.MTA:
            self.render_mta_content(message["content"])
        if message.get("type") == RenderMessageType.MTA_ALERT:
            self.render_mta_alert_content(message["content"])
        if message.get("type") == RenderMessageType.MUSIC:
            self.render_music_content(message["content"])

    def clear(self):
        self.animation_manager.clear()
        self.canvas.Clear()
        self.swap_canvas()

    def swap_canvas(self):
        self.matrix.SwapOnVSync(self.canvas)

    def render_frame_content(self, content: Tuple[Rect, Any]):
        bbox, frame = content
        self.canvas.SetImage(frame, int(bbox.x), int(bbox.y))

    def render_swap_content(self, content: None):
        self.swap_canvas()

    def render_text_content(self, text: str):
        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT))
        draw = self._get_draw_context_antialiased(image)
        draw.text((0, 0), text, font=self.default_font, fill=Colors.WHITE)
        self._update_display(image)

    def render_mta_content(self, content: List[mta.TrainTime]):
        render_mta_content(self, content)

    def render_mta_alert_content(self, content: str):
        render_mta_alert_content(self, content)

    def render_mbta_content(
            self, content: Tuple
            [mbta.PredictionStatus, List[mbta.Prediction]]):
        render_mbta_content(self, content)

    def render_mbta_banner_content(self, content: List[str]):
        render_mbta_banner_content(self, content)

    def render_music_content(self, content: Tuple[SpotifyResponse, Song]):
        render_music_content(self, content)

    def render_clock_content(self, content):
        clock_type = content["type"]
        clock_time = content["time"]
        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), Colors.BLACK)
        draw = self._get_draw_context_antialiased(image)
        if clock_type == ClockType.MTA:
            lines = [
                clock_time.strftime("%a, %b %-d, %Y"),
                clock_time.strftime("%-I:%M:%S %p")
            ]
            for i, line in enumerate(lines):
                draw.text((SCREEN_WIDTH / 2, 2 + 16 * i), line,
                          font=Fonts.MTA, fill=Colors.MTA_GREEN, anchor="mt")
        self._update_display(image)

    def _update_display(self, image: Image, x: int = 0, y: int = 0):
        self.canvas.SetImage(image, int(x), int(y))
        self.swap_canvas()

    def _get_draw_context_antialiased(self, image: Image):
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1"  # turn off antialiasing
        return draw

    def _get_text_length(self, text: str, font: ImageFont):
        draw = self._get_draw_context_antialiased(Image.new('RGB', (0, 0)))
        return draw.textlength(text, font=font)

    def _trim_text_to_fit(
            self, text: str, font: ImageFont, max_width: int) -> str:
        draw = self._get_draw_context_antialiased(Image.new('RGB', (0, 0)))
        while draw.textlength(text, font=font) > max_width:
            text = text[:-1]
        return text

    def _format_time(self, seconds: int, is_negative: bool) -> str:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        if hours > 0:
            return f"{'-' if is_negative else ''}{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{'-' if is_negative else ''}{minutes:02d}:{seconds:02d}"
