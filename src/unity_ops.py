from __future__ import annotations

import mmap
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from settings import PREFERRED_SLOT, TARGET_BYTES, TARGET_SET


@dataclass(frozen=True)
class Segment:
    number: int
    offset: int
    size: int


@dataclass(frozen=True)
class Target:
    package: Path
    segment: Segment
    slot_name: str


def cstr(mm, pos: int, limit: int = 256):
    end = mm.find(b"\0", pos, min(len(mm), pos + limit))
    if end < 0:
        raise ValueError
    return mm[pos:end].decode("utf-8", "replace"), end + 1


def parse_segment(mm, offset: int) -> Optional[int]:
    try:
        p = offset
        signature, p = cstr(mm, p, 16)
        if signature != "UnityFS":
            return None
        version = struct.unpack_from(">I", mm, p)[0]
        p += 4
        _, p = cstr(mm, p, 128)
        _, p = cstr(mm, p, 128)
        size = struct.unpack_from(">Q", mm, p)[0]
        if not (5 <= version <= 20):
            return None
        if size < (p + 8 - offset) or size > len(mm) - offset:
            return None
        return int(size)
    except Exception:
        return None


def segments(pkg: Path) -> list[Segment]:
    found: list[Segment] = []
    with pkg.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        pos = 0
        while True:
            offset = mm.find(b"UnityFS\0", pos)
            if offset < 0:
                break
            size = parse_segment(mm, offset)
            if size:
                found.append(Segment(len(found) + 1, offset, size))
                pos = offset + max(size, 8)
            else:
                pos = offset + 8
    return found


def read_segment(pkg: Path, segment: Segment) -> bytes:
    with pkg.open("rb") as f:
        f.seek(segment.offset)
        data = f.read(segment.size)
    if len(data) != segment.size:
        raise IOError("BPSR file changed while it was being read. Please try again.")
    return data


def texture_objects(env):
    for obj in env.objects:
        if obj.type.name != "Texture2D":
            continue
        try:
            name = obj.peek_name()
        except Exception:
            try:
                name = obj.parse_as_object().m_Name
            except Exception:
                continue
        yield obj, name


def choose_slot(names: set[str], cached_slot: Optional[str] = None) -> Optional[str]:
    if cached_slot and cached_slot in names:
        return cached_slot
    if PREFERRED_SLOT in names:
        return PREFERRED_SLOT

    def slot_number(name: str) -> int:
        match = re.search(r"(\d+)$", name)
        return int(match.group(1)) if match else 9999

    valid = sorted((name for name in names if name in TARGET_SET), key=slot_number)
    return valid[0] if valid else None


def target_name_from_blob(blob: bytes, cached_slot: Optional[str] = None) -> Optional[str]:
    import UnityPy

    try:
        env = UnityPy.load(blob)
        names = {name for _, name in texture_objects(env) if name in TARGET_SET}
        return choose_slot(names, cached_slot)
    except Exception:
        return None


def quick_blob_hint(blob: bytes) -> bool:
    return any(name in blob for name in TARGET_BYTES)


def replace_texture(blob: bytes, image_path: Path, slot_name: str) -> bytes:
    import UnityPy
    from PIL import Image, ImageOps

    env = UnityPy.load(blob)
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).copy()
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")

    changed = 0
    for obj, name in texture_objects(env):
        if name != slot_name:
            continue
        texture = obj.parse_as_object()
        texture.image = image.copy()
        texture.save()
        changed += 1

    if changed != 1:
        raise RuntimeError(
            "The picture slot is different from what was expected. Nothing was installed. "
            "Use Advanced Options → Search Again, then retry."
        )

    # Preserve the bundle's original compression flags. UnityPy's default is uncompressed.
    # A few uncommon UnityFS flag combinations cannot be re-packed exactly by UnityPy;
    # LZ4 is the safer compact fallback rather than silently expanding the bundle.
    try:
        return env.file.save("original")
    except NotImplementedError:
        return env.file.save("lz4")
