"""Production HBC patch gates/layout, plus emitted instruction semantics.

The large fixture is NOT Twitch or a runnable JS bundle. A fixture SHA callback
isolates container handling; tools/verify_rn_width.py validates the real donor
with actual SHA-1, its complete instruction table and every original branch.
Neither test establishes on-device Fabric execution.
"""
import math
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = r'''
#include <assert.h>
#include <stdio.h>
#include "TASRNWidthPatch.h"
#include "TASRNLocalEchoPatch.h"
static bool fail_sha;
static unsigned char *fixture_sha(const void *p,uint32_t n,unsigned char *out) {
    (void)p;(void)n;if(fail_sha)return NULL;
    const unsigned char d[]={0x5f,0x22,0x11,0x97,0x49,0x24,0x27,0x17,0xf3,0x78,
        0x87,0x97,0xcf,0x50,0xa7,0x7f,0x0e,0xdc,0x07,0x15};memcpy(out,d,20);return out;
}
int main(int argc,char **argv) {
    assert(argc==2);
    unsigned char code[192];size_t a=tas_rn_width_code(code,13);
    if(!strcmp(argv[1],"code")){assert(fwrite(code,1,a,stdout)==a);return 0;}
    if(!strcmp(argv[1],"localcode")){a=tas_rn_local_code(code);assert(fwrite(code,1,a,stdout)==a);return 0;}
    assert(tas_rn_width_id(900000000000001ULL,1)%10000==1000);
    assert(tas_rn_width_id(900000000000001ULL,0)%10000==1000);
    assert(tas_rn_width_id(900000000000001ULL,-2)%10000==1000);
    assert(tas_rn_width_id(900000000000001ULL,.01)%10000==125);
    assert(tas_rn_width_id(900000000000001ULL,8)%10000==5000);
    assert(tas_rn_width_id(900000000000001ULL,3.333)%10000==3333);
    assert(tas_rn_width_id(900000000000001ULL,1)!=tas_rn_width_id(900000000000002ULL,1));
    unsigned char *body=calloc(1,TAS_RN_BODY_SIZE);assert(body);
    const unsigned char small[]={0xf4,0x4b,0x9b,0,0,0x40,0,0,0,0,0,0x20};
    const unsigned char large[]={0x79,0x1a,0x49,1,2,0,0,0,0,0,0,0,0xb3,3,0,0,
        0x37,0x41,0,0,2,0,0,0,2,0,0,0,0x29,0,0,0,0x1b,0,0,0};
    tas_rn_put32(body,0x03bc1fc6);tas_rn_put32(body+4,0x1f1903c1);
    tas_rn_put32(body+8,98);tas_rn_put32(body+32,TAS_RN_BODY_SIZE);
    memcpy(body+TAS_RN_SMALL_HEADER,small,sizeof(small));
    memcpy(body+TAS_RN_LARGE_HEADER,large,sizeof(large));
    const unsigned char local_header[]={0xc2,0x1e,0x7e,7,0xac,2,0x3e,0x18,0x22,0x15,1,2};
    memcpy(body+TAS_RN_LOCAL_HEADER,local_header,12);
    tas_rn_put32(body+TAS_RN_LOCAL_OFFSET+9,672);
    tas_rn_put32(body+TAS_RN_LOCAL_OFFSET+0x14,661);
    fixture_sha(NULL,0,body+TAS_RN_BODY_SIZE-20);
    for(unsigned i=0;i<TAS_RN_FUNCTION_SIZE;i++)body[TAS_RN_FUNCTION_OFFSET+i]=(unsigned char)i;
    size_t n=99;assert(!tas_rn_width_patch(NULL,TAS_RN_BODY_SIZE,fixture_sha,&n)&&!n);
    assert(!tas_rn_width_patch(body,TAS_RN_BODY_SIZE-1,fixture_sha,&n));
    assert(!tas_rn_width_patch(body,TAS_RN_BODY_SIZE,NULL,&n));
    assert(!tas_rn_width_patch(body,TAS_RN_BODY_SIZE,fixture_sha,NULL));
    const unsigned offsets[]={0,4,8,32,TAS_RN_SMALL_HEADER,TAS_RN_LARGE_HEADER,TAS_RN_BODY_SIZE-20};
    for(unsigned i=0;i<sizeof(offsets)/sizeof(offsets[0]);i++) {
        body[offsets[i]]^=1;assert(!tas_rn_width_patch(body,TAS_RN_BODY_SIZE,fixture_sha,&n));body[offsets[i]]^=1;
    }
    fail_sha=true;assert(!tas_rn_width_patch(body,TAS_RN_BODY_SIZE,fixture_sha,&n));fail_sha=false;
    unsigned char *copy=tas_rn_width_patch(body,TAS_RN_BODY_SIZE,fixture_sha,&n);assert(copy);
    assert(n==TAS_RN_BODY_SIZE+TAS_RN_FUNCTION_SIZE+a*2 && tas_rn_u32(copy+32)==n);
    assert(!memcmp(body+TAS_RN_SMALL_HEADER,copy+TAS_RN_SMALL_HEADER,12));
    assert(!memcmp(body+TAS_RN_FUNCTION_OFFSET,copy+TAS_RN_FUNCTION_OFFSET,TAS_RN_FUNCTION_SIZE));
    for(unsigned i=0;i<TAS_RN_BODY_SIZE-20;i++) {
        if((i>=32&&i<36)||(i>=TAS_RN_LARGE_HEADER&&i<TAS_RN_LARGE_HEADER+4)||
            (i>=TAS_RN_LARGE_HEADER+12&&i<TAS_RN_LARGE_HEADER+16))continue;
        assert(body[i]==copy[i]);
    }
    unsigned char *fn=copy+TAS_RN_BODY_SIZE-20;
    assert(!memcmp(fn,body+TAS_RN_FUNCTION_OFFSET,0xd0));
    assert(!memcmp(fn+0xd0,code,a));
    assert(!memcmp(fn+0xd0+a,body+TAS_RN_FUNCTION_OFFSET+0xd0,0x238-0xd0));
    tas_rn_width_code(code,14);assert(!memcmp(fn+0x238+a,code,a));
    assert(!memcmp(fn+0x238+a*2,body+TAS_RN_FUNCTION_OFFSET+0x238,TAS_RN_FUNCTION_SIZE-0x238));
    size_t second=5;assert(!tas_rn_width_patch(copy,n,fixture_sha,&second)&&!second);
    unsigned char local_code[96];size_t local_extra=tas_rn_local_code(local_code),local_count=0;
    assert(!tas_rn_local_patch(body,TAS_RN_BODY_SIZE,fixture_sha,&local_count));
    copy[TAS_RN_LOCAL_HEADER]^=1;assert(!tas_rn_local_patch(copy,n,fixture_sha,&local_count));copy[TAS_RN_LOCAL_HEADER]^=1;
    copy[n-1]^=1;assert(!tas_rn_local_patch(copy,n,fixture_sha,&local_count));copy[n-1]^=1;
    fail_sha=true;assert(!tas_rn_local_patch(copy,n,fixture_sha,&local_count));fail_sha=false;
    unsigned char *local=tas_rn_local_patch(copy,n,fixture_sha,&local_count);assert(local);
    assert(local_count==n+684+local_extra);
    assert(!memcmp(local+TAS_RN_LARGE_HEADER,copy+TAS_RN_LARGE_HEADER,36));
    assert(!memcmp(local+TAS_RN_BODY_SIZE-20,copy+TAS_RN_BODY_SIZE-20,1207));
    assert(!memcmp(local+TAS_RN_LOCAL_OFFSET,copy+TAS_RN_LOCAL_OFFSET,684));
    unsigned char *new_fn=local+n-20;
    assert(tas_rn_u32(new_fn+9)==672+local_extra && tas_rn_u32(new_fn+0x14)==661+local_extra);
    assert(!memcmp(new_fn+0x2a6,local_code,local_extra));
    assert(!memcmp(new_fn+0x2a6+local_extra,body+TAS_RN_LOCAL_OFFSET+0x2a6,6));
    for(unsigned i=0;i<n-20;i++) {
        if((i>=32&&i<36)||(i>=TAS_RN_LOCAL_HEADER&&i<TAS_RN_LOCAL_HEADER+6))continue;
        assert(copy[i]==local[i]);
    }
    assert(!tas_rn_local_patch(local,local_count,fixture_sha,&second));free(local);
    free(copy);free(body);return 0;
}
'''


def evaluate(code, identity, gigantified=False):
    """Only the emitted non-call instructions, not a fabricated RN success."""
    original = object()
    regs = {10: identity, 11: gigantified, 13: original}
    pos = 0
    while pos < len(code):
        at = pos
        op = code[pos]
        pos += 1
        if op == 154:  # ToNumber
            dest, src = code[pos:pos+2]; pos += 2
            try: regs[dest] = float(regs[src])
            except ValueError: regs[dest] = math.nan
        elif op in (141, 140, 139, 144):
            dest = code[pos]; pos += 1
            form = {141: 'd', 140: 'i', 139: 'B', 144: 'H'}[op]
            size = struct.calcsize('<'+form)
            value = struct.unpack_from('<'+form, code, pos)[0]; pos += size
            regs[dest] = 'width' if op == 144 else value
        elif op in (26, 27, 33, 35, 37):
            dest, left, right = code[pos:pos+3]; pos += 3
            x, y = regs[left], regs[right]
            regs[dest] = {26: lambda: x < y, 27: lambda: x <= y,
                33: lambda: x*y, 35: lambda: x/y, 37: lambda: x % y}[op]()
        elif op in (179, 178):
            size = 4 if op == 179 else 1
            delta = int.from_bytes(code[pos:pos+size], 'little', signed=True)
            test = code[pos+size]; pos += size+1
            if not regs[test]: pos = at+delta
        elif op == 4:
            regs[code[pos]] = {}; pos += 1
        elif op == 96:
            obj, key, val = code[pos:pos+3]; pos += 3
            regs[obj][regs[key]] = regs[val]
        elif op == 8:
            dest = code[pos]; count = struct.unpack_from('<H', code, pos+1)[0]; pos += 3
            regs[dest] = [None]*count
        elif op == 90:
            dest, src, index = code[pos:pos+3]; pos += 3
            regs[dest][index] = regs[src]
        elif op == 16:
            dest, src = code[pos:pos+2]; pos += 2; regs[dest] = regs[src]
        else: raise AssertionError(f'Unexpected opcode {op} at {at}')
    return original, regs[13]


class RNWidthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        root = Path(cls.directory.name)
        source = root/'width.c'; source.write_text('#include <stdbool.h>\n'+HARNESS)
        cls.binary = root/'width'
        zig = os.environ.get('ZIG') or shutil.which('zig')
        if not zig: raise AssertionError('Zig required for production width harness')
        result = subprocess.run([zig,'cc','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
            '-I',str(ROOT/'src'),str(source),'-o',str(cls.binary)],capture_output=True,text=True)
        if result.returncode: raise AssertionError(result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_exact_admission_immutable_body_headers_footer_and_fallback(self):
        result = subprocess.run([self.binary,'patch'],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode())

    def test_emitted_styles_native_identity_square_wide_narrow_and_enlarged(self):
        result = subprocess.run([self.binary,'code'],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        for identity in ['25','emotesv2_ABC','900000000001234','859999999999999',
            '861000000000000','860000000000124','860000000005001']:
            before, after = evaluate(result.stdout,identity)
            self.assertIs(before,after)
        for aspect in [.125,.5,1,2,3.2,5]:
            for enlarged in [False,True]:
                identity = str(860000000000000+round(aspect*1000))
                before, after = evaluate(result.stdout,identity,enlarged)
                self.assertIs(after[0],before)
                self.assertEqual(after[1],{'width': (56 if enlarged else 24)*aspect})

    def test_local_shim_uses_native_modules_loader_and_preserves_missing_bridge_identity(self):
        code=subprocess.run([self.binary,'localcode'],capture_output=True,check=True).stdout
        for route in ['classic_config','native_proxy']:
            for available in range(6):
                original=object(); replacement=object(); calls=[]; requires=[]
                def render(this,line):
                    self.assertIs(this,module)
                    self.assertIs(line,original);calls.append(line);return replacement
                module={} if available<5 else {'buildLocalEcho':render}
                modules={} if available<4 else {'buildLocalEcho':module}
                exports={} if available<3 else {'default':modules}
                def require(this,identity):
                    self.assertIs(this,global_object);self.assertEqual(identity,16)
                    requires.append(identity)
                    return None if available<2 else exports
                global_object={} if available<1 else {'__r':require}
                # Classic RN has no global nativeModuleProxy. In bridgeless RN
                # NativeModules returns that proxy through the same module.
                if route=='native_proxy': global_object['nativeModuleProxy']=modules
                regs={3:original};pos=0
                while pos<len(code):
                    at=pos;op=code[pos];pos+=1
                    if op==61: regs[code[pos]]=global_object;pos+=1
                    elif op==144:
                        dest=code[pos];key=struct.unpack_from('<H',code,pos+1)[0];pos+=3
                        regs[dest]={18843:'__r',110:'default',20058:'buildLocalEcho'}[key]
                    elif op==139:
                        dest,val=code[pos:pos+2];pos+=2;regs[dest]=val
                    elif op==93:
                        dest,obj,key=code[pos:pos+3];pos+=3;regs[dest]=regs[obj].get(regs[key])
                    elif op==179:
                        delta=struct.unpack_from('<i',code,pos)[0];test=code[pos+4];pos+=5
                        # Empty JS objects are truthy.
                        if regs[test] is None: pos=at+delta
                    elif op==110:
                        dest,fn,this,arg=code[pos:pos+4];pos+=4;regs[dest]=regs[fn](regs[this],regs[arg])
                    else: self.fail(f'Unexpected local shim opcode {op}')
                self.assertIs(regs[3],replacement if available==5 else original)
                self.assertEqual(len(calls),available==5)
                self.assertEqual(len(requires),available>0)
