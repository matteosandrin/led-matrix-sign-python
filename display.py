from typing import List, Tuple
from mbta import Prediction, PredictionStatus
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
import os

PANEL_WIDTH = 32
PANEL_HEIGHT = 32
PANEL_COUNT = 5
SCREEN_WIDTH = PANEL_WIDTH * PANEL_COUNT
SCREEN_HEIGHT = PANEL_HEIGHT
CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))


class Display:
    def __init__(self):
        # Configure RGB matrix
        options = RGBMatrixOptions()
        options.rows = PANEL_HEIGHT
        options.cols = PANEL_WIDTH
        options.chain_length = PANEL_COUNT
        options.brightness = 50
        options.hardware_mapping = "adafruit-hat"

        options.gpio_slowdown = 3

        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()
        self.font = ImageFont.truetype(os.path.join(
            CURRENT_FOLDER, "fonts/MBTASans-Regular.otf"), 8)

        self.colors = {
            "amber": (255, 191, 0),
            "black": (0, 0, 0)
        }

    def render_text_content(self, text: str):
        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT))
        draw = ImageDraw.Draw(image)
        draw.text((0, 0), text, font=self.font, fill=(255, 255, 255))
        self.canvas.SetImage(image)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def render_mbta_content(self, content: Tuple[PredictionStatus, List[Prediction]]):
        AMBER = self.colors["amber"]
        BLACK = self.colors["black"]

        # Create new image with black background
        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), BLACK)
        draw = ImageDraw.Draw(image)
        status, predictions = content

        if status in [PredictionStatus.OK,
                      PredictionStatus.ERROR_SHOW_CACHED,
                      PredictionStatus.ERROR_EMPTY]:

            # Swap predictions if first line is empty
            if not predictions[0].label:
                predictions[0], predictions[1] = predictions[1], predictions[0]

            p1, p2 = predictions[0], predictions[1]

            # Draw first prediction line
            draw.text((0, 0), p1.label, font=self.font, fill=AMBER)
            value_width = draw.textlength(p1.value, font=self.font)
            x_pos = max(PANEL_WIDTH * 3, SCREEN_WIDTH - value_width)
            draw.text((x_pos, 0), p1.value, font=self.font, fill=AMBER)

            # Draw second prediction line
            draw.text((0, 16), p2.label, font=self.font, fill=AMBER)
            value_width = draw.textlength(p2.value, font=self.font)
            x_pos = max(PANEL_WIDTH * 3, SCREEN_WIDTH - value_width)
            draw.text((x_pos, 16), p2.value, font=self.font, fill=AMBER)

            # Draw cached data indicator if needed
            if status == PredictionStatus.ERROR_SHOW_CACHED:
                draw.point((SCREEN_WIDTH - 1, 0), fill=AMBER)

        elif status in [PredictionStatus.OK_SHOW_ARR_BANNER_SLOT_1,
                        PredictionStatus.OK_SHOW_ARR_BANNER_SLOT_2,
                        PredictionStatus.OK_SHOW_STATION_BANNER]:
            self.render_mbta_banner_content(status, predictions)
            return
        else:
            draw.text((0, 0), "Failed to fetch MBTA data",
                      font=self.font, fill=AMBER)

        # Update display
        self.canvas.SetImage(image)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def render_mbta_banner_content(self, status: PredictionStatus, predictions: List[Prediction]):
        AMBER = self.colors["amber"]
        BLACK = self.colors["black"]

        # Create new image with black background
        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), BLACK)
        draw = ImageDraw.Draw(image)

        if status in [PredictionStatus.OK_SHOW_ARR_BANNER_SLOT_1,
                      PredictionStatus.OK_SHOW_ARR_BANNER_SLOT_2]:
            slot = 0
            if status == PredictionStatus.OK_SHOW_ARR_BANNER_SLOT_2:
                slot = 1

            line1 = f"{predictions[slot].label} train"
            line2 = "is now arriving."

            # Center text for both lines
            width1 = draw.textlength(line1, font=self.font)
            width2 = draw.textlength(line2, font=self.font)
            x1 = (SCREEN_WIDTH - width1) // 2
            x2 = (SCREEN_WIDTH - width2) // 2

            draw.text((x1, 0), line1, font=self.font, fill=AMBER)
            draw.text((x2, 16), line2, font=self.font, fill=AMBER)

        elif status == PredictionStatus.OK_SHOW_STATION_BANNER:
            draw.text((0, 0), predictions[0].label, font=self.font, fill=AMBER)

        # Update display
        self.canvas.SetImage(image)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
