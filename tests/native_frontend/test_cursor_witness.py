"""Inspect and emulate only the donor's pure cursor value-witness operations.

No Twitch application, account, network or Apple runtime executes in this test.
The donor is mandatory; absent binary evidence is not a passing layout check.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import unittest
import zipfile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X30,UC_ARM64_REG_SP
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/native_frontend')]
from probes import file_offset
PLAN=json.loads((ROOT/'native/twitch32.json').read_text())


class CursorWitness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        donor=Path(os.environ.get('SSN_DONOR',ROOT.parent/'donors/tv.twitch-32.0.ipa'))
        if not donor.exists():raise AssertionError('Set SSN_DONOR to the exact Twitch 32.0 IPA')
        if hashlib.sha256(donor.read_bytes()).hexdigest()!=PLAN['donor_sha256']:raise AssertionError('Wrong donor identity')
        with zipfile.ZipFile(donor) as z:cls.data=z.read('Payload/Twitch.app/Frameworks/TwitchKit.framework/TwitchKit')
        cls.evidence=PLAN['value_layouts']['page_cursor']

    def test_exact_native_value_size_stride_and_witnesses(self):
        e=self.evidence;pos=file_offset(self.data,e['witness_table'])
        size,stride,flags=struct.unpack_from('<QQQ',self.data,pos+64)
        self.assertEqual((size,stride,flags),(17,24,e['flags_and_extra_inhabitants']))
        for index,name in [(6,'get_single_payload_tag'),(7,'store_single_payload_tag')]:
            self.assertEqual(struct.unpack_from('<Q',self.data,pos+8*index)[0]&((1<<36)-1),e[name])

    def test_actual_native_witness_constructs_nil_without_touching_stride_padding(self):
        e=self.evidence;u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
        u.mem_map(e['get_single_payload_tag']&~4095,8192)
        for name,length in [('get_single_payload_tag',0x48),('store_single_payload_tag',0x40)]:
            addr=e[name];pos=file_offset(self.data,addr);u.mem_write(addr,self.data[pos:pos+length])
        buffer=0x900000;stack=0x800000;end=0x700000
        for a in [buffer,stack,end]:u.mem_map(a,4096)
        u.mem_write(buffer,bytes(17)+bytes([0xcc])*7)
        def call(name,x1,x2):
            u.reg_write(UC_ARM64_REG_X0,buffer);u.reg_write(UC_ARM64_REG_X1,x1);u.reg_write(UC_ARM64_REG_X2,x2)
            u.reg_write(UC_ARM64_REG_X3,0);u.reg_write(UC_ARM64_REG_SP,stack+2048);u.reg_write(UC_ARM64_REG_X30,end)
            u.emu_start(e[name],end,count=1000)
        call('store_single_payload_tag',1,1)
        call('get_single_payload_tag',1,0)
        self.assertEqual(u.reg_read(UC_ARM64_REG_X0),1)
        self.assertEqual(bytes(u.mem_read(buffer+17,7)),bytes([0xcc])*7)
        self.assertEqual(struct.unpack('<Q',u.mem_read(buffer+8,8))[0],0)


if __name__=='__main__':unittest.main()
