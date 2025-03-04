from common import Fonts, Colors
from PIL import Image, ImageDraw, ImageFont
import os.path

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

text = """
ABCDEFGHIJKLMNOPQRSTUVWXYZ
abcdefghijklmnopqrstuvwxyz
0123456789 !"#$%&\'()*+,-./
:;<=>?@[\\]^_`{|}~
""".replace('\n', '')
fonts = [f for f in vars(Fonts).values()
         if isinstance(f, ImageFont.FreeTypeFont)]
for font in fonts:
    w_cell_size = max([font.getbbox(c)[2] for c in text]) + 1
    h_cell_size = max([font.getbbox(c)[3] for c in text]) + 1
    w_cells, h_cells = 26, 4
    w, h = w_cells * w_cell_size, h_cells * h_cell_size
    image = Image.new('RGB', (w, h))
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"  # turn off antialiasing
    for i, c in enumerate(text):
        x = (i % w_cells) * w_cell_size
        y = (i // w_cells) * h_cell_size
        draw.text((x, y), text[i], font=font, fill=Colors.WHITE)
    font_name = font.getname()[0].replace(' ', '_')
    image = image.resize((image.width * 4, image.height * 4), Image.Resampling.NEAREST)
    image.save(f'{CURRENT_DIR}/fonts/img/{font_name}.png')
