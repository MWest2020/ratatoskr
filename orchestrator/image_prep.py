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
KEEP = {"png": set(image_strip.PNG_KEEP), "webp": {b"VP8X", b"ALPH", b"VP8 ", b"VP8L"},
        "jpg": {0xD8, 0xD9, 0xE0, 0xDB, 0xC4, 0xDD, 0xC0, 0xC1, 0xC2, 0xDA}}   # self-check


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


def _parts(d, fmt):
    """Part names of an output, listed without the stripper's keep logic. Each loop
    step moves >= 12 (PNG), 8 (WebP), 2 (JPEG marker) or 1 (JPEG scan) bytes."""
    names, pos = [], 8 if fmt == "png" else 12 if fmt == "webp" else 0
    while pos < len(d):
        if fmt == "png":
            n, t = struct.unpack_from(">I4s", d, pos); names.append(t); pos += 12 + n
        elif fmt == "webp":
            t, n = struct.unpack_from("<4sI", d, pos); names.append(t); pos += 8 + n + n % 2
        else:
            if d[pos] != 0xFF: raise ValueError(f"no marker at offset {pos}")
            m = d[pos + 1]; names.append(m); pos += 2
            if m in (0xD8, 0xD9): continue
            pos += struct.unpack_from(">H", d, pos)[0]
            while m == 0xDA and not (d[pos] == 0xFF and d[pos + 1] not in (0x00, *range(0xD0, 0xD8))): pos += 1
    return names


def _self_check(out, fmt, strip, w, h):
    try:
        names = _parts(out, fmt)
        recheck, w2, h2 = strip(out)
    except Exception as e:
        raise Refused(f"strip self-check failed: {e}") from e
    extra = [n for n in names if n not in KEEP[fmt]]
    if fmt == "jpg" and (out[2:20] != image_strip.JFIF_APP0 or names.count(0xE0) != 1):
        extra.append("APP0 other than the canonical JFIF")
    if extra:
        raise Refused(f"strip self-check failed: {extra[0]!r} is not on the keep-list")
    if recheck != out or (w2, h2) != (w, h):
        raise Refused("strip self-check failed: output changed on re-walk")


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
    _self_check(out, fmt, strip, w, h)
    return out, fmt


def main():
    if len(sys.argv) != 3:
        print("image_prep: usage: image_prep.py <src> <outdir>", file=sys.stderr)
        return 2
    src, outdir = sys.argv[1], sys.argv[2]
    if not os.path.isfile(src):
        print("image_prep: not a regular file", file=sys.stderr)
        return 2
    try:
        with open(src, "rb") as f:
            data = f.read(LIMIT + 1)
    except OSError as e:
        print(f"image_prep: cannot read the file: {e.strerror or e}", file=sys.stderr)
        return 2
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
