import providers.mbta as mbta
from typing import Tuple, List
from PIL import Image
from common import Colors, Fonts, Rect
from .animation import MBTABannerAnimation, MoveAnimation


def render_mbta_content(
        display, content: Tuple[mbta.PredictionStatus, List[mbta.Prediction]]):
    # Create new image with black background
    image = Image.new(
        'RGB', (display.SCREEN_WIDTH, display.SCREEN_HEIGHT), Colors.BLACK)
    draw = display._get_draw_context_antialiased(image)
    status, predictions = content

    if status in [mbta.PredictionStatus.OK,
                  mbta.PredictionStatus.ERROR_SHOW_CACHED,
                  mbta.PredictionStatus.ERROR_EMPTY]:
        # Swap predictions if first line is empty
        if not predictions[0].label:
            predictions[0], predictions[1] = predictions[1], predictions[0]

        for i, p in enumerate(predictions):
            draw.text((0, i * 16), p.label, font=Fonts.MBTA,
                    fill=Colors.MBTA_AMBER)
            draw.text((display.SCREEN_WIDTH, i * 16), p.value, font=Fonts.MBTA,
                    fill=Colors.MBTA_AMBER, anchor="rt")

        if status == mbta.PredictionStatus.ERROR_SHOW_CACHED:
            draw.point((display.SCREEN_WIDTH - 1, 0), fill=Colors.MBTA_AMBER)
    else:
        draw.text((0, 0), "Failed to fetch MBTA data",
                  font=display.default_font, fill=Colors.MBTA_AMBER)

    display.last_mbta_image = image
    display._update_display(image)


def render_mbta_banner_content(display, lines: [str]):
    lines = lines[:2]
    animations = {
        "mbta_banner": MBTABannerAnimation(
            Rect(0, 32, display.SCREEN_WIDTH, display.SCREEN_HEIGHT),
            Rect(0, 0, display.SCREEN_WIDTH, display.SCREEN_HEIGHT),
            lines[0], lines[1])
    }
    if display.last_mbta_image is not None:
        animations["mbta_content_scroll_away"] = MoveAnimation(
            Rect(0, 0, display.SCREEN_WIDTH, display.SCREEN_HEIGHT),
            Rect(0, -display.SCREEN_HEIGHT, display.SCREEN_WIDTH, display.SCREEN_HEIGHT),
            display.last_mbta_image, speed=60, loop=False)
    display.animation_manager.add_animations(animations)
