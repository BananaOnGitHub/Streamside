"""Verify the WebP implementation is defined, not an unresolved weak fallback."""
import struct
import sys
from pathlib import Path
from macho import load_commands
REQUIRED={'_tas_animated_image_create','_tas_animated_image_prepare','_tas_animated_image_retry_hooks','_tas_animated_image_status'}
def verify(path):
    data=Path(path).read_bytes();defined=set()
    for command in load_commands(data):
        if command.command!=2:continue
        symbols,count,strings,size=struct.unpack_from('<IIII',data,command.offset+8)
        for index in range(count):
            name,kind,section,_,address=struct.unpack_from('<IBBHQ',data,symbols+16*index)
            if name<size and kind&0xe==0xe and section and address:
                end=data.index(b'\0',strings+name,strings+size)
                defined.add(data[strings+name:end].decode())
    missing=REQUIRED-defined
    if missing:raise ValueError('WebP implementation missing: '+', '.join(sorted(missing)))
    print('WebP native definitions verified:',path)
if __name__=='__main__':
    for path in sys.argv[1:]:verify(path)
