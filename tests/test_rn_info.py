"""Diagnostic prefix operands, sequential Hermes call staging, and fallback.

The exact donor/container checks are in tools/verify_rn_info.py. This harness
executes the emitted prefixes with missing modules, missing IDs and faults at
every lookup/call. It never claims to simulate React or device presentation.
"""
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS = {18843: '__r', 110: 'default', 20058: 'buildLocalEcho', 26600: 'trace',
        52778: 'emoteId', 31772: 'emoteID', 61502: 'openCard', 26897: 'emote',
        156: 'id', 194: 'onPress'}


def execute(code, props, global_object, frame, fail_at=None):
    def truth(value):
        return bool(value) if isinstance(value, (str, int, float, bool)) else value is not None
    regs = {}; pos = stage = caught = 0
    while pos < len(code):
        at = pos; op = code[pos]; pos += 1
        try:
            if op == 61:
                regs[code[pos]] = global_object; pos += 1
            elif op == 144:
                dest = code[pos]; key = struct.unpack_from('<H', code, pos+1)[0]; pos += 3
                regs[dest] = KEYS[key]
            elif op in (147, 148):
                regs[code[pos]] = None; pos += 1
            elif op == 137:
                dest, param = code[pos:pos+2]; pos += 2
                assert param == 1; regs[dest] = props
            elif op == 52:
                dest, depth = code[pos:pos+2]; pos += 2
                assert depth == 0; regs[dest] = [props]
            elif op == 59:
                dest, env, slot = code[pos:pos+3]; pos += 3
                regs[dest] = regs[env][slot]
            elif op == 139:
                dest, value = code[pos:pos+2]; pos += 2; regs[dest] = value
            elif op == 19:
                dest, source = code[pos:pos+2]; pos += 2; regs[dest] = not truth(regs[source])
            elif op == 93:
                dest, obj, key = code[pos:pos+3]; pos += 3; stage += 1
                if fail_at == stage: raise RuntimeError('lookup')
                regs[dest] = regs[obj].get(regs[key])
            elif op in (176, 179):
                size = 1 if op == 176 else 4
                delta = int.from_bytes(code[pos:pos+size], 'little', signed=True)
                test = code[pos+size]; pos += size+1
                if truth(regs[test]) == (op == 176): pos = at+delta
            elif op in (110, 112):
                length = 4 if op == 110 else 6
                dest, fn, this, *args = code[pos:pos+length]; pos += length; stage += 1
                # Hermes reads operands sequentially, then the callee. A small
                # frame can overwrite the callee before bridge entry.
                for i, reg in enumerate([this, *args]): regs[frame-8-i] = regs[reg]
                callee = regs[fn]
                for i in range(frame-7, frame): regs[i] = object()
                if fail_at == stage: raise RuntimeError('call')
                regs[dest] = callee(regs[frame-8], *(regs[frame-9-i] for i in range(len(args))))
            elif op == 175:
                pos = at + struct.unpack_from('<i', code, pos)[0]
            elif op == 119:
                regs[code[pos]] = None; pos += 1; caught += 1
            else:
                raise AssertionError(f'Unexpected opcode {op} at {at}')
        except (RuntimeError, TypeError, AttributeError):
            if at >= len(code)-7: raise
            pos = len(code)-2
    return caught, stage


class RNInfoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        root = Path(cls.directory.name)
        source = root/'info.c'
        source.write_text('''#include "TASRNInfoPatch.h"
size_t code(unsigned char *p,unsigned seam){return tas_rn_info_code(p,seam);}
''')
        binary = root/'info.so'
        zig = os.environ.get('ZIG') or shutil.which('zig')
        if not zig: raise AssertionError('Zig required')
        subprocess.run([zig, 'cc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror',
                        '-I', str(ROOT/'src'), str(source), '-o', str(binary)], check=True)
        import ctypes
        cls.lib = ctypes.CDLL(str(binary)); cls.lib.code.restype = ctypes.c_size_t
        cls.codes = []
        for seam in range(5):
            out = ctypes.create_string_buffer(256)
            size = cls.lib.code(out, seam)
            cls.codes.append(out.raw[:size])

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_each_seam_passes_only_identity_and_flag_and_preserves_props(self):
        identifier = '860000000002000'; text = object(); handler = object()
        fixtures = [{'emoteId': identifier, 'onPress': handler, 'text': text},
                    {'emoteId': identifier, 'text': text},
                    {'openCard': {'emoteID': identifier, 'token': text}},
                    {'emoteID': identifier, 'token': text},
                    {'emote': {'id': identifier, 'name': text}}]
        for seam, (code, frame, props) in enumerate(zip(self.codes, [41,24,28,46,95], fixtures)):
            calls = []
            def trace(this, boundary, identity, press):
                self.assertIs(this, module); calls.append((boundary, identity, press))
            module = {'trace': trace}
            glob = {'__r': lambda this, identity: {'default': {'buildLocalEcho': module}}}
            before = repr(props)
            caught, stages = execute(code, props, glob, frame)
            self.assertEqual(caught, 0)
            self.assertEqual(calls, [(seam, identifier, True if seam == 0 else None)])
            self.assertEqual(repr(props), before)
            for stage in range(1, stages+1):
                calls.clear()
                caught, _ = execute(code, props, glob, frame, stage)
                self.assertEqual(caught, 1)
                self.assertEqual(repr(props), before)
            caught, _ = execute(code, props, {}, frame)
            self.assertEqual(caught, 0)

    def test_missing_id_and_host_state_still_measure_boundary_without_payload(self):
        for seam, (code, frame) in enumerate(zip(self.codes, [41,24,28,46,95])):
            calls = []
            module = {'trace': lambda this, *args: calls.append(args)}
            glob = {'__r': lambda this, identity: {'default': {'buildLocalEcho': module}}}
            caught, _ = execute(code, {}, glob, frame)
            self.assertEqual(caught, 0)
            self.assertEqual(calls, [(seam, None, False if seam == 0 else None)])

    def test_tap_frame_overlap_reproduced_and_corrected(self):
        calls = []
        module = {'trace': lambda this, *args: calls.append(args)}
        glob = {'__r': lambda this, identity: {'default': {'buildLocalEcho': module}}}
        props = {'emoteId': '25'}
        caught, _ = execute(self.codes[1], props, glob, 14)
        self.assertEqual((caught, calls), (1, []))
        caught, _ = execute(self.codes[1], props, glob, 24)
        self.assertEqual((caught, calls), (0, [(1, '25', None)]))
