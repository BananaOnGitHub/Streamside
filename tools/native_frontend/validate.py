"""Validate the integration declarations against the exact donor's exports."""
import struct
from macho import load_commands
from probes import file_offset


def exports(data, base):
    def uleb(pos):
        result=shift=0
        while True:
            value=data[pos];pos+=1;result|=(value&127)<<shift
            if not value&128:return result,pos
            shift+=7
    result={}
    for command in load_commands(data):
        if command.command not in [0x80000033,0x80000022]:continue
        offset,size=struct.unpack_from('<II',data,command.offset+(8 if command.command==0x80000033 else 40))
        if not size:continue
        def walk(relative,prefix):
            pos=offset+relative;length,pos=uleb(pos);end=pos+length
            if length:
                flags,q=uleb(pos)
                if not flags&8:
                    value,q=uleb(q);result[prefix]=value+base
            pos=end;count=data[pos];pos+=1
            for _ in range(count):
                end=data.index(0,pos);edge=data[pos:end].decode();pos=end+1
                child,pos=uleb(pos);walk(child,prefix+edge)
        walk(0,'')
    return result


def validate_abi(images,plan):
    tables={name:exports(data,plan['layout'].get(name,{}).get('base',0)) for name,(_,data) in images.items()}
    for name,spec in plan['abi'].items():
        _,data=images[spec['image']]
        pos=file_offset(data,spec['address'])
        if data[pos:pos+16].hex()!=spec['bytes']:raise ValueError('ABI entry prefix mismatch: '+name)
        if name.startswith('_$') and tables[spec['image']].get(name)!=spec['address']:
            raise ValueError('Native Swift symbol is not exported at the inspected address: '+name)

    for spec in plan.get('value_layouts',{}).values():
        _,data=images['TwitchKit']
        pos=file_offset(data,spec['witness_table'])
        layout=struct.unpack_from('<QQQ',data,pos+64)
        if layout!=(spec['size'],spec['stride'],spec['flags_and_extra_inhabitants']):
            raise ValueError('Native cursor value-witness layout mismatch')
        for index,name in [(6,'get_single_payload_tag'),(7,'store_single_payload_tag')]:
            address=struct.unpack_from('<Q',data,pos+8*index)[0]&((1<<36)-1)
            if address!=spec[name]:raise ValueError('Native cursor enum witness mismatch')

    # The existing donor Objective-C adapter owns all Swift witness dispatch.
    from inspect_native_frontend import Image
    for spec in plan.get('objc_services',{}).values():
        _,data=images[spec['image']]
        image=Image(data)
        classes=image.selected_classes({spec['class_name']})
        methods=[m for m in classes[0]['methods'] if m['selector']==spec['selector']]
        if len(methods)!=1 or methods[0]['encoding']!=spec['encoding'] or int(methods[0]['address'],16)!=spec['address']:
            raise ValueError('Objective-C account adapter signature/address changed')
        pos=file_offset(data,spec['address'])
        if data[pos:pos+16].hex()!=spec['bytes']:raise ValueError('Objective-C account adapter prefix changed')

    # These public enum tags and generic metadata arguments are inspected, not
    # inferred from names or guessed witness slots. Whole-image identity is pinned.
    feed=plan.get('feed_contract')
    if feed:
        for spec in feed['enum_descriptors'].values():
            _,data=images[spec['image']];image=Image(data);address=spec['address']
            pos=file_offset(data,address+16)
            field=address+16+struct.unpack_from('<i',data,pos)[0]
            pos=file_offset(data,field)
            _,_,kind,step,count=struct.unpack_from('<iiHHI',data,pos)
            if kind!=2 or step!=12 or count!=len(spec['cases']):raise ValueError('Feed enum descriptor changed')
            names=[]
            for i in range(count):
                at=field+16+i*step;flags,_,name=struct.unpack_from('<Iii',data,file_offset(data,at))
                if flags:raise ValueError('Unexpected feed enum payload')
                names.append(image.text(at+8+name))
            if names!=spec['cases']:raise ValueError('Feed enum case order changed')
        spec=feed['trackable_descriptor'];_,data=images[spec['image']];image=Image(data)
        counts=struct.unpack_from('<4H',data,file_offset(data,spec['address']+36))
        if counts!=(spec['generic_parameters'],spec['requirements'],spec['key_arguments'],0):
            raise ValueError('TrackableItem generic metadata contract changed')
        at=spec['address']+56;relative=struct.unpack_from('<i',data,file_offset(data,at))[0]
        target=at+relative
        if not target&1 or image.ptr(target&~1)!='_'+spec['requirement']:
            raise ValueError('TrackableItem conformance requirement changed')
