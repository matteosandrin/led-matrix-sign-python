from config import config
if not config.EMULATE_RGB_MATRIX:
    import RPi.GPIO as GPIO
import time
import threading
from typing import Callable, Optional


class Button:
    def __init__(
            self, pin: int, short_press_callback: Optional[Callable[[], None]] = None,
            long_press_callback: Optional[Callable[[], None]] = None,
            long_press_duration: float = 3.0) -> None:
        self.pin = pin
        self.short_press_callback = short_press_callback
        self.long_press_callback = long_press_callback
        self.long_press_duration = long_press_duration  # seconds

        self.button_press_time: Optional[float] = None
        self.button_released = True
        self.long_press_triggered = False  # Flag to prevent multiple triggers
        self.running = True  # Control flag for the monitoring thread

        if not config.EMULATE_RGB_MATRIX:
            self.setup_gpio()
            # Only start the monitoring thread if there's a long press callback
            if self.long_press_callback:
                self.monitor_thread = threading.Thread(
                    target=self._monitor_long_press)
                self.monitor_thread.daemon = True
                self.monitor_thread.start()

    def setup_gpio(self) -> None:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(
            self.pin,
            GPIO.BOTH,
            callback=self._button_callback,
            bouncetime=50
        )

    def _button_callback(self, channel: int) -> None:
        # Button pressed (falling edge)
        if GPIO.input(self.pin) == GPIO.LOW:
            self.button_press_time = time.time()
            self.button_released = False
            self.long_press_triggered = False

        # Button released (rising edge)
        else:
            if self.button_press_time is not None and not self.button_released:
                # Only trigger short press if long press hasn't occurred
                if not self.long_press_triggered and self.short_press_callback:
                    self.short_press_callback()
                self.button_released = True
                self.button_press_time = None

    def _monitor_long_press(self) -> None:
        while self.running:
            if (not self.button_released and
                self.button_press_time is not None and
                    not self.long_press_triggered):

                press_duration = time.time() - self.button_press_time
                if press_duration >= self.long_press_duration and self.long_press_callback:
                    self.long_press_callback()
                    self.long_press_triggered = True

            time.sleep(0.1)

    def cleanup(self) -> None:
        self.running = False  # Stop the monitoring thread
        if not config.EMULATE_RGB_MATRIX:
            GPIO.cleanup()
