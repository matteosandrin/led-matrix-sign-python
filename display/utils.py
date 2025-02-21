from PIL import Image
import numpy as np


def get_image_with_color(
        image: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    image = np.array(image.convert("RGB"))
    image = (image / 255) * np.array(color)
    image = image.astype(np.uint8)
    return Image.fromarray(image, mode="RGB")

