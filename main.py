import json
import time
import threading
import queue
from datetime import datetime
from enum import Enum
import RPi.GPIO as GPIO
from typing import Optional, List
from mbta import MBTA
from display import Display
import config

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
BUTTON_PIN = 18
REFRESH_RATE = 0.1  # seconds
SIGN_MODE_KEY = "sign_mode"
DEFAULT_SIGN_MODE = SignMode.MBTA

# Global queues
ui_queue = queue.Queue(maxsize=16)
provider_queue = queue.Queue(maxsize=32)
render_queue = queue.Queue(maxsize=32)

current_mode = SignMode.MBTA

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
            if message.get("type") == "mbta":
                display.render_mbta_content(message["content"])
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
    mbta = MBTA(api_key=config.MBTA_API_KEY)
    while True:
        if current_mode == SignMode.MBTA:
            status, predictions = mbta.get_predictions_both_directions()
            print(status)
            print(predictions)
            render_queue.put({
                "type": "mbta",
                "content": predictions
            })
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