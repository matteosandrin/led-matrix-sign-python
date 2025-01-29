import time
from common import RenderMessageType, Rect
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple
from queue import Queue
from abc import ABC, abstractmethod
import threading


class Animation(ABC):
    def __init__(self, render_queue: Queue, bbox: Rect, speed: int, loop: bool):
        self.render_queue = render_queue
        self.bbox = bbox
        self.speed = speed
        self.loop = loop
        self.frames = []
        self.thread = threading.Thread(target=self.render, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.thread.join()

    def render(self):
        while True:
            for i, frame in enumerate(self.frames):
                print(f"Rendering frame {i}")
                self.render_queue.put({
                    "type": RenderMessageType.IMAGE,
                    "content": (self.bbox, frame)
                })
                time.sleep(self.speed / 1000)
            if not self.loop:
                break

    @abstractmethod
    def render_frames(self):
        """Generate and return a list of frames for the animation"""
        pass


class TextScrollAnimation(Animation):
    def __init__(self, render_queue: Queue, bbox: Rect, speed: int, loop: bool, text: str, font: ImageFont, color: Tuple[int, int, int]):
        super().__init__(render_queue, bbox, speed, loop)
        self.text = text
        if len(self.text) > 0 and self.text[-1] != " ":
            self.text += " "
        self.font = font
        self.color = color
        self.frames = self.render_frames()

    def text_width(self):
        image = Image.new('RGB', (self.bbox.w, self.bbox.h))
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1"  # antialiasing off
        return draw.textlength(self.text, font=self.font)

    def render_frames(self):
        frames = []
        distance = int(max(self.bbox.x, self.text_width()))
        for i in range(0, distance):
            image = Image.new('RGB', (self.bbox.w, self.bbox.h))
            draw = ImageDraw.Draw(image)
            draw.fontmode = "1"  # antialiasing off
            x_pos1, x_pos2 = -i, -i + self.text_width()
            draw.text((x_pos1, 0), self.text, font=self.font, fill=self.color)
            draw.text((x_pos2, 0), self.text, font=self.font, fill=self.color)
            frames.append(image)
        return frames
