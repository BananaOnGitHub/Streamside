"""Reproduce bounded static auth evidence for the exact Twitch 32.0 donor.

The Hermes tool only disassembles bytecode. No JavaScript, donor application,
account request or credential payload is executed or exported.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile
from inspect_native_frontend import Image,IPA_SHA,BUNDLE_SHA,EXPECTED

FUNCTIONS={'LoginScreen','parseLoginPortalMessage','parseLoginMessage','AuthProvider','AuthSession',
           'setToken','logout','PortalWebView','PortalWebViewContent','usePortalIdentity',
           'buildInjectedJS','buildPortalBridgeJS','ChallengeWebView','useChallengeSudoPhase',
           'createHostTrustedSession','buildChallengeUrl','keychainPersistence'}
PROPERTIES={'useAuth','completeLogin','getToken','setToken','logout','LOGIN_URL','SIGNUP_URL',
            'PortalWebView','parseLoginMessage','accessToken','token','spareKey','authyId','eventName',
            'persistence','save','load','parseMessage','navPolicy','injectedJS','onOutcome','session',
            'clientId','fetchImpl','requestDeviceCode','userId','deviceId','languageCode','isLoggedIn',
            'createNativeModul','onRawMessage','setGenericPasswo','getGenericPasswo','resetGenericPas'}
CLASSES={'_TtC6Twitch14LoginNetworker','_TtC6Twitch17SocialAuthSession',
         '_TtC6Twitch22SocialAuthEventHandler','_TtC6Twitch22StandardAccountManager',
         '_TtC6Twitch31LoginVerificationViewController','_TtC6Twitch13TWAppDelegate',
         'AMZNAuthorizationManager','AMZNASWebAuthenticationSessionViewStrategy'}


def inspect(ipa,hermesc):
    if hashlib.sha256(ipa.read_bytes()).hexdigest()!=IPA_SHA:raise ValueError('Exact inspected Twitch 32.0 donor required')
    with zipfile.ZipFile(ipa) as z:
        native=z.read('Payload/Twitch.app/Twitch');body=z.read('Payload/Twitch.app/main.jsbundle')
    if hashlib.sha256(native).hexdigest()!=EXPECTED['Twitch'] or hashlib.sha256(body).hexdigest()!=BUNDLE_SHA:
        raise ValueError('Changed native image or HBC')
    image=Image(native)
    result=dict(schema=1,scope='static donor inspection only',donor_sha256=IPA_SHA,
                main_sha256=EXPECTED['Twitch'],bundle_sha256=BUNDLE_SHA,
                hermesc_sha256=hashlib.sha256(hermesc.read_bytes()).hexdigest(),
                native_classes=image.selected_classes(CLASSES),functions=[],native_execution=False,
                authenticated_requests=False,fresh_login_established=False,
                hosted_portal_literals={url:url.encode() in body for url in ['https://m.twitch.tv/wv/auth/login','https://m.twitch.tv/wv/auth/signup']},
                login_event_literals={event:event.encode() in body for event in ['login-success','signup-success','login-portal-ready','close-login-portal']})
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'main.jsbundle';path.write_bytes(body)
        dump=Path(tmp)/'disassembly.txt'
        with dump.open('w') as f:subprocess.run([str(hermesc),'-b','-dump-bytecode',str(path)],stdout=f,check=True)
        result['disassembly_sha256']=hashlib.sha256(dump.read_bytes()).hexdigest()
        ordinal=-1;name=None;block=[];start=0
        def finish():
            if name not in FUNCTIONS:return
            text=''.join(block)
            refs=sorted(set(re.findall(r'GetById\w*\s+[^\n]*?"([^"\n]+)"',text)))
            refs=[ref for ref in refs if ref in PROPERTIES]
            result['functions'].append(dict(ordinal=ordinal,name=name,disassembly_line=start,
                sha256=hashlib.sha256(text.encode()).hexdigest(),relevant_property_references=refs))
        with dump.open() as f:
            for line_number,line in enumerate(f,1):
                match=re.match(r'^(?:NC)?Function<([^>]*)>\(',line)
                if match:
                    finish();ordinal+=1;name=match[1];block=[];start=line_number
                if name in FUNCTIONS:block.append(line)
            finish()
    if not {'LoginScreen','parseLoginMessage','AuthProvider','AuthSession','PortalWebViewContent'} <= {f['name'] for f in result['functions']}:
        raise ValueError('Required authentication functions missing')
    result['limits']=['Named function/property relationships are static evidence, not complete call-graph or route-execution proof.',
                      'Presence of native social SDK/system session components does not prove provider completion or first-party session compatibility.',
                      'No credential values, request headers/bodies, login submissions, Keychain items, or full disassembly are retained.']
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--donor',type=Path,required=True)
    p.add_argument('--hermesc',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=inspect(a.donor,a.hermesc);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print('Recorded',len(r['functions']),'selected bytecode functions and',len(r['native_classes']),'native classes; no login executed')
