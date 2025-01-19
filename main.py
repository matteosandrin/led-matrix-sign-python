import json
import time
import threading
import queue
import ntplib
from datetime import datetime, timezone
import pytz
from enum import Enum
import RPi.GPIO as GPIO
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
import requests
from typing import Optional, List
from mbta import MBTA
# Enum definitions
class SignMode(Enum):
    TEST = 0
    MBTA = 1
    CLOCK = 2
    MUSIC = 3
    MAX = 4

class UIMessageType(Enum):
    MODE_SHIFT = 0
    MODE_CHANGE = 1
    MBTA_CHANGE_STATION = 2

# Constants
PANEL_WIDTH = 32
PANEL_HEIGHT = 32
PANEL_COUNT = 5
SCREEN_WIDTH = PANEL_WIDTH * PANEL_COUNT
SCREEN_HEIGHT = PANEL_HEIGHT
BUTTON_PIN = 18
REFRESH_RATE = 0.1  # seconds
SIGN_MODE_KEY = "sign_mode"
DEFAULT_SIGN_MODE = SignMode.MBTA

# Global queues
ui_queue = queue.Queue(maxsize=16)
provider_queue = queue.Queue(maxsize=32)
render_queue = queue.Queue(maxsize=32)

current_mode = SignMode.MBTA

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
        self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
        
    def render_text_content(self, text):
        image = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT))
        draw = ImageDraw.Draw(image)
        draw.text((0, 0), text, font=self.font, fill=(255, 255, 255))
        self.canvas.SetImage(image)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

class Server:
    def __init__(self):
        # Implement web server functionality if needed
        pass

class MBTA:
    def __init__(self):
        self.api_key = "YOUR_MBTA_API_KEY"
        self.base_url = "https://api-v3.mbta.com"
        
    def get_predictions(self):
        # Implement MBTA API calls
        pass

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, 
                         callback=button_callback, 
                         bouncetime=300)

def button_callback(channel):
    ui_queue.put({"type": UIMessageType.MODE_SHIFT})

def render_task():
    display = Display()
    while True:
        try:
            message = render_queue.get(timeout=REFRESH_RATE)
            if message.get("type") == "text":
                display.render_text_content(message["content"])
            # Add other render types as needed
        except queue.Empty:
            continue

def clock_provider_task():
    while True:
        if current_mode == SignMode.CLOCK:
            now = datetime.now()
            time_str = now.strftime("%A, %B %d %Y\n%H:%M:%S")
            render_queue.put({
                "type": "text",
                "content": time_str
            })
        time.sleep(REFRESH_RATE)

def mbta_provider_task():
    mbta = MBTA(api_key="")
    while True:
        if current_mode == SignMode.MBTA:
            status, predictions = mbta.get_predictions_both_directions()
            print(status)
            print(predictions)
            time.sleep(5)

def main():
    # Setup
    setup_gpio()
    
    # Start threads
    render_thread = threading.Thread(target=render_task, daemon=True)
    clock_thread = threading.Thread(target=clock_provider_task, daemon=True)
    mbta_thread = threading.Thread(target=mbta_provider_task, daemon=True)

    render_thread.start()
    clock_thread.start()
    mbta_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        GPIO.cleanup()

if __name__ == "__main__":
    main()