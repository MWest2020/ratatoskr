#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# /// script
# dependencies = ["cairosvg"]
# ///
"""Rasterise chat/icon.svg into the PNG sizes the manifest asks for.

One source of truth on purpose. The first version of this script *drew* a house
glyph in pure Python next to a hand-written icon.svg, so the two could — and
did — drift apart: change the SVG and the PNGs stayed a house. Now the SVG is
the drawing and this is only a converter.

    uv run chat/gen_icons.py
"""
import os

import cairosvg

HERE = os.path.dirname(os.path.abspath(__file__))
SVG = os.path.join(HERE, "icon.svg")

for size, name in [(192, "icon-192.png"), (512, "icon-512.png"),
                   (180, "apple-touch-icon.png")]:
    cairosvg.svg2png(url=SVG, write_to=os.path.join(HERE, name),
                     output_width=size, output_height=size)
    print("written:", name)
