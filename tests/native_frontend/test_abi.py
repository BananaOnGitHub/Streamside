import os
import shutil
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X8,UC_ARM64_REG_X20,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_PC

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from macho import load_commands


class SwiftCalls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();directory=Path(cls.temp.name)
        prebuilt=os.environ.get('SSN_ABI_OBJECT')
        if prebuilt:
            cls.object=Path(prebuilt).resolve()
        else:
            executable=os.environ.get('ZIG') or shutil.which('zig')
            if not executable: raise RuntimeError('Set ZIG or add Zig 0.14.0 to PATH, or provide SSN_ABI_OBJECT')
            zig=Path(executable).resolve()
            cls.object=directory/'abi.o'
            subprocess.run([str(zig),'cc','-target','aarch64-ios-none','-O1','-c','-isystem',str(zig.parent/'lib/libc/include/any-macos-any'),'-I'+str(ROOT/'native'),
                            '-o',str(cls.object),str(ROOT/'tests/native_frontend/abi_calls.c')],check=True,
                            env=dict(os.environ,ZIG_LOCAL_CACHE_DIR=str(directory/'cache'),ZIG_GLOBAL_CACHE_DIR=str(directory/'global')))
        data=cls.object.read_bytes();cls.symbols={};cls.sections=[]
        for command in load_commands(data):
            if command.command==0x19:
                for i in range(struct.unpack_from('<I',data,command.offset+64)[0]):
                    pos=command.offset+72+i*80;addr,length,off=struct.unpack_from('<QQI',data,pos+32)
                    cls.sections.append((addr,data[off:off+length]))
            if command.command==2:
                so,n,st,ss=struct.unpack_from('<4I',data,command.offset+8)
                for i in range(n):
                    no,ty,se,de,addr=struct.unpack_from('<IBBHQ',data,so+i*16)
                    if no:cls.symbols[data[st+no:data.index(0,st+no)].decode()]=addr

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def call(self,name,arguments,expected,context=None,out=None,stack_arguments=None):
        u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);base=0x100000;callback=0x200000;stack=0x300000;end=0x400000
        u.mem_map(base,0x10000);u.mem_map(callback,4096);u.mem_map(stack,0x10000);u.mem_map(end,4096)
        for addr,data in self.sections:
            if data:u.mem_write(base+addr,data)
        for i,arg in enumerate([callback]+arguments):u.reg_write(UC_ARM64_REG_X0+i,arg)
        u.reg_write(UC_ARM64_REG_SP,stack+0x8000);u.reg_write(UC_ARM64_REG_X30,end)
        seen=[]
        def hook(u,pc,size,unused):
            if pc==callback:
                seen.append(True)
                for i,value in enumerate(expected):self.assertEqual(u.reg_read(UC_ARM64_REG_X0+i),value,('argument',i))
                if context is not None:self.assertEqual(u.reg_read(UC_ARM64_REG_X20),context,'swiftself/context must use X20')
                if out is not None:self.assertEqual(u.reg_read(UC_ARM64_REG_X8),out,'indirect result must use X8')
                if stack_arguments is not None:
                    current_sp=u.reg_read(UC_ARM64_REG_SP)
                    self.assertEqual(struct.unpack('<'+'Q'*len(stack_arguments),bytes(u.mem_read(current_sp,8*len(stack_arguments)))),tuple(stack_arguments))
                ret=u.reg_read(UC_ARM64_REG_X30)
                u.reg_write(UC_ARM64_REG_X0,0xabcdef01);u.reg_write(UC_ARM64_REG_X0+1,0xabcdef02);u.reg_write(UC_ARM64_REG_X0+2,0xabcdef03)
                u.reg_write(UC_ARM64_REG_PC,ret)
        u.hook_add(UC_HOOK_CODE,hook)
        u.emu_start(base+self.symbols['_'+name],end,count=2000)
        self.assertEqual(seen,[True]);return u

    def test_current_user_indirect_result_and_native_self(self):self.call('call_current',[0x1234,0x5678],[],context=0x5678,out=0x1234)
    def test_followed_users_limit_cursor_set_self_and_result(self):
        self.call('call_follows',[0x1234,0x5678,11,22,33,44],[50,11,22,33,44],context=0x5678,out=0x1234)
    def test_promise_mapping_closures_metadata_and_self(self):
        u=self.call('call_promise',[0x1234,0x1111,0x2222,0x3333,0x4444],[0x1111,0,0x2222,0,0x3333,0x4444,0x4444],context=0x1234)
        self.assertEqual(u.reg_read(UC_ARM64_REG_X0),0xabcdef01)
    def test_mapping_closure_value_and_context(self):self.call('call_map',[0x1234,0x5678],[0x1234],context=0x5678)
    def test_string_pair_direct_result(self):
        u=self.call('call_string',[0x1234],[],context=0x1234)
        self.assertEqual(u.reg_read(UC_ARM64_REG_X0),0xabcdef01);self.assertEqual(u.reg_read(UC_ARM64_REG_X0+1),0xabcdef02)
    def test_model_getter_indirect_result(self):self.call('call_getter',[0x1234,0x5678],[],context=0x5678,out=0x1234)

    def test_personal_sections_native_self_nil_name_sort_and_set(self):
        self.call('call_personal',[0x1234,0x5678,44],[0,0,0,44],context=0x5678,out=0x1234)
    def test_sections_passes_complete_direct_response(self):
        self.call('call_sections',[11,22],[11,22])
    def test_generic_trackable_item_metadata_and_native_self(self):
        self.call('call_item',[0x1234,0x4321,0x5678],[0x4321],context=0x5678,out=0x1234)
    def test_thumbnails_three_word_result(self):
        u=self.call('call_thumbnails',[0x304000,0x5678],[],context=0x5678)
        self.assertEqual(bytes(u.mem_read(0x304000,24)),struct.pack('<3Q',0xabcdef01,0xabcdef02,0xabcdef03))
    def test_thumbnail_url_size_and_three_value_words(self):
        self.call('call_thumbnail_url',[0x1234,11,22,33],[2,11,22,33],out=0x1234)
    def test_viewer_count_context(self):
        self.call('call_integer',[0x5678],[],context=0x5678)

    def test_playback_client_native_self(self):self.call('call_client',[0x5678],[],context=0x5678)
    def test_playback_params_registers_and_stack(self):
        self.call('call_playback_params',[],[0,2,2,0,0,0,0,11],stack_arguments=[22,0,0,33,44,0,1])
    def test_playback_query_consuming_arguments_and_metatype(self):
        self.call('call_playback_query',[0x5678],[11,22,33],context=0x5678)
    def test_playback_fetch_expanded_client_generics_and_result(self):
        self.call('call_playback_fetch',[0x1234,0x5678,0x9abc],[11,1,22,33,0x5678,0x9abc],out=0x1234)
    def test_playback_generated_fields_are_direct_values(self):
        self.call('call_playback_field',[0x5678],[0x5678])
        self.call('call_playback_string',[0x5678],[0x5678])

if __name__=='__main__':unittest.main()
