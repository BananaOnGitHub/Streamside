"""ARM64 execution tests; these are host emulation, never iOS validation."""
import json
import os
from pathlib import Path
import random
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/native_frontend'))
sys.path.insert(0,str(ROOT/'tools'))
from probes import trampoline,layout,branch,patch,launch_gate_layout
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UcError
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X29,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_NZCV,UC_ARM64_REG_Q0

PLAN=json.loads((ROOT/'native/twitch32.json').read_text())
GPRS=[UC_ARM64_REG_X0+i for i in range(29)]+[UC_ARM64_REG_X29,UC_ARM64_REG_X30]


class ProbeExecution(unittest.TestCase):
    def run_probe(self,probe,slide,armed=True,deny=False):
        item=PLAN['layout'][probe['image']]
        cave=next(c for p,c,_ in layout(PLAN,probe['image']) if p==probe)
        code=trampoline(item['base']+cave,probe['address'],bytes.fromhex(probe['bytes']),item['slot'],probe['id'])
        entry=probe['address']+slide; target=item['base']+cave+slide;slot=item['slot']+slide
        callback=0x700000000; stack=0x800000000
        def setup(instrumented):
            u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
            for page in set([entry&~4095,target&~4095,(target+len(code))&~4095,slot&~4095,callback]):u.mem_map(page,4096)
            u.mem_map(stack,0x10000)
            u.mem_write(entry,struct.pack('<I',branch(probe['address'],item['base']+cave)) if instrumented else bytes.fromhex(probe['bytes'])[:4])
            if instrumented:u.mem_write(target,code)
            u.mem_write(slot,struct.pack('<Q',callback if armed else 0))
            rng=random.Random(9000+probe['id'])
            for reg in GPRS:u.reg_write(reg,rng.getrandbits(64))
            for i in range(32):u.reg_write(UC_ARM64_REG_Q0+i,rng.getrandbits(128))
            u.reg_write(UC_ARM64_REG_SP,stack+0x8000);u.reg_write(UC_ARM64_REG_NZCV,0xa0000000)
            return u
        visits=[]
        def hook(u,address,size,unused):
            if address==entry+4:u.emu_stop()
            if address==callback:
                visits.append(u.reg_read(UC_ARM64_REG_X0))
                if deny:u.emu_stop();return
                ret=u.reg_read(UC_ARM64_REG_X30)
                for i in range(19):u.reg_write(UC_ARM64_REG_X0+i,0xdead0000+i)
                for i in range(32):u.reg_write(UC_ARM64_REG_Q0+i,(1<<127)+i)
                u.reg_write(UC_ARM64_REG_NZCV,0x50000000)
                u.reg_write(UC_ARM64_REG_X30,0xbad)
                from unicorn.arm64_const import UC_ARM64_REG_PC
                u.reg_write(UC_ARM64_REG_PC,ret)
        control=setup(False);control.hook_add(UC_HOOK_CODE,hook);control.emu_start(entry,entry+4,count=1000)
        candidate=setup(True);candidate.hook_add(UC_HOOK_CODE,hook)
        if not armed:
            with self.assertRaises(UcError):candidate.emu_start(entry,entry+4,count=1000)
            self.assertEqual(visits,[]);return
        candidate.emu_start(entry,entry+4,count=1000)
        self.assertEqual(visits,[probe['id']])
        if deny:
            self.assertEqual(candidate.reg_read(UC_ARM64_REG_SP),stack+0x8000-704)
            return
        for reg in GPRS+[UC_ARM64_REG_SP,UC_ARM64_REG_NZCV]+[UC_ARM64_REG_Q0+i for i in range(32)]:
            self.assertEqual(candidate.reg_read(reg),control.reg_read(reg),(probe['name'],reg))
        sp=control.reg_read(UC_ARM64_REG_SP)
        # Compare bytes written by the relocated original STP. Probe scratch below
        # the restored stack is allowed to differ, just like an ordinary call.
        if bytes.fromhex(probe['bytes'])[3]==0xa9:self.assertEqual(candidate.mem_read(sp,16),control.mem_read(sp,16))

    def test_all_entries_preserve_arguments_results_vectors_flags_and_stack(self):
        for probe in PLAN['probes']:
            for slide in [0x40000000,0x48004000]:
                with self.subTest(probe=probe['name'],slide=slide):self.run_probe(probe,slide)

    def test_unarmed_observer_traps_before_donor(self):
        self.run_probe(PLAN['probes'][16],0x40000000,armed=False)

    def test_guard_can_stop_before_runtime_entry(self):
        self.run_probe(PLAN['probes'][16],0x40000000,deny=True)

    def test_one_shot_gate_preserves_original_abi_or_returns_native_false(self):
        cave,code=launch_gate_layout(PLAN);item=PLAN['layout']['Twitch'];gate=PLAN['gate']
        for slide in [0x40000000,0x48004000]:
            entry=gate['address']+slide;target=item['base']+cave+slide;slot=item['slot']+8+slide
            stack=0x800000000;ret=0x700000000
            def setup(selection,instrumented):
                u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
                for page in {entry&~4095,target&~4095,slot&~4095,ret}:u.mem_map(page,4096)
                u.mem_map(stack,0x10000)
                u.mem_write(entry,struct.pack('<I',branch(gate['address'],item['base']+cave)) if instrumented else bytes.fromhex(gate['bytes'])[:4])
                u.mem_write(target,code);u.mem_write(slot,struct.pack('<Q',selection))
                rng=random.Random(47)
                for reg in GPRS:u.reg_write(reg,rng.getrandbits(64))
                for i in range(32):u.reg_write(UC_ARM64_REG_Q0+i,rng.getrandbits(128))
                u.reg_write(UC_ARM64_REG_SP,stack+0x8000);u.reg_write(UC_ARM64_REG_NZCV,0xa0000000);u.reg_write(UC_ARM64_REG_X30,ret)
                u.hook_add(UC_HOOK_CODE,lambda uc,a,size,data:uc.emu_stop() if a in [entry+4,ret] else None)
                return u
            control=setup(2,False);control.emu_start(entry,entry+4,count=100)
            original=setup(2,True);original.emu_start(entry,ret,count=100)
            regs=GPRS+[UC_ARM64_REG_SP,UC_ARM64_REG_NZCV]+[UC_ARM64_REG_Q0+i for i in range(32)]
            for reg in regs:self.assertEqual(original.reg_read(reg),control.reg_read(reg),reg)
            sp=control.reg_read(UC_ARM64_REG_SP);self.assertEqual(original.mem_read(sp,16),control.mem_read(sp,16))
            native=setup(1,True);before={reg:native.reg_read(reg) for reg in regs}
            native.emu_start(entry,ret,count=100)
            for reg in regs:self.assertEqual(native.reg_read(reg),0 if reg==UC_ARM64_REG_X0 else before[reg],reg)
            unselected=setup(0,True)
            with self.assertRaises(UcError):unselected.emu_start(entry,ret,count=100)

    def test_rejects_unknown_first_instruction_and_far_branch(self):
        with self.assertRaises(ValueError):trampoline(0,4,bytes.fromhex('00000090'),4096,0)
        with self.assertRaises(ValueError):branch(0,1<<28)

    def test_rejects_changed_donor_image(self):
        with self.assertRaisesRegex(ValueError,'Exact donor'):patch(b'unknown',PLAN,'Twitch','0'*64,True)


if __name__=='__main__':unittest.main()
