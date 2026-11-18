"""Execute inspected donor leaf boundaries; never use a network or credentials."""
import struct
import unittest
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X20, UC_ARM64_REG_X30, UC_ARM64_REG_PC, UC_ARM64_REG_SP
import test_feed_contract as feed

PREFIX='_$s16TwitchGraphQLAPI45ContentClassificationLabelStreamMetadataQueryC'

class ContentLabelsContract(unittest.TestCase):
    setUpClass = classmethod(feed.NativeFeedContract.setUpClass.__func__)
    def machine(self,image):
        # The full GraphQL image exceeds the feed fixture's scratch address.
        # Map only the inspected functions/stubs, with separate scratch regions.
        from probes import file_offset
        data=self.images[image][1];u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u.mem_map(0,0x900000)
        for spec in self.plan['abi'].values():
            if spec['image']==image:
                at=spec['address'];pos=file_offset(data,at);u.mem_write(at,data[pos:pos+256])
        for address in [0x1000000,0x1100000,0x1200000]:u.mem_map(address,4096)
        u.reg_write(UC_ARM64_REG_SP,0x1100800);u.reg_write(UC_ARM64_REG_X30,0x1200000)
        return u

    def test_actual_consuming_constructor_uses_string_and_metatype(self):
        u=self.machine('TwitchGraphQLAPI');allocated=0x1000500
        u.reg_write(UC_ARM64_REG_X0,11);u.reg_write(UC_ARM64_REG_X1,22);u.reg_write(UC_ARM64_REG_X20,0x1000400)
        observed=[]
        def hook(vm,pc,size,unused):
            if pc==0x816ec4:
                observed.append([vm.reg_read(r) for r in [UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2]])
                vm.reg_write(UC_ARM64_REG_X0,allocated);vm.reg_write(UC_ARM64_REG_PC,vm.reg_read(UC_ARM64_REG_X30))
        u.hook_add(UC_HOOK_CODE,hook)
        u.emu_start(self.plan['abi'][PREFIX+'9channelIdACSS_tcfC']['address'],0x1200000,count=80)
        self.assertEqual(observed,[[0x1000400,32,7]])
        self.assertEqual(u.reg_read(UC_ARM64_REG_X0),allocated)
        self.assertEqual(bytes(u.mem_read(allocated+16,16)),struct.pack('<QQ',11,22))

    def test_actual_label_fields_take_direct_value_and_native_keys(self):
        for suffix,target,key in [('13localizedNameSSvg',0x47c0,b'localizedName'),('9isEnabledSbvg',0x5880,b'isEnabled')]:
            with self.subTest(field=suffix):
                u=self.machine('TwitchGraphQLAPI');u.reg_write(UC_ARM64_REG_X0,0x1000500);u.reg_write(UC_ARM64_REG_X20,0xdeadbeef)
                observed=[]
                def hook(vm,pc,size,unused):
                    if pc==target:
                        observed.append([vm.reg_read(r) for r in [UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2]])
                        vm.reg_write(UC_ARM64_REG_PC,0x1200000)
                u.hook_add(UC_HOOK_CODE,hook)
                u.emu_start(self.plan['abi'][PREFIX+'4DataV4UserV0G0V0deF0V'+suffix]['address'],0x1200000,count=40)
                self.assertEqual(len(observed),1)
                a,b,value=observed[0];self.assertEqual(value,0x1000500)
                self.assertEqual(struct.pack('<QQ',a,b)[:len(key)],key)

if __name__=='__main__':unittest.main()
