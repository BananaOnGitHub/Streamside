"""Execute inspected donor leaf boundaries with synthetic runtime callbacks only."""
import copy
import struct
import unittest
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X8,UC_ARM64_REG_X20,UC_ARM64_REG_X30,UC_ARM64_REG_PC,UC_ARM64_REG_SP
import test_feed_contract as feed
from probes import file_offset
from validate import validate_abi,chained_fixup_locations

class ProfileContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        feed.NativeFeedContract.setUpClass();cls.images=feed.NativeFeedContract.images;cls.plan=feed.NativeFeedContract.plan
    def machine(self,image):
        data=self.images[image][1];u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
        u.mem_map(0,((len(data)+4095)//4096)*4096)
        for spec in self.plan['abi'].values():
            if spec['image']==image:
                pos=file_offset(data,spec['address']);u.mem_write(spec['address'],data[pos:pos+256])
        for address in [0x4000000,0x4100000,0x4200000]:u.mem_map(address,4096)
        u.reg_write(UC_ARM64_REG_SP,0x4100800);u.reg_write(UC_ARM64_REG_X30,0x4200000);return u
    def test_profile_query_actual_allocator_consumes_exact_lowering(self):
        u=self.machine('TwitchGraphQLAPI');allocated=0x4000100;metatype=0x4000500
        for index,arg in enumerate([11,22,33,44,55,66,77]):u.reg_write(UC_ARM64_REG_X0+index,arg)
        u.reg_write(UC_ARM64_REG_X20,metatype);calls=[]
        def hook(vm,pc,size,unused):
            if pc==0x816ec4:
                calls.append([vm.reg_read(UC_ARM64_REG_X0+i) for i in range(3)])
                vm.reg_write(UC_ARM64_REG_X0,allocated);vm.reg_write(UC_ARM64_REG_PC,vm.reg_read(UC_ARM64_REG_X30))
        u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x54bd94,0x4200000,count=100)
        self.assertEqual(calls,[[metatype,65,7]])
        self.assertEqual(struct.unpack('<2Q',u.mem_read(allocated+16,16)),(11,22))
        for offset,value,width in [(32,33,1),(40,44,8),(48,55,1),(56,66,8),(64,77,1)]:
            self.assertEqual(int.from_bytes(u.mem_read(allocated+offset,width),'little'),value)
        self.assertEqual(u.reg_read(UC_ARM64_REG_X0),allocated)
    def test_actual_nullable_initializer_delegates_to_payload_value_witness(self):
        u=self.machine('ApolloAPI');metadata=0x4000100;table=0x4000300;callback=0x4000400;out=0x4000500
        u.mem_write(metadata-8,struct.pack('<Q',table));u.mem_write(table+56,struct.pack('<Q',callback))
        u.reg_write(UC_ARM64_REG_X0,metadata);u.reg_write(UC_ARM64_REG_X8,out);calls=[]
        def hook(vm,pc,size,unused):
            if pc==callback:
                calls.append([vm.reg_read(UC_ARM64_REG_X0+i) for i in range(4)])
                vm.reg_write(UC_ARM64_REG_PC,0x4200000)
        u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0xcb88,0x4200000,count=40)
        self.assertEqual(calls,[[out,1,2,metadata]])
    def test_profile_descriptor_changes_are_rejected(self):
        for field,value in [('generic_parameters',3),('key_arguments',3)]:
            plan=copy.deepcopy(self.plan);plan['profile_contract']['mutation_result'][field]=value
            with self.assertRaisesRegex(ValueError,'Profile mutation'):validate_abi(self.images,plan)
        plan=copy.deepcopy(self.plan);plan['profile_contract']['nullable']['cases'][1]='null'
        with self.assertRaisesRegex(ValueError,'Profile nullable'):validate_abi(self.images,plan)

    def test_value_metadata_fixup_is_rejected_as_a_runtime_prefix(self):
        spec=self.plan['profile_contract']['error_metadata_export'];data=self.images[spec['image']][1]
        address=spec['address']+spec['rebased_pointer_offset']
        self.assertIn(address,chained_fixup_locations(data))
        raw=struct.unpack_from('<Q',data,file_offset(data,address))[0]
        self.assertEqual(raw&((1<<36)-1),spec['target'])
        for slide in [0x100000000,0x410000000]:
            self.assertNotEqual(struct.pack('<Q',slide+spec['target']),struct.pack('<Q',raw))
        plan=copy.deepcopy(self.plan)
        plan['abi'][spec['symbol']]={k:spec[k] for k in ['image','address','bytes']}
        with self.assertRaisesRegex(ValueError,'ABI prefix includes a dyld fixup'):validate_abi(self.images,plan)

    def test_actual_error_metadata_accessor_survives_image_relocation(self):
        spec=self.plan['abi']['_$s12TwitchApollo0A12GraphQLErrorVMa'];data=self.images[spec['image']][1]
        prefix=data[file_offset(data,spec['address']):file_offset(data,spec['address'])+16]
        for slide in [0,0x410000000]:
            u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);page=slide+(spec['address']&~4095)
            u.mem_map(page,4096);u.mem_write(slide+spec['address'],prefix)
            end=0x500000000;u.mem_map(end,4096);u.reg_write(UC_ARM64_REG_X30,end)
            u.emu_start(slide+spec['address'],end,count=10)
            self.assertEqual(u.reg_read(UC_ARM64_REG_X0),slide+0x14a20)
            self.assertEqual(u.reg_read(UC_ARM64_REG_X1),0)

    def test_notification_raw_value_accessor_uses_metadata_and_swift_context(self):
        spec = self.plan['abi']['_$s9ApolloAPI11GraphQLEnumO8rawValueSSvg']
        for known in (False, True):
            with self.subTest(known=known):
                vm = self.machine('ApolloAPI')
                value, metadata, payload = 0x4000100, 0x4000200, 0x4000300
                enum_vwt, payload_vwt, conformance = 0x4000400, 0x4000500, 0x4000600
                copy, project, destroy = 0x4000700, 0x4000800, 0x4000900
                getter = 0x4000A00
                words = struct.pack('<2Q', 0x1234, 0x5678)
                vm.mem_write(value, words + b'\x00')
                for addr, word in (
                    (metadata - 8, enum_vwt), (metadata + 16, payload), (metadata + 24, conformance),
                    (enum_vwt + 16, copy), (enum_vwt + 64, 17), (payload - 8, payload_vwt),
                    (payload_vwt + 8, destroy), (payload_vwt + 32, project), (payload_vwt + 64, 16),
                    (conformance + 32, getter),
                ):
                    vm.mem_write(addr, struct.pack('<Q', word))
                vm.reg_write(UC_ARM64_REG_X0, metadata)
                vm.reg_write(UC_ARM64_REG_X20, value)
                calls = []

                def hook(machine, pc, size, _):
                    x0, x1, x2 = (machine.reg_read(register) for register in
                                  (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2))
                    if pc == copy:
                        self.assertEqual((x1, x2), (value, metadata))
                        machine.mem_write(x0, bytes(machine.mem_read(x1, 17)))
                    elif pc == 0x256EC:
                        self.assertEqual(x1, metadata)
                        machine.reg_write(UC_ARM64_REG_X0, 0 if known else 1)
                    elif pc == project:
                        self.assertEqual(x2, payload)
                        machine.mem_write(x0, bytes(machine.mem_read(x1, 16)))
                    elif pc == 0x2511C:
                        self.assertEqual((x0, x1), (payload, getter))
                        self.assertEqual(bytes(machine.mem_read(machine.reg_read(UC_ARM64_REG_X20), 16)), words)
                        machine.mem_write(machine.reg_read(UC_ARM64_REG_X8), words)
                    elif pc == destroy:
                        self.assertEqual(x1, payload)
                    else:
                        return
                    calls.append(pc)
                    machine.reg_write(UC_ARM64_REG_PC, machine.reg_read(UC_ARM64_REG_X30))

                vm.hook_add(UC_HOOK_CODE, hook)
                vm.emu_start(spec['address'], 0x4200000, count=100)
                self.assertEqual(vm.reg_read(UC_ARM64_REG_PC), 0x4200000)
                self.assertEqual((vm.reg_read(UC_ARM64_REG_X0), vm.reg_read(UC_ARM64_REG_X1)), (0x1234, 0x5678))
                self.assertEqual(calls, [copy, 0x256EC, project, 0x2511C, destroy] if known else [copy, 0x256EC])
