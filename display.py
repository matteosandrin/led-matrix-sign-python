from typing import List
from mbta import Prediction
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont

PANEL_WIDTH = 32
PANEL_HEIGHT = 32
PANEL_COUNT = 5
SCREEN_WIDTH = PANEL_WIDTH * PANEL_COUNT
SCREEN_HEIGHT = PANEL_HEIGHT

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
        self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        
    def render_text_content(self, text):
        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT))
        draw = ImageDraw.Draw(image)
        draw.text((0, 0), text, font=self.font, fill=(255, 255, 255))
        self.canvas.SetImage(image)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def render_mbta_content(self, content: List[Prediction]):
        if len(content) != 2:
            print("There should be exactly 2 predictions. Received: ", len(content))
            return
        p1, p2 = content[0], content[1]
        p1_text = f"{p1.label} {p1.value}"
        p2_text = f"{p2.label} {p2.value}"

        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT))
        draw = ImageDraw.Draw(image)
        draw.text((0, 0), p1_text, font=self.font, fill=(255, 255, 255))
        draw.text((0, 16), p2_text, font=self.font, fill=(255, 255, 255))
        self.canvas.SetImage(image)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
