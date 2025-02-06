from abc import ABC, abstractmethod
import threading
import time
import queue
from typing import Any, Optional
from datetime import datetime
from common import RenderMessageType, Rect, Fonts, Colors
from PIL import Image, ImageDraw
import requests
from pprint import pprint

class Widget(ABC):
    def __init__(self, bbox: Rect, refresh_rate: float = 1.0):
        self.bbox = bbox
        self.refresh_rate = refresh_rate
        self.active = False
        self._thread: Optional[threading.Thread] = None
        self._image = Image.new('RGB', (bbox.w, bbox.h))
        self._image_lock = threading.Lock()  # Add lock for image access
        self._draw = ImageDraw.Draw(self._image)
        self._draw.fontmode = "1"  # turn off antialiasing

    @abstractmethod
    def update(self) -> None:
        """Update widget content. Must be implemented by subclasses."""
        pass

    def start(self):
        """Start the widget's update thread."""
        if not self._thread:
            self.active = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self):
        """Stop the widget's update thread."""
        self.active = False
        self._thread = None

    def _run(self):
        """Main widget loop."""
        while self.active:
            try:
                self.update()
            except Exception as e:
                print(f"Error in widget {self.__class__.__name__}: {e}")
            time.sleep(self.refresh_rate)

    def get_render_data(self) -> dict:
        """Get the widget's current render data."""
        with self._image_lock:
            return {
                "type": RenderMessageType.FRAME,
                "content": (self.bbox, self._image.copy())
            }

class ClockWidget(Widget):
    def __init__(self, bbox: Rect):
        super().__init__(bbox, refresh_rate=0.1)
        
    def update(self):
        with self._image_lock:
            self._image.paste((0, 0, 0), (0, 0, self.bbox.w, self.bbox.h))
            now = datetime.now()
            if now.microsecond < 500000:
                time_str = now.strftime("%H:%M:%S")
            else:
                time_str = now.strftime("%H %M %S")
            self._draw.text((0, 0), time_str, font=Fonts.MBTA, fill=Colors.WHITE)

class WeatherWidget(Widget):
    def __init__(self, bbox: Rect, ipdata_api_key: str):
        super().__init__(bbox, refresh_rate=30)
        self.ipdata_api_key = ipdata_api_key
        self.location = self.get_location()

    def get_location(self):
        response = requests.get("https://api.ipdata.co", params={
            "api-key": self.ipdata_api_key
        })
        if response.status_code == 200:
            lat, lon = response.json()["latitude"], response.json()["longitude"]
            tz = response.json()["time_zone"]["name"]
            description = response.json()["city"] + ", " + response.json()["region"] + ", " + response.json()["country_name"]
            print(f"Weather location: ({lat}, {lon}) {description}")
            print(f"Weather timezone: {tz}")
            return (lat, lon, tz)
        return None

    def get_weather(self):
        if self.location is not None:
            lat, lon, tz = self.location
        else:
            # New York City
            lat, lon, tz = 40.71427, -74.00597, "America/New_York"
            print("WARNING: No location found, using default location (New York City)")
        response = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min",
            "hourly" : "weather_code",
            "temporal_resolution": "hourly_3",
            "current": "temperature_2m,weather_code",
            "timezone": tz, 
            "forecast_days": "1"
        })
        if response.status_code == 200:
            pprint(response.json())
            return response.json()
        else:
            return None

    def update(self):
        weather = self.get_weather()
        if weather is None:
            return
        current_temp = int(round(weather['current']['temperature_2m']))
        min_temp = int(round(weather['daily']['temperature_2m_min'][0]))
        max_temp = int(round(weather['daily']['temperature_2m_max'][0]))
        right_anchor = self._draw.textlength("H-00", font=Fonts.LCD)
        self._image.paste((0, 0, 0), (0, 0, self.bbox.w, self.bbox.h))
        self._draw.text((0, 0), f"{current_temp}", font=Fonts.MBTA, fill=Colors.WHITE, anchor="lt") # left-top
        self._draw.text((0, 16), f"H", font=Fonts.LCD, fill=Colors.WHITE, anchor="lt") # left-top
        self._draw.text((right_anchor, 16), f"{max_temp}", font=Fonts.LCD, fill=Colors.WHITE, anchor="rt") # right-top
        self._draw.text((0, 16+8), f"L", font=Fonts.LCD, fill=Colors.WHITE, anchor="lt") # left-top
        self._draw.text((right_anchor, 16+8), f"{min_temp}", font=Fonts.LCD, fill=Colors.WHITE, anchor="rt") # right-top

class WidgetManager:
    def __init__(self, render_queue: queue.Queue):
        self.render_queue = render_queue
        self.widgets: list[Widget] = []
        self.active = False
        self._thread: Optional[threading.Thread] = None

    def add_widget(self, widget: Widget):
        """Add a widget to the display."""
        self.widgets.append(widget)

    def remove_widget(self, widget: Widget):
        """Remove a widget from the display."""
        if widget in self.widgets:
            widget.stop()
            self.widgets.remove(widget)

    def start(self):
        """Start all widgets and the manager."""
        if not self._thread:
            self.active = True
            for widget in self.widgets:
                widget.start()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self):
        """Stop all widgets and the manager."""
        self.active = False
        self._thread = None
        for widget in self.widgets:
            widget.stop()

    def _run(self):
        """Main loop to collect and send all widget renders."""
        while self.active:
            for widget in self.widgets:
                self.render_queue.put(widget.get_render_data())
            self.render_queue.put({
                "type": RenderMessageType.SWAP
            })
            time.sleep(0.1)  # Throttle updates 