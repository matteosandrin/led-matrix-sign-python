import providers.mta as mta
import threading
from .animation import MTAAlertAnimation, MTABlinkAnimation
from .utils import get_image_with_color
from common import Colors, Fonts, Rect
from datetime import datetime
from PIL import Image, ImageFont
from typing import List

def render_mta_content(display, content: List[mta.TrainTime]):
    mta_render_thread = threading.Thread(
        target=_render_mta_content_task,
        args=(display, content)
    )
    mta_render_thread.start()

def _render_mta_content_task(display, content: List[mta.TrainTime]):
    if content is None or len(content) == 0:
        render_mta_empty(display)
        return
    image = Image.new(
        'RGB', (display.SCREEN_WIDTH, display.SCREEN_HEIGHT),
        Colors.BLACK)
    draw = display._get_draw_context_antialiased(image)
    should_run_blink_animation = False
    is_alert_running = display.animation_manager.is_animation_running("mta_alert")
    is_blink_running = display.animation_manager.is_animation_running("mta_blink")
    for i, train in enumerate(content):
        minutes = int(round(train.time / 60.0))
        text_color = Colors.MTA_GREEN
        if train.time <= 30 and i == 0:
            text_color = Colors.MTA_RED_AMBER
            if train.time > 20 and not is_blink_running:
                should_run_blink_animation = True
        x_cursor = 0
        y_cursor = 2 + 16 * i
        number_str = f"{train.display_order+1}."
        number_str_width = display._get_text_length(number_str, Fonts.MTA)
        draw.text((x_cursor, y_cursor), number_str,
                  font=Fonts.MTA, fill=text_color)
        x_cursor += int(number_str_width)
        route_img_data = mta.get_route_image(
            train.route_id, train.is_express)
        if route_img_data is not None:
            route_img, color = route_img_data
            route_img = get_image_with_color(route_img, color)
            image.paste(route_img, (x_cursor, 16 * i))
            x_cursor += 16 + 1
        minutes_str = f"{minutes}min"
        minutes_str_width = display._get_text_length(minutes_str, Fonts.MTA)
        train_str_available_width = display.SCREEN_WIDTH - x_cursor - minutes_str_width
        train_str = trim_train_name(
            display, train.long_name, Fonts.MTA, train_str_available_width)
        draw.text((x_cursor, y_cursor), train_str,
                  font=Fonts.MTA, fill=text_color)
        draw.text((display.SCREEN_WIDTH+1, y_cursor), minutes_str,
                  font=Fonts.MTA, fill=text_color, anchor="rt")
    display.last_mta_image = image
    half_screen_h = int(display.SCREEN_HEIGHT / 2)
    x, y = 0, 0
    if is_alert_running and is_blink_running:
        return
    if is_alert_running:
        # if there is an alert in progress, we only draw the top half of the
        # screen, so the alert can be displayed in the bottom half
        crop_rect = Rect(0, 0, display.SCREEN_WIDTH, half_screen_h)
        image = image.copy().crop(crop_rect.to_crop_tuple())
    if is_blink_running:
        # if the blink animation is running, we only draw the bottom half of the
        # screen, so the blink animation can be displayed in the top half
        crop_rect = Rect(0, half_screen_h, display.SCREEN_WIDTH, half_screen_h)
        image = image.copy().crop(crop_rect.to_crop_tuple())
        x, y = crop_rect.x, crop_rect.y
    if should_run_blink_animation:
        render_mta_blink(display, "0min")
    display._update_display(image, x, y)


def render_mta_alert_content(display, content: str):
    half_screen_h = int(display.SCREEN_HEIGHT / 2)
    bbox = Rect(0, half_screen_h, display.SCREEN_WIDTH, half_screen_h)
    last_frame = display.last_mta_image.copy().crop(bbox.to_crop_tuple())
    alert_animation = MTAAlertAnimation(text=content, bbox=bbox, last_frame=last_frame)
    display.animation_manager.add_animation("mta_alert", alert_animation)

def render_mta_blink(display, text: str):
    text_length = int(display._get_text_length(text, Fonts.MTA))
    x = int(display.SCREEN_WIDTH - text_length)
    bbox = Rect(x, 0, text_length, 16)
    blink_animation = MTABlinkAnimation(text=text, bbox=bbox)
    display.animation_manager.add_animation("mta_blink", blink_animation)

def render_mta_empty(display):
    image = Image.new(
        'RGB', (display.SCREEN_WIDTH, display.SCREEN_HEIGHT),
        Colors.BLACK)
    draw = display._get_draw_context_antialiased(image)
    now = datetime.now()
    draw.text((0, 2 + 16 * 0), "Schedule is not available.", font=Fonts.MTA, fill=Colors.MTA_GREEN)
    draw.text((0, 2 + 16 * 1), now.strftime("%m/%d/%y %-I:%M %p"), font=Fonts.MTA, fill=Colors.MTA_GREEN)
    display._update_display(image)

def trim_train_name(
        display, text: str, font: ImageFont, max_width: int) -> str:
    draw = display._get_draw_context_antialiased(Image.new('RGB', (0, 0)))
    if draw.textlength(text, font=font) <= max_width:
        return text
    if "-" in text:
        parts = text.split("-")
        parts = parts[:-1]
        return trim_train_name(display, "-".join(parts), font, max_width)
    if " " in text:
        parts = text.split(" ")
        parts = parts[:-1]
        return trim_train_name(display, " ".join(parts), font, max_width)
    return display._trim_text_to_fit(text, font, max_width)
