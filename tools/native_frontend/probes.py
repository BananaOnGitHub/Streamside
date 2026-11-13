"""Exact-donor ARM64 entry probes. No run-time code writes or executable allocation.

Only a stack-adjusting first instruction may be relocated. Every argument GPR,
all vector registers, LR and NZCV survive the C observer. The donor resumes at
entry+4 after its original instruction. A missing observer traps before entry.
"""
import hashlib
import json
from pathlib import Path
import struct

FRAME = 704
GPRS = list(range(19)) + [29, 30]


def branch(source, target):
    delta = target - source
    if delta % 4 or not -(1 << 27) <= delta < (1 << 27):
        raise ValueError('ARM64 branch out of range')
    return 0x14000000 | ((delta // 4) & 0x3ffffff)


def trampoline(address, entry, original, slot, probe_id):
    word, = struct.unpack('<I', original[:4])
    # SUB SP,SP,#imm or STP Xn,Xm,[SP,#negative]! only. Neither is PC relative.
    if not (word & 0xffc003ff == 0xd10003ff or
            word & 0xffc003e0 == 0xa98003e0):
        raise ValueError('Unvalidated first instruction; cannot relocate')
    words = [0xd10003ff | (FRAME << 10)]
    words += [0xf90003e0 | ((i * 8 // 8) << 10) | r for i, r in enumerate(GPRS)]
    words += [0x3d8003e0 | (((176 + r * 16) // 16) << 10) | r for r in range(32)]
    words += [0xd53b4211, 0xf90003f1 | ((688 // 8) << 10)]  # NZCV
    pc = address + len(words) * 4
    page_delta = (slot >> 12) - (pc >> 12)
    if not -(1 << 20) <= page_delta < (1 << 20) or slot % 8:
        raise ValueError('Observer slot cannot be addressed')
    words += [0x90000010 | ((page_delta & 3) << 29) |
              (((page_delta >> 2) & 0x7ffff) << 5),
              0x91000210 | ((slot & 4095) << 10),
              0xc8dffe10,  # ADD X16,slot offset; LDAR X16,[X16] publishes observer state
              0xb5000050, 0xd42a6a60,  # CBNZ X16,+8; BRK #0x5353
              0xd2800000 | (probe_id << 5), 0xd63f0200]
    words += [0xf94003f1 | ((688 // 8) << 10), 0xd51b4211]
    words += [0x3dc003e0 | (((176 + r * 16) // 16) << 10) | r for r in range(32)]
    words += [0xf94003e0 | (i << 10) | r for i, r in enumerate(GPRS)]
    words += [0x910003ff | (FRAME << 10), word]
    words += [branch(address + len(words) * 4, entry + 4)]
    return struct.pack('<' + 'I' * len(words), *words)


def offsets(data):
    from macho import load_commands
    result = []
    for c in load_commands(data):
        if c.command == 0x19:
            vm, size, off, length = struct.unpack_from('<4Q', data, c.offset + 24)
            result.append((vm, length, off))
    return result


def file_offset(data, address):
    for vm, length, off in offsets(data):
        if vm <= address < vm + length:
            return off + address - vm
    raise ValueError('Address outside file-backed segments')


def layout(plan, name):
    item = plan['layout'][name]
    cursor = item['code_offset'] + 64
    result = []
    for probe in plan['probes']:
        if probe['image'] != name:
            continue
        code = trampoline(item['base'] + cursor, probe['address'],
                          bytes.fromhex(probe['bytes']), item['slot'], probe['id'])
        result.append((probe, cursor, code))
        cursor = (cursor + len(code) + 15) & ~15
    if cursor > item['code_offset'] + item['code_size']:
        raise ValueError('Probe cave overflow')
    return result


def launch_gate_layout(plan):
    item=plan['layout']['Twitch']
    probes=layout(plan,'Twitch')
    cave=max(c+len(code) for _,c,code in probes)
    cave=(cave+15)&~15
    address=item['base']+cave
    gate=plan['gate'];word=struct.unpack('<I',bytes.fromhex(gate['bytes'])[:4])[0]
    if not (word & 0xffc003ff == 0xd10003ff or word & 0xffc003e0 == 0xa98003e0):
        raise ValueError('Unvalidated launch gate first instruction')
    slot=item['slot']+8;pc=address+4
    delta=(slot>>12)-(pc>>12)
    if not -(1<<20)<=delta<(1<<20):raise ValueError('Launch slot out of range')
    words=[0xa9bf47f0, # STP X16,X17,[SP,#-16]!
           0x90000010|((delta&3)<<29)|(((delta>>2)&0x7ffff)<<5),
           0x91000210|((slot&4095)<<10),0xc8dffe11, # LDAR X17,[X16]
           0xb4000011|(8<<5), # zero selection traps (instruction 12)
           0x36000011|(1<<19)|(4<<5), # TBZ X17,#1,native (instruction 9)
           0xa8c147f0,word,branch(address+32,gate['address']+4),
           0xa8c147f0,0x52800000,0xd65f03c0,0xd42a6a60]
    code=struct.pack('<'+'I'*len(words),*words)
    if cave+len(code)>item['code_offset']+item['code_size']:raise ValueError('Launch gate cave overflow')
    return cave,code


def validate_launch_slot(data,plan):
    # The existing observer uses the penultimate word of a verified unused DATA
    # tail. Admit both words, including the selector, beyond every section.
    from macho import load_commands
    slot=plan['layout']['Twitch']['slot']
    for c in load_commands(data):
        if c.command!=0x19:continue
        vm,size,off,filesize=struct.unpack_from('<4Q',data,c.offset+24)
        if not vm<=slot<vm+size:continue
        _,protection,count=struct.unpack_from('<3I',data,c.offset+56)
        end=max((sum(struct.unpack_from('<2Q',data,c.offset+72+i*80+32)) for i in range(count)),default=vm)
        if not protection&2 or slot<end or slot+16>vm+size:raise ValueError('Launch slot is not unused writable DATA tail')
        if slot<vm+filesize and any(data[off+slot-vm:off+min(slot+16-vm,filesize)]):raise ValueError('Launch slot is not zero')
        return
    raise ValueError('Launch slot is not mapped')


def patch(data, plan, name, proof_id, native):
    if hashlib.sha256(data).hexdigest() != plan['images'][name]:
        raise ValueError('Exact donor image required: ' + name)
    out = bytearray(data)
    item = plan['layout'][name]
    at = item['code_offset']
    if any(out[at:at + item['code_size']]):
        raise ValueError('Probe cave is not empty')
    out[at:at + 64] = b'SSNPROBE' + bytes.fromhex(proof_id) + bytes(24)
    for probe, cave, code in layout(plan, name):
        pos = file_offset(out, probe['address'])
        if out[pos:pos+16].hex() != probe['bytes']:
            raise ValueError('Entry prefix mismatch')
        out[pos:pos+4] = struct.pack('<I', branch(probe['address'], item['base'] + cave))
        out[cave:cave+len(code)] = code
    if native and name == 'Twitch':
        gate = plan['gate']; pos = file_offset(out, gate['address'])
        if out[pos:pos+16].hex() != gate['bytes']:
            raise ValueError('Eligibility gate prefix mismatch')
        validate_launch_slot(data,plan)
        cave,code=launch_gate_layout(plan)
        out[pos:pos+4]=struct.pack('<I',branch(gate['address'],item['base']+cave))
        out[cave:cave+len(code)]=code
    return bytes(out)


def generate_header(plan, proof_id, revision, destination):
    lines = ['/* Generated from native/twitch32.json by the dedicated build. */',
             '#define SSN_PROOF_ID ' + json.dumps(proof_id),
             '#define SSN_REVISION ' + json.dumps(revision),
             '#define SSN_PROBE_COUNT ' + str(len(plan['probes'])),
             'static const SSNProbeSpec ssn_specs[] = {']
    for probe in plan['probes']:
        item = plan['layout'][probe['image']]
        cave = next(c for p, c, _ in layout(plan, probe['image']) if p == probe)
        opcode = branch(probe['address'], item['base'] + cave)
        lines.append('{%s,%s,0x%x,0x%x,%d},' %
                     (json.dumps(probe['name']), json.dumps(probe['image']),
                      probe['address'] - item['base'], opcode, probe['guard']))
    lines += ['};', 'static const SSNImageSpec ssn_images[] = {']
    for name, item in plan['layout'].items():
        lines.append('{%s,0x%x,0x%x},' %
                     (json.dumps(name), item['code_offset'], item['slot'] - item['base']))
    lines += ['};', '#define SSN_IMAGE_COUNT 4',
              'typedef struct { const char *name,*image; uintptr_t offset; unsigned char prefix[16]; } SSNABISpec;',
              'static const SSNABISpec ssn_abi[] = {']
    bases = {n: item['base'] for n, item in plan['layout'].items()}
    for name, spec in plan['abi'].items():
        lines.append('{%s,%s,0x%x,{%s}},' %
                     (json.dumps(name.lstrip('_')), json.dumps(spec['image']),
                      spec['address'] - bases.get(spec['image'], 0),
                      ','.join('0x'+spec['bytes'][i:i+2] for i in range(0,32,2))))
    lines += ['};']
    cave,_=launch_gate_layout(plan);item=plan['layout']['Twitch']
    contract={k:plan[k] for k in ['probes','layout','gate','required_baseline']}
    contract=hashlib.sha256(json.dumps(contract,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    lines += ['#define SSN_PROBE_CONTRACT '+json.dumps(contract),
              '#define SSN_LAUNCH_SLOT_OFFSET 0x%x'%(item['slot']+8-item['base']),
              '#define SSN_LAUNCH_GATE_OFFSET 0x%x'%(plan['gate']['address']-item['base']),
              '#define SSN_LAUNCH_GATE_OPCODE 0x%x'%branch(plan['gate']['address'],item['base']+cave)]
    spec=plan['objc_services']['logout']
    lines += ['typedef struct { const char *image,*class_name,*selector,*encoding; uintptr_t offset; unsigned char prefix[16]; } SSNObjCServiceSpec;',
              'static const SSNObjCServiceSpec ssn_logout = {%s,%s,%s,%s,0x%x,{%s}};' %
              (json.dumps(spec['image']),json.dumps(spec['class_name']),json.dumps(spec['selector']),json.dumps(spec['encoding']),
               spec['address']-bases[spec['image']],','.join('0x'+spec['bytes'][i:i+2] for i in range(0,32,2)))]
    Path(destination).write_text('\n'.join(lines) + '\n')
