from PIL import Image, ImageDraw, ImageFont
from common import Fonts, Colors
from .types import RenderMessage
from typing import Tuple


def render_game_of_life_content(message: RenderMessage.GameOfLife, screen_width: int, screen_height: int) -> Image.Image:
    """Render Conway's Game of Life grid to an image."""
    
    # Create image
    img = Image.new('RGB', (screen_width, screen_height), Colors.BLACK)
    draw = ImageDraw.Draw(img)
    
    grid = message.grid
    grid_height, grid_width = grid.shape
    
    for y in range(min(grid_height, screen_height)):
        for x in range(min(grid_width, screen_width)):
            if grid[y, x]:  # Cell is alive
                draw.point((x, y), fill=Colors.WHITE)
    return img