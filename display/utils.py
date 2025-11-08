from PIL import Image
import numpy as np


def get_image_with_color(
    image: Image.Image, color: tuple[int, int, int]
) -> Image.Image:
    image_array = np.array(image.convert("RGB"))
    image_array = (image_array / 255) * np.array(color)
    image_array = image_array.astype(np.uint8)
    return Image.fromarray(image_array, mode="RGB")
