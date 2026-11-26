# SPDX-License-Identifier: MIT
"""PNG/JPEG/WebP keep-list walkers: no decode, no re-encode, exact lengths
on every kept part, an unknown part dropped or refused — never kept by
accident. design.md "Preparing the image"."""
import struct
import zlib

import image_exif


class Refused(Exception):
    pass

def _check_exif(raw):
    try:
        o = image_exif.read_orientation(raw)
    except (struct.error, IndexError, ValueError) as e:
        raise Refused(f"EXIF unreadable: {e}") from e
    if o is not None and o != 1:
        raise Refused(f"orientation {o}: rotate the pixels before sending")

PNG_SIG = b"\x89PNG\r\n\x1a\n"
PNG_KEEP = (b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND")

def strip_png(data):
    if data[:8] != PNG_SIG: raise ValueError("bad PNG signature")
    pos, kept, seen, ihdr, plte_n = 8, [PNG_SIG], set(), None, 0
    while pos < len(data):
        if pos + 8 > len(data): raise ValueError("chunk header truncated")
        length, ctype = struct.unpack_from(">I4s", data, pos)
        start, end, crc_end = pos + 8, pos + 8 + length, pos + 12 + length
        if end > len(data) or crc_end > len(data): raise ValueError("chunk runs past end of file")
        body = data[start:end]
        crc, = struct.unpack_from(">I", data, end)
        if (zlib.crc32(ctype + body) & 0xFFFFFFFF) != crc: raise Refused(f"bad CRC in {ctype!r}")
        if ctype in (b"acTL", b"fcTL", b"fdAT"): raise Refused("animated PNG")
        if ctype == b"eXIf": _check_exif(body)
        if ctype not in PNG_KEEP:
            if ctype[:1].isupper(): raise Refused(f"unknown critical chunk {ctype!r}")
            pos = crc_end; continue
        if ctype in seen and ctype in (b"IHDR", b"IEND", b"PLTE", b"tRNS"): raise Refused(f"duplicate {ctype!r}")
        if ctype == b"IHDR":
            if pos != 8 or length != 13: raise Refused("IHDR must be the first chunk, 13 bytes")
            ihdr = struct.unpack(">IIBBBBB", body)
        elif ctype == b"PLTE":
            if length % 3 or length > 768: raise Refused("PLTE has a bad length")
            plte_n = length // 3
        elif ctype == b"tRNS":
            ct = ihdr[3] if ihdr else -1
            ok = ((ct == 0 and length == 2) or (ct == 2 and length == 6)
                  or (ct == 3 and 0 < length <= plte_n))
            if not ok: raise Refused("tRNS has a bad length for its colour type")
        seen.add(ctype)
        kept.append(data[pos:crc_end])
        pos = crc_end
        if ctype == b"IEND": break
    if ihdr is None or b"IEND" not in seen: raise Refused("no IHDR or no IEND")
    w, h = ihdr[0], ihdr[1]
    if w == 0 or h == 0: raise Refused("zero width or height")
    return b"".join(kept), w, h

JFIF_APP0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
_SOF_OTHER = (0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF)

def _marker(data, pos):   # fill bytes (extra 0xFF) are skipped, never copied
    if pos >= len(data) or data[pos] != 0xFF: raise Refused("expected a marker")
    pos += 1
    while pos < len(data) and data[pos] == 0xFF: pos += 1
    if pos >= len(data): raise ValueError("marker truncated at end of file")
    return data[pos], pos + 1

def _tables(payload, size_of):   # DQT/DHT: a segment is one or more tables
    p = 0
    while p < len(payload):
        size = size_of(payload, p)
        if size is None or p + size > len(payload): raise Refused("a table runs past the segment")
        p += size
    if p != len(payload): raise Refused("table length does not match its tables")

def _dqt(payload):
    _tables(payload, lambda d, p: 1 + 64 * (1 + (d[p] >> 4)))

def _dht(payload):
    _tables(payload, lambda d, p: (1 + 16 + sum(d[p + 1:p + 17])) if p + 17 <= len(d) else None)

def _sof(payload):
    if len(payload) < 6: raise ValueError("SOF too short")
    height, width = struct.unpack_from(">HH", payload, 1)
    nf = payload[5]
    if len(payload) != 6 + 3 * nf: raise Refused("SOF length does not match its component count")
    if height == 0: raise Refused("a SOF with height 0 (a DNL marker) is not supported")
    if width == 0: raise Refused("zero width")
    if nf not in (1, 3): raise Refused(f"component count {nf} is not 1 or 3")
    if nf == 3 and (payload[6], payload[9], payload[12]) == (0x52, 0x47, 0x42):
        raise Refused("RGB-coded JPEG (component IDs R/G/B): re-save as PNG")
    return width, height

def strip_jpeg(data):
    if data[:3] != b"\xff\xd8\xff": raise ValueError("bad JPEG signature")
    pos, kept, seen_sof, dims = 2, [b"\xff\xd8", JFIF_APP0], False, None
    while True:
        marker, pos = _marker(data, pos)
        if marker == 0xD9: break                        # EOI: trailing bytes dropped
        if marker == 0xD8: raise Refused("duplicate SOI")
        if pos + 2 > len(data): raise ValueError("segment length missing")
        length = struct.unpack_from(">H", data, pos)[0]
        if length < 2: raise Refused("segment length below 2")
        end = pos + length
        if end > len(data): raise ValueError("segment runs past end of file")
        payload = data[pos + 2:end]
        seg = bytes((0xFF, marker)) + data[pos:end]
        if marker == 0xDA:                               # SOS: header + the entropy scan
            if not payload or len(payload) != 4 + 2 * payload[0]: raise Refused("SOS header length does not match its component count")
            i = end
            while i < len(data) and not (
                    data[i] == 0xFF and i + 1 < len(data)
                    and not (data[i + 1] == 0x00 or 0xD0 <= data[i + 1] <= 0xD7)):
                i += 1
            if i >= len(data): raise ValueError("scan runs to end of file without a marker")
            kept.append(seg + data[end:i])
            pos = i; continue
        if marker == 0xDB:
            _dqt(payload)
        elif marker == 0xC4:
            _dht(payload)
        elif marker == 0xDD:
            if len(payload) != 2: raise Refused("DRI is not 2 bytes")
        elif marker in (0xC0, 0xC1, 0xC2):
            if seen_sof: raise Refused("duplicate SOF")
            seen_sof, dims = True, _sof(payload)
        elif marker in _SOF_OTHER: raise Refused(f"SOF marker 0x{marker:02X} is not supported")
        elif marker == 0xEE: raise Refused("APP14 (Adobe colour transform): re-save as PNG")
        elif marker == 0xE1 and payload[:6] == b"Exif\x00\x00":
            _check_exif(payload[6:])
            pos = end; continue
        elif 0xE0 <= marker <= 0xEF or marker == 0xFE:   # other APPn, COM: dropped
            pos = end; continue
        else:
            raise Refused(f"unsupported marker 0x{marker:02X}")
        kept.append(seg)
        pos = end
    if not seen_sof: raise Refused("no SOF")
    kept.append(b"\xff\xd9")
    return b"".join(kept), dims[0], dims[1]

def _wchunk(ctype, body):
    return ctype + struct.pack("<I", len(body)) + body + (b"\x00" if len(body) % 2 else b"")

def _vp8_dims(data):
    if len(data) < 10 or data[3:6] != b"\x9d\x01\x2a": raise Refused("VP8 frame header is not a key frame")
    w = struct.unpack_from("<H", data, 6)[0] & 0x3FFF
    h = struct.unpack_from("<H", data, 8)[0] & 0x3FFF
    if not w or not h: raise Refused("zero width or height")
    return w, h

def _vp8l_dims(data):
    if len(data) < 5 or data[0] != 0x2F: raise Refused("VP8L frame header has a bad signature")
    bits = struct.unpack_from("<I", data, 1)[0]
    return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1

def strip_webp(data):   # simple form (RIFF/WEBP/VP8 or VP8L), or +VP8X+ALPH
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP": raise ValueError("bad WebP signature")
    if struct.unpack_from("<I", data, 4)[0] != len(data) - 8: raise Refused("RIFF size does not match the file length")
    pos, vp8, vp8l, alph, canvas = 12, None, None, None, None
    while pos < len(data):
        if pos + 8 > len(data): raise ValueError("chunk header truncated")
        ctype = data[pos:pos + 4]
        size = struct.unpack_from("<I", data, pos + 4)[0]
        if pos + 8 + size > len(data): raise Refused("chunk runs past the end of the file")
        body = data[pos + 8:pos + 8 + size]
        if ctype in (b"ANIM", b"ANMF"): raise Refused("animated WebP")
        if ctype == b"VP8X":
            if canvas is not None: raise Refused("duplicate VP8X")
            if body[0] & 0x02: raise Refused("animated WebP")
            canvas = (int.from_bytes(body[4:7], "little") + 1, int.from_bytes(body[7:10], "little") + 1)
        elif ctype in (b"VP8 ", b"VP8L"):
            if vp8 is not None or vp8l is not None: raise Refused("more than one image chunk")
            vp8, vp8l = (body, None) if ctype == b"VP8 " else (None, body)
        elif ctype == b"ALPH":
            if alph is not None: raise Refused("more than one ALPH chunk")
            alph = body
        elif ctype == b"EXIF":
            _check_exif(body[6:] if body[:6] == b"Exif\x00\x00" else body)
        pos += 8 + size + (size % 2)
    if vp8 is None and vp8l is None: raise Refused("no image chunk")
    if alph is not None and vp8l is not None: raise Refused("ALPH next to VP8L")
    if alph is not None and vp8 is None: raise Refused("ALPH without VP8")
    frame = _vp8_dims(vp8) if vp8 is not None else _vp8l_dims(vp8l)
    if canvas is not None and canvas != frame: raise Refused("VP8X canvas does not match the frame size")
    if alph is not None:
        out = (_wchunk(b"VP8X", bytes((0x10, 0, 0, 0))
                       + (frame[0] - 1).to_bytes(3, "little")
                       + (frame[1] - 1).to_bytes(3, "little"))
               + _wchunk(b"ALPH", alph) + _wchunk(b"VP8 ", vp8))
    elif vp8 is not None:
        out = _wchunk(b"VP8 ", vp8)
    else:
        out = _wchunk(b"VP8L", vp8l)
    body = b"WEBP" + out
    return b"RIFF" + struct.pack("<I", len(body)) + body, frame[0], frame[1]
