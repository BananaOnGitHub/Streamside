"""Read-only donor-specific RN presentation trace (requires capstone).

Prints code/Objective-C metadata only, never arbitrary donor text or assets.
Uses the same bounded thin-arm64 metadata reader as the ABI verifier.
Offsets identify this binary only; do not use them as runtime storage offsets.
"""
import argparse
import struct
from pathlib import Path

try:
    from .verify_rn_hook_abi import Metadata
except ImportError:  # Direct script invocation.
    from verify_rn_hook_abi import Metadata


class PresentationMetadata(Metadata):
    def __init__(self, path):
        super().__init__(path)
        self.names = {}
        self.imps = {}
        self.functions = []
        commands = []
        at = 32
        for _ in range(struct.unpack_from("<I", self.data, 16)[0]):
            cmd, size = struct.unpack_from("<II", self.data, at)
            commands.append((cmd, at))
            at += size
        symtab = next((at for cmd, at in commands if cmd == 2), None)
        if symtab is not None:
            symoff, nsyms, stroff, strsize = struct.unpack_from("<IIII", self.data, symtab + 8)
            symbols = []
            for i in range(nsyms):
                name_at, typ, _, _, address = struct.unpack_from("<IBBHQ", self.data, symoff + 16 * i)
                if name_at >= strsize:
                    raise ValueError("invalid symbol string")
                end = self.data.index(b"\0", stroff + name_at, stroff + strsize)
                name = self.data[stroff + name_at:end].decode()
                symbols.append(name)
                if address and not typ & 0xe0:
                    self.names[address] = name
            dysym = next((at for cmd, at in commands if cmd == 0xb), None)
            if dysym is not None:
                indirect_at, indirect_n = struct.unpack_from("<II", self.data, dysym + 56)
                for cmd, at in commands:
                    if cmd != 0x19:
                        continue
                    for i in range(struct.unpack_from("<I", self.data, at + 64)[0]):
                        s = at + 72 + i * 80
                        address, size = struct.unpack_from("<QQ", self.data, s + 32)
                        flags, first, stride = struct.unpack_from("<III", self.data, s + 64)
                        kind = flags & 0xff
                        if kind not in (6, 7, 8):
                            continue
                        stride = stride if kind == 8 else 8
                        if not stride:
                            raise ValueError("invalid indirect-symbol stride")
                        for j in range(size // stride):
                            if first + j >= indirect_n:
                                break
                            index = struct.unpack_from("<I", self.data, indirect_at + 4 * (first + j))[0]
                            if index < len(symbols):
                                self.names[address + j * stride] = symbols[index]
        base = min(vm for vm, _, size in self.segments if size)
        starts = next((at for cmd, at in commands if cmd == 0x26), None)
        if starts is not None:
            off, size = struct.unpack_from("<II", self.data, starts + 8)
            current, value, shift = base, 0, 0
            for byte in self.data[off:off + size]:
                value |= (byte & 127) << shift
                if byte & 128:
                    shift += 7
                    if shift > 63:
                        raise ValueError("invalid function-start delta")
                    continue
                if not value:
                    break
                current += value
                self.functions.append(current)
                value = shift = 0
        if "__objc_selrefs" in self.sections:
            start, size, _ = self.sections["__objc_selrefs"]
            for at in range(start, start + size, 8):
                try:
                    self.names[at] = "selector:" + self.string(self.pointer(at))
                except ValueError:
                    pass
        if "__objc_classlist" in self.sections:
            start, size, _ = self.sections["__objc_classlist"]
            for at in range(start, start + size, 8):
                cls = self.pointer(at)
                ro = self.pointer(cls + 32) & ~7
                name = self.string(self.pointer(ro + 24))
                self.names[cls] = "class:" + name
                for meta, owner in ((False, cls), (True, self.pointer(cls))):
                    r = self.pointer(owner + 32) & ~7
                    methods = self.pointer(r + 32)
                    if not methods:
                        continue
                    flags, count = struct.unpack_from("<II", self.data, self.offset(methods))
                    stride = flags & 0xffff
                    if stride < (12 if flags & 0x80000000 else 24) or count > 8192:
                        raise ValueError("invalid method list")
                    for i in range(count):
                        entry = methods + 8 + i * stride
                        if flags & 0x80000000:
                            n, _, imp = struct.unpack_from("<iii", self.data, self.offset(entry))
                            np = entry + n
                            if not flags & 0x40000000:
                                np = self.pointer(np)
                            imp += entry + 8
                        else:
                            np, imp = self.pointer(entry), self.pointer(entry + 16)
                        selector = self.string(np)
                        label = ("+" if meta else "-") + "[" + name + " " + selector + "]"
                        self.names[imp] = label
                        self.imps[(name, selector, meta)] = imp

    def disassemble(self, start, limit=512):
        import capstone
        if not 1 <= limit <= 4096 or start % 4:
            raise ValueError("expected aligned code address and instruction limit 1..4096")
        text_start, text_size, _ = self.sections["__text"]
        if not text_start <= start < text_start + text_size:
            raise ValueError("address outside code section")
        md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_LITTLE_ENDIAN)
        md.detail = True
        end = next((x for x in self.functions if x > start), start + limit * 4)
        end = min(end, start + limit * 4, text_start + text_size)
        page_registers = {}
        at = self.offset(start)
        print(f"\n{self.names.get(start, 'code')} @ 0x{start:x}, {end - start} bytes")
        for ins in md.disasm(self.data[at:at + end - start], start):
            annotations = []
            ops = ins.operands
            tracked_destination = None
            if ins.mnemonic == "adrp" and len(ops) == 2:
                tracked_destination = ins.reg_name(ops[0].reg)
                page_registers[tracked_destination] = ops[1].imm
            elif ins.mnemonic == "add" and len(ops) == 3 and ops[2].type == capstone.arm64.ARM64_OP_IMM:
                src = ins.reg_name(ops[1].reg)
                if src in page_registers:
                    target = page_registers[src] + ops[2].imm
                    tracked_destination = ins.reg_name(ops[0].reg)
                    page_registers[tracked_destination] = target
                    if target in self.names:
                        annotations.append(self.names[target])
            elif ins.mnemonic.startswith("ldr") and len(ops) > 1 and ops[1].type == capstone.arm64.ARM64_OP_MEM:
                src = ins.reg_name(ops[1].mem.base)
                if src in page_registers:
                    target = page_registers[src] + ops[1].mem.disp
                    if target in self.names:
                        annotations.append(self.names[target])
            if ins.mnemonic in ("b", "bl") and ops and ops[0].imm in self.names:
                annotations.append(self.names[ops[0].imm])
            print(f"{ins.address:08x}  {ins.mnemonic:8} {ins.op_str}" + (" ; " + "; ".join(annotations) if annotations else ""))
            # Annotation tracking is deliberately local/conservative, not dataflow proof.
            _, writes = ins.regs_access()
            for reg in writes:
                name = ins.reg_name(reg)
                if name != tracked_destination:
                    page_registers.pop(name, None)
            if ins.mnemonic == "bl":
                for i in range(19):
                    page_registers.pop("x" + str(i), None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--class-name")
    parser.add_argument("--selector")
    parser.add_argument("--address", type=lambda x: int(x, 0))
    parser.add_argument("--symbol", help="Exact defined symbol, not arbitrary donor-string search")
    parser.add_argument("--limit", type=int, default=512)
    args = parser.parse_args()
    metadata = PresentationMetadata(args.binary)
    if args.address is not None:
        metadata.disassemble(args.address, args.limit)
    elif args.symbol:
        starts = [a for a, name in metadata.names.items() if name == args.symbol]
        if len(starts) != 1:
            raise ValueError("defined symbol missing or ambiguous")
        metadata.disassemble(starts[0], args.limit)
    else:
        rows = [(selector, imp) for (name, selector, meta), imp in metadata.imps.items()
                if name == args.class_name and not meta and (not args.selector or selector == args.selector)]
        if not rows:
            raise ValueError("instance method not found")
        for selector, imp in rows:
            if args.selector:
                metadata.disassemble(imp, args.limit)
            else:
                print(f"{selector}: 0x{imp:x}")
