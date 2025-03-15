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
from .render_mta import render_mta_content, render_mta_alert_content, render_mta_all_images, render_mta_startup
from .render_music import render_music_content
from .types import RenderMessage, BaseRenderMessage, Rect
from common import Fonts, Colors, ClockType
from PIL import Image, ImageDraw, ImageFont
from providers.music.types import Song, SpotifyResponse
from queue import Queue
from typing import List, Tuple, Any
import threading

PANEL_WIDTH = 32
PANEL_HEIGHT = 32
PANEL_COUNT = 5
SCREEN_WIDTH = PANEL_WIDTH * PANEL_COUNT
SCREEN_HEIGHT = PANEL_HEIGHT


class Display:
    def __init__(self, render_queue: Queue):
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
        self.matrix_lock = threading.Lock()

    def render(self, message: BaseRenderMessage):
        if isinstance(message, RenderMessage.Clear):
            self.clear()
        elif isinstance(message, RenderMessage.Frame):
            self.render_frame_content(message)
        elif isinstance(message, RenderMessage.Swap):
            self.swap_canvas()
        elif isinstance(message, RenderMessage.Text):
            self.render_text_content(message)
        elif isinstance(message, RenderMessage.Clock):
            self.render_clock_content(message)
        elif isinstance(message, RenderMessage.MBTA):
            render_mbta_content(self, message)
        elif isinstance(message, RenderMessage.MBTABanner):
            render_mbta_banner_content(self, message)
        elif isinstance(message, RenderMessage.MTA):
            render_mta_content(self, message)
        elif isinstance(message, RenderMessage.MTAAlert):
            render_mta_alert_content(self, message)
        elif isinstance(message, RenderMessage.MTATestImages):
            render_mta_all_images(self)
        elif isinstance(message, RenderMessage.MTAStartup):
            render_mta_startup(self)
        elif isinstance(message, RenderMessage.Music):
            render_music_content(self, message)

    def clear(self):
        self.animation_manager.clear()
        self.canvas.Clear()
        self.swap_canvas()

    def swap_canvas(self):
        with self.matrix_lock:
            self.matrix.SwapOnVSync(self.canvas)

    def render_frame_content(self, message: RenderMessage.Frame):
        self.canvas.SetImage(message.frame, int(message.bbox.x), int(message.bbox.y))

    def render_text_content(self, message: RenderMessage.Text):
        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT))
        draw = self._get_draw_context_antialiased(image)
        draw.text((0, 0), message.text, font=self.default_font, fill=Colors.WHITE)
        self._update_display(image)

    def render_clock_content(self, message: RenderMessage.Clock):
        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), Colors.BLACK)
        draw = self._get_draw_context_antialiased(image)
        if message.clock_type == ClockType.MTA:
            lines = [
                message.time.strftime("%a, %b %-d, %Y"),
                message.time.strftime("%-I:%M:%S %p")
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
