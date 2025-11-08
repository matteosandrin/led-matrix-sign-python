from PIL import Image
from common import Colors
from .types import RenderMessage
import numpy as np


def render_game_of_life_content(
    message: RenderMessage.GameOfLife, screen_width: int, screen_height: int
) -> Image.Image:
    grid = message.grid
    grid_height, grid_width = grid.shape

    # Convert boolean numpy array to RGB image data
    # Create RGB array: alive cells = white (255,255,255), dead cells = black (0,0,0)
    rgb_array = np.zeros((grid_height, grid_width, 3), dtype=np.uint8)
    rgb_array[grid] = [255, 255, 255]  # Set alive cells to white
    game_img = Image.fromarray(rgb_array, "RGB")

    # If grid is smaller than screen, paste onto black background
    if grid_width != screen_width or grid_height != screen_height:
        img = Image.new("RGB", (screen_width, screen_height), Colors.BLACK)
        img.paste(game_img, (0, 0))
        return img
    else:
        return game_img
