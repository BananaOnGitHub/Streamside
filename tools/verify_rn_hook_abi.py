"""Check guarded RN hook encodings against a supplied arm64 donor app.

Reads Objective-C metadata only. No donor strings except matching class names,
selectors and encodings are emitted. Supports the donor's relative method lists
and low-48-bit image-relative pointers; this is not a general dyld loader.
Foundation methods are explicitly runtime-only, never claimed donor-verified.
"""
from pathlib import Path
import re
import struct
import sys


class Metadata:
    def __init__(self, path):
        self.data = path.read_bytes()
        if self.data[:4] != b"\xcf\xfa\xed\xfe":
            raise ValueError("expected thin little-endian Mach-O 64")
        self.segments = []
        self.sections = {}
        offset = 32
        for _ in range(struct.unpack_from("<I", self.data, 16)[0]):
            command, size = struct.unpack_from("<II", self.data, offset)
            if size < 8 or offset + size > len(self.data):
                raise ValueError("invalid load command")
            if command == 0x19:
                vm, _, file_offset, file_size = struct.unpack_from("<QQQQ", self.data, offset + 24)
                self.segments.append((vm, file_offset, file_size))
                n = struct.unpack_from("<I", self.data, offset + 64)[0]
                if 72 + n * 80 > size:
                    raise ValueError("invalid section table")
                for index in range(n):
                    at = offset + 72 + index * 80
                    name = self.data[at:at + 16].split(b"\0")[0].decode()
                    self.sections[name] = struct.unpack_from("<QQI", self.data, at + 32)
            offset += size

    def offset(self, pointer):
        pointer &= 0xffffffffffff
        for vm, at, size in self.segments:
            if vm <= pointer < vm + size:
                return at + pointer - vm
        raise ValueError("metadata pointer outside file-backed image")

    def pointer(self, at):
        return struct.unpack_from("<Q", self.data, self.offset(at))[0] & 0xffffffffffff

    def string(self, pointer):
        at = self.offset(pointer)
        end = self.data.index(b"\0", at, min(at + 8192, len(self.data)))
        return self.data[at:end].decode()

    def methods(self, pointer):
        if not pointer:
            return {}
        flags, count = struct.unpack_from("<II", self.data, self.offset(pointer))
        stride = flags & 0xffff
        if stride < (12 if flags & 0x80000000 else 24) or count > 8192:
            raise ValueError("invalid method list")
        methods = {}
        for index in range(count):
            at = pointer + 8 + index * stride
            if flags & 0x80000000:
                name, encoding, _ = struct.unpack_from("<iii", self.data, self.offset(at))
                name_pointer = at + name
                if not flags & 0x40000000:
                    name_pointer = self.pointer(name_pointer)
                methods[self.string(name_pointer)] = self.string(at + 4 + encoding)
            else:
                methods[self.string(self.pointer(at))] = self.string(self.pointer(at + 8))
        return methods

    def classes(self, targets):
        if "__objc_classlist" not in self.sections:
            return {}
        address, size, _ = self.sections["__objc_classlist"]
        result = {}
        for index in range(size // 8):
            cls = self.pointer(address + index * 8)
            ro = self.pointer(cls + 32) & ~7
            name = self.string(self.pointer(ro + 24))
            if name not in targets:
                continue
            result[(name, False)] = self.methods(self.pointer(ro + 32))
            meta = self.pointer(cls)
            meta_ro = self.pointer(meta + 32) & ~7
            result[(name, True)] = self.methods(self.pointer(meta_ro + 32))
        return result


def verify(app):
    source = (Path(__file__).resolve().parents[1] / "src/TASRNProbe.c").read_text()
    macros = dict(re.findall(r'^#define (INPUT|ATTACHMENT) "([^"]+)"', source, re.M))
    specs = []
    for cls, sel, encoding, meta in re.findall(
        r'SPEC\(\w+,("[^"]+"|INPUT|ATTACHMENT),"([^"]+)","([^"]+)",\w+,(true|false)\)', source
    ):
        specs.append((macros.get(cls, cls.strip('"')), sel, encoding, meta == "true"))
    targets = {row[0] for row in specs} - {"NSURL", "NSTextAttachment"}
    found = {}
    for framework in sorted((app / "Frameworks").glob("*.framework")):
        binary = framework / framework.stem
        if binary.is_file():
            rows = Metadata(binary).classes(targets)
            for key, value in rows.items():
                if key in found:
                    raise ValueError("duplicate target class")
                found[key] = value
    matched, runtime, errors = 0, 0, []
    for cls, selector, expected, meta in specs:
        if cls in ("NSURL", "NSTextAttachment"):
            runtime += 1
            continue
        actual = found.get((cls, meta), {}).get(selector)
        if actual != expected:
            errors.append(f"{cls}.{selector}: expected {expected}, found {actual}")
        else:
            matched += 1
    if errors:
        raise ValueError("\n".join(errors))
    print(f"Matched {matched} donor hook encodings; {runtime} Foundation hooks runtime-only.")


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
