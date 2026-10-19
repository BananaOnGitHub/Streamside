"""Inspect recorded React donor Objective-C methods; never execute donor code."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from macho import load_commands

EXPECTED='7d8182670d42fcf521470b5e6221b21f7c3cfb23a3bfe1461ff464a6f9cc3f38'
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
    def methods(self):
        result=[];start,size=self.sections['__objc_classlist']
        for p in range(start,start+size,8):
            cls=self.ptr(p);ro=self.ptr(cls+32)&~7;name=self.text(self.ptr(ro+24));methods=self.ptr(ro+32)
            if not methods:continue
            flags,count=self.unpack('<2I',methods)
            if count>2048:raise ValueError('Method bound')
            entry_size=flags&0xffff
            for i in range(count):
                at=methods+8+i*entry_size
                if flags&0x80000000:
                    n,t,imp=self.unpack('<3i',at);np=at+n
                    if not flags&0x40000000:np=self.ptr(np)
                    selector=self.text(np);address=at+8+imp
                    encoding=self.text(at+4+t) if name in {'RCTCallableJSModules','RCTInstance','RCTModuleData','RCTBridgeModuleDecorator'} else '<not inspected>'
                else:
                    selector=self.text(self.ptr(at));encoding=self.text(self.ptr(at+8));address=self.ptr(at+16)
                result.append({'class':name,'selector':selector,'encoding':encoding,'address':address})
        return result
def inspect(path):
    from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=EXPECTED:raise ValueError('Unrecorded React donor')
    image=Image(data);methods=image.methods();dis=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);dis.detail=True
    addresses=sorted({x['address'] for x in methods})
    targets={'RCTCallableJSModules':{'invokeModule:method:withArgs:','invokeModule:method:withArgs:onComplete:','setBridgelessJSModuleMethodInvoker:'},'RCTInstance':{'_attachBridgelessAPIsToModule:'},'RCTModuleData':{'setUpInstanceAndBridge:'},'RCTBridgeModuleDecorator':{'attachInteropAPIsToModule:'}}
    result=[]
    for m in methods:
        if m['selector'] not in targets.get(m['class'],set()):continue
        at=m['address'];end=next((a for a in addresses if a>at),at+2048);size=min(end-at,4096)
        output=[]
        for x in dis.disasm(data[image.offset(at):image.offset(at)+size],at):output.append(hex(x.address)+' '+x.mnemonic+' '+x.op_str)
        result.append(dict(m,disassembly=output))
    return {'react_sha256':EXPECTED,'methods':result,'native_execution':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('react',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();result=inspect(a.react);text=json.dumps(result,indent=2)+'\n'
    if a.output:a.output.write_text(text)
    else:print(text)
