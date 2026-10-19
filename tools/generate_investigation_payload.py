"""Generate owned payloads and relocation metadata, never donor function bodies."""
import argparse
import hashlib
from pathlib import Path
import struct
import tempfile
from rn_graft import generate,read,parse_hbc_bytecode
from hermes_dec.parsers.hbc_opcodes import hbc98
from validate_rn_snapshot import patch_chain
ROOT=Path(__file__).resolve().parent.parent
JOIN=0x11ce
def encode(name,*args):
    op=hbc98._name_to_instruction[name];v=op.structure()
    for i,a in enumerate(args):setattr(v,'arg'+str(i+1),a)
    return bytes([op.opcode])+bytes(v)
def parts(h):
    f=h.function_headers[22318]
    if f.frameSize!=91 or f.hasExceptionHandler or f.hasDebugInfo:raise ValueError('Unsupported list function frame/metadata')
    ops=list(parse_hbc_bytecode(f,h));bypos={x.original_pos:x for x in ops}
    seam=bypos[JOIN]
    if seam.inst.name!='Call3' or [getattr(seam,'arg'+str(i)) for i in range(1,6)]!=[13,35,2,34,13]:raise ValueError('Changed scoped list JSX seam')
    if bypos[0].inst.name!='GetParentEnvironment' or bypos[0].arg1!=16:raise ValueError('Changed list parent environment')
    changes=[]
    for x in ops:
        addr=[i for i,o in enumerate(x.inst.operands) if o.operand_type.name.startswith('Addr')]
        if not addr:continue
        if addr!=[0]:raise ValueError('Unsupported branch operand layout')
        wide=hbc98._name_to_instruction[x.inst.name+'Long'] if x.inst.operands[0].operand_type.name=='Addr8' else x.inst
        if wide.operands[0].operand_type.name!='Addr32':raise ValueError('Unsupported branch width')
        changes.append((x,wide))
    before=lambda pos:sum(w.binary_size-x.inst.binary_size for x,w in changes if x.original_pos<pos)
    extra=encode('LoadFromEnvironment',36,16,19)+encode('JmpFalseLong',0,36)+encode('LoadFromEnvironment',37,41,0)+encode('Call3',13,36,37,34,13)+encode('JmpLong',0)
    mapping=lambda pos:pos+before(pos)+(len(extra) if pos>JOIN else 0)
    join=mapping(JOIN)
    extra=encode('LoadFromEnvironment',36,16,19)+encode('JmpFalseLong',len(extra)-4,36)+encode('LoadFromEnvironment',37,41,0)+encode('Call3',13,36,37,34,13)+encode('JmpLong',11)
    # Conditional target is original Call3; successful hook skips that call.
    assert len(extra)==25
    assert any(x.inst.name=="StoreToEnvironment" and (x.arg1,x.arg2,x.arg3)==(41,0,39) for x in ops[:20])
    assert all(not any(o.operand_type.name.startswith("Reg") and getattr(x,"arg"+str(i+1)) in [36,37,41] for i,o in enumerate(x.inst.operands)) for x in ops if x.original_pos>JOIN)
    rows=[(x.original_pos,mapping(x.original_pos),x.inst.binary_size,1 if x.inst.operands[0].operand_type.name=='Addr8' else 4,w.opcode,mapping(x.original_pos+x.arg1)) for x,w in changes]
    return rows,extra,f.bytecodeSizeInBytes+before(f.bytecodeSizeInBytes)+len(extra),join
def generate_all(a):
    donor=a.donor.read_bytes();h=read(donor)
    with tempfile.TemporaryDirectory() as folder:
        predecessor=patch_chain(a.zig,donor,Path(folder))
    original=read(donor);functional=read(predecessor)
    if original.header.functionCount!=48985 or functional.header.functionCount!=49127:raise ValueError('Changed predecessor function counts')
    for label,base in [('Original',48985),('Functional',49127)]:
        generate(a.donor,a.hermesc,ROOT/'src/rn/Investigation.js',ROOT/('src/TASRNInvestigation'+label+'Payload.h'),prefix='INV_'+label.upper(),factory_id=4900,function_base=base)
    rows,extra,size,join=parts(h)
    output=['/* Generated structural metadata; no donor function body. */','#define TAS_INV_INNER_JOIN '+str(JOIN)+'U','#define TAS_INV_INNER_OLD_SIZE '+str(h.function_headers[22318].bytecodeSizeInBytes)+'U','#define TAS_INV_INNER_NEW_SIZE '+str(size)+'U', 'static const unsigned char tas_inv_inner_extra[]={'+','.join(map(str,extra))+'};','static const TASInvBranch tas_inv_branches[]={']
    output += [' {'+','.join(map(str,row))+'},' for row in rows]
    output+=['};']
    for label,body,base in [('original',donor,48985),('functional',predecessor,49127)]:
        output+=['#define TAS_INV_'+label.upper()+'_SIZE '+str(len(body))+'U','static const unsigned char tas_inv_'+label+'_sha256[32]={'+','.join(map(str,hashlib.sha256(body).digest()))+'};']
    output+=['']
    (ROOT/'src/TASRNInvestigationLayout.h').write_text('\n'.join(output))
    print('Scoped inner seam:',len(rows),'branches,',size,'bytes; original component export unchanged')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--donor',type=Path,required=True);p.add_argument('--hermesc',type=Path,required=True);p.add_argument('--zig',type=Path,required=True);generate_all(p.parse_args())
