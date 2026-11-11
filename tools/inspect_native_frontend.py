"""Reproduce the Twitch 32.0 native-frontend static evidence; never run donor code.

Writes metadata and verified call relationships, not donor instructions or tokens.
Addresses are unslid evidence for this exact input, never runtime hook offsets.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import struct
import uuid
import zipfile

from inspect_investigation_channel import Image as MetadataImage
from macho import encryption_ids, load_commands, loaded_dylibs

EXPECTED = {
    'Twitch': 'f256c2a8576f4bafb26d4bd8f3c36470c0a6fc779e06fd1e254bbefa059875f1',
    'TwitchKit': 'f9cf2a880924bfcef7b46a7f64887fb835c28f5aa7e1593c6d5fa31bd1711401',
    'TwitchIdentity': '5129aa20a21789e1c72f28bd10250a4192da009229d2c866af44cb58fc2d6f03',
    'TwitchApollo': 'e6c609a1b602f87fa73d41b8b1db8dc8e065d522d5c98144d38fc016bc44e3c7',
    'TwitchGraphQLAPI': 'bb5792e2c28d6c7799ae67fca95144547097e622efb61ab2b5838eaa87f41ee8',
    'React': '74a3b3cde26076fd5fb9b327c7e15928443a514a4f86b27ecb376b7cc33d76f5',
    'hermesvm': 'fce4c67d0e4acdc65edfbe5c029cd5b90c17f9a0249d686df753e5db598e3a33',
    'AmazonIVSPlayer': 'f6bbfbf4ab295778e431f44e3ba8d242d9f3681e27d1413280db095bad85b4c5',
}
IPA_SHA = '076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129'
BUNDLE_SHA = '1866099398b36a4fc98717dca5715547d6f16785bfa3dc8f74605fe98d1755d8'
SELECTED = {
    'Twitch': {
        '_TtC6Twitch13TWAppDelegate', '_TtC6Twitch13SceneDelegate',
        '_TtC6Twitch18RootViewController', '_TtC6Twitch9AppRouter',
        '_TtC6Twitch22StandardAccountManager', '_TtC6Twitch12TwitchRNHost',
        '_TtC6Twitch23TwitchRNFactoryDelegate', 'TwitchRNExpoHostBootstrap',
    },
    'TwitchKit': {
        '_TtC9TwitchKit9TKGraphQL', '_TtC9TwitchKit19HTTPAccessTokenAuth',
        '_TtC9TwitchKit31AuthorizationRequestInterceptor',
        '_TtC9TwitchKit32AuthorizationResponseInterceptor',
        '_TtC9TwitchKit25TwitchInterceptorProvider',
    },
    'React': {'RCTRootViewFactory', 'RCTReactNativeFactory', 'RCTHost',
              'RCTInstance', 'RCTDefaultReactNativeFactoryDelegate'},
    'AmazonIVSPlayer': {'IVSPlayer'},
}
# Role, instruction address, expected direct target or resolved import/selector fragment.
PROBES = {
    'Twitch': [
        ('scene connection worker', 0x1030b150c, 0x1030b4fbc),
        ('scene window creation', 0x1030b5628, 'objc:initWithWindowScene:'),
        ('window presentation', 0x1030b56e0, 'objc:makeKeyAndVisible'),
        ('root installation', 0x1039adc2c, 'objc:setRootViewController:'),
        ('startup RN eligibility', 0x1030adccc, 0x1033e5a80),
        ('startup RN warmup', 0x1030adcec, 0x1033c0174),
        ('warmup factory access', 0x1033c01bc, 0x1033bf864),
        ('RN factory construction', 0x1033bfb04, 'objc:initWithDelegate:'),
        ('host-start metric', 0x1033c01e0, 'objc:recordReactHostStart'),
        ('warmup root-view request', 0x1033c026c, 'objc:viewWithModuleName:initialProperties:'),
        ('warmup frame assignment', 0x1033c02a4, 'objc:setFrame:'),
        ('native HTTP auth construction', 0x10075b68c, 'HTTPAccessTokenAuthC06accessD0'),
        ('native HTTP default auth assignment', 0x10075b8d0, 'HTTPManagerC11defaultAuth'),
        ('saved-token login during refresh', 0x100756144, 0x100754c08),
        ('native stream-access query', 0x1025e0854, 'StreamAccessTokenQueryCMa'),
        ('native playback query execution', 0x1025e0958, 'TWApolloClientV14fetchAsPromise'),
    ],
    'TwitchKit': [
        ('GraphQL reads shared HTTP manager', 0x25cf44, 'PMHTTP4HTTP'),
        ('GraphQL reads native authentication', 0x25cf4c, 'HTTPManagerC11defaultAuth'),
        ('GraphQL obtains OAuth headers', 0x25cf78, 0x2e3b7c),
        ('native URLSession construction', 0x2ce7ec, 'URLSessionClientC20sessionConfiguration'),
        ('native Apollo network transport', 0x2ce9d0, 'RequestChainNetworkTransportC19interceptorProvider'),
        ('unauthorized notification', 0x2e4a1c, 0x2e3c60),
    ],
    'React': [
        ('root request initializes host', 0x341f18, 'objc:initializeReactHostWithLaunchOptions:bundleConfiguration:devMenuConfiguration:'),
        ('host creates runtime instance', 0x2b3134, 'objc:initWithDelegate:jsRuntimeFactory:bundleManager:turboModuleManagerDelegate:moduleRegistry:parentInspectorTarget:launchOptions:devMenuConfiguration:'),
        ('default Hermes factory', 0x33f6f8, 0xd9970),
        ('Hermes runtime implementation', 0x2b2594, 0x2b0228),
        ('Hermes runtime allocation', 0x2b0784, 'makeHermesRuntime'),
    ],
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


class Image(MetadataImage):
    """This donor uses DYLD_CHAINED_PTR_64_OFFSET (6), including its executable."""
    def __init__(self, data):
        super().__init__(data)
        self.base = min(vm for vm, size, off in self.segments if size)
        self.imports = []
        for c in load_commands(data):
            if c.command != 0x80000034:
                continue
            off, size = struct.unpack_from('<II', data, c.offset + 8)
            ver, starts, imports, symbols, count, fmt, symfmt = struct.unpack_from('<7I', data, off)
            require(ver == 0 and fmt == 1 and symfmt == 0, 'Unsupported chained fixups')
            start = off + starts
            nseg = struct.unpack_from('<I', data, start)[0]
            for i in range(nseg):
                rel = struct.unpack_from('<I', data, start + 4 + i * 4)[0]
                if rel:
                    require(struct.unpack_from('<H', data, start + rel + 6)[0] == 6,
                            'Unsupported chained pointer format')
            for i in range(count):
                raw = struct.unpack_from('<I', data, off + imports + i * 4)[0]
                at = off + symbols + (raw >> 9)
                end = data.index(0, at)
                self.imports.append(data[at:end].decode())

    def ptr(self, at):
        raw = self.unpack('<Q', at)[0]
        if not raw:
            return 0
        if raw >> 63:
            return self.imports[raw & 0xffffff]
        return self.base + (raw & ((1 << 36) - 1))

    def method_list(self, at):
        if not at:
            return []
        flags, count = self.unpack('<II', at)
        size = flags & 0xffff
        require(count <= 3000 and size in (12, 24), 'Unsupported method list')
        result = []
        for i in range(count):
            p = at + 8 + i * size
            if flags & 0x80000000:
                name, types, implementation = self.unpack('<iii', p)
                np = p + name
                if not flags & 0x40000000:
                    np = self.ptr(np)
                selector, encoding, imp = self.text(np), self.text(p + 4 + types), p + 8 + implementation
            else:
                selector, encoding, imp = self.text(self.ptr(p)), self.text(self.ptr(p + 8)), self.ptr(p + 16)
            result.append({'selector': selector, 'encoding': encoding, 'address': hex(imp)})
        return result

    def selected_classes(self, selected):
        result = {}
        start, size = self.sections.get('__objc_classlist', (0, 0))
        for p in range(start, start + size, 8):
            cls = self.ptr(p)
            ro = self.ptr(cls + 32) & ~7
            name = self.text(self.ptr(ro + 24))
            if name not in selected:
                continue
            meta = self.ptr(self.ptr(cls) + 32) & ~7
            fields = []
            ivars = self.ptr(ro + 48)
            if ivars:
                step, count = self.unpack('<II', ivars)
                require(step == 32 and count < 512, 'Unsupported ivar list')
                fields = [self.text(self.ptr(ivars + 8 + i * step + 8)) for i in range(count)]
            result[cls] = {'class': name, 'address': hex(cls), 'field_names': fields,
                           'methods': self.method_list(self.ptr(ro + 32)),
                           'class_methods': self.method_list(self.ptr(meta + 32))}
        for section in ('__objc_catlist', '__objc_catlist2'):
            start, size = self.sections.get(section, (0, 0))
            for p in range(start, start + size, 8):
                cat = self.ptr(p)
                cls = self.ptr(cat + 8)
                if cls in result:
                    result[cls]['methods'] += self.method_list(self.ptr(cat + 16))
                    result[cls]['class_methods'] += self.method_list(self.ptr(cat + 24))
        require({c['class'] for c in result.values()} == selected, 'Missing selected class')
        return sorted(result.values(), key=lambda c: c['class'])

    def instruction(self, at):
        return self.unpack('<I', at)[0]

    def stub_name(self, at):
        for section, objc in (('__stubs', False), ('__objc_stubs', True)):
            start, size = self.sections.get(section, (0, 0))
            if not start <= at < start + size:
                continue
            w, load = self.instruction(at), self.instruction(at + 4)
            require(w & 0x9f000000 == 0x90000000 and load & 0xffc00000 == 0xf9400000,
                    'Unrecognized stub')
            imm = ((w >> 29) & 3) | (((w >> 5) & 0x7ffff) << 2)
            if imm & (1 << 20):
                imm -= 1 << 21
            slot = (at & ~4095) + (imm << 12) + ((load >> 10) & 0xfff) * 8
            value = self.ptr(slot)
            return 'objc:' + self.text(value) if objc else value
        return None

    def probe(self, role, pc, expected):
        word = self.instruction(pc)
        require(word & 0x7c000000 == 0x14000000, 'Expected direct branch: ' + role)
        imm = word & 0x3ffffff
        if imm & (1 << 25):
            imm -= 1 << 26
        target = pc + imm * 4
        name = self.stub_name(target)
        require(target == expected if isinstance(expected, int) else name and expected in name,
                'Changed call relationship: ' + role)
        return {'role': role, 'instruction': hex(pc), 'target': hex(target), 'resolved_name': name}


def closure(graph, root):
    visited, pending = set(), [root]
    while pending:
        node = pending.pop()
        if node not in visited:
            visited.add(node)
            pending.extend(PurePosixPath(p).name for p in graph.get(node, []) if p.startswith('@rpath/'))
    return sorted(visited)


def inspect(path):
    with path.open('rb') as source:
        ipa_sha = hashlib.file_digest(source, 'sha256').hexdigest()
    require(ipa_sha == IPA_SHA, 'Unrecorded Twitch 32.0 IPA')
    result = {'schema': 1, 'evidence': 'static-only', 'native_execution': False,
              'authenticated_requests': False, 'device_validation': False,
              'ipa': {'bytes': path.stat().st_size, 'sha256': ipa_sha}}
    images, graph, identity, runtime_symbols = {}, {}, {}, {}
    with zipfile.ZipFile(path) as z:
        info = plistlib.loads(z.read('Payload/Twitch.app/Info.plist'))
        require((info['CFBundleShortVersionString'], info['CFBundleVersion']) ==
                ('32.0', '263110145453907615'), 'Wrong app version/build')
        result['app'] = {k: info[k] for k in ('CFBundleIdentifier', 'CFBundleShortVersionString',
                         'CFBundleVersion', 'MinimumOSVersion', 'UIApplicationSceneManifest')}
        body = z.read('Payload/Twitch.app/main.jsbundle')
        require(hashlib.sha256(body).hexdigest() == BUNDLE_SHA, 'Wrong JS bundle')
        require(hashlib.sha1(body[:-20]).digest() == body[-20:], 'Invalid HBC footer')
        result['hermes_bundle'] = {'path': 'main.jsbundle', 'bytes': len(body),
                                   'sha256': BUNDLE_SHA, 'version': struct.unpack_from('<I', body, 8)[0],
                                   'footer_valid': True}
        for name in z.namelist():
            p = PurePosixPath(name)
            if not (name == 'Payload/Twitch.app/Twitch' or len(p.parts) == 5 and
                    p.parts[2] == 'Frameworks' and p.name == p.parent.stem):
                continue
            data = z.read(name)
            digest = hashlib.sha256(data).hexdigest()
            if p.name in EXPECTED:
                require(digest == EXPECTED[p.name], 'Unrecorded image: ' + p.name)
                images[p.name] = Image(data)
            graph[p.name] = loaded_dylibs(data)
            uid = next((str(uuid.UUID(bytes=data[c.offset + 8:c.offset + 24]))
                        for c in load_commands(data) if c.command == 0x1b), None)
            if p.name in {'React', 'worklets', 'hermesvm'}:
                syms = []
                for c in load_commands(data):
                    if c.command != 2:
                        continue
                    so, count, st, ss = struct.unpack_from('<4I', data, c.offset + 8)
                    for i in range(count):
                        no, kind, section, desc, address = struct.unpack_from('<IBBHQ', data, so + i * 16)
                        if not no:
                            continue
                        end = data.index(0, st + no)
                        symbol = data[st + no:end].decode()
                        if 'makeHermesRuntime' in symbol or 'jsrt_create_hermes_factory' in symbol:
                            syms.append({'symbol': symbol, 'address': hex(address),
                                         'undefined': (kind & 14) == 0})
                runtime_symbols[p.name] = syms
            identity[p.name] = {'path': name, 'bytes': len(data), 'sha256': digest,
                                'uuid': uid, 'encryption_ids': encryption_ids(data)}
    require(set(EXPECTED) <= images.keys(), 'Missing required donor images')
    require(all(encryption_ids(im.data) == [0] for im in images.values()), 'Encrypted required image')
    result['images'] = identity
    result['runtime_creation_symbols'] = runtime_symbols
    result['load_graph'] = graph
    result['selected_classes'] = {n: images[n].selected_classes(s) for n, s in SELECTED.items()}
    result['verified_calls'] = {n: [images[n].probe(*p) for p in probes] for n, probes in PROBES.items()}
    # Recover the two immediate words of the Swift small-string module name.
    regs = {}
    for pc in range(0x1033c0200, 0x1033c0220, 4):
        w = images['Twitch'].instruction(pc)
        require(w & 0xff800000 in (0xd2800000, 0xf2800000), 'Changed warmup module name')
        rd, shift, value = w & 31, ((w >> 21) & 3) * 16, (w >> 5) & 0xffff
        regs[rd] = ((regs.get(rd, 0) & ~(0xffff << shift)) if w & 0xff800000 == 0xf2800000 else 0) | (value << shift)
    raw = struct.pack('<QQ', regs[0], regs[1])
    module = raw[:raw[-1] & 15].decode()
    require(module == 'TwitchRNWarmup', 'Wrong warmup module')
    result['warmup_module'] = module
    roots = ('TwitchKit', 'TwitchIdentity', 'TwitchApollo', 'TwitchGraphQLAPI', 'AmazonIVSPlayer', 'PMHTTP')
    rn = {'React', 'hermesvm', 'ReactNativeDependencies', 'ReactCodegen', 'worklets', 'reanimated'}
    result['native_dependency_closures'] = {n: closure(graph, n) for n in roots}
    require(all(not rn.intersection(c) for c in result['native_dependency_closures'].values()),
            'Native framework closure now includes RN/Hermes')
    result['limits'] = ['No proof of safe Swift ABI bridging or live authentication/playback.',
                        'No proof that all runtime startup routes have been excluded.',
                        'Linked-image absence and runtime-instance absence are different checks.']
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    receipt = inspect(args.ipa)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print('Verified', sum(map(len, receipt['verified_calls'].values())),
          'static call relationships; native/device behavior remains untested')
