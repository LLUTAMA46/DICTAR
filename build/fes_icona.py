"""Converteix logo.png en dictar.ico (la icona de Windows). Necessita Pillow."""

import os
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
logo = Image.open(os.path.join(AQUI, "..", "logo.png")).convert("RGBA")
logo.save(os.path.join(AQUI, "dictar.ico"),
          sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("Icona feta: build/dictar.ico")
