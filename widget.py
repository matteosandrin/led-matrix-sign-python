from abc import ABC, abstractmethod
import threading
import time
import queue
from typing import Any, Optional
from datetime import datetime
from common import RenderMessageType, Rect, Fonts, Colors, Images
from PIL import Image, ImageDraw
import requests
from pprint import pprint
import numpy as np

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
        self.temp_color_map = {
            -20: (0, 60, 98),      # dark blue
            -10: (120, 162, 204),  # darker blue
            0: (164, 195, 210),    # light blue
            10: (121, 210, 179),   # turquoise  
            20: (252, 245, 112),   # yellow
            30: (255, 150, 79),    # orange
            40: (255, 192, 159),   # red
        }

    def get_image_with_color(self, image: Image.Image, color: tuple[int, int, int]) -> Image.Image:
        image = np.array(image.convert("RGB"))
        image = (image / 255) * np.array(color)
        image = image.astype(np.uint8)
        return Image.fromarray(image, mode="RGB")

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

    def get_temp_color(self, temp: float) -> tuple[int, int, int]:
        """Get interpolated color for a given temperature."""
        temps = sorted(self.temp_color_map.keys())
        if temp <= temps[0]:
            return self.temp_color_map[temps[0]]
        if temp >= temps[-1]:
            return self.temp_color_map[temps[-1]]
        for i in range(len(temps) - 1):
            t1, t2 = temps[i], temps[i + 1]            
            if t1 <= temp <= t2:
                c1 = self.temp_color_map[t1]
                c2 = self.temp_color_map[t2]
                fraction = (temp - t1) / (t2 - t1)
                r = int(c1[0] + fraction * (c2[0] - c1[0]))
                g = int(c1[1] + fraction * (c2[1] - c1[1]))
                b = int(c1[2] + fraction * (c2[2] - c1[2]))
                return (r, g, b)
        return Colors.WHITE

    def update(self):
        weather = self.get_weather()
        if weather is None:
            return
        current_temp = int(round(weather['current']['temperature_2m']))
        min_temp = int(round(weather['daily']['temperature_2m_min'][0]))
        max_temp = int(round(weather['daily']['temperature_2m_max'][0]))
        right_anchor = int(self._draw.textlength("H-00", font=Fonts.LCD))
        self._image.paste((0, 0, 0), (0, 0, self.bbox.w, self.bbox.h))
        current_color = self.get_temp_color(current_temp)
        max_color = self.get_temp_color(max_temp)
        min_color = self.get_temp_color(min_temp)
        arrow_up = self.get_image_with_color(Images.ARROW_UP, max_color)
        arrow_down = self.get_image_with_color(Images.ARROW_DOWN, min_color)
        deg_symbol_max = self.get_image_with_color(Images.DEG_SYMBOL, max_color)
        deg_symbol_min = self.get_image_with_color(Images.DEG_SYMBOL, min_color)
        self._draw.text((right_anchor, 0), f"{current_temp}", font=Fonts.MBTA, fill=current_color, anchor="rt")
        self._image.paste(arrow_up, (0, 16))
        self._draw.text((right_anchor, 16), f"{max_temp}", font=Fonts.LCD, fill=max_color, anchor="rt")
        self._image.paste(deg_symbol_max, (right_anchor, 16))
        self._image.paste(arrow_down, (0, 16+8))
        self._draw.text((right_anchor, 16+8), f"{min_temp}", font=Fonts.LCD, fill=min_color, anchor="rt")
        self._image.paste(deg_symbol_min, (right_anchor, 16+8))

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