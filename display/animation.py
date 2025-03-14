import math
import random
import threading
import time
from abc import ABC, abstractmethod
from common import Fonts, Colors
from PIL import Image, ImageDraw, ImageFont
from queue import Queue
from typing import Dict, Tuple
from common import hex_to_rgb
from display.utils import get_image_with_color
from providers import mta
from .types import Rect, RenderMessage

ANIMATION_REFRESH_RATE = 1 / 60.0  # 60 fps


class Animation(ABC):
    def __init__(self, bbox: Rect, speed: float, loop: bool):
        self.bbox = bbox
        self.speed = speed  # frames per second
        self.loop = loop
        self._frame_generator = None
        self._current_frame = None

    @abstractmethod
    def frame_generator(self):
        """Generate frames for the animation one at a time"""
        pass

    def get_next_frame(self) -> Tuple[any, bool]:
        """Returns (frame, is_complete) tuple. Frame is None if no frames exist."""
        if self._frame_generator is None:
            self._frame_generator = self.frame_generator()

        try:
            self._current_frame = next(self._frame_generator)
            return self._current_frame, False
        except StopIteration:
            if self.loop:
                self._frame_generator = self.frame_generator()
                self._current_frame = next(self._frame_generator)
                return self._current_frame, False
            return self._current_frame, True


class TextScrollAnimation(Animation):
    def __init__(
            self, bbox: Rect, speed: float, loop: bool, wrap: bool, text: str,
            font: ImageFont, color: Tuple[int, int, int],
            text_pos=(0, 0), start_blank: bool = False):
        super().__init__(bbox, speed, loop)
        self.text = text
        self.text_pos = text_pos
        self.wrap = wrap
        if self.wrap and len(self.text) > 0 and self.text[-1] != " ":
            self.text += " " * 4
        self.font = font
        self.color = color
        self.start_blank = start_blank

    def text_width(self):
        image = Image.new('RGB', (self.bbox.w, self.bbox.h))
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1"  # antialiasing off
        return draw.textlength(self.text, font=self.font)

    def frame_generator(self):
        tx, ty = self.text_pos
        start = 0
        if self.start_blank:
            start = self.bbox.w
        end = -int(max(self.bbox.w, self.text_width()))
        for i in range(start, end, -1):
            image = Image.new('RGB', (self.bbox.w, self.bbox.h))
            draw = ImageDraw.Draw(image)
            draw.fontmode = "1"  # antialiasing off
            x_pos1 = i
            draw.text((i+tx, ty), self.text,
                      font=self.font, fill=self.color)
            if self.wrap:
                x_pos2 = i + self.text_width()
                draw.text((x_pos2+tx, ty), self.text,
                          font=self.font, fill=self.color)
            yield (self.bbox, image)


class MoveAnimation(Animation):
    def __init__(
            self, start_bbox: Rect, end_bbox: Rect,
            image: Image.Image, speed: float = 60, loop: bool = False):
        super().__init__(start_bbox, speed, loop)
        self.start_bbox = start_bbox
        self.end_bbox = end_bbox
        self.image = image

    def frame_generator(self):
        x_delta = self.end_bbox.x - self.start_bbox.x
        y_delta = self.end_bbox.y - self.start_bbox.y
        delta = math.sqrt(x_delta ** 2 + y_delta ** 2)
        frame_count = int(delta)

        for i in range(0, frame_count + 1):
            x_pos = self.start_bbox.x + (x_delta * i / frame_count)
            y_pos = self.start_bbox.y + (y_delta * i / frame_count)
            yield (Rect(x_pos, y_pos, self.bbox.w, self.bbox.h), self.image)


class MBTABannerAnimation(MoveAnimation):
    def __init__(
            self, start_bbox: Rect, end_bbox: Rect,
            line1: str, line2: str):
        # Create the banner image first
        image = Image.new('RGB', (start_bbox.w, start_bbox.h))
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1"  # antialiasing off

        # Truncate and center text
        line1 = line1[:16]
        line2 = line2[:16]
        font = Fonts.MBTA
        color = Colors.MBTA_AMBER

        line1_width = draw.textlength(line1, font=font)
        line2_width = draw.textlength(line2, font=font)
        x1 = (start_bbox.w - line1_width) // 2
        x2 = (start_bbox.w - line2_width) // 2

        draw.text((x1, 0), line1, font=font, fill=color)
        draw.text((x2, 16), line2, font=font, fill=color)

        # Initialize the move animation with our banner image
        super().__init__(start_bbox, end_bbox, image, speed=60, loop=False)


class MTAAlertAnimation(TextScrollAnimation):
    def __init__(self, text: str, bbox: Rect, last_frame: Image.Image):
        # the last frame is shown right after the text scrolls off the screen,
        # while we wait for the next train update to complete.
        self.last_frame = last_frame
        super().__init__(bbox=bbox,
                         speed=60, loop=False, wrap=False, text=text, font=Fonts.MTA,
                         color=Colors.MTA_RED_AMBER, text_pos=(0, 2), start_blank=True)

    def frame_generator(self):
        for frame in super().frame_generator():
            yield frame
        yield (self.bbox, self.last_frame)

class MTABlinkAnimation(Animation):
    def __init__(self, text: str, bbox: Rect):
        super().__init__(bbox=bbox, speed=6, loop=False)
        self.text_image = self.make_text_image(text)
        self.blank_image = self.make_blank_image()
        # show text 2/3 of the time
        self.text_time_fraction = 2/3

    def make_text_image(self, text: str):
        image = Image.new('RGB', (self.bbox.w, self.bbox.h))
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1"  # antialiasing off
        draw.text((1, 2), text, font=Fonts.MTA, fill=Colors.MTA_RED_AMBER)
        return image
    
    def make_blank_image(self):
        image = Image.new('RGB', (self.bbox.w, self.bbox.h), Colors.BLACK)
        return image

    def frame_generator(self):
        total_time = 15 # seconds
        text_frame_number = int(self.text_time_fraction * self.speed)
        for i in range(total_time):
            for k in range(int(self.speed)):
                if (k < text_frame_number):
                    yield (self.bbox, self.text_image)
                else:
                    yield (self.bbox, self.blank_image)
        # show the text image as the last frame to not leave the screen blank
        yield (self.bbox, self.text_image)

class MTAStartupAnimation(Animation):
    def __init__(self, bbox: Rect):
        super().__init__(bbox=bbox, speed=10, loop=False)
        self.route_images = [
            get_image_with_color(item["img"], hex_to_rgb(item["color"]))
            for _ , item in mta.get_all_route_images().items()]        

    def frame_generator(self):
        random.shuffle(self.route_images)
        frame = Image.new('RGB', (self.bbox.w, self.bbox.h), Colors.BLACK)
        black_square = Image.new('RGB', (16, 16), Colors.BLACK)
        for i in range(2):
            for y in range(0, self.bbox.h, 16):
                for x in range(0, self.bbox.w, 16):
                    index = int((x / 16) + (y / 16) * 10)
                    if i == 0:
                        frame.paste(self.route_images[index], (x, y))
                    else:
                        frame.paste(black_square, (x, y))
                    yield (self.bbox, frame)

class AnimationGroup:
    def __init__(self, speed: float):
        self.speed = speed
        self.animation_keys = []
        self.last_update = 0
        self.frames_per_update = round(1 / (ANIMATION_REFRESH_RATE * self.speed))

    def add_animation(self, key: str):
        self.animation_keys.append(key)

    def remove_animation(self, key: str):
        if key in self.animation_keys:
            self.animation_keys.remove(key)

    def is_empty(self):
        return len(self.animation_keys) == 0

    def should_update(self, frame_count: int) -> bool:
        return frame_count - self.last_update >= self.frames_per_update


class AnimationManager:
    def __init__(self, render_queue: Queue):
        self.render_queue = render_queue
        self.animations = {}
        self.is_running = False
        self.thread = None
        self.animation_groups = {}  # speed -> AnimationGroup
        self.lock = threading.Lock()  # Add lock

    def add_animation(self, key: str, animation: Animation):
        with self.lock:
            self.animations[key] = animation
            if animation.speed not in self.animation_groups:
                self.animation_groups[animation.speed] = AnimationGroup(
                    animation.speed)
            self.animation_groups[animation.speed].add_animation(key)

    def add_animations(self, animations: Dict[str, Animation]):
        with self.lock:
            for key, animation in animations.items():
                self.animations[key] = animation
                if animation.speed not in self.animation_groups:
                    self.animation_groups[animation.speed] = AnimationGroup(
                        animation.speed)
                self.animation_groups[animation.speed].add_animation(key)

    def remove_animation(self, key: str):
        with self.lock:
            if key in self.animations:
                speed = self.animations[key].speed
                group = self.animation_groups[speed]
                group.remove_animation(key)
                if group.is_empty():
                    del self.animation_groups[speed]
                del self.animations[key]

    def get_animation(self, key: str):
        with self.lock:
            return self.animations.get(key)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(
                target=self._run_animations, daemon=True)
            self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join()

    def clear(self):
        self.stop()
        with self.lock:
            self.animations = {}
            self.animation_groups = {}
        self.start()

    def is_animation_running(self, key: str) -> bool:
        with self.lock:
            return key in self.animations

    def _run_animations(self):
        frame_count = 0
        next_frame_time = time.time()
        while self.is_running:
            current_time = time.time()
            if current_time >= next_frame_time:
                next_frame_time = current_time + ANIMATION_REFRESH_RATE
                update_count = 0
                completed_keys = []
                for speed, group in list(self.animation_groups.items()):
                    if group.should_update(frame_count):
                        for key in group.animation_keys:
                            animation = self.get_animation(key)
                            if animation is None:  # Skip if animation was removed
                                completed_keys.append(key)
                                continue
                            frame, is_complete = animation.get_next_frame()
                            if frame is not None:
                                bbox, image = frame
                                self.render_queue.put(RenderMessage.Frame(bbox=bbox, frame=image))
                                update_count += 1
                            if is_complete:
                                completed_keys.append(key)
                        group.last_update = frame_count
                if update_count > 0:
                    self.render_queue.put(RenderMessage.Swap())

                for key in completed_keys:
                    self.remove_animation(key)
                
                frame_count += 1
            time.sleep(0.001)
