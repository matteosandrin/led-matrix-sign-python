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
    w, h = int(w_cells * w_cell_size), int(h_cells * h_cell_size)
    image = Image.new('RGB', (w, h))
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"  # turn off antialiasing
    for i, c in enumerate(text):
        x = (i % w_cells) * w_cell_size
        y = (i // w_cells) * h_cell_size
        draw.text((x, y), c, font=font, fill=Colors.WHITE)
    font_name_raw = font.getname()[0]
    font_name = font_name_raw.replace(' ', '_') if font_name_raw else "unknown"
    image = image.resize((image.width * 4, image.height * 4), Image.Resampling.NEAREST)
    image.save(f'{CURRENT_DIR}/fonts/img/{font_name}.png')
