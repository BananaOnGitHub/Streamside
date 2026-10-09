"""Compile owned functions into an exact-donor Hermes-98 function graft.

No donor bytecode is emitted into the repository. Only property string IDs
and owned compiled functions are generated. Literal buffers, switch tables,
debug data and non-string/function indexed operands are refused.
"""
import ctypes
import hashlib
import io
import struct
import subprocess
import tempfile
from pathlib import Path

from hermes_dec.parsers.hbc_file_parser import HBCReader as ProvisionalReader
from hermes_dec.parsers.hbc_bytecode_parser import parse_hbc_bytecode
from hermes_dec.parsers.hbc_opcodes import hbc98

class HBCReader(ProvisionalReader):
    def get_large_func_header_reader(self):
        reader = super().get_large_func_header_reader()
        if self.header.version != 98: return reader
        fields = list(reader._fields_)
        at = next(i for i, f in enumerate(fields) if f[0] == 'prohibitInvoke')
        fields.insert(at, ('_cache_padding', ctypes.c_uint8))
        fields.append(('_tail_padding', ctypes.c_uint8 * 3))
        return type('Hermes98FullHeader', (ctypes.LittleEndianStructure,),
                    {'_pack_': True, '_fields_': fields})

def read(body):
    h = HBCReader(); h.read_whole_file(io.BytesIO(body)); return h

def assemble(reader, fid, strings, base):
    f = reader.function_headers[fid]
    instructions = list(parse_hbc_bytecode(f, reader))
    rows = []
    for x in instructions:
        inst = x.inst
        if ('Buffer' in inst.name or inst.name in ('SwitchImm', 'CacheNewObject') or
            any(o.operand_meaning and o.operand_meaning.name not in ('string_id','function_id') for o in inst.operands)):
            raise ValueError('Unsupported graft instruction: ' + inst.name)
        args = [getattr(x, 'arg'+str(i+1)) for i in range(len(inst.operands))]
        for i, o in enumerate(inst.operands):
            if o.operand_meaning:
                args[i] = strings[reader.strings[args[i]]] if o.operand_meaning.name == 'string_id' else args[i]+base
        if inst.name.endswith('Short') and any(o.operand_meaning and
                o.operand_meaning.name == 'string_id' and args[i] > 255 for i,o in enumerate(inst.operands)):
            inst = hbc98._name_to_instruction[inst.name[:-5]]
        if any(o.operand_meaning and o.operand_meaning.name == 'string_id' and args[i] > 65535
               for i,o in enumerate(inst.operands)):
            name = {'LoadConstString':'LoadConstStringLongIndex', 'GetById':'GetByIdLong',
                    'PutByIdLoose':'PutByIdLooseLong','PutByIdStrict':'PutByIdStrictLong',
                    'PutNewOwnByIdShort':'PutNewOwnById','PutNewOwnById':'PutNewOwnByIdLong',
                    'TryGetById':'TryGetByIdLong'}.get(inst.name)
            if not name or name not in hbc98._name_to_instruction: raise ValueError('Cannot widen '+inst.name)
            inst = hbc98._name_to_instruction[name]
        # Always widen short branches: relocation then has no fixed point.
        if any(o.operand_type.name == 'Addr8' for o in inst.operands):
            inst = hbc98._name_to_instruction[inst.name+'Long']
        rows.append((x,inst,args))
    # Get/PutById require an already materialized identifier in Hermes. A
    # spelling present only as a donor literal (e.g. "remember") is not enough:
    # getSymbolIDMustExist does not intern it. Materialize those owned property
    # operands with LoadConstString before the function initializes registers.
    # Register 0 is uninitialized at entry; no frame/outgoing-call layout changes.
    literal_properties = set()
    for x,inst,args in rows:
        if inst.name.startswith(('GetById','TryGetById','PutById','PutNewOwnById')):
            for i,o in enumerate(x.inst.operands):
                if o.operand_meaning and o.operand_meaning.name == 'string_id':
                    # strings carries the exact donor kind alongside IDs below.
                    if getattr(strings,'kinds',{}).get(args[i]) == 0: literal_properties.add(args[i])
    prefix = bytearray()
    if literal_properties and not f.frameSize: raise ValueError('No entry scratch register')
    for sid in sorted(literal_properties):
        inst=hbc98._name_to_instruction['LoadConstStringLongIndex' if sid>65535 else 'LoadConstString']
        encoded=inst.structure();encoded.arg1=0;encoded.arg2=sid
        prefix.append(inst.opcode);prefix.extend(bytes(encoded))
    positions = {}; total = len(prefix)
    for x,inst,args in rows:
        positions[x.original_pos] = total; total += inst.binary_size
    positions[f.bytecodeSizeInBytes] = total
    body = prefix
    for x,inst,args in rows:
        for i,o in enumerate(inst.operands):
            if o.operand_type.name.startswith('Addr'):
                args[i] = positions[x.original_pos+args[i]]-positions[x.original_pos]
        encoded = inst.structure()
        for i,o in enumerate(inst.operands):
            v=args[i]; typ=o.operand_type.c_type
            if typ is not ctypes.c_double:
                bits=ctypes.sizeof(typ)*8; signed=o.operand_type.name.startswith(('Addr','Imm'))
                valid = (-(1<<(bits-1)) <= v < (1<<(bits-1))) if signed else (0 <= v < (1<<bits))
                if not valid:
                    raise ValueError('Operand overflow '+inst.name)
            setattr(encoded,'arg'+str(i+1),v)
        body.append(inst.opcode); body.extend(bytes(encoded))
    exceptions = [(positions[e.start],positions[e.end],positions[e.target])
                  for e in reader.function_id_to_exc_handlers.get(fid,[])]
    return bytes(body), exceptions

def generate(donor, compiler, source, output, *, prefix='POPUP', factory_id=3801, function_base=None):
    original = Path(donor).read_bytes()
    if hashlib.sha256(original).hexdigest() != '422314432a66fd439fee24a62959e74678dcd9394a0b4d9ec43bbed970ffc83b':
        raise ValueError('Wrong donor')
    h = read(original)
    class DonorStrings(dict): pass
    ids = DonorStrings({s:i for i,s in reversed(list(enumerate(h.strings)))})
    ids.kinds = dict(enumerate(h.string_kinds))
    with tempfile.TemporaryDirectory() as tmp:
        file = Path(tmp)/'owned.hbc'
        subprocess.run([str(compiler),'-O','-fno-inline','-g0','-emit-binary','-out',str(file),str(source)],check=True)
        owned = read(file.read_bytes())
    if owned.header.version != 98 or owned.strings[owned.function_headers[1].functionName] != 'install':
        raise ValueError('Unexpected compiler/entry point')
    # Global function is never imported/invoked. Function 1 is install(),
    # compiled without parent captures, and all closures are within its tree.
    base = (h.header.functionCount if function_base is None else function_base)-1
    payload = bytearray(); entries=[]
    for fid,f in enumerate(owned.function_headers):
        if not fid: continue
        if f.hasDebugInfo: raise ValueError('Owned debug metadata is not supported')
        code,exc = assemble(owned,fid,ids,base)
        start=len(payload); payload.extend(code)
        while len(payload)%4: payload.append(0)
        info=len(payload)
        flags=f.prohibitInvoke | (int(f.strictMode)<<2) | (bool(exc)<<3) | (f.kind<<6)
        payload.extend(struct.pack('<8I',start,f.paramCount,f.loopDepth,len(code),ids[''],f.numberRegCount,f.nonPtrRegCount,f.frameSize))
        payload.extend(bytes((f.readCacheSize,f.writeCacheSize,f.privateNameCacheSize,0,flags,0,0,0)))
        if exc:
            payload.extend(struct.pack('<I',len(exc)))
            for e in exc: payload.extend(struct.pack('<3I',*e))
        entries.append(info)
    factory=h.function_headers[factory_id]
    small=original[128+factory_id*12:128+(factory_id+1)*12]
    if not small[11]&32: raise ValueError('Factory must use a full header')
    factory_info=(int.from_bytes(small[:4],'little')&0xffffff) | ((int.from_bytes(small[4:8],'little')>>14)<<24)
    lines=['/* Generated from owned '+Path(source).name+'; tools/rn_graft.py. */',
           '#define TAS_RN_POPUP_FUNCTIONS '+str(len(entries))+'U',
           '#define TAS_RN_POPUP_BASE '+str(base+1)+'U',
           '#define TAS_RN_POPUP_FACTORY_OFFSET '+str(factory.offset)+'U',
           '#define TAS_RN_POPUP_FACTORY_SIZE '+str(factory.bytecodeSizeInBytes)+'U',
           '#define TAS_RN_POPUP_FACTORY_INFO '+str(factory_info)+'U',
           '#define TAS_RN_POPUP_DEBUG_FIELD '+str(type(h.header).debugInfoOffset.offset)+'U',
           'static const unsigned char tas_rn_popup_factory_small[12]={'+','.join(map(str,small))+'};',
           'static const uint32_t tas_rn_popup_infos[]={'+','.join(map(str,entries))+'};',
           'static const unsigned char tas_rn_popup_payload[]={']
    for i in range(0,len(payload),24): lines.append(' '+','.join(map(str,payload[i:i+24]))+',')
    lines+=['};','']
    content='\n'.join(lines).replace('TAS_RN_POPUP','TAS_RN_'+prefix).replace('tas_rn_popup','tas_rn_'+prefix.lower())
    Path(output).write_text(content)
    print('Owned graft:',len(entries),'functions,',len(payload),'bytes; factory frame',factory.frameSize)

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('donor');p.add_argument('compiler');p.add_argument('source');p.add_argument('output')
    a=p.parse_args();generate(a.donor,a.compiler,a.source,a.output)
