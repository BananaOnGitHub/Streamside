"""Independent metadata fixtures; no donor or capstone required for parsing."""
import contextlib
import importlib.util
import io
from pathlib import Path
import struct
import tempfile
import unittest

from tools.inspect_rn_presentation import PresentationMetadata


def fixture(relative=False, invalid=False):
    data = bytearray(0x1000)
    size = 72 + 2 * 80
    struct.pack_into("<8I", data, 0, 0xFEEDFACF, 0x0100000C, 0, 6, 2, size + 16, 0, 0)
    struct.pack_into("<II16s4Q4I", data, 32, 0x19, size, b"__TEXT", 0, len(data),
                     0, len(data), 7, 5, 2, 0)
    for i, (name, address, length) in enumerate(((b"__text", 0x800, 8),
                                                (b"__objc_classlist", 0x900, 8))):
        struct.pack_into("<16s16s2Q8I", data, 104 + 80 * i, name, b"__TEXT", address,
                         length, address, 2, 0, 0, 0, 0, 0, 0)
    struct.pack_into("<4I", data, 32 + size, 0x26, 16, 0xc00, 4)
    data[0xc00:0xc04] = bytes((0x80, 0x10, 4, 0))  # Function starts 0x800, 0x804.
    data[0x800:0x808] = bytes.fromhex("c0035fd6c0035fd6")  # arm64 ret, ret.
    struct.pack_into("<Q", data, 0x900, 0x920)
    struct.pack_into("<Q", data, 0x920, 0x960)  # Class -> metaclass.
    struct.pack_into("<Q", data, 0x940, 0x9a0)  # Class read-only metadata.
    struct.pack_into("<Q", data, 0x980, 0x9e0)  # Metaclass read-only metadata.
    struct.pack_into("<QQ", data, 0x9b8, 0xa40, 0xb00)
    data[0xa40:0xa48] = b"Fixture\0"
    data[0xa60:0xa68] = b"sample:\0"
    flags = (0xc0000000 | 12) if relative else 24
    struct.pack_into("<II", data, 0xb00, 0 if invalid else flags, 1)
    if relative:
        struct.pack_into("<iii", data, 0xb08, 0xa60 - 0xb08, 0, 0x800 - 0xb10)
    else:
        struct.pack_into("<QQQ", data, 0xb08, 0xa60, 0, 0x800)
    return data


class PresentationTraceTests(unittest.TestCase):
    def metadata(self, **kwargs):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture"
            path.write_bytes(fixture(**kwargs))
            return PresentationMetadata(path)

    def test_absolute_and_relative_imps(self):
        for relative in (False, True):
            with self.subTest(relative=relative):
                metadata = self.metadata(relative=relative)
                self.assertEqual(metadata.imps[("Fixture", "sample:", False)], 0x800)
                self.assertEqual(metadata.functions, [0x800, 0x804])
                self.assertEqual(metadata.names[0x800], "-[Fixture sample:]")

    def test_invalid_method_stride(self):
        with self.assertRaisesRegex(ValueError, "invalid method list"):
            self.metadata(invalid=True)

    @unittest.skipUnless(importlib.util.find_spec("capstone"), "optional disassembler absent")
    def test_code_bounds_and_function_boundary(self):
        metadata = self.metadata()
        for address, limit in ((0x900, 1), (0x801, 1), (0x800, 0), (0x800, 4097)):
            with self.assertRaises(ValueError):
                metadata.disassemble(address, limit)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            metadata.disassemble(0x800)
        self.assertIn("00000800", output.getvalue())
        self.assertNotIn("00000804", output.getvalue())


if __name__ == "__main__":
    unittest.main()
