#!/usr/bin/env python3
"""Fail-closed validation of this project's unsigned arm64 Mach-O artifacts.

A build/layout check, not certificate trust or an on-device launch test.
Packagers call verify_bytes directly; make is not the only enforcement point.
"""
from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path

try:
    from .macho import (LC_CODE_SIGNATURE, LC_ID_DYLIB, LC_LOAD_DYLIB,
                        LC_SEGMENT_64, MH_DYLIB, MachOError, dylib_id,
                        dylib_loads, header, load_commands)
except ImportError:
    from macho import (LC_CODE_SIGNATURE, LC_ID_DYLIB, LC_LOAD_DYLIB,
                       LC_SEGMENT_64, MH_DYLIB, MachOError, dylib_id,
                       dylib_loads, header, load_commands)

PAGE_SIZE = 0x4000
FRAMEWORK_IDENTITY = "@rpath/Streamside.framework/Streamside"
DYLIB_IDENTITY = "@rpath/TwitchAdBlock.dylib"


def align(value: int, size: int = PAGE_SIZE) -> int:
    return (value + size - 1) // size * size


def segments(data: bytes) -> list[dict]:
    result = []
    for item in load_commands(data):
        if item.command != LC_SEGMENT_64:
            continue
        if item.size < 72:
            raise MachOError("truncated LC_SEGMENT_64")
        name = data[item.offset + 8:item.offset + 24].split(b"\0", 1)[0].decode("ascii")
        vmaddr, vmsize, fileoff, filesize = struct.unpack_from("<4Q", data, item.offset + 24)
        section_count = struct.unpack_from("<I", data, item.offset + 64)[0]
        if item.size != 72 + section_count * 80:
            raise MachOError(f"{name} has an invalid section table")
        if filesize > vmsize or fileoff + filesize > len(data):
            raise MachOError(f"{name} file range exceeds its VM range or EOF")
        for index in range(section_count):
            section = item.offset + 72 + index * 80
            address, size = struct.unpack_from("<QQ", data, section + 32)
            offset = struct.unpack_from("<I", data, section + 48)[0]
            flags = struct.unpack_from("<I", data, section + 64)[0]
            if address < vmaddr or address + size > vmaddr + vmsize:
                raise MachOError(f"{name} section exceeds its VM range")
            # Zero-fill sections have no corresponding file bytes.
            if size and (flags & 0xFF) not in {1, 0xC, 0x12}:
                if offset < fileoff or offset + size > fileoff + filesize:
                    raise MachOError(f"{name} section exceeds its file range")
        result.append(dict(name=name, vmaddr=vmaddr, vmsize=vmsize,
                           fileoff=fileoff, filesize=filesize))
    if not result or len({s["name"] for s in result}) != len(result):
        raise MachOError("segments are missing or duplicated")
    return result


def _verify_page_aligned_segments(data: bytes, layout: list[dict]) -> None:
    # This is our linker contract, not a permissive generic Mach-O rule.
    if layout[0]["name"] != "__TEXT" or layout[0]["fileoff"] != 0:
        raise MachOError("__TEXT must be the first segment at fileoff 0")
    if layout[-1]["name"] != "__LINKEDIT":
        raise MachOError("__LINKEDIT must be the final segment")
    for segment in layout:
        name = segment["name"]
        if not segment["filesize"]:
            raise MachOError(f"{name} is not file-backed")
        if segment["vmaddr"] % PAGE_SIZE or segment["fileoff"] % PAGE_SIZE:
            raise MachOError(f"{name} does not start on a 16 KiB boundary")
        if not segment["vmsize"] or segment["vmsize"] % PAGE_SIZE:
            raise MachOError(f"{name} virtual size is not 16 KiB aligned")
        if name != "__LINKEDIT" and segment["filesize"] % PAGE_SIZE:
            raise MachOError(f"{name} file size is not 16 KiB aligned")
    for current, following in zip(layout, layout[1:]):
        if (current["vmaddr"] + current["vmsize"] != following["vmaddr"]
                or current["fileoff"] + current["filesize"] != following["fileoff"]):
            raise MachOError(f"{current['name']} does not fill its aligned segment range")
    last = layout[-1]
    if last["fileoff"] + last["filesize"] != len(data):
        raise MachOError("__LINKEDIT file range does not end at EOF")
    if last["vmsize"] != align(last["filesize"]):
        raise MachOError("__LINKEDIT VM size does not round its file size to 16 KiB")


def _verify_signature(data: bytes, offset: int, reserved: int, text: dict,
                      expected_identifier: str | None, compact: bool) -> dict:
    if offset % 16 or reserved % 16 or reserved < 12 or offset + reserved != len(data):
        raise MachOError("signature reservation must be 16-byte aligned and end at EOF")
    magic, length, count = struct.unpack_from(">III", data, offset)
    if magic != 0xFADE0CC0 or not 12 <= length <= reserved or count > (length - 12) // 8:
        raise MachOError("invalid embedded signature superblob")
    if compact and reserved != align(length, 16):
        raise MachOError("sideload signature reservation is not compact")
    if any(data[offset + length:]):
        raise MachOError("signature reservation padding is non-zero")
    ranges, slots, directories = [], set(), []
    for index in range(count):
        slot, relative = struct.unpack_from(">II", data, offset + 12 + index * 8)
        if slot in slots or relative < 12 + count * 8 or relative + 8 > length:
            raise MachOError("invalid or duplicate signature slot")
        slots.add(slot)
        start = offset + relative
        blob_magic, blob_length = struct.unpack_from(">II", data, start)
        if blob_length < 8 or relative + blob_length > length:
            raise MachOError("signature blob is out of bounds")
        ranges.append((relative, relative + blob_length))
        if slot == 0x10000:
            raise MachOError("expected ad-hoc build artifact, not a CMS signature")
        if slot != 0 and not 0x1000 <= slot < 0x1005:
            continue
        if blob_magic != 0xFADE0C02 or blob_length < 88:
            raise MachOError("invalid CodeDirectory")
        version, flags, hash_offset, ident_offset, special, codes, code_limit = struct.unpack_from(
            ">7I", data, start + 8)
        hash_size, hash_type, _platform, shift = struct.unpack_from(">4B", data, start + 36)
        if not 0x20400 <= version <= 0x20600 or not flags & 2:
            raise MachOError("expected modern ad-hoc CodeDirectory")
        sizes = {0x20400: 88, 0x20500: 96, 0x20600: 108}
        header_size = max(size for ver, size in sizes.items() if version >= ver)
        if blob_length < header_size or not header_size <= ident_offset < blob_length:
            raise MachOError("CodeDirectory header/identifier is out of bounds")
        if struct.unpack_from(">I", data, start + 44)[0]:
            raise MachOError("scatter CodeDirectories are not supported")
        limit64 = struct.unpack_from(">Q", data, start + 56)[0]
        if code_limit == 0xFFFFFFFF:
            code_limit = limit64
        elif limit64 not in {0, code_limit}:
            raise MachOError("inconsistent CodeDirectory code limits")
        exec_base, exec_limit, _exec_flags = struct.unpack_from(">3Q", data, start + 64)
        if exec_base != text["fileoff"] or exec_limit != text["filesize"]:
            raise MachOError("CodeDirectory executable range differs from normalized __TEXT")
        end = data.find(b"\0", start + ident_offset, start + blob_length)
        if end < 0:
            raise MachOError("unterminated CodeDirectory identifier")
        identifier = data[start + ident_offset:end].decode("utf-8")
        if expected_identifier is not None and identifier != expected_identifier:
            raise MachOError("unexpected CodeDirectory signing identifier")
        algorithms = {1: (hashlib.sha1, 20), 2: (hashlib.sha256, 32),
                      3: (hashlib.sha256, 20), 4: (hashlib.sha384, 48)}
        if hash_type not in algorithms or algorithms[hash_type][1] != hash_size or shift > 30:
            raise MachOError("unsupported CodeDirectory hash format")
        if code_limit != offset:
            raise MachOError("CodeDirectory must cover all bytes before its signature")
        page_size = (1 << shift) if shift else code_limit
        if not page_size or codes != (code_limit + page_size - 1) // page_size:
            raise MachOError("CodeDirectory code-slot count is incorrect")
        if (hash_offset - special * hash_size < header_size
                or hash_offset + codes * hash_size > blob_length
                or end >= start + hash_offset - special * hash_size):
            raise MachOError("CodeDirectory hash table overlaps metadata or exceeds its blob")
        constructor, digest_size = algorithms[hash_type]
        for code in range(codes):
            begin = code * page_size
            digest = constructor(data[begin:min(begin + page_size, code_limit)]).digest()[:digest_size]
            actual = data[start + hash_offset + code * hash_size:start + hash_offset + (code + 1) * hash_size]
            if actual != digest:
                raise MachOError(f"CodeDirectory code-page hash mismatch at slot {code}")
        directories.append(dict(identifier=identifier, code_limit=code_limit,
                                exec_base=exec_base, exec_limit=exec_limit))
    if 0 not in slots or not directories:
        raise MachOError("primary CodeDirectory is missing")
    ordered = sorted(ranges)
    if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
        raise MachOError("signature blobs overlap")
    return dict(offset=offset, reserved=reserved, declared=length, directories=directories)


def _verify_linkedit_tables(data: bytes, commands: list, linkedit: dict, signature_offset: int) -> None:
    """A trailing signature must not overlap dyld/symbol/linkedit objects."""
    ranges = []
    for item in commands:
        at, kind = item.offset, item.command
        if kind == 0x2:  # LC_SYMTAB; nlist_64 is 16 bytes
            if item.size != 24:
                raise MachOError("invalid LC_SYMTAB")
            symoff, symbols, stroff, strings = struct.unpack_from("<4I", data, at + 8)
            ranges.extend(((symoff, symbols * 16), (stroff, strings)))
        elif kind == 0xB:  # LC_DYSYMTAB
            if item.size != 80:
                raise MachOError("invalid LC_DYSYMTAB")
            values = struct.unpack_from("<18I", data, at + 8)
            for index, stride in ((6, 8), (8, 56), (10, 4), (12, 4), (14, 8), (16, 8)):
                ranges.append((values[index], values[index + 1] * stride))
        elif kind in {0x22, 0x80000022}:
            if item.size != 48:
                raise MachOError("invalid LC_DYLD_INFO")
            values = struct.unpack_from("<10I", data, at + 8)
            ranges.extend(zip(values[::2], values[1::2]))
        elif kind in {0x1E, 0x26, 0x29, 0x2B, 0x2E, 0x80000033, 0x80000034}:
            if item.size != 16:
                raise MachOError("invalid linkedit_data_command")
            ranges.append(struct.unpack_from("<II", data, at + 8))
    for offset, size in ranges:
        if size and (offset < linkedit["fileoff"] or offset + size > signature_offset):
            raise MachOError("linkedit table is outside __LINKEDIT or overlaps the signature")


def verify_bytes(data: bytes, expected_identity: str = DYLIB_IDENTITY,
                 minimum_signature_size: int = 65536,
                 page_aligned_segments: bool = True,
                 compact_signature: bool = False,
                 expected_identifier: str | None = None) -> dict:
    info = header(data)
    commands = load_commands(data)
    if info.file_type != MH_DYLIB:
        raise MachOError("file is not a Mach-O dylib")
    if any(item.size % 8 for item in commands):
        raise MachOError("load-command sizes must be 8-byte aligned")
    if sum(item.command == LC_ID_DYLIB for item in commands) != 1 or dylib_id(data) != expected_identity:
        raise MachOError("expected exactly one matching LC_ID_DYLIB")
    required = {(LC_LOAD_DYLIB, name) for name in
                ("/usr/lib/libobjc.A.dylib", "/usr/lib/libSystem.B.dylib")}
    dependencies = dylib_loads(data)
    if len(dependencies) != len(required) or set(dependencies) != required:
        raise MachOError("unexpected dependencies or non-required system load commands")
    sigs = [item for item in commands if item.command == LC_CODE_SIGNATURE]
    if len(sigs) != 1 or sigs[0].size != 16:
        raise MachOError("expected exactly one LC_CODE_SIGNATURE")
    offset, reserved = struct.unpack_from("<II", data, sigs[0].offset + 8)
    if reserved < minimum_signature_size or offset < 32 + info.command_size:
        raise MachOError("signature reservation is too small or overlaps load commands")
    layout = segments(data)
    if page_aligned_segments:
        _verify_page_aligned_segments(data, layout)
    linkedit = [s for s in layout if s["name"] == "__LINKEDIT"]
    text = [s for s in layout if s["name"] == "__TEXT"]
    if len(linkedit) != 1 or len(text) != 1 or offset < linkedit[0]["fileoff"]:
        raise MachOError("code signature must be inside the final __LINKEDIT range")
    _verify_linkedit_tables(data, commands, linkedit[0], offset)
    signature = _verify_signature(data, offset, reserved, text[0], expected_identifier, compact_signature)
    return dict(identity=expected_identity, segments=layout, signature=signature,
                size=len(data), sha256=hashlib.sha256(data).hexdigest())


def verify(path: Path, expected_identity: str = DYLIB_IDENTITY,
           minimum_signature_size: int = 65536, page_aligned_segments: bool = True,
           compact_signature: bool = False, expected_identifier: str | None = None) -> dict:
    return verify_bytes(path.read_bytes(), expected_identity, minimum_signature_size,
                        page_aligned_segments, compact_signature, expected_identifier)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dylib", type=Path)
    parser.add_argument("--identity", default=DYLIB_IDENTITY)
    parser.add_argument("--minimum-signature-size", type=int, default=65536)
    parser.add_argument("--page-aligned-segments", action="store_true",
                        help="compatibility flag; normalization is always required by the CLI")
    parser.add_argument("--compact-signature", action="store_true")
    parser.add_argument("--signing-identifier")
    args = parser.parse_args()
    try:
        verify(args.dylib, args.identity, args.minimum_signature_size, True,
               args.compact_signature, args.signing_identifier)
    except (OSError, ValueError, struct.error) as error:
        parser.error(str(error))
    print(f"valid normalized arm64 dylib: {args.dylib}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
