# SPDX-License-Identifier: MIT
"""Read the images of a relay message from its `imeta` tags. Stdlib only.

One parser for one tag format (design.md of agent-image-to-chat, fourth FAIL,
gap 7): the push notification (`agents/notify.py`) uses it now, and the chat's
read path (`agent-image-to-chat-read`) reuses it. Both are pinned against the
one recorded event, `chat/testdata/imeta-event.json`.

buzz writes an image message as a caption plus a Markdown line,
`<caption>\\n![image](<url>)`, and one tag
`["imeta", "url <url>", "m image/png", "x <sha256>", "size <n>", "dim <w>x<h>", ...]`.

Neither function ever raises. A malformed tag (tags that are not a list, an
entry that is not a list, an `imeta` entry without fields, a field that is not a
string or has no space) is skipped, so a bad event gives no images and the
unchanged content, and the caller falls back to plain text.
"""

KEYS = ("url", "m", "x", "size", "dim")


def _fields(entry):
    """The `key value` fields of one imeta entry as a dict; bad fields skipped."""
    out = {}
    for field in entry[1:]:
        if not isinstance(field, str) or " " not in field:
            continue
        key, value = field.split(" ", 1)
        out.setdefault(key, value)
    return out


def from_tags(tags):
    """One dict per `imeta` tag whose `m` is an image type, with the keys
    url, m, x, size and dim (None when the tag lacks one). Never raises."""
    if not isinstance(tags, list):
        return []
    images = []
    for entry in tags:
        if not isinstance(entry, list) or not entry or entry[0] != "imeta":
            continue
        fields = _fields(entry)
        if not fields.get("m", "").startswith("image/"):
            continue
        images.append({k: fields.get(k) for k in KEYS})
    return images


def clean_content(content, tags):
    """The caption: `content` without the `![image](<url>)` line of each image,
    leading newline included, then stripped. Unchanged when there is no image
    (or the content is not a string). Never raises."""
    images = from_tags(tags)
    if not images or not isinstance(content, str):
        return content
    for img in images:
        url = img["url"]
        if not url:
            continue
        line = f"![image]({url})"
        content = content.replace("\n" + line, "").replace(line, "")
    return content.strip()
