"""Small independent arm64/signature fixture; no compiler or real IPA needed."""
import struct

from tools.macho import LC_ID_DYLIB, LC_LOAD_DYLIB, LC_SEGMENT_64, code_signature, load_commands
from tools.reserve_codesign_space import refresh_adhoc_code_directories
from tools.verify_macho import FRAMEWORK_IDENTITY, align


def string_command(kind: int, name: str) -> bytes:
    encoded = name.encode() + b"\0"
    size = align(24 + len(encoded), 8)
    return struct.pack("<6I", kind, size, 24, 0, 0, 0) + encoded + b"\0" * (size - 24 - len(encoded))


def synthetic_dylib() -> bytes:
    commands = []
    for name, vmaddr, vmsize, fileoff, filesize, section in (
        ("__TEXT", 0, 0x4000, 0, 0x4000, (0x1000, 0x1000)),
        ("__DATA_CONST", 0x4000, 0x4000, 0x4000, 0x4000, (0x4000, 0x4000)),
        ("__DATA", 0x8000, 0x8000, 0x8000, 0x4000, (0x8000, 0x8000)),
        ("__LINKEDIT", 0x10000, 0x4000, 0xC000, 0, None),
    ):
        size = 72 + (80 if section else 0)
        raw = struct.pack("<II16s4Q4I", LC_SEGMENT_64, size, name.encode(),
                          vmaddr, vmsize, fileoff, filesize, 7, 5, bool(section), 0)
        if section:
            address, offset = section
            raw += struct.pack("<16s16s2Q8I", b"__fixture", name.encode(), address,
                               16, offset, 2, 0, 0, 0, 0, 0, 0)
        commands.append(raw)
    commands += [string_command(LC_ID_DYLIB, FRAMEWORK_IDENTITY),
                 string_command(LC_LOAD_DYLIB, "/usr/lib/libSystem.B.dylib"),
                 string_command(LC_LOAD_DYLIB, "/usr/lib/libobjc.A.dylib")]
    signature_offset = 0xC100
    identifier = b"Streamside\0"
    hash_offset = 88 + len(identifier)
    code_count = (signature_offset + 4095) // 4096
    cd = bytearray(hash_offset + 32 * code_count)
    struct.pack_into(">9I4B", cd, 0, 0xFADE0C02, len(cd), 0x20400, 2,
                     hash_offset, 88, 0, code_count, signature_offset, 32, 2, 0, 12)
    struct.pack_into(">3Q", cd, 64, 0, 0x4000, 0)
    cd[88:hash_offset] = identifier
    signature = struct.pack(">5I", 0xFADE0CC0, 20 + len(cd), 1, 0, 20) + cd
    reserved = align(len(signature), 16)
    linkedit = bytearray(commands[3])
    struct.pack_into("<Q", linkedit, 48, signature_offset + reserved - 0xC000)
    commands[3] = linkedit
    commands.append(struct.pack("<4I", 0x1D, 16, signature_offset, reserved))
    table = b"".join(commands)
    data = bytearray(signature_offset + reserved)
    struct.pack_into("<8I", data, 0, 0xFEEDFACF, 0x0100000C, 0, 6, len(commands), len(table), 0, 0)
    data[32:32 + len(table)] = table
    data[signature_offset:signature_offset + len(signature)] = signature
    refresh_adhoc_code_directories(data, signature_offset)
    return bytes(data)


def segment_command(data: bytes, name: str) -> int:
    for item in load_commands(data):
        if item.command == LC_SEGMENT_64 and data[item.offset + 8:item.offset + 24].split(b"\0")[0].decode() == name:
            return item.offset
    raise AssertionError(name)


def refresh(data: bytes | bytearray) -> bytes:
    output = bytearray(data)
    refresh_adhoc_code_directories(output, code_signature(output)[0])
    return bytes(output)
