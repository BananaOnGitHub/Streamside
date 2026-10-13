"""Flat sideload-app icons. Appearance variants are left to iOS for this trial."""
from __future__ import annotations

import copy
from pathlib import Path
import struct
import zlib

ICON_DIRECTORY = Path(__file__).resolve().parents[1] / "packaging" / "app-icons"
PHONE_BASES = ["StreamsideIcon29x29", "StreamsideIcon40x40", "StreamsideIcon60x60"]
IPAD_BASES = PHONE_BASES + ["StreamsideIcon76x76", "StreamsideIcon83.5x83.5"]
ICON_SIZES = {
    "StreamsideIcon1024.png": 1024,
    "StreamsideIcon29x29@2x.png": 58,
    "StreamsideIcon29x29@3x.png": 87,
    "StreamsideIcon40x40@2x.png": 80,
    "StreamsideIcon40x40@3x.png": 120,
    "StreamsideIcon60x60@2x.png": 120,
    "StreamsideIcon60x60@3x.png": 180,
    "StreamsideIcon29x29~ipad.png": 29,
    "StreamsideIcon29x29@2x~ipad.png": 58,
    "StreamsideIcon40x40~ipad.png": 40,
    "StreamsideIcon40x40@2x~ipad.png": 80,
    "StreamsideIcon76x76~ipad.png": 76,
    "StreamsideIcon76x76@2x~ipad.png": 152,
    "StreamsideIcon83.5x83.5@2x~ipad.png": 167,
}


def check_png(data: bytes, size: int) -> None:
    """Require complete, ordinary RGB PNGs with the declared square dimensions."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("app icon is not a PNG")
    offset = 8
    kinds = []
    image_data = bytearray()
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("truncated app icon PNG")
        length, kind = struct.unpack_from(">I4s", data, offset)
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("truncated app icon PNG chunk")
        payload = data[offset + 8:end - 4]
        crc = struct.unpack_from(">I", data, end - 4)[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise ValueError("app icon PNG checksum mismatch")
        if not kinds:
            if kind != b"IHDR" or length != 13:
                raise ValueError("app icon PNG must start with IHDR")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if (width, height, depth, color, compression, filtering, interlace) != (size, size, 8, 2, 0, 0, 0):
                raise ValueError(f"app icon must be opaque RGB, {size}x{size}, noninterlaced")
        elif kind == b"IHDR":
            raise ValueError("duplicate app icon PNG header")
        if kind in {b"tRNS", b"acTL", b"fcTL", b"fdAT"}:
            raise ValueError("app icon PNG must not contain transparency or animation")
        if kind == b"IDAT":
            image_data.extend(payload)
        kinds.append(kind)
        offset = end
        if kind == b"IEND":
            if length or offset != len(data):
                raise ValueError("app icon PNG has invalid end/trailing bytes")
            break
    if not kinds or kinds[-1] != b"IEND" or not image_data:
        raise ValueError("incomplete app icon PNG")
    try:
        decoder = zlib.decompressobj()
        # Bound decoding to the exact RGB scanline budget plus one refusal byte.
        budget = size * (size * 3 + 1)
        pixels = decoder.decompress(image_data, budget + 1)
        if len(pixels) != budget or not decoder.eof or decoder.unused_data:
            raise ValueError("invalid app icon PNG image data length")
        if any(pixels[i] > 4 for i in range(0, budget, size * 3 + 1)):
            raise ValueError("invalid app icon PNG scanline filter")
    except zlib.error as error:
        raise ValueError("invalid app icon PNG image data") from error


def load_icons(directory: Path = ICON_DIRECTORY) -> dict[str, bytes]:
    icons = {}
    for name, size in ICON_SIZES.items():
        data = (directory / name).read_bytes()
        check_png(data, size)
        icons[name] = data
    return icons


def apply_icon_info(original: dict) -> dict:
    """Replace only primary-icon metadata; retain native alternate icons/settings."""
    info = copy.deepcopy(original)
    for key, bases in (("CFBundleIcons", PHONE_BASES), ("CFBundleIcons~ipad", IPAD_BASES)):
        existing = info.get(key, {})
        if not isinstance(existing, dict):
            raise ValueError(f"unsupported {key} metadata")
        icons = copy.deepcopy(existing)
        # No CFBundleIconName: that would select Twitch's unchanged asset catalog.
        primary = icons.get("CFBundlePrimaryIcon", {})
        if not isinstance(primary, dict):
            raise ValueError(f"unsupported {key} primary-icon metadata")
        primary = copy.deepcopy(primary)
        primary.pop("CFBundleIconName", None)
        primary.pop("CFBundleIconFile", None)
        primary["CFBundleIconFiles"] = list(bases)
        primary["UIPrerenderedIcon"] = False
        icons["CFBundlePrimaryIcon"] = primary
        info[key] = icons
    # Remove old top-level asset/file selectors as well, including iPad overrides.
    for suffix in ("", "~ipad"):
        for key in ("CFBundleIconName", "CFBundleIconFile", "CFBundleIconFiles"):
            info.pop(key + suffix, None)
        info["UIPrerenderedIcon" + suffix] = False
    return info


def verify_icons(info: dict, root: str, archive, expected: dict[str, bytes]) -> None:
    if info != apply_icon_info(info):
        raise ValueError("app primary-icon metadata does not select Streamside's flat icons")
    for name, data in expected.items():
        entry = f"{root}/{name}"
        if entry not in archive.namelist() or archive.read(entry) != data:
            raise ValueError(f"app icon missing or changed during packaging: {name}")
