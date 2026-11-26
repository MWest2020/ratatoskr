# SPDX-License-Identifier: MIT
"""Prepare an image for an agent to post: magic-byte sniff, strip metadata
(image_strip.py), refuse what cannot be stripped without changing the
picture. CLI: python3 image_prep.py <src> <outdir>. See design.md
"Preparing the image"."""
import os
import struct
import sys

import image_strip
from image_strip import Refused

LIMIT = 20 * 1024 * 1024
OUT_LIMIT = 5 * 1024 * 1024
MAX_SIDE = 2560


def _sniff(data):
    if data[:8] == image_strip.PNG_SIG:
        return "png", image_strip.strip_png
    if data[:3] == b"\xff\xd8\xff":
        return "jpg", image_strip.strip_jpeg
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", image_strip.strip_webp
    if data[:4] == b"GIF8":
        raise Refused("GIF is not a supported image type")
    stripped = data.lstrip()
    if stripped[:5].lower() == b"<?xml" or stripped[:4].lower() == b"<svg":
        raise Refused("SVG is not a supported image type")
    if data[4:8] == b"ftyp":
        raise Refused("HEIC/AVIF is not a supported image type")
    if data[:4] == b"%PDF":
        raise Refused("PDF is not a supported image type")
    raise Refused("unknown file type")


def prepare(data):
    """(bytes, ext) for the PNG/JPEG/WebP image prepared for posting, or
    raises Refused(reason). Never decodes or re-encodes the pixel data."""
    if len(data) > LIMIT:
        raise Refused(f"input exceeds {LIMIT} bytes")
    fmt, strip = _sniff(data)
    try:
        out, w, h = strip(data)
    except (struct.error, IndexError, ValueError) as e:
        raise Refused(f"cannot parse {fmt}: {e}") from e
    if w > MAX_SIDE or h > MAX_SIDE:
        raise Refused(
            f'{w}x{h} exceeds {MAX_SIDE} px per side; make it smaller at the source '
            f'(Playwright: no fullPage, viewport or clip <= {MAX_SIDE}, scale: "css"; '
            f'matplotlib: figsize x dpi <= {MAX_SIDE})')
    if len(out) > OUT_LIMIT:
        raise Refused(f"output is {len(out)} bytes, over the {OUT_LIMIT} byte limit")
    try:
        recheck, w2, h2 = strip(out)
    except Exception as e:
        raise Refused(f"strip self-check failed: {e}") from e
    if recheck != out or (w2, h2) != (w, h):
        raise Refused("strip self-check failed: output changed on re-walk")
    return out, fmt


def main():
    if len(sys.argv) != 3:
        print("usage: image_prep.py <src> <outdir>", file=sys.stderr)
        return 2
    src, outdir = sys.argv[1], sys.argv[2]
    if not os.path.isfile(src):
        print("image_prep: not a regular file", file=sys.stderr)
        return 2
    with open(src, "rb") as f:
        data = f.read(LIMIT + 1)
    try:
        out, ext = prepare(data)
    except Refused as e:
        print(f"image_prep: {e}", file=sys.stderr)
        return 2
    path = os.path.join(outdir, f"image.{ext}")
    with open(path, "wb") as f:
        f.write(out)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
