# SPDX-License-Identifier: MIT
# /// script
# dependencies = ["pillow>=12"]
# ///
"""Write the committed image fixtures for orchestrator/test_image_*.py.

Host-only and run by hand; the build, verify.sh and CI never run this file.
They read the committed fixtures with the standard library only. Pillow is
used here for one thing: encoding a small clean base picture. Every piece of
metadata is then added with struct/zlib byte surgery, so what each fixture
carries is visible below and not left to an encoder's defaults.

    uv run --offline orchestrator/testdata/make_image_fixtures.py
"""
import io
import os
import struct
import zlib

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 24, 16                      # not square: a swapped width/height shows
XMP = (b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF><rdf:Description '
       b'xmlns:dc="http://purl.org/dc/elements/1.1/" dc:creator="fixture-author"/>'
       b'</rdf:RDF></x:xmpmeta>')
ICC = b"\x00\x00\x00\x80fixture-icc-profile" + b"\x00" * 100


def tiff(orientation):
    """A big-endian TIFF block: IFD0 with Orientation and a GPS IFD pointer,
    and a GPS IFD holding a latitude of 52 N."""
    ifd0_at, gps_at = 8, 8 + 2 + 2 * 12 + 4
    rat_at = gps_at + 2 + 2 * 12 + 4
    out = b"MM\x00\x2a" + struct.pack(">I", ifd0_at)
    out += struct.pack(">H", 2)
    out += struct.pack(">HHIHH", 0x0112, 3, 1, orientation, 0)    # Orientation
    out += struct.pack(">HHII", 0x8825, 4, 1, gps_at)             # GPS IFD
    out += struct.pack(">I", 0)
    out += struct.pack(">H", 2)
    out += struct.pack(">HHI4s", 0x0001, 2, 2, b"N\x00\x00\x00")   # GPSLatitudeRef
    out += struct.pack(">HHII", 0x0002, 5, 3, rat_at)             # GPSLatitude
    out += struct.pack(">I", 0)
    return out + struct.pack(">6I", 52, 1, 22, 1, 0, 1)


def png_chunk(ctype, data):
    return (struct.pack(">I", len(data)) + ctype + data
            + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF))


def png(orientation):
    raw = b"".join(b"\x00" + bytes(v for x in range(W) for v in (x * 10, y * 15, 128))
                   for y in range(H))
    idat = zlib.compress(raw, 9)
    half = len(idat) // 2
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
            + png_chunk(b"gAMA", struct.pack(">I", 45455))
            + png_chunk(b"iCCP", b"fixture\x00\x00" + zlib.compress(ICC))
            + png_chunk(b"pHYs", struct.pack(">IIB", 2835, 2835, 1))
            + png_chunk(b"tEXt", b"Author\x00fixture-author")
            + png_chunk(b"zTXt", b"Comment\x00\x00" + zlib.compress(b"fixture-comment"))
            + png_chunk(b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00" + XMP)
            + png_chunk(b"eXIf", tiff(orientation))
            + png_chunk(b"tIME", struct.pack(">HBBBBB", 2026, 11, 26, 12, 0, 0))
            + png_chunk(b"IDAT", idat[:half]) + png_chunk(b"IDAT", idat[half:])
            + png_chunk(b"prVt", b"private ancillary chunk")
            + png_chunk(b"IEND", b""))


def base_rgb():
    im = Image.new("RGB", (W, H))
    im.putdata([(x * 10, y * 15, 128) for y in range(H) for x in range(W)])
    return im


def encode(im, fmt, **kw):
    buf = io.BytesIO()
    im.save(buf, fmt, **kw)
    return buf.getvalue()


def jseg(marker, payload):
    return b"\xff" + bytes([marker]) + struct.pack(">H", len(payload) + 2) + payload


def jpeg_split(data):
    """(SOI, [APPn segments Pillow wrote], everything from the first DQT on)."""
    pos = 2
    while data[pos + 1] in range(0xE0, 0xF0):
        pos += 2 + struct.unpack(">H", data[pos + 2:pos + 4])[0]
    return data[:2], data[pos:]


def jpeg_dirty(orientation, progressive=False):
    soi, rest = jpeg_split(encode(base_rgb(), "JPEG", quality=85, progressive=progressive))
    jfif_thumb = b"JFIF\x00\x01\x02\x01\x00H\x00H\x02\x01" + b"\xff\x00\x00\x00\xff\x00"
    meta = (jseg(0xE0, jfif_thumb)
            + jseg(0xE1, b"Exif\x00\x00" + tiff(orientation))
            + jseg(0xE1, b"http://ns.adobe.com/xap/1.0/\x00" + XMP)
            + jseg(0xE2, b"ICC_PROFILE\x00\x01\x01" + ICC)
            + jseg(0xED, b"Photoshop 3.0\x008BIM\x04\x04\x00\x00\x00\x00\x00\x0c"
                   b"\x1c\x02\x50\x00\x07fixture")
            + jseg(0xFE, b"fixture-comment"))
    if progressive:                # a COM between two scans: the walker must keep going
        second_sos = rest.index(b"\xff\xda", rest.index(b"\xff\xda") + 2)
        cut = rest.rindex(b"\xff\xc4", 0, second_sos)
        rest = rest[:cut] + jseg(0xFE, b"between-scans-comment") + rest[cut:]
    return soi + meta + rest + b"TRAILER-after-EOI fixture-author"


def riff(chunks):
    body = b"WEBP" + b"".join(chunks)
    return b"RIFF" + struct.pack("<I", len(body)) + body


def wchunk(ctype, data):
    return ctype + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) % 2 else b"")


def webp_chunks(data):
    pos, out = 12, []
    while pos < len(data):
        ctype, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        out.append((ctype, data[pos + 8:pos + 8 + size]))
        pos += 8 + size + (size & 1)
    return out


def vp8x(flags):
    return wchunk(b"VP8X", bytes([flags, 0, 0, 0]) + (W - 1).to_bytes(3, "little")
                  + (H - 1).to_bytes(3, "little"))


def webp_dirty(lossless=False, alpha=False):
    im = base_rgb()
    if alpha:                      # a real gradient: an opaque alpha is dropped by libwebp
        im = im.convert("RGBA")
        im.putalpha(Image.linear_gradient("L").resize((W, H)))
    parts = dict(webp_chunks(encode(im, "WEBP", quality=80, lossless=lossless)))
    image = ([wchunk(b"ALPH", parts[b"ALPH"])] if b"ALPH" in parts else []) + [
        wchunk(t, parts[t]) for t in (b"VP8 ", b"VP8L") if t in parts]
    flags = 0x20 | 0x08 | 0x04 | (0x10 if alpha else 0)   # ICC, EXIF, XMP (+alpha)
    return riff([vp8x(flags), wchunk(b"ICCP", ICC)] + image
                + [wchunk(b"EXIF", b"Exif\x00\x00" + tiff(1)), wchunk(b"XMP ", XMP),
                   wchunk(b"fxTR", b"unknown chunk")])


def webp_animated():
    frames = [base_rgb(), base_rgb().transpose(Image.Transpose.FLIP_LEFT_RIGHT)]
    return encode(frames[0], "WEBP", save_all=True, append_images=frames[1:], duration=100)


FIXTURES = {
    "dirty.png": lambda: png(1),
    "rotated.png": lambda: png(6),
    "dirty.jpg": lambda: jpeg_dirty(1),
    "dirty-progressive.jpg": lambda: jpeg_dirty(1, progressive=True),
    "rotated.jpg": lambda: jpeg_dirty(6),
    "cmyk.jpg": lambda: encode(Image.new("CMYK", (W, H), (0, 128, 255, 0)), "JPEG"),
    "dirty-lossy.webp": lambda: webp_dirty(),
    "dirty-lossless.webp": lambda: webp_dirty(lossless=True),
    "dirty-lossy-alpha.webp": lambda: webp_dirty(alpha=True),
    "animated.webp": webp_animated,
}

if __name__ == "__main__":
    for name, make in FIXTURES.items():
        with open(os.path.join(HERE, name), "wb") as f:
            f.write(make())
        print(f"{name}: {os.path.getsize(os.path.join(HERE, name))} bytes")
