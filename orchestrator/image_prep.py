# SPDX-License-Identifier: MIT
# /// script
# dependencies = ["pillow>=11,<12"]
# ///
"""Prepare an image for `ping.sh --image`: refuse what is not safe, strip the rest.

Every refusal goes to stderr with exit 2 and a reason. On success the prepared
file's path is printed to stdout (written into the output directory given on
the command line); `ping.sh` owns that directory (a `mktemp -d` with a `trap`
cleanup) and this script never deletes it.

Re-encoding from raw pixels (`Image.frombytes(mode, size, tobytes())`) is the
strip: there is no `info` dict, EXIF, XMP, ICC profile or text chunk on the
result to carry over, because nothing of the source object survives except the
pixels themselves. Hand-parsing PNG/JPEG/WebP segments to cut out metadata was
rejected (design.md): that is three container formats to get exactly right,
and the #223 review found exactly this kind of parser still carrying an APP1.

    uv run orchestrator/image_prep.py chart.png /tmp/outdir
"""
import sys
import warnings

MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_SIDE = 2560
MAX_OUTPUT_BYTES = 5 * 1024 * 1024

MAGIC = {
    b"\x89PNG\r\n\x1a\n": ("PNG", "png"),
    b"\xff\xd8\xff": ("JPEG", "jpg"),
    # WebP: RIFF....WEBP — the format marker sits at offset 8, checked separately.
}
WEBP_RIFF = b"RIFF"
WEBP_TAG = b"WEBP"


def refuse(reason):
    sys.stderr.write(f"[image_prep] refused: {reason}\n")
    sys.exit(2)


def sniff(data):
    """Magic bytes only — the extension is never consulted (design.md)."""
    for magic, (fmt, ext) in MAGIC.items():
        if data.startswith(magic):
            return fmt, ext
    if data[:4] == WEBP_RIFF and data[8:12] == WEBP_TAG:
        return "WEBP", "webp"
    return None, None


def load(path):
    import os
    try:
        size = os.path.getsize(path)
    except OSError as e:
        refuse(f"cannot read {path}: {e}")
    if size == 0:
        refuse("empty file")
    if size > MAX_INPUT_BYTES:
        refuse(f"input is {size} bytes, over the {MAX_INPUT_BYTES} limit")

    with open(path, "rb") as f:
        head = f.read(64)
    fmt, ext = sniff(head)
    if fmt is None:
        refuse("not PNG, JPEG or WebP (checked by magic bytes, not the extension)")

    from PIL import Image
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(path, formats=[fmt])
            img.load()
    except Image.DecompressionBombWarning as e:
        refuse(f"image is too large to decode safely: {e}")
    except Image.DecompressionBombError as e:
        refuse(f"image is too large to decode safely: {e}")
    except Exception as e:  # noqa: BLE001 — any decode failure is a refusal, not a crash
        refuse(f"could not decode as {fmt}: {e}")
    return img, fmt, ext


def strip(img):
    """Re-encode from raw pixels: nothing of the source `info`/EXIF/XMP/ICC
    survives, because only the pixel bytes are carried over."""
    from PIL import Image, ImageOps

    img = ImageOps.exif_transpose(img)  # orientation survives the strip
    if getattr(img, "is_animated", False):
        img.seek(0)  # first frame only

    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)

    mode = img.mode
    if mode in ("P", "LA"):
        mode = "RGBA" if "A" in img.getbands() else "RGB"
        img = img.convert(mode)
    elif mode == "CMYK":
        mode = "RGB"
        img = img.convert(mode)

    clean = Image.frombytes(img.mode, img.size, img.tobytes())
    return clean


def save(img, fmt, ext, outdir):
    import os
    path = os.path.join(outdir, f"prepared.{ext}")
    if fmt == "PNG":
        img.save(path, format="PNG", optimize=True)
    elif fmt == "JPEG":
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.save(path, format="JPEG", quality=88)
    else:  # WEBP
        img.save(path, format="WEBP", quality=88)

    size = os.path.getsize(path)
    if size > MAX_OUTPUT_BYTES:
        os.remove(path)
        refuse(f"output is {size} bytes, over the {MAX_OUTPUT_BYTES} limit")
    return path


def main():
    if len(sys.argv) != 3:
        sys.stderr.write("usage: image_prep.py <input path> <output dir>\n")
        sys.exit(2)
    src, outdir = sys.argv[1], sys.argv[2]
    img, fmt, ext = load(src)
    clean = strip(img)
    path = save(clean, fmt, ext, outdir)
    print(path)


if __name__ == "__main__":
    main()
