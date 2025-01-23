from common import config
if config.EMULATE_RGB_MATRIX:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
else:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
from io import BytesIO
from typing import List, Tuple
from mbta import Prediction, PredictionStatus
from music import Song, SpotifyResponse
from PIL import Image, ImageDraw, ImageFont
import os

PANEL_WIDTH = 32
PANEL_HEIGHT = 32
PANEL_COUNT = 5
SCREEN_WIDTH = PANEL_WIDTH * PANEL_COUNT
SCREEN_HEIGHT = PANEL_HEIGHT
CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))

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

class Display:
    def __init__(self):
        # Configure RGB matrix
        options = RGBMatrixOptions()
        options.rows = PANEL_HEIGHT
        options.cols = PANEL_WIDTH
        options.chain_length = PANEL_COUNT
        options.brightness = 50
        options.hardware_mapping = "adafruit-hat-pwm"

        options.gpio_slowdown = 3

        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()

        self.default_font = Fonts.SILKSCREEN

    def _update_display(self, image: Image):
        self.canvas.SetImage(image)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def _get_draw_context_antialiased(self, image: Image):
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1" # turn off antialiasing
        return draw

    def render_text_content(self, text: str):
        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT))
        draw = self._get_draw_context_antialiased(image)
        draw.text((0, 0), text, font=self.default_font, fill=Colors.WHITE)
        self._update_display(image)

    def render_mbta_content(self, content: Tuple[PredictionStatus, List[Prediction]]):
        # Create new image with black background
        image = Image.new(
            'RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), Colors.BLACK)
        draw = self._get_draw_context_antialiased(image)
        status, predictions = content

        if status in [PredictionStatus.OK,
                      PredictionStatus.ERROR_SHOW_CACHED,
                      PredictionStatus.ERROR_EMPTY]:

            # Swap predictions if first line is empty
            if not predictions[0].label:
                predictions[0], predictions[1] = predictions[1], predictions[0]

            p1, p2 = predictions[0], predictions[1]

            # Draw first prediction line
            draw.text((0, 0), p1.label, font=Fonts.MBTA, fill=Colors.MBTA_AMBER)
            value_width = draw.textlength(p1.value, font=Fonts.MBTA)
            x_pos = max(PANEL_WIDTH * 3, SCREEN_WIDTH - value_width)
            draw.text((x_pos, 0), p1.value, font=Fonts.MBTA,
                      fill=Colors.MBTA_AMBER)

            # Draw second prediction line
            draw.text((0, 16), p2.label, font=Fonts.MBTA, fill=Colors.MBTA_AMBER)
            value_width = draw.textlength(p2.value, font=Fonts.MBTA)
            x_pos = max(PANEL_WIDTH * 3, SCREEN_WIDTH - value_width)
            draw.text((x_pos, 16), p2.value,
                      font=Fonts.MBTA, fill=Colors.MBTA_AMBER)

            # Draw cached data indicator if needed
            if status == PredictionStatus.ERROR_SHOW_CACHED:
                draw.point((SCREEN_WIDTH - 1, 0), fill=Colors.MBTA_AMBER)

        elif status in [PredictionStatus.OK_SHOW_ARR_BANNER_SLOT_1,
                        PredictionStatus.OK_SHOW_ARR_BANNER_SLOT_2,
                        PredictionStatus.OK_SHOW_STATION_BANNER]:
            self.render_mbta_banner_content(status, predictions)
            return
        else:
            draw.text((0, 0), "Failed to fetch MBTA data",
                      font=self.default_font, fill=Colors.MBTA_AMBER)

        self._update_display(image)

    def render_mbta_banner_content(self, status: PredictionStatus, predictions: List[Prediction]):
        # Create new image with black background
        image = Image.new(
            'RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), Colors.BLACK)
        draw = self._get_draw_context_antialiased(image)
        mbta_font = Fonts.MBTA

        if status in [PredictionStatus.OK_SHOW_ARR_BANNER_SLOT_1,
                      PredictionStatus.OK_SHOW_ARR_BANNER_SLOT_2]:
            slot = 0
            if status == PredictionStatus.OK_SHOW_ARR_BANNER_SLOT_2:
                slot = 1

            line1 = f"{predictions[slot].label} train"
            line2 = "is now arriving."

            # Center text for both lines
            width1 = draw.textlength(line1, font=mbta_font)
            width2 = draw.textlength(line2, font=mbta_font)
            x1 = (SCREEN_WIDTH - width1) // 2
            x2 = (SCREEN_WIDTH - width2) // 2

            draw.text((x1, 0), line1, font=mbta_font, fill=Colors.MBTA_AMBER)
            draw.text((x2, 16), line2, font=mbta_font, fill=Colors.MBTA_AMBER)

        elif status == PredictionStatus.OK_SHOW_STATION_BANNER:
            draw.text((0, 0), predictions[0].label,
                      font=self.default_font, fill=Colors.MBTA_AMBER)

        self._update_display(image)

    def render_music_content(self, content: Tuple[SpotifyResponse, Song]):
        status, song = content

        # Create new image with black background
        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), Colors.BLACK)
        draw = self._get_draw_context_antialiased(image)

        if status in [SpotifyResponse.OK, SpotifyResponse.OK_SHOW_CACHED]:
            # Draw progress bar
            progress_bar_width = SCREEN_WIDTH - 32
            progress = song.progress_ms / song.duration_ms
            current_bar_width = int(progress_bar_width * progress)
            
            # Draw progress bar background
            draw.rectangle(
                [(32, SCREEN_HEIGHT - 2), (32 + progress_bar_width, SCREEN_HEIGHT)],
                fill=(255, 255, 255)
            )
            
            # Draw progress bar fill
            if current_bar_width > 0:
                draw.rectangle(
                    [(32, SCREEN_HEIGHT - 2), (32 + current_bar_width, SCREEN_HEIGHT)],
                    fill=Colors.SPOTIFY_GREEN
                )
            
            # Draw time progress
            progress_time = self._format_time(song.progress_ms // 1000, False)
            time_to_end = self._format_time((song.duration_ms - song.progress_ms) // 1000, True)
            
            # Use smaller font for time display
            small_font = Fonts.PICOPIXEL

            # Draw song title and artist
            draw.text((32+1, 0), song.title, font=small_font, fill=(255, 255, 255))
            draw.text((32+1, 8), song.artist, font=small_font, fill=(255, 255, 255))
            # Draw progress time (left side)
            progress_time_y = SCREEN_HEIGHT - 8
            draw.text((32 + 1, progress_time_y), progress_time, 
                    font=small_font, fill=Colors.SPOTIFY_GREEN)
            
            # Draw time to end (right side)
            time_to_end_width = draw.textlength(time_to_end, font=small_font)
            draw.text((SCREEN_WIDTH - time_to_end_width - 1, progress_time_y), 
                    time_to_end, font=small_font, fill=Colors.SPOTIFY_GREEN)
            
            # Draw album art if available
            if song.cover.data is not None:
                album_art = Image.open(BytesIO(song.cover.data), formats=['JPEG'])
                album_art = album_art.resize((32, 32))
                image.paste(album_art, (0, 0, 32, 32))

            self._update_display(image)
            
        elif status == SpotifyResponse.EMPTY:
            draw.text((0, 0), "Nothing is playing", 
                    font=self.default_font, fill=Colors.SPOTIFY_GREEN)
            self._update_display(image)
        else:
            draw.text((0, 0), "Error querying the spotify API", 
                    font=self.default_font, fill=Colors.SPOTIFY_GREEN)
            self._update_display(image)

    def _format_time(self, seconds: int, is_negative: bool) -> str:
        """Helper function to format time strings"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{'-' if is_negative else ''}{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{'-' if is_negative else ''}{minutes:02d}:{seconds:02d}"

