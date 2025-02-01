import math
import time
from common import RenderMessageType, Fonts, Colors, Rect
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple
from queue import Queue
from abc import ABC, abstractmethod
import threading

ANIMATION_REFRESH_RATE = 1 / 60.0 # 60 fps

class Animation(ABC):
    def __init__(self, bbox: Rect, speed: float, loop: bool):
        self.bbox = bbox
        self.speed = speed # frames per second
        self.loop = loop
        self.frames = []
        self.current_frame = 0
        self.last_update = 0

    @abstractmethod
    def render_frames(self):
        """Generate and return a list of frames for the animation"""
        pass

    def advance_frame(self) -> bool:
        """Advances to the next frame. Returns True if animation is complete."""
        if not self.frames:
            return False
            
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        
        # Return True if animation should end (non-looping and back to start)
        return not self.loop and self.current_frame == 0

    def get_current_frame(self):
        """Returns the current frame or None if no frames exist"""
        if not self.frames:
            return None
        return self.frames[self.current_frame]

    def next_frame(self):
        """Returns the next frame and advances frame counter. 
        Returns (frame, is_complete) tuple, where frame is None if no frames exist."""
        if not self.frames:
            return None, False
            
        frame = self.frames[self.current_frame]
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        
        # Check if animation should end (non-looping and back to start)
        is_complete = not self.loop and self.current_frame == 0
        
        return frame, is_complete



class TextScrollAnimation(Animation):
    def __init__(
            self, bbox: Rect, speed: float, loop: bool,
            text: str, font: ImageFont, color: Tuple[int, int, int]):
        super().__init__(bbox, speed, loop)
        self.text = text
        if len(self.text) > 0 and self.text[-1] != " ":
            self.text += " " * 4
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
        delta = int(max(self.bbox.x, self.text_width()))
        for i in range(0, delta):
            image = Image.new('RGB', (self.bbox.w, self.bbox.h))
            draw = ImageDraw.Draw(image)
            draw.fontmode = "1"  # antialiasing off
            x_pos1, x_pos2 = -i, -i + self.text_width()
            draw.text((x_pos1, 0), self.text, font=self.font, fill=self.color)
            draw.text((x_pos2, 0), self.text, font=self.font, fill=self.color)
            frames.append((self.bbox, image))
        return frames

class MBTABannerAnimation(Animation):
    def __init__(
            self, start_bbox: Rect, end_bbox: Rect,
            line1: str, line2: str):
        super().__init__(start_bbox, 60, False)
        self.start_bbox = start_bbox
        self.end_bbox = end_bbox
        self.line1 = line1
        self.line2 = line2
        self.font = Fonts.MBTA
        self.color = Colors.MBTA_AMBER
        self.frames = self.render_frames()

    def render_frames(self):
        frames = []
        image = Image.new('RGB', (self.bbox.w, self.bbox.h))
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1"  # antialiasing off
        line1 = self.line1[:16]
        line2 = self.line2[:16]
        # Center text for both lines
        line1_width = draw.textlength(line1, font=self.font)
        line2_width = draw.textlength(line2, font=self.font)
        x1 = (self.bbox.w - line1_width) // 2
        x2 = (self.bbox.w - line2_width) // 2
        draw.text((x1, 0), self.line1, font=self.font, fill=self.color)
        draw.text((x2, 16), self.line2, font=self.font, fill=self.color)
        x_delta, y_delta = self.end_bbox.x - self.start_bbox.x, self.end_bbox.y - self.start_bbox.y
        delta = math.sqrt(x_delta ** 2 + y_delta ** 2)
        frame_count = int(delta)
        for i in range(0, frame_count + 1):
            x_pos = self.start_bbox.x + (x_delta * i / frame_count)
            y_pos = self.start_bbox.y + (y_delta * i / frame_count)
            frames.append((Rect(x_pos, y_pos, self.bbox.w, self.bbox.h), image))
        return frames

class AnimationManager:
    def __init__(self, render_queue: Queue):
        self.render_queue = render_queue
        self.animations = {}
        self.is_running = False
        self.thread = None
        self.sync_groups = {}
        self.last_update = {}

    def add_animation(self, key: str, animation: Animation):
        self.animations[key] = animation
        if animation.speed not in self.sync_groups:
            self.sync_groups[animation.speed] = []
        self.sync_groups[animation.speed].append(key)
        self.last_update[animation.speed] = 0

    def remove_animation(self, key: str):
        if key in self.animations:
            if self.last_update[self.animations[key].speed] == 0:
                del self.last_update[self.animations[key].speed]
            del self.animations[key]
            for speed, keys in self.sync_groups.items():
                if key in keys:
                    keys.remove(key)
            

    def get_animation(self, key: str):
        return self.animations.get(key)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._run_animations, daemon=True)
            self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join()

    def clear(self):
        self.animations = {}

    def _run_animations(self):
        frame_count = 0
        while self.is_running:
            completed_keys = []
            start_time = time.time()
            
            update_count = 0
            for speed, keys in self.sync_groups.items():
                if frame_count - self.last_update[speed] >= math.floor(60 / speed):
                    for key in keys:
                        animation = self.animations[key]
                        frame, is_complete = animation.next_frame()
                        if frame is not None:
                            self.render_queue.put({
                                "type": RenderMessageType.ANIMATION_FRAME,
                                "content": frame
                            })
                            update_count += 1
                    if is_complete:
                        completed_keys.append(key)
                    self.last_update[speed] = frame_count
            if update_count > 0:
                self.render_queue.put({
                    "type": RenderMessageType.ANIMATION_SWAP,
                    "content": None
                })
                
            for key in completed_keys:
                self.remove_animation(key)
                
            frame_count += 1
            elapsed_time = time.time() - start_time
            sleep_time = min(ANIMATION_REFRESH_RATE, ANIMATION_REFRESH_RATE - elapsed_time)
            time.sleep(sleep_time)