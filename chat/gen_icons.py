#!/usr/bin/env python3
"""Generate the PWA icons (pure Python, no PIL or rasterizer needed).

Draws a simple 'boomhuis' glyph (roof + house + door) on a green rounded
background and writes real PNGs (192/512 plus 180 apple-touch). Also a crisp
icon.svg for the manifest 'any' size. Idempotent: overwrites the assets.
"""
import struct
import zlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))

BG = (23, 107, 69)       # boomhuis green
BG2 = (14, 74, 47)       # dark roof
CREAM = (244, 236, 216)  # house


def _png(width, height, pixels):
    """pixels: bytearray of RGBA (width*height*4). Returns PNG bytes."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0
        raw += pixels[y * width * 4:(y + 1) * width * 4]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def draw(n):
    px = bytearray(n * n * 4)

    def put(x, y, c, a=255):
        if 0 <= x < n and 0 <= y < n:
            i = (y * n + x) * 4
            px[i], px[i + 1], px[i + 2], px[i + 3] = c[0], c[1], c[2], a

    r = n * 0.22  # corner radius of the background
    for y in range(n):
        for x in range(n):
            # rounded square background
            cx = min(max(x, r), n - r)
            cy = min(max(y, r), n - r)
            inside = (x - cx) ** 2 + (y - cy) ** 2 <= r * r or (
                r <= x <= n - r or r <= y <= n - r)
            if inside:
                put(x, y, BG)

    # house body
    hw, hh = int(n * 0.42), int(n * 0.34)
    hx, hy = (n - hw) // 2, int(n * 0.46)
    for y in range(hy, hy + hh):
        for x in range(hx, hx + hw):
            put(x, y, CREAM)
    # roof (triangle)
    roof_h = int(n * 0.22)
    apex_y = hy - roof_h
    for y in range(apex_y, hy):
        t = (y - apex_y) / max(1, roof_h)
        half = int((hw * 0.62) * t)
        for x in range(n // 2 - half, n // 2 + half):
            put(x, y, BG2)
    # door
    dw, dh = int(n * 0.12), int(n * 0.17)
    dx, dy = (n - dw) // 2, hy + hh - dh
    for y in range(dy, dy + dh):
        for x in range(dx, dx + dw):
            put(x, y, BG2)
    return _png(n, n, px)


for size, name in [(192, "icon-192.png"), (512, "icon-512.png"),
                   (180, "apple-touch-icon.png")]:
    open(os.path.join(HERE, name), "wb").write(draw(size))
    print("written:", name)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" rx="112" fill="rgb{BG}"/>
<polygon points="256,84 380,214 132,214" fill="rgb{BG2}"/>
<rect x="146" y="214" width="220" height="184" fill="rgb{CREAM}"/>
<rect x="226" y="312" width="60" height="86" fill="rgb{BG2}"/>
</svg>'''
open(os.path.join(HERE, "icon.svg"), "w").write(svg)
print("written: icon.svg")
