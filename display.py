from common import Fonts, Colors, Rect, ClockType
import config
if config.EMULATE_RGB_MATRIX:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
else:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
from io import BytesIO
from typing import List, Tuple, Any
from music import Song, SpotifyResponse
from PIL import Image, ImageDraw, ImageFont
from animation import AnimationManager, MBTABannerAnimation, MoveAnimation, TextScrollAnimation
import mta
import mbta
import numpy as np
import os

PANEL_WIDTH = 32
PANEL_HEIGHT = 32
PANEL_COUNT = 5
SCREEN_WIDTH = PANEL_WIDTH * PANEL_COUNT
SCREEN_HEIGHT = PANEL_HEIGHT


def get_image_with_color(
        image: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    image = np.array(image.convert("RGB"))
    image = (image / 255) * np.array(color)
    image = image.astype(np.uint8)
    return Image.fromarray(image, mode="RGB")


class Display:
    def __init__(self):
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
        self.default_font = Fonts.SILKSCREEN
        self.animation_manager = None
        self.last_mbta_image = None

    def set_animation_manager(self, animation_manager: AnimationManager):
        self.animation_manager = animation_manager
        self.animation_manager.start()

    def clear(self):
        self.animation_manager.clear()
        self.canvas.Clear()
        self.swap_canvas()

    def swap_canvas(self):
        self.matrix.SwapOnVSync(self.canvas)

    def _update_display(self, image: Image, x: int = 0, y: int = 0):
        self.canvas.SetImage(image, int(x), int(y))
        self.swap_canvas()

    def _get_draw_context_antialiased(self, image: Image):
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1"  # turn off antialiasing
        return draw

    def render_text_content(self, text: str):
        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT))
        draw = self._get_draw_context_antialiased(image)
        draw.text((0, 0), text, font=self.default_font, fill=Colors.WHITE)
        self._update_display(image)

    def render_mbta_content(
            self, content: Tuple[mbta.PredictionStatus, List[mbta.Prediction]]):
        # Create new image with black background
        image = Image.new(
            'RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), Colors.BLACK)
        draw = self._get_draw_context_antialiased(image)
        status, predictions = content

        if status in [mbta.PredictionStatus.OK,
                      mbta.PredictionStatus.ERROR_SHOW_CACHED,
                      mbta.PredictionStatus.ERROR_EMPTY]:

            # Swap predictions if first line is empty
            if not predictions[0].label:
                predictions[0], predictions[1] = predictions[1], predictions[0]

            p1, p2 = predictions[0], predictions[1]

            # Draw first prediction line
            draw.text((0, 0), p1.label, font=Fonts.MBTA,
                      fill=Colors.MBTA_AMBER)
            value_width = draw.textlength(p1.value, font=Fonts.MBTA)
            x_pos = max(PANEL_WIDTH * 3, SCREEN_WIDTH - value_width)
            draw.text((x_pos, 0), p1.value, font=Fonts.MBTA,
                      fill=Colors.MBTA_AMBER)

            # Draw second prediction line
            draw.text((0, 16), p2.label, font=Fonts.MBTA,
                      fill=Colors.MBTA_AMBER)
            value_width = draw.textlength(p2.value, font=Fonts.MBTA)
            x_pos = max(PANEL_WIDTH * 3, SCREEN_WIDTH - value_width)
            draw.text((x_pos, 16), p2.value,
                      font=Fonts.MBTA, fill=Colors.MBTA_AMBER)

            # Draw cached data indicator if needed
            if status == mbta.PredictionStatus.ERROR_SHOW_CACHED:
                draw.point((SCREEN_WIDTH - 1, 0), fill=Colors.MBTA_AMBER)
        else:
            draw.text((0, 0), "Failed to fetch MBTA data",
                      font=self.default_font, fill=Colors.MBTA_AMBER)

        self.last_mbta_image = image
        self._update_display(image)

    def render_mbta_banner_content(self, lines: [str]):
        lines = lines[:2]
        # Create new image with black background
        animations = {
            "mbta_banner": MBTABannerAnimation(
                Rect(0, 32, SCREEN_WIDTH, SCREEN_HEIGHT),
                Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT),
                lines[0], lines[1])
        }
        if self.last_mbta_image is not None:
            animations["mbta_content_scroll_away"] = MoveAnimation(
                Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT),
                Rect(0, -SCREEN_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT),
                self.last_mbta_image, speed=60, loop=False)
        self.animation_manager.add_animations(animations)

    def render_music_content(self, content: Tuple[SpotifyResponse, Song]):
        status, song = content

        if status in [SpotifyResponse.OK, SpotifyResponse.OK_SHOW_CACHED,
                      SpotifyResponse.OK_NEW_SONG]:

            progress_bar_image = self._get_progress_bar_image(song)
            self.canvas.SetImage(progress_bar_image, 32,
                                 SCREEN_HEIGHT - progress_bar_image.height)

            if status == SpotifyResponse.OK_NEW_SONG:
                self.animation_manager.remove_animation("song_title")
                self.animation_manager.remove_animation("song_artist")
                title_and_artist_image = self._get_title_and_artist_image(song)
                self.canvas.SetImage(title_and_artist_image, 32, 0)
                animations = {}
                if self._get_text_length(
                        song.title, Fonts.SILKSCREEN) > title_and_artist_image.width:
                    animations["song_title"] = TextScrollAnimation(
                        Rect(32, 0, title_and_artist_image.width, 8), 10,
                        True, song.title, Fonts.SILKSCREEN, Colors.WHITE)
                if self._get_text_length(song.artist, Fonts.SILKSCREEN) > title_and_artist_image.width:
                    animations["song_artist"] = TextScrollAnimation(
                        Rect(32, 8, title_and_artist_image.width, 8), 10,
                        True, song.artist, Fonts.SILKSCREEN, Colors.WHITE)
                self.animation_manager.add_animations(animations)
            if song.cover.data is not None:
                album_art_image = Image.open(
                    BytesIO(song.cover.data),
                    formats=['JPEG'])
                album_art_image = album_art_image.resize((32, 32))
                self.canvas.SetImage(album_art_image, 0, 0)
            self.matrix.SwapOnVSync(self.canvas)

        elif status == SpotifyResponse.EMPTY:
            image = Image.new(
                'RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), Colors.BLACK)
            draw = self._get_draw_context_antialiased(image)
            draw.text((0, 0), "Nothing is playing",
                      font=self.default_font, fill=Colors.SPOTIFY_GREEN)
            self._update_display(image)
        else:
            image = Image.new(
                'RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), Colors.BLACK)
            draw = self._get_draw_context_antialiased(image)
            draw.text((0, 0), "Error querying the spotify API",
                      font=self.default_font, fill=Colors.SPOTIFY_GREEN)
            self._update_display(image)

    def _get_progress_bar_image(self, song: Song):
        image = Image.new('RGB', (SCREEN_WIDTH - 32, 8), Colors.BLACK)
        draw = self._get_draw_context_antialiased(image)
        # Draw progress bar
        progress_bar_width = SCREEN_WIDTH - 32
        progress = song.progress_ms / song.duration_ms
        current_bar_width = int(progress_bar_width * progress)

        # Draw progress bar background
        draw.rectangle(
            [(0, image.height - 2),
                (image.width, image.height)],
            fill=(255, 255, 255))

        # Draw progress bar fill
        if current_bar_width > 0:
            draw.rectangle(
                [(0, image.height - 2),
                    (current_bar_width, image.height)],
                fill=Colors.SPOTIFY_GREEN)

        # Draw time progress
        progress_time = self._format_time(song.progress_ms // 1000, False)
        time_to_end = self._format_time(
            (song.duration_ms - song.progress_ms) // 1000, True)

        small_font = Fonts.PICOPIXEL
        # Draw progress time (left side)
        draw.text((1, 0), progress_time,
                  font=small_font, fill=Colors.SPOTIFY_GREEN)

        # Draw time to end (right side)
        time_to_end_width = draw.textlength(time_to_end, font=small_font)
        draw.text((image.width - time_to_end_width, 0),
                  time_to_end, font=small_font, fill=Colors.SPOTIFY_GREEN)
        return image

    def _get_title_and_artist_image(self, song: Song):
        image = Image.new('RGB', (SCREEN_WIDTH - 32, 24), Colors.BLACK)
        draw = self._get_draw_context_antialiased(image)
        draw.text((0, 0), song.title,
                  font=Fonts.SILKSCREEN, fill=Colors.WHITE)
        draw.text((0, 8), song.artist,
                  font=Fonts.SILKSCREEN, fill=Colors.WHITE)
        return image

    def _get_text_length(self, text: str, font: ImageFont):
        draw = self._get_draw_context_antialiased(Image.new('RGB', (0, 0)))
        return draw.textlength(text, font=font)

    def render_frame_content(self, content: Tuple[Rect, Any]):
        bbox, frame = content
        self.canvas.SetImage(frame, int(bbox.x), int(bbox.y))

    def render_swap_content(self, content: None):
        self.swap_canvas()

    def render_mta_content(self, content: List[mta.TrainTime]):
        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), Colors.BLACK)
        draw = self._get_draw_context_antialiased(image)
        for i, train in enumerate(content):
            minutes = int(round(train.time / 60.0))
            route_img_data = mta.get_route_image(
                train.route_id, train.is_express)
            x_cursor = 0
            if route_img_data is not None:
                route_img, color = route_img_data
                route_img = get_image_with_color(route_img, color)
                image.paste(route_img, (0, 16 * i))
                x_cursor = 16 + 3
            minutes_str = f"{minutes}min"
            minutes_str_width = self._get_text_length(minutes_str, Fonts.MTA)
            train_str_available_width = SCREEN_WIDTH - x_cursor - minutes_str_width
            train_str = self._mta_trim_train_name(
                train.long_name, Fonts.MTA, train_str_available_width)
            draw.text((x_cursor, 2 + 16 * i), train_str,
                      font=Fonts.MTA, fill=Colors.MTA_GREEN)
            draw.text((SCREEN_WIDTH+1, 2 + 16 * i), minutes_str,
                      font=Fonts.MTA, fill=Colors.MTA_GREEN, anchor="rt")
        self._update_display(image)

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

    def _mta_trim_train_name(
            self, text: str, font: ImageFont, max_width: int) -> str:
        draw = self._get_draw_context_antialiased(Image.new('RGB', (0, 0)))
        if draw.textlength(text, font=font) <= max_width:
            return text
        if "-" in text:
            parts = text.split("-")
            parts = parts[:-1]
            return self._mta_trim_train_name("-".join(parts), font, max_width)
        if " " in text:
            parts = text.split(" ")
            parts = parts[:-1]
            return self._mta_trim_train_name(" ".join(parts), font, max_width)
        return self._trim_text_to_fit(text, font, max_width)

    def _trim_text_to_fit(
            self, text: str, font: ImageFont, max_width: int) -> str:
        draw = self._get_draw_context_antialiased(Image.new('RGB', (0, 0)))
        while draw.textlength(text, font=font) > max_width:
            text = text[:-1]
        return text

    def _format_time(self, seconds: int, is_negative: bool) -> str:
        """Helper function to format time strings"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        if hours > 0:
            return f"{'-' if is_negative else ''}{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{'-' if is_negative else ''}{minutes:02d}:{seconds:02d}"
