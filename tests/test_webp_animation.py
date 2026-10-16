"""Production WebP container/timing admission with synthetic, pixel-free fixtures."""
import ctypes
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def chunk(kind,data):
    return kind+struct.pack('<I',len(data))+data+b'\0'*(len(data)&1)
def u24(value):return value.to_bytes(3,'little')
def animation(delays,width=4,height=3,rect=None):
    body=chunk(b'VP8X',b'\x02\0\0\0'+u24(width-1)+u24(height-1))+chunk(b'ANIM',b'\0'*6)
    for delay in delays:
        x,y,w,h=rect or (0,0,width,height)
        header=u24(x//2)+u24(y//2)+u24(w-1)+u24(h-1)+u24(delay)+b'\0'
        body+=chunk(b'ANMF',header+chunk(b'VP8L',b'\x2f'+struct.pack('<I',(w-1)|((h-1)<<14))))
    return b'RIFF'+struct.pack('<I',len(body)+4)+b'WEBP'+body

class Info(ctypes.Structure):
    _fields_=[('width',ctypes.c_uint),('height',ctypes.c_uint),('count',ctypes.c_uint),('delays',ctypes.c_uint32*2048)]
class WebPAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();root=Path(cls.temp.name)
        (root/'test.c').write_text('#include "TASWebPModel.h"\nint parse(const unsigned char *p,size_t n,TASWebPInfo *v){return tas_webp_info(p,n,v);}\n')
        subprocess.run(['cc','-shared','-fPIC','-Wall','-Wextra','-Werror','-I',str(ROOT/'src'),str(root/'test.c'),'-o',str(root/'test.so')],check=True)
        cls.lib=ctypes.CDLL(str(root/'test.so'));cls.lib.parse.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(Info)]
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def parse(self,body):
        info=Info();return self.lib.parse(body,len(body),ctypes.byref(info)),info
    def test_real_asset_timing_shapes_and_arbitrary_holds(self):
        # Measured public 7TV WebP timings; no provider artwork in the fixture.
        for delays in [[200]*8+[600],[300]+[30]*46+[2170],[20,12500,30,60000]]:
            ok,info=self.parse(animation(delays));self.assertEqual(ok,1)
            self.assertEqual(list(info.delays)[:info.count],delays)
    def test_short_frame_browser_normalization_and_static_webp(self):
        ok,info=self.parse(animation([0,1,10,11,19,20]));self.assertEqual(ok,1)
        self.assertEqual(list(info.delays)[:6],[100,100,100,20,20,20])
        body=chunk(b'VP8L',b'\x2f'+b'\0'*4);ok,info=self.parse(b'RIFF'+struct.pack('<I',len(body)+4)+b'WEBP'+body)
        self.assertEqual((ok,info.width,info.height,info.count),(1,1,1,1))
    def test_complete_structure_canvas_bounds_and_frame_caps(self):
        body=animation([200,600]);self.assertEqual(self.parse(body)[0],1)
        for end in range(len(body)):self.assertEqual(self.parse(body[:end])[0],0)
        self.assertEqual(self.parse(body+b'\0')[0],0)
        for invalid in [animation([20]),animation([20]*2049),animation([20,20],1024,1024),animation([20,20],4,3,(2,0,4,3))]:
            self.assertEqual(self.parse(invalid)[0],0)
        self.assertEqual(self.parse(animation([20]*2048))[0],1)
        bad=bytearray(body);bad[4:8]=b'\xff'*4
        self.assertEqual(self.parse(bytes(bad))[0],0)
        bad=bytearray(body);at=bad.index(b'ANMF');bad[at+4:at+8]=b'\xff'*4
        self.assertEqual(self.parse(bytes(bad))[0],0)
    def test_inner_bitstream_cannot_exceed_declared_frame_budget(self):
        body=bytearray(animation([20,600]));index=body.index(b'VP8L')+8
        body[index+1:index+5]=struct.pack('<I',8191|(8191<<14))
        self.assertEqual(self.parse(bytes(body))[0],0)

    def test_subrectangle_blend_and_disposal_flags_are_accepted(self):
        body=bytearray(animation([20,600],8,8,(2,2,4,4)))
        # Both no-blend and background-disposal are delegated to ImageIO.
        at=body.index(b'ANMF')+8+15;body[at]=3
        self.assertEqual(self.parse(bytes(body))[0],1)
        body[at]=4;self.assertEqual(self.parse(bytes(body))[0],0)

    def test_native_adapter_factory_cache_lifecycle_and_provider_scope(self):
        import os, shutil
        from test_emote_ui import RUNTIME
        zig=os.environ.get('ZIG') or shutil.which('zig');self.assertTrue(zig)
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);(folder/'objc').mkdir()
            runtime=RUNTIME+'\nBOOL class_addIvar(Class,const char *,size_t,uint8_t,const char *);\n'
            for name in ['objc.h','runtime.h','message.h']:(folder/'objc'/name).write_text(runtime)
            body=animation([200,12500,600])
            source=(ROOT/'src/TASAnimatedImage.c').read_text().replace('((id (*)(id,SEL,double))objc_msgSend)','test_number')
            (folder/'TASAnimatedImage.c').write_text(source)
            harness=(ROOT/'tests/native/webp_adapter.c').read_text()
            harness='static unsigned char fixture[]={'+','.join(str(b) for b in body)+'};\n'+harness
            (folder/'test.c').write_text(harness)
            result=subprocess.run([zig,'cc','-fblocks','-fsanitize=address,undefined','-I',str(folder),'-I',str(ROOT/'src'),str(folder/'test.c'),'-ldl','-pthread','-o',str(folder/'test')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            subprocess.run([str(folder/'test')],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
