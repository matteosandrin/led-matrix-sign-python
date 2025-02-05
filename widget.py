from abc import ABC, abstractmethod
import threading
import time
import queue
from typing import Any, Optional
from datetime import datetime
from common import RenderMessageType, Rect, Fonts, Colors
from PIL import Image, ImageDraw

class Widget(ABC):
    def __init__(self, rect: Rect, refresh_rate: float = 1.0):
        self.rect = rect
        self.refresh_rate = refresh_rate
        self.active = False
        self._thread: Optional[threading.Thread] = None
        self._image = Image.new('RGB', (rect.w, rect.h))
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
        return {
            "type": RenderMessageType.FRAME,
            "content": (self.rect, self._image)
        }

class ClockWidget(Widget):
    def __init__(self, rect: Rect):
        super().__init__(rect, refresh_rate=1.0)
        
    def update(self):
        self._image.paste((0, 0, 0), (0, 0, self.rect.w, self.rect.h))
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        self._draw.text((0, 0), time_str, font=Fonts.PICOPIXEL, fill=Colors.WHITE)

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