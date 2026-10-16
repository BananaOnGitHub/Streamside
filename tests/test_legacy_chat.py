"""Production legacy hit testing and picker edits at a controlled UIKit boundary."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from test_emote_ui import RUNTIME

ROOT = Path(__file__).resolve().parents[1]

HITS = r'''
#include <assert.h>
#include <stdarg.h>
#include "TASEmoteUI.c"
struct Fake {
 const char *cls,*text;Rect frame;id data,requester,children[12],root,view_layer;
 unsigned n;BOOL hidden,clipped;float alpha;Point origin;
};
static struct Fake classes[16],strings[1024];static unsigned nc,ns;
static Point touch;
Class objc_getClass(const char *s){for(unsigned i=0;i<nc;i++)if(!strcmp(classes[i].cls,s))return &classes[i];assert(nc<16);classes[nc].cls=s;return &classes[nc++];}
Class object_getClass(id o){return o;}
SEL sel_registerName(const char *s){return s;}
Ivar class_getInstanceVariable(Class o,const char *s){
 static ptrdiff_t offsets[3]={offsetof(struct Fake,frame),offsetof(struct Fake,requester),offsetof(struct Fake,root)};
 if(!strcmp(s,"messageStringLayer"))return &offsets[2];
 if(!strcmp(o->cls,"_TtC6Twitch20ImageAttachmentLayer")){
  if(!strcmp(s,"content"))return &offsets[0];if(!strcmp(s,"networkImageRequester"))return &offsets[1];
 }return NULL;
}
ptrdiff_t ivar_getOffset(Ivar p){return *(ptrdiff_t *)p;}
static id dispatch(id o,SEL s,...){
 if(!o)return nil;va_list ap;va_start(ap,s);id r=nil;
 if(!strcmp(s,"isKindOfClass:")){Class c=va_arg(ap,Class);r=(id)(uintptr_t)(!strcmp(o->cls,c->cls) || (!strcmp(c->cls,"CALayer") && strstr(o->cls,"Layer")));}
 else if(!strcmp(s,"respondsToSelector:")){const char *a=va_arg(ap,SEL);r=(id)(uintptr_t)(!strcmp(a,"staticURL") || !strcmp(a,"host") || !strcmp(a,"path"));}
 else if(!strcmp(s,"isHidden"))r=(id)(uintptr_t)o->hidden;
 else if(!strcmp(s,"masksToBounds"))r=(id)(uintptr_t)o->clipped;
 else if(!strcmp(s,"sublayers") || !strcmp(s,"host") || !strcmp(s,"path") || !strcmp(s,"staticURL") || !strcmp(s,"description"))r=o;
 else if(!strcmp(s,"layer"))r=o->view_layer;
 else if(!strcmp(s,"count"))r=(id)(uintptr_t)o->n;
 else if(!strcmp(s,"objectAtIndex:")){unsigned i=va_arg(ap,NSUInteger);assert(i<o->n);r=o->children[i];}
 else if(!strcmp(s,"stringWithUTF8String:")){assert(ns<1024);r=&strings[ns++];r->cls="NSString";r->text=va_arg(ap,const char *);}
 else if(!strcmp(s,"isEqualToString:")){id a=va_arg(ap,id);r=(id)(uintptr_t)(o->text && a->text && !strcmp(o->text,a->text));}
 else if(!strcmp(s,"UTF8String"))r=(id)o->text;
 else assert(!"unexpected hit-test selector");
 va_end(ap);return r;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
static Point test_convert_point(id layer,id source,Point p){assert(source);return (Point){p.x-layer->origin.x,p.y-layer->origin.y};}
static Point test_touch(id gesture,id view){assert(gesture && view);return touch;}
static Rect test_bounds(id layer){return layer->frame;}
static float test_opacity(id layer){return layer->alpha;}
int main(void){
 struct Fake root={.cls="CALayer",.alpha=1,.frame={{0,0},{300,120}}},view={.cls="View",.root=&root,.view_layer=&root},gesture={.cls="Gesture"};
 struct Fake emotes[6],data[6];
 /* Displayed widths/wrapping, not a guessed TextKit re-layout. Repeated IDs
  * have distinct layer positions. Parent content includes a nonzero origin. */
 const char *urls[]={"/emoticons/v2/9000000001/default/dark/1.0","/emoticons/v2/9000000002/default/dark/1.0","/emoticons/v2/9000000003/default/dark/1.0"};
 double x[]={20,90,135,15,85,130},y[]={10,10,10,55,55,55},w[]={65,40,110,65,40,110};
 for(unsigned i=0;i<6;i++){
  data[i]=(struct Fake){.cls="_TtC6Twitch22MessageStringImageData",.text=urls[i%3]};
  emotes[i]=(struct Fake){.cls="_TtC6Twitch20ImageAttachmentLayer",.alpha=1,.data=&data[i],.frame={{3,4},{w[i],28}},.origin={x[i]-3,y[i]-4}};
  root.children[root.n++]=&emotes[i];
 }
 /* Host and path have different values on real NSURL, modeled below. */
 for(unsigned i=0;i<6;i++){touch=(Point){x[i]+w[i]/2,y[i]+14};assert(tapped_emote(&view,&gesture)==9000000001ULL+i%3);}
 touch=(Point){88,20};assert(!tapped_emote(&view,&gesture)); /* actual gap */
 emotes[5].hidden=YES;touch=(Point){150,60};assert(!tapped_emote(&view,&gesture));emotes[5].hidden=NO;
 root.hidden=YES;assert(!tapped_emote(&view,&gesture));root.hidden=NO;
 root.clipped=YES;root.frame.size.height=40;assert(!tapped_emote(&view,&gesture));root.clipped=NO;
 emotes[5].alpha=0;assert(!tapped_emote(&view,&gesture));emotes[5].alpha=1;
 data[5].text="/emoticons/v2/25/default/dark/1.0";assert(!tapped_emote(&view,&gesture)); /* native fallback */
 unsigned remaining=1;assert(!emote_layer_at_point(&root,&root,touch,0,&remaining) && !remaining);
 return 0;
}
'''

PICK = r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdarg.h>
typedef struct Fake *id;
typedef id Class;
typedef const char *SEL;
typedef const char *Method;
typedef ptrdiff_t *Ivar;
typedef unsigned long U;
typedef int BOOL;
#define YES 1
#define NO 0
#define nil ((id)0)
typedef struct {U location,length;} Range;
typedef struct {size_t start,length;} SSSpan;
#define MAX_TOKENS 512
struct Fake {const char *text;id name,native;unsigned char detent,dismissing;char padding[6];id host;};
typedef struct {id owner;Range completion;} State;
static struct Fake editor,owner,delegate,room,name={.text="YAY"},metadata={.name=&name},code={.text="YAY "};
static struct Fake controller,coordinator,window,controller_class,coordinator_class;
static BOOL available=YES,visible=YES,closing=NO,allowed=YES,found=YES,layout=YES,abi=YES;
static unsigned transitions;
static State context={.owner=&owner,.completion={1,3}};
static unsigned focus,edits,remembers,insertions,selection_missing,lookup_misses,native_insertions;
#define INC(v) (++(v))
static State *state(id d){assert(d==&delegate);return &context;}
static id objc_loadWeakRetained(id *s){return *s;}
static void objc_release(id o){(void)o;}
static id objc_retain(id o){return o;}
static id editor_for(id o){assert(o==&owner);return &editor;}
static id room_for(id o){assert(o==&owner);return &room;}
static id key(id o,const char *s){return !strcmp(s,"name")?o->name:!strcmp(s,"native")?o->native:nil;}
static id native_named(State *s,id n){(void)s;(void)n;return found?&metadata:nil;}
static id tas_emotes_named_copy(id r,id n){assert(r==&room && n==&name);return found?&metadata:nil;}
static void refresh(id d){assert(d==&delegate);}
static BOOL equal(id a,id b){return a==b;}
static id m0(id o,const char *s){
 if(o==&controller && !strcmp(s,"viewIfLoaded"))return visible?&controller:nil;
 if(o==&controller && !strcmp(s,"window"))return &window;
 if(!o)return nil;
 assert(o==&editor && !strcmp(s,"becomeFirstResponder"));focus++;return o;
}
static BOOL yes(id o,const char *s){assert(o==&controller && !strcmp(s,"isBeingDismissed"));return closing;}
static id object_field(id o,const char *n,const char *cls){
 (void)cls;
 if(o==&owner && !strcmp(n,"presentedEmoticonPaletteVC"))return available?&controller:nil;
 assert(o==&controller && !strcmp(n,"paletteCoordinator"));return &coordinator;
}
static Class object_getClass(id o){return o==&coordinator?&coordinator_class:&controller_class;}
static Class objc_getClass(const char *s){assert(!strcmp(s,"_TtC6Twitch23EmotePaletteCoordinator"));return &coordinator_class;}
static Ivar class_getInstanceVariable(Class c,const char *s){
 assert(c==&coordinator_class);
 static ptrdiff_t d=offsetof(struct Fake,detent),x=offsetof(struct Fake,dismissing),h=offsetof(struct Fake,host);
 if(!layout)return NULL;
 return !strcmp(s,"detent")?&d:!strcmp(s,"isDismissing")?&x:&h;
}
static ptrdiff_t ivar_getOffset(Ivar i){return *i;}
static size_t class_getInstanceSize(Class c){assert(c==&coordinator_class);return sizeof(coordinator);}
static SEL sel_registerName(const char *s){return s;}
static Method class_getInstanceMethod(Class c,SEL s){assert(c==&controller_class && !strcmp(s,"grabberTapped"));return abi?"v16@0:8":"v24@0:8@16";}
static const char *method_getTypeEncoding(Method m){return m;}
static void objc_msgSend(id o,SEL s){assert(o==&controller && !strcmp(s,"grabberTapped"));assert(coordinator.detent==1 && !coordinator.dismissing);coordinator.detent=0;transitions++;}
static id str(const char *s){assert(!strcmp(s," "));return &code;}
static id m1(id o,const char *s,id a){assert(o==&name && !strcmp(s,"stringByAppendingString:") && a==&code);return &code;}
static Range selection(id e){assert(e==&editor);return (Range){7,0};}
static id expanded_copy(id e,Range *r,SSSpan *s,size_t *n){assert(e==&editor && r && s);*n=0;return nil;}
static BOOL replace_plain(id d,Range r,id text){assert(d==&delegate && text==&code);assert((r.location==7 && !r.length)||(r.location==1 && r.length==3));edits++;return allowed;}
static void remember(id n){assert(n==&name);remembers++;}
#include "choose.c"
int main(void){
 coordinator.detent=1;
 choose(&delegate,&metadata,NO); /* same transition as native selection */
 assert(!focus && edits==1 && remembers==1 && insertions==1 && transitions==1 && !coordinator.detent);
 choose(&delegate,&metadata,NO);assert(transitions==1); /* compact stays compact */
 coordinator.detent=1;
 choose(&delegate,&metadata,YES); /* suggestions preserve the expanded state */
 assert(!focus && edits==3 && remembers==3 && insertions==3 && transitions==1 && coordinator.detent==1);
 allowed=NO;choose(&delegate,&metadata,NO);assert(transitions==1);allowed=YES;
 found=NO;choose(&delegate,&metadata,NO);assert(transitions==1 && edits==4);found=YES;
 available=NO;choose(&delegate,&metadata,NO);assert(transitions==1);available=YES;
 visible=NO;choose(&delegate,&metadata,NO);assert(transitions==1);visible=YES;
 closing=YES;choose(&delegate,&metadata,NO);assert(transitions==1);closing=NO;
 coordinator.dismissing=1;choose(&delegate,&metadata,NO);assert(transitions==1);coordinator.dismissing=0;
 layout=NO;choose(&delegate,&metadata,NO);assert(transitions==1);layout=YES;
 abi=NO;choose(&delegate,&metadata,NO);assert(transitions==1);abi=YES;
 coordinator.detent=2;choose(&delegate,&metadata,NO);assert(transitions==1);
 coordinator.detent=1;metadata.native=&name;
 choose(&delegate,&metadata,NO);assert(transitions==2 && native_insertions==1 && !focus);

 return 0;
}
'''

class LegacyChatTests(unittest.TestCase):
    def test_picker_insertion_preserves_twitch_responder_and_completion_range(self):
        source = (ROOT/'src/SSComposer.c').read_text()
        choose = source[source.index('static void reveal_library_input('):source.index('\nstatic void target(')]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path/'choose.c').write_text(choose)
            (path/'test.c').write_text(PICK)
            built = subprocess.run(['cc','-fsanitize=address,undefined','-I',str(path),str(path/'test.c'),'-o',str(path/'test')],capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran = subprocess.run([str(path/'test')],capture_output=True,text=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
            self.assertEqual(ran.returncode,0,ran.stderr)

    def test_repeated_and_wrapped_emotes_use_displayed_layer_identity(self):
        zig = os.environ.get('ZIG') or shutil.which('zig')
        self.assertTrue(zig)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path/'objc').mkdir()
            for name in ['objc.h', 'runtime.h', 'message.h']:
                (path/'objc'/name).write_text(RUNTIME)
            source = (ROOT/'src/TASEmoteUI.c').read_text()
            # Typed structure/floating returns need dedicated ABI shims on
            # the host; traversal, admission and containment remain production.
            source = source.replace('Point local=((Point (*)(id,SEL,Point,id))objc_msgSend)(layer,sel_registerName("convertPoint:fromLayer:"),point,source);', 'Point local=test_convert_point(layer,source,point);')
            source = source.replace('Rect bounds=((Rect (*)(id,SEL))objc_msgSend)(layer,sel_registerName("bounds"));', 'Rect bounds=test_bounds(layer);')
            source = source.replace('((float (*)(id,SEL))objc_msgSend)(layer,sel_registerName("opacity"))', 'test_opacity(layer)')
            source = source.replace('Point point=((Point (*)(id,SEL,id))objc_msgSend)(gesture,sel_registerName("locationInView:"),self);', 'Point point=test_touch(gesture,self);')
            start = source.index('static IMP g_receive')
            source = source[:start] + 'static Point test_convert_point(id,id,Point);\nstatic Point test_touch(id,id);\nstatic Rect test_bounds(id);\nstatic float test_opacity(id);\n' + source[start:]
            # The URL fixture's host is intentionally independent of its path.
            harness = HITS.replace('else if(!strcmp(s,"isEqualToString:")){id a=va_arg(ap,id);r=(id)(uintptr_t)(o->text && a->text && !strcmp(o->text,a->text));}', 'else if(!strcmp(s,"isEqualToString:")){id a=va_arg(ap,id);r=(id)(uintptr_t)!strcmp(a->text,"static-cdn.jtvnw.net");}')
            (path/'TASEmoteUI.c').write_text(source)
            (path/'test.c').write_text(harness)
            built = subprocess.run([zig,'cc','-fblocks','-fsanitize=address,undefined','-ffunction-sections','-fdata-sections','-I',str(path),'-I',str(ROOT/'src'),str(path/'test.c'),'-Wl,--gc-sections','-o',str(path/'test')],capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran = subprocess.run([str(path/'test')],capture_output=True,text=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
            self.assertEqual(ran.returncode,0,ran.stderr)
