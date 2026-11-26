# SPDX-License-Identifier: MIT
"""The strip self-check (design.md "Preparing the image", step 7): list the
output's parts with a walker that has no keep logic, and compare them with
keep-lists written out here, not imported from image_strip. A wrong entry in
image_strip's constants (PNG_KEEP, JFIF_APP0) is then caught, not trusted."""
import struct

from image_strip import Refused

KEEP = {"png": {b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND"},
        "webp": {b"VP8X", b"ALPH", b"VP8 ", b"VP8L"},
        "jpg": {0xD8, 0xD9, 0xE0, 0xDB, 0xC4, 0xDD, 0xC0, 0xC1, 0xC2, 0xDA}}
JFIF_APP0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"   # no thumbnail


def parts(d, fmt):
    """Part names of an output. Each loop step moves >= 12 (PNG), 8 (WebP),
    2 (JPEG marker) or 1 (JPEG scan) bytes."""
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


def check(out, fmt, strip, w, h):
    """Raise Refused("strip self-check failed: …") unless every part of `out`
    is on the keep-list and a second strip gives the same bytes and size."""
    try:
        names = parts(out, fmt)
        recheck, w2, h2 = strip(out)
    except Exception as e:
        raise Refused(f"strip self-check failed: {e}") from e
    extra = [n for n in names if n not in KEEP[fmt]]
    if fmt == "jpg" and (out[2:20] != JFIF_APP0 or names.count(0xE0) != 1):
        extra.append("APP0 other than the canonical JFIF")
    if extra:
        raise Refused(f"strip self-check failed: {extra[0]!r} is not on the keep-list")
    if recheck != out or (w2, h2) != (w, h):
        raise Refused("strip self-check failed: output changed on re-walk")
