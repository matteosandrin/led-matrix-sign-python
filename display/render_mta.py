import providers.mta as mta
from typing import List
from PIL import Image, ImageFont
from common import Colors, Fonts, Rect
from .animation import TextScrollAnimation
from .utils import get_image_with_color


def render_mta_content(display, content: List[mta.TrainTime]):
    image = Image.new(
        'RGB', (display.SCREEN_WIDTH, display.SCREEN_HEIGHT),
        Colors.BLACK)
    draw = display._get_draw_context_antialiased(image)
    for i, train in enumerate(content):
        minutes = int(round(train.time / 60.0))
        route_img_data = mta.get_route_image(
            train.route_id, train.is_express)
        x_cursor = 0
        if route_img_data is not None:
            route_img, color = route_img_data
            route_img = get_image_with_color(route_img, color)
            image.paste(route_img, (0, 16 * i))
            x_cursor = 16 + 3
        minutes_str = f"{minutes}min"
        minutes_str_width = display._get_text_length(minutes_str, Fonts.MTA)
        train_str_available_width = display.SCREEN_WIDTH - x_cursor - minutes_str_width
        train_str = trim_train_name(
            display, train.long_name, Fonts.MTA, train_str_available_width)
        draw.text((x_cursor, 2 + 16 * i), train_str,
                  font=Fonts.MTA, fill=Colors.MTA_GREEN)
        draw.text((display.SCREEN_WIDTH+1, 2 + 16 * i), minutes_str,
                  font=Fonts.MTA, fill=Colors.MTA_GREEN, anchor="rt")
    display.last_mta_image = image
    if display.animation_manager.is_animation_running("mta_alert"):
        # if there is an alert in progress, we only draw the top half of the
        # screen, so the alert can be displayed in the bottom half
        half_screen_h = int(display.SCREEN_HEIGHT / 2)
        image = image.copy().crop((0, 0, display.SCREEN_WIDTH, half_screen_h))
    display._update_display(image)


def render_mta_alert_content(display, content: str):

    def render_alert_complete():
        display._update_display(display.last_mta_image)

    half_screen_h = int(display.SCREEN_HEIGHT / 2)
    alert_animation = TextScrollAnimation(
        bbox=Rect(0, half_screen_h, display.SCREEN_WIDTH, half_screen_h),
        speed=60, loop=False, wrap=False, text=content, font=Fonts.MTA,
        color=Colors.MTA_RED_AMBER, text_pos=(0, 2))
    alert_animation.set_completion_callback(render_alert_complete)
    display.animation_manager.add_animation("mta_alert", alert_animation)


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
