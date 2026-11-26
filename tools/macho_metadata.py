"""Read the file-backed segments and metadata strings of a Mach-O image."""
import struct
from macho import load_commands

class Image:
    def __init__(self,data):
        self.data=data;self.segments=[];self.sections={}
        for c in load_commands(data):
            if c.command!=0x19:continue
            vm,vs,off,size=struct.unpack_from('<4Q',data,c.offset+24);self.segments.append((vm,size,off))
            for i in range(struct.unpack_from('<I',data,c.offset+64)[0]):
                at=c.offset+72+i*80;name=data[at:at+16].split(b'\0')[0].decode();addr,size=struct.unpack_from('<2Q',data,at+32)
                self.sections[name]=(addr,size)
    def offset(self,vm,n=1):
        for start,size,off in self.segments:
            if start<=vm and n<=size-(vm-start):return off+vm-start
        raise ValueError('Address outside file-backed image: '+hex(vm))
    def unpack(self,fmt,at):return struct.unpack_from(fmt,self.data,self.offset(at,struct.calcsize(fmt)))
    def ptr(self,at):
        raw=self.unpack('<Q',at)[0]
        if raw>>63:raise ValueError('External chained bind is not an image pointer')
        return raw&((1<<36)-1)
    def text(self,at):
        off=self.offset(at);end=self.data.find(b'\0',off,min(len(self.data),off+2048))
        if end<0:raise ValueError('Unterminated metadata')
        return self.data[off:end].decode('utf-8')
