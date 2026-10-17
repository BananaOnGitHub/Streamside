"""Bounded numeric RN composer collector and bridge; no UIKit behavior claim."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from test_emote_ui import RUNTIME

ROOT=Path(__file__).resolve().parent.parent
HARNESS=r'''
#include <assert.h>
#include <stdarg.h>
#include <objc/runtime.h>
#include "TASComposerTraceModel.h"
typedef struct {double x,y;} TestPoint;
typedef struct {double width,height;} TestSize;
typedef struct {TestPoint origin;TestSize size;} TestRect;
typedef struct {unsigned long location,length;} TestRange;
struct Fake {
 const char *cls,*text;
 id editor,resolved_font,resolved_color,label,editor_label,trace_editor,window,parent,attributes,before,after,font,color,attachment;
 id items[8];unsigned count,length,location,selected_length;
 BOOL hidden,first,marked;double point_size,rgba[4],alpha;TestRect rect;
};
static double test_scalar(id,const char *);
static TestRect test_rect(id);
static TestRect test_convert(id,TestRect,id);
static TestRange test_range(id);
static id test_timer(void);
size_t class_getInstanceSize(Class);
#include "trace.c"
void *_NSConcreteStackBlock[32];
void *_NSConcreteGlobalBlock[32];
static unsigned calls,installed,notifications,queued,captures;
static BOOL main_thread=YES,modal=NO;
static unsigned policy=1;
unsigned tas_diag_policy_word(void){return policy;}
BOOL tas_emote_ui_modal_visible(id o){assert(o);return modal;}
static struct Fake classes[32],pool[256];static unsigned nc,np;
static id fresh(const char *cls){assert(np<256);id o=&pool[np++];o->cls=cls;o->alpha=1;return o;}
Class objc_getClass(const char *s){for(unsigned i=0;i<nc;i++)if(!strcmp(classes[i].cls,s))return &classes[i];assert(nc<32);classes[nc].cls=s;return &classes[nc++];}
Class object_getClass(id o){return o;}
SEL sel_registerName(const char *s){return s;}
id objc_retain(id o){return o;}
void objc_release(id o){(void)o;}
Ivar class_getInstanceVariable(Class c,const char *s){(void)c;if(!strcmp(s,"resolvedFont"))return (Ivar)(uintptr_t)offsetof(struct Fake,resolved_font);if(!strcmp(s,"resolvedTextColor"))return (Ivar)(uintptr_t)offsetof(struct Fake,resolved_color);return NULL;}
ptrdiff_t ivar_getOffset(Ivar i){return (ptrdiff_t)(uintptr_t)i;}
size_t class_getInstanceSize(Class c){(void)c;return sizeof(struct Fake);}
id objc_getAssociatedObject(id o,const void *key){return key==&label_key?o->label:key==&editor_identity_key?o->editor_label:o->trace_editor;}
void objc_setAssociatedObject(id o,const void *key,id value,uintptr_t p){assert(p==1);if(key==&label_key)o->label=value;else if(key==&editor_identity_key)o->editor_label=value;else {assert(key==&editor_key);o->trace_editor=value;}}
Class objc_allocateClassPair(Class base,const char *s,size_t n){assert(base==objc_getClass("NSObject")&&!n);return objc_getClass(s);}
BOOL class_addMethod(Class c,SEL s,IMP imp,const char *encoding){assert(c&&imp&&!strcmp(encoding,"v24@0:8@16"));assert(!strcmp(s,"tick:")||!strcmp(s,"keyboard:"));installed++;return YES;}
void objc_registerClassPair(Class c){assert(c);}
static double test_scalar(id o,const char *s){return !o?0:!strcmp(s,"alpha")?o->alpha:o->point_size;}
static TestRect test_rect(id o){return o?o->rect:(TestRect){0};}
static TestRect test_convert(id o,TestRect r,id window){assert(o);(void)window;return r;}
static TestRange test_range(id o){return (TestRange){o->location,o->selected_length};}
static id test_timer(void){return fresh("NSTimer");}
static id dispatch(id o,SEL s,...){
 calls++;if(!o)return nil;va_list ap;va_start(ap,s);id result=nil;
 if(!strcmp(s,"isMainThread"))result=(id)(uintptr_t)main_thread;
 else if(!strcmp(s,"isKindOfClass:")){Class c=va_arg(ap,Class);result=(id)(uintptr_t)(!strcmp(o->cls,c->cls));}
 else if(!strcmp(s,"stringWithUTF8String:")){result=fresh("NSString");result->text=va_arg(ap,const char *);}
 else if(!strcmp(s,"new"))result=fresh(o->cls);
 else if(!strcmp(s,"unsignedIntValue"))result=(id)(uintptr_t)o->length;
 else if(!strcmp(s,"numberWithUnsignedInt:")){result=fresh("NSNumber");result->length=va_arg(ap,unsigned);}
 else if(!strcmp(s,"weakObjectsHashTable"))result=fresh("NSHashTable");
 else if(!strcmp(s,"count"))result=(id)(uintptr_t)o->count;
 else if(!strcmp(s,"length"))result=(id)(uintptr_t)o->length;
 else if(!strcmp(s,"addObject:")){assert(o->count<8);o->items[o->count++]=va_arg(ap,id);}
 else if(!strcmp(s,"allObjects"))result=o;
 else if(!strcmp(s,"objectAtIndex:"))result=o->items[va_arg(ap,unsigned long)];
 else if(!strcmp(s,"defaultCenter")||!strcmp(s,"mainRunLoop")||!strcmp(s,"mainQueue"))result=o;
 else if(!strcmp(s,"addObserver:selector:name:object:")){assert(va_arg(ap,id)==observer);assert(!strcmp(va_arg(ap,SEL),"keyboard:"));assert(va_arg(ap,id));assert(!va_arg(ap,id));notifications++;}
 else if(!strcmp(s,"addTimer:forMode:")){assert(va_arg(ap,id));assert(!strcmp(va_arg(ap,id)->text,"kCFRunLoopCommonModes"));}
 else if(!strcmp(s,"window"))result=o->window;
 else if(!strcmp(s,"superview"))result=o->parent;
 else if(!strcmp(s,"isFirstResponder"))result=(id)(uintptr_t)o->first;
 else if(!strcmp(s,"markedTextRange"))result=o->marked?o:nil;
 else if(!strcmp(s,"isHidden"))result=(id)(uintptr_t)o->hidden;
 else if(!strcmp(s,"clipsToBounds"))result=(id)(uintptr_t)YES;
 else if(!strcmp(s,"attributedText"))result=o;
 else if(!strcmp(s,"typingAttributes"))result=o->attributes;
 else if(!strcmp(s,"font"))result=o->font;
 else if(!strcmp(s,"textColor"))result=o->color;
 else if(!strcmp(s,"respondsToSelector:")){(void)va_arg(ap,SEL);result=(id)(uintptr_t)NO;}
 else if(!strcmp(s,"objectForKey:")){id key=va_arg(ap,id);if(!strcmp(key->text,"NSFont"))result=o->font;else if(!strcmp(key->text,"NSColor"))result=o->color;else if(!strcmp(key->text,"NSAttachment"))result=o->attachment;else assert(0);}
 else if(!strcmp(s,"getRed:green:blue:alpha:")){for(unsigned i=0;i<4;i++)*va_arg(ap,double *)=o->rgba[i];result=(id)(uintptr_t)YES;}
 else if(!strcmp(s,"attributesAtIndex:effectiveRange:")){unsigned long i=va_arg(ap,unsigned long);assert(!va_arg(ap,TestRange *));result=i==0?o->before:o->after;captures++;}
 else if(!strcmp(s,"addOperationWithBlock:")){void (^block)(void)=(void (^)(void))va_arg(ap,id);queued++;block();}
 else {fprintf(stderr,"Unexpected diagnostic selector %s\n",s);abort();}
 va_end(ap);return result;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
typedef struct {const char *js_name,*objc_name;BOOL synchronous;} TASRNMethodInfo;
#define TAS_CT_RN_DOUBLE(o) ((o)->point_size)
#include "TASComposerRNBridge.h"
static void model(void){
 TASComposerRing r={0};TASComposerSample s={0};s.event=2;s.owner=1;
 for(unsigned i=0;i<140;i++){s.ms=i;s.length=i;tas_ct_store(&r,&s);}
 assert(r.count==128&&r.overwritten==12&&r.accepted==140);
 char report[32768];tas_ct_report(&r,report,sizeof(report));assert(strstr(report,"export-omitted=64"));
 assert(strstr(report,"76 e2")&&strstr(report,"139 e2"));assert(!strstr(report,"75 e2"));
 char short_report[600];tas_ct_report(&r,short_report,sizeof(short_report));assert(strstr(short_report,"export truncated"));
 r=(TASComposerRing){0};for(unsigned i=0;i<120;i++)assert(tas_ct_budget(&r,2000));assert(!tas_ct_budget(&r,2000));assert(r.rate_dropped==1);assert(tas_ct_budget(&r,3000));
 s=(TASComposerSample){.event=12,.owner=1};tas_ct_store(&r,&s);s.ms=25;tas_ct_store(&r,&s);assert(r.count==1&&r.coalesced==1);
 assert(tas_ct_number(NAN)==-100001&&tas_ct_number(1e99)==100000&&tas_ct_point_size(18)==180);
}
int main(void){
 model();id owner=fresh("_TtC21twitch_rn_emote_input20TwitchEmoteInputView"),editor=fresh("UITextView");
 unsigned before_calls=calls;tas_composer_trace_native(owner,editor,2);assert(calls==before_calls&&ring.count==0);
 unsigned evaluated=0;TAS_CT_CAPTURE(owner,(evaluated++,editor),2);assert(!evaluated);
 policy=1|(1<<TAS_DIAG_COMPOSER)|TAS_DIAG_DETAIL_BIT;
 editor->window=fresh("UIWindow");editor->window->rect=(TestRect){{0,0},{390,844}};editor->rect=(TestRect){{0,700},{390,44}};
 editor->parent=fresh("UIView");editor->parent->rect=(TestRect){{0,690},{390,60}};editor->parent->hidden=YES;
 editor->first=YES;editor->length=2;editor->location=1;
 editor->font=fresh("UIFont");editor->font->point_size=18;owner->resolved_font=editor->font;
 editor->color=fresh("UIColor");editor->color->rgba[0]=editor->color->rgba[1]=editor->color->rgba[2]=editor->color->rgba[3]=1;owner->resolved_color=editor->color;
 editor->attributes=fresh("NSDictionary");editor->attributes->font=fresh("UIFont");editor->attributes->font->point_size=12;
 editor->attributes->color=fresh("UIColor");editor->attributes->color->rgba[3]=1;
 editor->before=fresh("NSDictionary");editor->before->attachment=fresh("_TtC21twitch_rn_emote_input21TwitchEmoteAttachment");editor->after=fresh("NSDictionary");
 tas_composer_trace_native(owner,editor,2);assert(installed==2&&notifications==4&&ring.count==1);
 TASComposerSample s=ring.samples[0];assert(s.owner==1&&s.font==120&&s.base_font==180&&s.resolved_font==180);
 assert(s.color==255&&s.base_color==0xffffffff&&s.resolved_color==0xffffffff);assert(s.adjacent==5&&s.hidden_depth==2&&(s.flags&32));assert(s.rect[1]==700);
 /* Read-only capture leaves the failing attributes and all editor state intact. */
 assert(editor->attributes->font->point_size==12&&editor->first&&editor->parent->hidden);
 unsigned reads=captures;editor->marked=YES;tas_composer_trace_native(owner,editor,6);assert(captures==reads);editor->marked=NO;
 policy=1;before_calls=calls;tas_composer_trace_native(owner,editor,2);tas_composer_trace_js(20,1,0,0,0,0);assert(calls==before_calls);
 char out[32768];tas_composer_trace_report(out,sizeof(out));assert(strstr(out,"collection disabled"));
 policy=1|(1<<TAS_DIAG_COMPOSER)|TAS_DIAG_DETAIL_BIT;
 id numbers[6];for(unsigned i=0;i<6;i++){numbers[i]=fresh("NSNumber");numbers[i]->point_size=i;}
 numbers[0]->point_size=22;numbers[1]->point_size=1;numbers[4]->point_size=390;numbers[5]->point_size=60;
 unsigned accepted=ring.accepted;
 rn_composer_trace(nil,NULL,numbers[0],numbers[1],numbers[2],numbers[3],numbers[4],numbers[5]);assert(ring.accepted>=accepted+1&&queued==1);
 const TASRNMethodInfo *info=rn_composer_trace_export(nil,NULL);assert(info->synchronous&&!strcmp(info->js_name,"onLayout"));
 accepted=ring.accepted;numbers[0]->point_size=22.5;rn_composer_trace(nil,NULL,numbers[0],numbers[1],numbers[2],numbers[3],numbers[4],numbers[5]);assert(ring.accepted==accepted);
 numbers[0]->point_size=22;numbers[4]->point_size=NAN;rn_composer_trace(nil,NULL,numbers[0],numbers[1],numbers[2],numbers[3],numbers[4],numbers[5]);assert(ring.accepted==accepted);
 tas_composer_trace_clear();assert(!ring.count&&!ring.accepted);
 return 0;
}
'''

class ComposerTraceTests(unittest.TestCase):
    def test_numeric_collector_bounds_privacy_gates_and_native_bridge(self):
        zig=os.environ.get('ZIG') or shutil.which('zig')
        self.assertTrue(zig,'Zig required')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'objc').mkdir();(p/'objc/runtime.h').write_text(RUNTIME);(p/'objc/objc.h').write_text('#include "runtime.h"\n');(p/'objc/message.h').write_text('#include "runtime.h"\n')
            source=(ROOT/'src/TASComposerTrace.c').read_text()
            source=source.replace('typedef struct {double x,y;} Point;','typedef TestPoint Point;')
            source=source.replace('typedef struct {double width,height;} Size;','typedef TestSize Size;')
            source=source.replace('typedef struct {Point origin;Size size;} Rect;','typedef TestRect Rect;')
            source=source.replace('typedef struct {U location,length;} Range;','typedef TestRange Range;')
            source=source.replace('((double (*)(id,SEL))objc_msgSend)(font,sel_registerName("pointSize"))','test_scalar(font,"pointSize")')
            source=source.replace('((double (*)(id,SEL))objc_msgSend)(ancestor,sel_registerName("alpha"))','test_scalar(ancestor,"alpha")')
            for obj in ('view','ancestor','window'):
                source=source.replace(f'((Rect (*)(id,SEL))objc_msgSend)({obj},sel_registerName("bounds"))',f'test_rect({obj})')
            source=source.replace('((Rect (*)(id,SEL,Rect,id))objc_msgSend)(view,sel_registerName("convertRect:toView:"),bounds,window)','test_convert(view,bounds,window)')
            source=source.replace('((Rect (*)(id,SEL,Rect,id))objc_msgSend)(window,sel_registerName("convertRect:fromWindow:"),keyboard,nil)','test_convert(window,keyboard,nil)')
            source=source.replace('((Range (*)(id,SEL))objc_msgSend)(editor,sel_registerName("selectedRange"))','test_range(editor)')
            source=source.replace('((Rect (*)(id,SEL))objc_msgSend)(value,sel_registerName("CGRectValue"))','test_rect(value)')
            source=source.replace('((id (*)(id,SEL,double,id,SEL,id,BOOL))objc_msgSend)((id)objc_getClass("NSTimer"),sel_registerName("timerWithTimeInterval:target:selector:userInfo:repeats:"),0.25,observer,sel_registerName("tick:"),nil,YES)','test_timer()')
            (p/'trace.c').write_text(source);(p/'test.c').write_text(HARNESS)
            result=subprocess.run([zig,'cc','-DTAS_RN_COMPOSER_DIAGNOSTIC=1','-fblocks','-Wall','-Wextra','-Werror','-Wno-cast-function-type-mismatch','-fsanitize=address,undefined','-I',str(p),'-I',str(ROOT/'src'),str(p/'test.c'),'-pthread','-o',str(p/'test')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([p/'test'],capture_output=True,text=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
            self.assertEqual(result.returncode,0,result.stderr)

    def test_compiled_out_entrypoints_do_not_require_a_runtime(self):
        zig=os.environ.get('ZIG') or shutil.which('zig');self.assertTrue(zig)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'objc').mkdir();(p/'objc/objc.h').write_text('typedef void *id;\n')
            (p/'test.c').write_text('#include "TASComposerTrace.h"\n#include <assert.h>\nint main(void){int evaluated=0;TAS_CT_CAPTURE((evaluated++,(id)0),(evaluated++,(id)0),1);assert(!evaluated);tas_composer_trace_native(0,0,1);tas_composer_trace_js(20,1,0,0,0,0);tas_composer_trace_clear();tas_composer_trace_sheet_closed();}\n')
            result=subprocess.run([zig,'cc','-Wall','-Wextra','-Werror','-I',str(p),'-I',str(ROOT/'src'),str(p/'test.c'),'-o',str(p/'test')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(subprocess.run([p/'test']).returncode,0)
