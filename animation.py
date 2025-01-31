import time
from common import RenderMessageType, Rect
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple
from queue import Queue
from abc import ABC, abstractmethod
import threading


class Animation(ABC):
    def __init__(self, bbox: Rect, loop: bool):
        self.bbox = bbox
        self.loop = loop
        self.frames = []
        self.current_frame = 0

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
            self, bbox: Rect, loop: bool,
            text: str, font: ImageFont, color: Tuple[int, int, int]):
        super().__init__(bbox, loop)
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


class AnimationManager:
    def __init__(self, render_queue: Queue):
        self.render_queue = render_queue
        self.animations = {}
        self.is_running = False
        self.thread = None

    def add_animation(self, key: str, animation: Animation):
        self.animations[key] = animation

    def remove_animation(self, key: str):
        if key in self.animations:
            del self.animations[key]

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

    def _run_animations(self):
        while self.is_running:
            completed_keys = []
            start_time = time.time()
            
            for key, animation in self.animations.items():
                frame, is_complete = animation.next_frame()
                if frame is not None:
                    self.render_queue.put({
                        "type": RenderMessageType.ANIMATION_FRAME,
                        "content": (animation.bbox, frame)
                    })
                if is_complete:
                    completed_keys.append(key)
                    
            if self.animations:
                self.render_queue.put({
                    "type": RenderMessageType.ANIMATION_SWAP,
                    "content": None
                })
                
            for key in completed_keys:
                self.remove_animation(key)
                
            elapsed_time = time.time() - start_time
            sleep_time = min(0.1, 0.1 - elapsed_time)
            time.sleep(sleep_time)