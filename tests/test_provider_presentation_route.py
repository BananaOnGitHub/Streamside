"""Four provider shapes keep registry identity, ratio, and native URL redirection."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_emote_ui import RUNTIME
from test_emote_picker import HARNESS as PICKER_RUNTIME

ROOT=Path(__file__).resolve().parent.parent
MAIN=r'''
int main(void) {
    g_enabled=true;time_t now=time(NULL);Room *room=room_locked("fixture",now);snprintf(room->id,sizeof(room->id),"42");
    const char *names[]={"Square","Wide","Animated","AnimatedWide"};
    const char *urls[]={"https://cdn.7tv.app/emote/square/2x.webp","https://cdn.frankerfacez.com/emote/wide/2",
        "https://cdn.7tv.app/emote/animated/2x.gif","https://cdn.7tv.app/emote/animated-wide/2x.gif"};
    double aspects[]={1,4,1,3};
    for(unsigned i=0;i<4;i++)add_emote_locked(room,MAX_ROOM,names[i],urls[i],i==1 ? 2 : 0,false,NULL,aspects[i]);
    for(unsigned i=0;i<4;i++) {
        id metadata=tas_emotes_named_copy(string("42"),string(names[i]));assert(metadata);
        uint64_t number=dict(metadata,"id")->number;Emote *e=find_word(room,names[i]);assert(e && e->fake_id==number);
        assert(tas_emotes_aspect(number)==aspects[i]);
        double width=28,height=28;tas_emote_proportions(&width,&height,tas_emotes_aspect(number));
        assert(width==28*aspects[i] && height==28);
        const char *modes[]={"static","default","animated"};
        for(unsigned j=0;j<3;j++) {
            char native[256];snprintf(native,sizeof(native),"https://static-cdn.jtvnw.net/emoticons/v2/%llu/%s/dark/1.0",(unsigned long long)number,modes[j]);
            id request=fresh("NSMutableURLRequest"),url=fresh("NSURL");snprintf(url->value,sizeof(url->value),"%s",native);request->children[0]=url;
            id redirected=tas_emotes_rewrite_request_copy(request);
            assert(redirected && redirected!=request && !strcmp(redirected->children[0]->value,urls[i]));
            assert(!strcmp(request->children[0]->value,native));objc_release(redirected);
        }
        objc_release(metadata);
    }
    id request=fresh("NSMutableURLRequest"),url=fresh("NSURL");request->children[0]=url;
    snprintf(url->value,sizeof(url->value),"https://static-cdn.jtvnw.net/emoticons/v2/25/default/dark/1.0");assert(!tas_emotes_rewrite_request_copy(request));
    snprintf(url->value,sizeof(url->value),"https://example.com/emoticons/v2/900000000000001/default/dark/1.0");assert(!tas_emotes_rewrite_request_copy(request));
    return 0;
}
'''
EXTRA=r'''
    else if(!strcmp(sel,"URL"))result=o->children[0];
    else if(!strcmp(sel,"host")) {
        const char *p=strstr(o->value,"://");assert(p);p+=3;const char *end=strchr(p,'/');assert(end);char host[256];size_t n=(size_t)(end-p);memcpy(host,p,n);host[n]=0;result=string(host);
    } else if(!strcmp(sel,"path")) { const char *p=strchr(strstr(o->value,"://")+3,'/');assert(p);result=string(p); }
    else if(!strcmp(sel,"mutableCopy")) { result=fresh(o->cls);*result=*o; }
    else if(!strcmp(sel,"URLWithString:")) { id v=va_arg(args,id);result=fresh("NSURL");snprintf(result->value,sizeof(result->value),"%s",v->value); }
    else if(!strcmp(sel,"setURL:"))o->children[0]=va_arg(args,id);
'''
HARNESS=PICKER_RUNTIME[:PICKER_RUNTIME.index('static void add(Room')]
HARNESS=HARNESS.replace('else assert(!"unexpected picker selector");',EXTRA+'    else assert(!"unexpected provider route selector");')+MAIN

class ProviderPresentationRouteTests(unittest.TestCase):
    def test_four_shapes_share_registry_ratios_and_all_native_url_modes(self):
        zig=os.environ.get("ZIG") or shutil.which("zig");self.assertTrue(zig)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/"objc").mkdir()
            (root/"objc/runtime.h").write_text(RUNTIME+'\nMethod *class_copyMethodList(Class,unsigned *);\nSEL method_getName(Method);\n')
            (root/"objc/objc.h").write_text('#include "runtime.h"\n')
            (root/"objc/message.h").write_text('#include "runtime.h"\n')
            harness=root/"route.c";binary=root/"route";harness.write_text(HARNESS)
            result=subprocess.run([zig,"cc","-fblocks","-std=gnu11","-Wall","-Wextra","-Werror","-Wno-cast-function-type-mismatch",
                "-ffunction-sections","-fdata-sections","-fsanitize=address,undefined","-I",str(root),"-I",str(ROOT/"src"),str(harness),"-Wl,--gc-sections","-lpthread","-o",str(binary)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([binary],capture_output=True,text=True,env={**os.environ,"ASAN_OPTIONS":"detect_leaks=0"})
            self.assertEqual(result.returncode,0,result.stderr)
