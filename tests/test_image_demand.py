"""Production probe logic against bounded fake objects; not a device benchmark."""
import ast
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent


class ImageDemandTests(unittest.TestCase):
    def test_aggregate_identity_bounds_native_lifetime_and_privacy(self):
        source = (ROOT/'src/TASImageDemand.c').read_text().replace('#include <objc/runtime.h>', '').replace('#include <objc/message.h>', '')
        prelude = r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#include <assert.h>
#include <stdlib.h>
typedef struct Fake *id;
typedef id Class; typedef const char *SEL; typedef void (*IMP)(void); typedef struct Fake *Method;
typedef signed char BOOL;
#define nil NULL
struct Fake {const char *text;id url,headers,keys,value,window,tag,scope,rows; id entries[40];unsigned n,type;};
static struct Fake base,number,method;
static SEL sel_registerName(const char *s){return s;}
static Class objc_getClass(const char *s){(void)s;return &base;}
static Class objc_allocateClassPair(Class c,const char *s,size_t n){(void)c;(void)s;(void)n;return &base;}
static void objc_disposeClassPair(Class c){(void)c;}
static void objc_registerClassPair(Class c){(void)c;}
static bool class_addMethod(Class c,SEL s,IMP f,const char *e){(void)c;(void)s;(void)f;(void)e;return true;}
static Method class_getInstanceMethod(Class c,SEL s){(void)c;(void)s;return &method;}
static const char *method_getTypeEncoding(Method m){(void)m;return "v16@0:8";}
static void noop(id o,SEL s){(void)o;(void)s;}
static IMP method_getImplementation(Method m){(void)m;return (IMP)noop;}
static IMP method_setImplementation(Method m,IMP f){(void)m;return f;}
id objc_retain(id o){return o;}
void objc_release(id o){(void)o;}
id objc_getAssociatedObject(id o,const void *k){(void)k;return o?o->scope:nil;}
void objc_setAssociatedObject(id o,const void *k,id v,uintptr_t p){(void)k;assert(p==1);o->scope=v;}
static id dispatch(id o,SEL s,...){
 if(!o)return nil;va_list a;va_start(a,s);id r=nil;
 if(!strcmp(s,"URL"))r=o->url;
 else if(!strcmp(s,"absoluteString"))r=o;
 else if(!strcmp(s,"UTF8String"))r=(id)o->text;
 else if(!strcmp(s,"allHTTPHeaderFields"))r=o->headers;
 else if(!strcmp(s,"allKeys"))r=o->keys;
 else if(!strcmp(s,"objectForKey:")){(void)va_arg(a,id);r=o->value;}
 else if(!strcmp(s,"count"))r=(id)(uintptr_t)o->n;
 else if(!strcmp(s,"objectAtIndex:"))r=o->entries[va_arg(a,unsigned long)];
 else if(!strcmp(s,"respondsToSelector:")){(void)va_arg(a,SEL);r=(id)1;}
 else if(!strcmp(s,"window"))r=o->window;
 else if(!strcmp(s,"accessibilityIdentifier"))r=o->tag;
 else if(!strcmp(s,"transactionMetrics"))r=o->rows;
 else if(!strcmp(s,"resourceFetchType") || !strcmp(s,"unsignedIntValue"))r=(id)(uintptr_t)o->type;
 else if(!strcmp(s,"numberWithUnsignedInt:")){number.type=va_arg(a,unsigned);r=&number;}
 else if(!strcmp(s,"new"))r=&base;
 else assert(!strcmp(s,"fetchStartDate") || !strcmp(s,"responseEndDate"));
 va_end(a);return r;
}
#define objc_msgSend dispatch
'''
        main = r'''
int main(void){
 struct Fake url={.text="https://cdn.test/private-emote?secret=query"},name={.text="Accept"},value={.text="PRIVATE-HEADER"};
 struct Fake keys={.n=1,.entries={&name}},headers={.keys=&keys,.value=&value},request={.url=&url,.headers=&headers};
 tas_demand_event(1,1,NULL,0,0);tas_demand_event(3,1,url.text,0,0);
 tas_demand_request(&request,0);tas_demand_request(&request,0);
 assert(first_asset_requests==1 && unique_requests==1 && repeated_requests==1 && repeated_assets==1 && source_masks[2]==2);
 value.text="OTHER-SECRET";tas_demand_request(&request,0);
 value.text="PRIVATE-HEADER";tas_demand_request(&request,0);
 assert(unique_requests==2 && repeated_requests==2 && variants==2);
 tas_demand_event(3,2,url.text,0,0);tas_demand_request(&request,0);assert(source_masks[6]==1);
 tas_demand_mark_url(&url,6);assert(tas_demand_url_scope(&url)==6);
 tas_demand_request(&request,6);assert(source_masks[64]==1);
 tas_demand_event(2,1,NULL,0,0);assert(!live[1] && peak[1]==1);
 tas_demand_event(8,0,NULL,390,700);tas_demand_event(9,0,NULL,390,260);
 tas_demand_event(10,0,NULL,12000,260);tas_demand_event(11,0,NULL,8,0);
 assert(geometry[0][0]==390 && geometry[0][1]==700 && geometry[1][1]==260 && geometry[2][0]==12000 && geometry[3][0]==8);
 tas_demand_event(6,1,NULL,700,0);assert(events[1][9]==1);
 struct Fake tag={.text="provider"},view={.tag=&tag,.window=&base};
 tas_demand_install();IMP original=move_original;tas_demand_install();assert(move_original==original);
 move(&view,"didMoveToWindow");layout(&view,"layoutSubviews");assert(native_live[1]==1 && native_window[1]==1);
 view.window=nil;move(&view,"didMoveToWindow");assert(native_live[1]==1 && !native_window[1]);
 recycle(&view,"prepareForRecycle");assert(!native_live[1] && native_recycles==1);
 layout(&view,"layoutSubviews");dealloc_view(&view,"dealloc");assert(!native_live[1]);
 assert(tas_demand_delegate());
 struct Fake cache={.type=3},network={.type=1},rows={.n=2,.entries={&cache,&network}},report={.rows=&rows};
 metrics(nil,NULL,nil,nil,&report);assert(fetches[3]==1 && fetches[1]==1 && metrics_calls==1);
 char report_text[32768];tas_demand_status(report_text,sizeof(report_text));
 assert(!strstr(report_text,"cdn.test") && !strstr(report_text,"private-emote") && !strstr(report_text,"SECRET"));
 assert(strstr(report_text,"local-cache"));
 char tiny[16];tas_demand_status(tiny,sizeof(tiny));assert(tiny[15]==0);

 /* Stage attribution is separate from launch totals and real native mounts. */
 memset(stages,0,sizeof(stages));memset(assets,0,sizeof(assets));live[1]=0;
 tas_demand_event(22,0,NULL,0,1);
 for(unsigned i=0;i<950;i++){char u[80];snprintf(u,sizeof(u),"https://cdn.test/stage-%u",i);
   tas_demand_event(1,1,u,0,0);tas_demand_event(3,1,u,0,0);tas_demand_event(5,1,NULL,0,0);}
 assert(stages[0].mount==950 && stages[0].peak==950 && stages[0].unique==950 && stages[0].starts==950 && !stages[0].remount);
 tas_demand_event(16,0,NULL,0,189);tas_demand_event(17,0,NULL,190,190);
 tas_demand_event(18,0,NULL,370,11716);tas_demand_event(19,0,NULL,0,1);
 assert(stages[0].range==190 && stages[0].mask==190 && stages[0].zero_zoom==1 && stages[0].pending==1);
 tas_demand_transport(6,128,134,7);assert(stages[0].active==6 && stages[0].queued==128 && stages[0].cancelled==7);
 tas_demand_event(22,0,NULL,1,1);assert(stages[1].peak==950 && !stages[1].mount);
 tas_demand_event(22,0,NULL,2,1);
 for(unsigned i=0;i<950;i++){char u[80];snprintf(u,sizeof(u),"https://cdn.test/stage-%u",i);tas_demand_event(2,1,u,0,0);}
 tas_demand_event(22,0,NULL,3,1);tas_demand_event(1,1,"https://cdn.test/stage-1",0,0);
 assert(stages[3].remount==1 && stages[3].unique==1 && stages[3].peak==1);
 tas_demand_event(1,1,"https://cdn.test/stage-1",0,0);assert(stages[3].duplicates==1 && stages[3].remount==1);
 tas_demand_event(22,0,NULL,4,1);tas_demand_event(2,1,"https://cdn.test/stage-1",0,0);tas_demand_event(2,1,"https://cdn.test/stage-1",0,0);assert(!live[1]);
 tas_demand_event(22,0,NULL,0,2);tas_demand_event(1,1,"https://cdn.test/stage-1",0,0);assert(opens==2 && stages[5].mount==1 && stages[5].remount==1);
 tas_demand_event(22,0,NULL,0,1);tas_demand_event(5,1,NULL,0,0);assert(late_stage==1 && !stages[5].starts);
 tas_demand_event(22,0,NULL,5,2);tas_demand_event(1,1,"https://cdn.test/filter",0,0);assert(stages[6].mount==1);
 tas_demand_status(report_text,sizeof(report_text));assert(strstr(report_text,"scroll-back") && strstr(report_text,"temporal ALL-provider"));
 assert(!strstr(report_text,"cdn.test") && !strstr(report_text,"stage-1"));
 /* Numeric boundary packets: two fixed slots, sixteen rows each, no raw strings. */
 char packet[4096];size_t used=0;packet[used++]='[';
 for(unsigned i=0;i<CALC_VALUES;i++)used+=(size_t)snprintf(packet+used,sizeof(packet)-used,"%s%u",i?",":"",i);
 packet[used++]=']';packet[used]=0;
 tas_demand_event(27,0,packet,1,0);assert(calculation_count[0]==1 && calculations[0][0].value[40]==40);
 tas_demand_event(27,0,"[PRIVATE-HEADER]",1,0);tas_demand_event(27,0,"[NaN]",1,0);
 tas_demand_event(27,0,packet,3,0);assert(calculation_refused==3);
 for(unsigned s=1;s<=CALC_SLOTS;s++)for(unsigned i=0;i<20;i++)tas_demand_event(27,0,packet,s,0);
 assert(calculation_count[0]==16 && calculation_count[1]==16 && calculation_refused==12);
 tas_demand_event(28,0,NULL,128,16);tas_demand_event(29,0,NULL,1,0);
 tas_demand_status(report_text,sizeof(report_text));assert(strstr(report_text,"calc list=2 transition=16"));
 assert(strstr(report_text,"No asset values or fingerprints reported."));
 assert(!strstr(report_text,"PRIVATE-HEADER") && !strstr(report_text,"cdn.test"));
 assert(sizeof(calculations)<16*1024);
 for(unsigned i=0;i<ASSETS+50;i++){char u[80];snprintf(u,sizeof(u),"https://cdn.test/%u",i);tas_demand_event(3,1,u,0,0);}
 assert(evictions>=50 && sizeof(assets)+sizeof(requests)+sizeof(views)<512*1024);
 char huge[URL_BUDGET+2];memset(huge,'x',sizeof(huge));huge[sizeof(huge)-1]=0;
 tas_demand_event(3,1,huge,0,0);assert(refusals);
 struct Fake *many=calloc(VIEWS+1,sizeof(*many));assert(many);
 for(unsigned i=0;i<VIEWS+1;i++)sample(&many[i],false);
 assert(native_refused==1);for(unsigned i=0;i<VIEWS+1;i++)sample(&many[i],true);free(many);
 return 0;
}
'''
        zig = os.environ.get('ZIG') or shutil.which('zig')
        self.assertTrue(zig)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'probe.c';binary=Path(folder)/'probe'
            path.write_text(prelude+source+main)
            built=subprocess.run([zig,'cc','-DTAS_IMAGE_DEMAND_DIAGNOSTIC=1','-I',str(ROOT/'src'),str(path),'-pthread','-o',str(binary)],capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([binary],capture_output=True,text=True)
            self.assertEqual(ran.returncode,0,ran.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node required')
    def test_committed_image_lifecycle_same_source_callbacks_and_unmount(self):
        # Mock React does not model Yoga/Fabric/native mounting or HTTP caching.
        tree=ast.parse((ROOT/'tests/test_rn_library.py').read_text())
        script=next(n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
        script=script.replace('deps.some((x,j)=>x!==old.deps[j])){if(old', '(!deps||deps.some((x,j)=>x!==old.deps[j]))){if(old')
        script=script.replace("const row=()=>g.props.renderItem({section:g.props.sections[1],item:g.props.sections[1].data[0]});", "const row=()=>{const e=g.props.renderItem({section:g.props.sections[1],item:g.props.sections[1].data[0]});return typeof e.type==='function'?render(e.type,e.props,'columns'):e;};")
        script += r'''
let observations=[],clock=0;env.performance={now:()=>clock};
env.setTimeout=()=>1;env.clearTimeout=()=>{};
bridge.observe=(...a)=>observations.push(a);
p.channelID='42';p.emotePickerSID='probe';library();g=grid();
const imageCell=cells()[0].children[0];assert.equal(typeof imageCell.type,'function');
let loads=0,failures=0,starts=0;
const props={...imageCell.props,data:{...imageCell.props.data,onLoad:()=>loads++,onError:()=>failures++,onLoadStart:()=>starts++}};
let image=render(imageCell.type,props,'probe-image');assert.equal(image.type,'image');
assert.strictEqual(image.props.source,props.data.source);assert.strictEqual(image.props.style,props.data.style);
assert.equal(observations.filter(a=>a[0]===1&&a[1]===1).length,1);
image.props.onLoadStart({});clock=700;image.props.onLoad({});image.props.onLoad({});
assert.equal(loads,2);assert.equal(starts,1);assert.equal(observations.filter(a=>a[0]===6&&a[1]===1).length,1);
image=render(imageCell.type,{...props,data:{...props.data,source:{uri:props.data.source.uri}}},'probe-image');
assert.equal(observations.filter(a=>a[0]===3&&a[1]===1).length,1);assert.equal(observations.filter(a=>a[0]===4&&a[1]===1).length,1);
const oldLoad=image.props.onLoad;
image=render(imageCell.type,{...props,data:{...props.data,source:{uri:'new-source'}}},'probe-image');
oldLoad({});assert.equal(observations.filter(a=>a[0]===6&&a[1]===1).length,1);
image.props.onError({});assert.equal(failures,1);
slots.get('probe-image').forEach(s=>{if(s&&s.cleanup)s.cleanup();});
assert.equal(observations.filter(a=>a[0]===2&&a[1]===1).length,1);
const nativeSource={src:'synthetic',testID:'chat-emote-opaque',style:{width:30}};
const chatRoute=jsx.jsx('CoreImage',nativeSource,'chat');const chat=render(chatRoute.type,chatRoute.props,'chat-image');
assert.equal(chat.type,'CoreImage');assert.equal(chat.props.src,nativeSource.src);assert.equal(chat.props.testID,nativeSource.testID);
assert.strictEqual(chat.props.style,nativeSource.style);
assert.equal(row().props.windowSize,3);assert.equal(row().props.initialNumToRender,7);
const cb=row().props.onViewableItemsChanged;library();g=grid();assert.strictEqual(row().props.onViewableItemsChanged,cb);
row().props.onLayout({nativeEvent:{layout:{width:390,height:260}}});row().props.onContentSizeChange(12000,260);
cb({viewableItems:[{},{}]});assert(observations.some(a=>a[0]===9&&a[3]===390));assert(observations.some(a=>a[0]===11&&a[3]===2));
'''
        ran=subprocess.run(['node','-e',script,str(ROOT/'src/rn/ProviderEmoteStrip.js')],capture_output=True,text=True)
        self.assertEqual(ran.returncode,0,ran.stderr)
