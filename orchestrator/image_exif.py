# SPDX-License-Identifier: MIT
"""Read one Exif/TIFF tag: IFD0's Orientation (0x0112). Nothing else.

Dropping an Exif block without checking its Orientation first would show the
picture sideways — a silent failure, not a missing feature. This does not
walk the GPS IFD or any other tag; it only has to answer "is this rotated".
"""
import struct

ORIENTATION = 0x0112


def read_orientation(data):
    """The Orientation value from IFD0, or None when the tag is absent.

    Raises struct.error/IndexError/ValueError on anything malformed (a bad
    byte order, an offset past the end, a truncated IFD) — the caller's
    catch-all turns that into a clean refusal."""
    if len(data) < 8:
        raise ValueError("TIFF header too short")
    order = data[0:2]
    if order == b"II":
        fmt = "<"
    elif order == b"MM":
        fmt = ">"
    else:
        raise ValueError("bad TIFF byte order")
    magic, = struct.unpack_from(fmt + "H", data, 2)
    if magic != 0x002A:
        raise ValueError("bad TIFF magic number")
    ifd_off, = struct.unpack_from(fmt + "I", data, 4)
    if ifd_off < 8 or ifd_off + 2 > len(data):
        raise ValueError("IFD0 offset out of range")
    count, = struct.unpack_from(fmt + "H", data, ifd_off)
    entries_end = ifd_off + 2 + count * 12
    if entries_end > len(data):
        raise ValueError("IFD0 truncated")
    for i in range(count):
        base = ifd_off + 2 + i * 12
        tag, typ, cnt = struct.unpack_from(fmt + "HHI", data, base)
        if tag == ORIENTATION:
            if typ != 3 or cnt != 1:
                raise ValueError("Orientation tag has an unexpected type")
            value, = struct.unpack_from(fmt + "H", data, base + 8)
            return value
    return None
