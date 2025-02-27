import RPi.GPIO as GPIO
import time
from config import config
from common import UIMessageType


class Button:
    def __init__(self, pin, ui_queue):
        self.pin = pin
        self.ui_queue = ui_queue
        self.button_press_time = None
        self.button_released = True
        self.long_press_duration = 3.0  # seconds

        if not config.EMULATE_RGB_MATRIX:
            self.setup_gpio()

    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(
            self.pin,
            GPIO.BOTH,
            callback=self._button_callback,
            bouncetime=50
        )

    def _button_callback(self, channel):
        # Button pressed (falling edge)
        if GPIO.input(self.pin) == GPIO.LOW:
            self.button_press_time = time.time()
            self.button_released = False

        # Button released (rising edge)
        else:
            if self.button_press_time is not None and not self.button_released:
                press_duration = time.time() - self.button_press_time
                if press_duration >= self.long_press_duration:
                    self.ui_queue.put({"type": UIMessageType.SHUTDOWN})
                else:
                    self.ui_queue.put({"type": UIMessageType.MODE_SHIFT})
                self.button_released = True

    def cleanup(self):
        if not config.EMULATE_RGB_MATRIX:
            GPIO.cleanup()
