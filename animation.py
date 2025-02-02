import math
import time
from common import RenderMessageType, Fonts, Colors, Rect
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Tuple
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
        delta = int(max(self.bbox.w, self.text_width()))
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

class AnimationGroup:
    def __init__(self, speed: float):
        self.speed = speed
        self.animation_keys = []
        self.last_update = 0

    def add_animation(self, key: str):
        self.animation_keys.append(key)

    def remove_animation(self, key: str):
        if key in self.animation_keys:
            self.animation_keys.remove(key)

    def is_empty(self):
        return len(self.animation_keys) == 0

    def should_update(self, frame_count: int) -> bool:
        return frame_count - self.last_update >= math.floor(60 / self.speed)

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
                self.animation_groups[animation.speed] = AnimationGroup(animation.speed)
            self.animation_groups[animation.speed].add_animation(key)
    
    def add_animations(self, animations: Dict[str, Animation]):
        with self.lock:
            for key, animation in animations.items():
                self.animations[key] = animation
                if animation.speed not in self.animation_groups:
                    self.animation_groups[animation.speed] = AnimationGroup(animation.speed)
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
            for speed, group in list(self.animation_groups.items()):
                if group.should_update(frame_count):
                    for key in group.animation_keys:
                        animation = self.get_animation(key)
                        frame, is_complete = animation.next_frame()
                        if frame is not None:
                            self.render_queue.put({
                                "type": RenderMessageType.ANIMATION_FRAME,
                                "content": frame
                            })
                            update_count += 1
                        if is_complete:
                            completed_keys.append(key)
                    group.last_update = frame_count
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
            if sleep_time > 0:
                time.sleep(sleep_time)
