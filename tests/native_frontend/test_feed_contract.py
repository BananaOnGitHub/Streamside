"""Exact donor feed register/enum evidence; no account or Apple runtime execution."""
import copy
import unittest
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X8, UC_ARM64_REG_X20, UC_ARM64_REG_X30, UC_ARM64_REG_SP, UC_ARM64_REG_PC
import test_admission as admission
from probes import file_offset
from validate import validate_abi
import struct


class NativeFeedContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        admission.AccountAdapterAdmission.setUpClass()
        cls.images=admission.AccountAdapterAdmission.images
        cls.plan=admission.AccountAdapterAdmission.plan

    def machine(self,image):
        data=self.images[image][1];u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
        u.mem_map(0,((len(data)+4095)//4096)*4096)
        # Only the inspected leaf functions are executed. Segment file offsets
        # are translated per symbol rather than assuming file/VM addresses match.
        for symbol,spec in self.plan['abi'].items():
            if spec['image']==image:
                at=spec['address'];pos=file_offset(data,at);u.mem_write(at,data[pos:pos+256])
        for address in [0x1000000,0x1100000,0x1200000]:u.mem_map(address,4096)
        u.reg_write(UC_ARM64_REG_SP,0x1100800);u.reg_write(UC_ARM64_REG_X30,0x1200000)
        return u

    def test_native_sort_tag_is_recommended(self):
        u=self.machine('TwitchKit');u.reg_write(UC_ARM64_REG_X0,0)
        address=self.plan['abi']['_$s9TwitchKit28FollowedLiveStreamsSortOrderO8rawValueSSvg']['address']
        u.emu_start(address,0x1200000,count=200)
        self.assertEqual(u.reg_read(UC_ARM64_REG_X0),0x6e656d6d6f636572)
        self.assertEqual(u.reg_read(UC_ARM64_REG_X1),0xeb00000000646564)

    def test_actual_response_getters_forward_direct_words(self):
        for property,expected in [('live',11),('offline',22)]:
            u=self.machine('TwitchKit')
            u.reg_write(UC_ARM64_REG_X0,11);u.reg_write(UC_ARM64_REG_X1,22)
            u.reg_write(UC_ARM64_REG_X20,0xdeadbeef) # These are not swiftself getters.
            spec=next(v for k,v in self.plan['abi'].items() if 'PersonalSectionsResponseV'+('4live' if property=='live' else '7offline') in k)
            seen=[]
            def hook(vm,pc,size,unused):
                if pc==0x43fe9c: # Inspected swift_bridgeObjectRetain import stub.
                    seen.append(vm.reg_read(UC_ARM64_REG_X0));vm.reg_write(UC_ARM64_REG_PC,0x1200000)
            u.hook_add(UC_HOOK_CODE,hook);u.emu_start(spec['address'],0x1200000,count=40)
            self.assertEqual(seen,[expected])

    def test_actual_generic_getter_uses_runtime_copy_witness(self):
        u=self.machine('TwitchAnalyticsCore')
        metadata=0x1000100;payload_type=0x1000200;table=0x1000300;copy=0x1000400
        u.mem_write(metadata+16,struct.pack('<Q',payload_type))
        u.mem_write(payload_type-8,struct.pack('<Q',table))
        u.mem_write(table+16,struct.pack('<Q',copy))
        u.reg_write(UC_ARM64_REG_X0,metadata);u.reg_write(UC_ARM64_REG_X8,0x1000500)
        u.reg_write(UC_ARM64_REG_X20,0x1000600)
        seen=[]
        def hook(vm,pc,size,unused):
            if pc==copy:
                seen.append([vm.reg_read(r) for r in [UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2]])
                vm.reg_write(UC_ARM64_REG_PC,0x1200000)
        u.hook_add(UC_HOOK_CODE,hook)
        u.emu_start(self.plan['abi']['_$s19TwitchAnalyticsCore13TrackableItemV4itemxvg']['address'],0x1200000,count=40)
        self.assertEqual(seen,[[0x1000500,0x1000600,payload_type]])

    def test_changed_enum_case_or_generic_requirement_rejected(self):
        plan=copy.deepcopy(self.plan)
        plan['feed_contract']['enum_descriptors']['ThumbnailBlurReason']['cases'][2]='unknown'
        with self.assertRaisesRegex(ValueError,'enum case'):validate_abi(self.images,plan)
        plan=copy.deepcopy(self.plan);plan['feed_contract']['trackable_descriptor']['requirement']='$sSHMp'
        with self.assertRaisesRegex(ValueError,'conformance requirement'):validate_abi(self.images,plan)


if __name__=='__main__':unittest.main()
