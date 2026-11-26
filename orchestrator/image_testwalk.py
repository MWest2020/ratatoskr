# SPDX-License-Identifier: MIT
"""A second, independent walker used only by the tests: to prove a fixture
carries the metadata its table claims, and that image_prep's output is
clean and well-formed. Deliberately not sharing code with image_strip.py —
an independent reader is the point. Not a test module (no test_ prefix),
so discovery does not run it as a test.
"""
import struct
import zlib

JFIF_PAYLOAD = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"


def png_parts(data):
    """[(type, body), ...] for every chunk, in order. Raises on a bad
    signature, a truncated chunk or a bad CRC."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("bad PNG signature")
    pos, parts = 8, []
    while pos < len(data):
        length, ctype = struct.unpack_from(">I4s", data, pos)
        body = data[pos + 8:pos + 8 + length]
        crc, = struct.unpack_from(">I", data, pos + 8 + length)
        if (zlib.crc32(ctype + body) & 0xFFFFFFFF) != crc:
            raise ValueError(f"bad CRC in {ctype!r}")
        parts.append((ctype.decode("latin1"), body))
        pos += 12 + length
        if ctype == b"IEND":
            break
    return parts


def png_sound(data):
    """True when every chunk's CRC checks out and the file ends at IEND."""
    parts = png_parts(data)
    return bool(parts) and parts[-1][0] == "IEND"


def jpeg_segments(data):
    """[(marker:int, payload:bytes), ...]; SOI/EOI carry an empty payload,
    SOS carries its header plus the entropy-coded scan. Raises on a
    structural problem."""
    if data[:2] != b"\xff\xd8":
        raise ValueError("bad JPEG signature")
    pos, segs = 2, [(0xD8, b"")]
    while pos < len(data):
        if data[pos] != 0xFF:
            raise ValueError("expected a marker")
        marker = data[pos + 1]
        pos += 2
        if marker == 0xD9:
            segs.append((marker, b""))
            break
        length = struct.unpack_from(">H", data, pos)[0]
        payload = data[pos + 2:pos + length]
        pos += length
        if marker == 0xDA:   # SOS: skip the entropy-coded scan to the next marker
            i = pos
            while i < len(data) and not (
                    data[i] == 0xFF and i + 1 < len(data)
                    and not (data[i + 1] == 0x00 or 0xD0 <= data[i + 1] <= 0xD7)):
                i += 1
            payload += data[pos:i]
            pos = i
        segs.append((marker, payload))
    return segs


def jpeg_sound(data):
    """True when the file is SOI, the canonical JFIF APP0 and ends at EOI."""
    segs = jpeg_segments(data)
    return (segs[0] == (0xD8, b"") and segs[1] == (0xE0, JFIF_PAYLOAD)
            and segs[-1][0] == 0xD9)


def webp_chunks(data):
    """[(type, body), ...]; raises on a bad signature or a bad RIFF size."""
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("bad WebP signature")
    size, = struct.unpack_from("<I", data, 4)
    if size != len(data) - 8:
        raise ValueError("RIFF size does not match the file length")
    pos, parts = 12, []
    while pos < len(data):
        ctype = data[pos:pos + 4]
        csize, = struct.unpack_from("<I", data, pos + 4)
        body = data[pos + 8:pos + 8 + csize]
        parts.append((ctype.decode("latin1"), body))
        pos += 8 + csize + (csize % 2)
    return parts


def webp_sound(data):
    """True when the RIFF container is well-formed end to end."""
    webp_chunks(data)
    return True
