from PIL import Image
from pathlib import Path
from typing import Dict
from common import hex_to_rgb

base_dir = Path(__file__).parent.parent
image_dir = base_dir.parent / 'img'
route_images: Dict[str, Dict] = {
    "1": {
        "img": Image.open(image_dir / 'mta_1.png'),
        "color": "#EE0900"
    },
    "2": {
        "img": Image.open(image_dir / 'mta_2.png'),
        "color": "#EE0900"
    },
    "3": {
        "img": Image.open(image_dir / 'mta_3.png'),
        "color": "#EE0900"
    },
    "4": {
        "img": Image.open(image_dir / 'mta_4.png'),
        "express_img": Image.open(image_dir / 'mta_4_express.png'),
        "color": "#057500"
    },
    "5": {
        "img": Image.open(image_dir / 'mta_5.png'),
        "color": "#057500"
    },
    "6": {
        "img": Image.open(image_dir / 'mta_6.png'),
        "express_img": Image.open(image_dir / 'mta_6_express.png'),
        "color": "#057500"
    },
    "7": {
        "img": Image.open(image_dir / 'mta_7.png'),
        "color": "#B200A2"
    },
    "A" : {
        "img" : Image.open(image_dir / 'mta_A.png'),
        "color" : "#0039A6"
    },
    # "C" : {
    #     "img" : Image.open(image_dir / 'mta_C.png'),
    #     "color" : "#0039A6"
    # },
    # "E" : {
    #     "img" : Image.open(image_dir / 'mta_E.png'),
    #     "color" : "#0039A6"
    # },
    # "G" : {
    #     "img" : Image.open(image_dir / 'mta_G.png'),
    #     "color" : "#6CBE45"
    # },
    # "B" : {
    #     "img" : Image.open(image_dir / 'mta_B.png'),
    #     "color" : "#FF6800"
    # },
    "D" : {
        "img" : Image.open(image_dir / 'mta_D.png'),
        "color" : "#FF6800"
    },
    "F": {
        "img": Image.open(image_dir / 'mta_F.png'),
        "color": "#FF6800"
    },
    "M": {
        "img": Image.open(image_dir / 'mta_M.png'),
        "color": "#FF6800"
    },
    # "J" : {
    #     "img" : Image.open(image_dir / 'mta_J.png'),
    #     "color" : "#824100"
    # },
    # "Z" : {
    #     "img" : Image.open(image_dir / 'mta_Z.png'),
    #     "color" : "#824100"
    # },
    # "L" : {
    #     "img" : Image.open(image_dir / 'mta_L.png'),
    #     "color" : "#5c5b5b"
    # },
    # "GS" : {
    #     "img" : Image.open(image_dir / 'mta_GS.png'),
    #     "color" : "#3c3e42"
    # },
    # "H" : {
    #     "img" : Image.open(image_dir / 'mta_H.png'),
    #     "color" : "#3c3e42"
    # },
    # "FS" : {
    #     "img" : Image.open(image_dir / 'mta_FS.png'),
    #     "color" : "#3c3e42"
    # },
    # "N" : {
    #     "img" : Image.open(image_dir / 'mta_N.png'),
    #     "color" : "#FCBB0A"
    # },
    "Q" : {
        "img" : Image.open(image_dir / 'mta_Q.png'),
        "color" : "#FCBB0A"
    },
    # "R" : {
    #     "img" : Image.open(image_dir / 'mta_R.png'),
    #     "color" : "#FCBB0A"
    # },
    "W" : {
        "img" : Image.open(image_dir / 'mta_W.png'),
        "color" : "#FCBB0A"
    },
    # "SI" : {
    #     "img" : Image.open(image_dir / 'mta_SI.png'),
    #     "color" : "#0039A6"
    # },
}


def get_route_image(route_id, is_express: bool = False):
    if route_id in route_images:
        item = route_images[route_id]
        if is_express and "express_img" in item:
            return item["express_img"], hex_to_rgb(item["color"])
        return item["img"], hex_to_rgb(item["color"])
    return None
