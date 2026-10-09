#include "TASImageDemand.h"
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
#include <objc/runtime.h>
#include <objc/message.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdlib.h>
extern id objc_retain(id);
extern void objc_release(id);
extern id objc_getAssociatedObject(id,const void *);
extern void objc_setAssociatedObject(id,const void *,id,uintptr_t);
enum { ASSETS=2048, VIEWS=4096, URL_BUDGET=2048, HEADER_BUDGET=16384 };
typedef struct {uint64_t x,y;} Key;
typedef struct {Key key; unsigned mask,mounted,stages,library_live; uint64_t requests,headers;} Asset;
typedef struct {Key key;uint64_t headers;bool occupied;} Request;
typedef struct {void *view; unsigned scope; bool window;} View;
static Asset assets[ASSETS];
static Request requests[ASSETS];
static View views[VIEWS];
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t install_lock=PTHREAD_MUTEX_INITIALIZER;
static uint64_t events[TAS_DEMAND_SCOPES][TAS_DEMAND_EVENTS],live[TAS_DEMAND_SCOPES],peak[TAS_DEMAND_SCOPES];
static uint64_t unique_assets,first_asset_requests,repeated_assets,unique_requests,repeated_requests,variants,evictions,refusals,source_masks[128];
static unsigned next_asset;
static unsigned next_request;
static uint64_t native_live[TAS_DEMAND_SCOPES],native_window[TAS_DEMAND_SCOPES],native_peak[TAS_DEMAND_SCOPES];
static uint64_t native_samples,native_refused,native_recycles;
static uint64_t metrics_calls,metrics_missing,metrics_truncated,fetches[4],fetch_time[4][4],geometry[4][2];
static IMP move_original,layout_original,recycle_original,dealloc_original;
static char scope_key;
/* Seven aggregate stages, no per-open or per-image histories. The JS sequence
 * is only a monotonic ephemeral ordering guard; never reported. */
typedef struct {
    uint64_t mount,unmount,peak,starts,loads,errors,unique,remount,recent_mount,recent_unmount,recent_peak;
    uint64_t samples,range,mask,items,visible,content,zero_zoom,missing_zoom,nested,disabled;
    uint64_t active,queued,consumers,cancelled;
    uint64_t pending,initial,window,batch,nonzero_offset,duplicates;
} Stage;
static Stage stages[7];
static unsigned stage=4,transport_active,transport_queued,transport_consumers;
static uint64_t epoch,opens,late_stage,stable_timeouts,window_refused,transport_cancelled;
static bool stage_current=true;
/* Fixed numeric calculation snapshots; never retain the input JSON, identifiers,
 * URLs or a per-image history. First two owned list instances, sixteen rows each. */
enum { CALC_SLOTS=2, CALC_ROWS=16, CALC_VALUES=41 };
typedef struct { double value[CALC_VALUES]; unsigned stage; } Calculation;
static Calculation calculations[CALC_SLOTS][CALC_ROWS];
static unsigned calculation_count[CALC_SLOTS];
static uint64_t calculation_status[8],calculation_calls,calculation_records,calculation_refused;
static bool calculation_values(const char *text,double out[CALC_VALUES]) {
    if(!text || strnlen(text,4097)>4096 || *text++!='[')return false;
    for(unsigned i=0;i<CALC_VALUES;i++) {
        /* Numeric JSON only. No strings, whitespace, NaN/Infinity or suffixes. */
        if(!((*text>='0' && *text<='9') || *text=='-'))return false;
        char *end;out[i]=strtod(text,&end);
        if(end==text || !isfinite(out[i]) || fabs(out[i])>=10000000)return false;
        for(const char *p=text;p<end;p++)if(!((*p>='0' && *p<='9') || *p=='-' || *p=='+' || *p=='.' || *p=='e' || *p=='E'))return false;
        if(*end!=(i+1==CALC_VALUES?']':','))return false;
        text=end+1;
    }
    return !*text;
}
static id m0(id o,const char *s){return ((id (*)(id,SEL))objc_msgSend)(o,sel_registerName(s));}
static id m1(id o,const char *s,id a){return ((id (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),a);}
static unsigned long integer(id o,const char *s){return ((unsigned long (*)(id,SEL))objc_msgSend)(o,sel_registerName(s));}
static const char *string(id o){return (const char *)m0(o,"UTF8String");}
static bool responds(id o,const char *s){return o && ((BOOL (*)(id,SEL,SEL))objc_msgSend)(o,sel_registerName("respondsToSelector:"),sel_registerName(s));}
static unsigned bucket(double seconds){return seconds<=.25?0:seconds<=1?1:seconds<=5?2:3;}
static Key key(const char *s) {
    Key k={1469598103934665603ULL,7809847782465536322ULL};
    if(!s || !*s || strnlen(s,URL_BUDGET+1)>URL_BUDGET)return (Key){0};
    for(;*s;s++){k.x=(k.x^(unsigned char)*s)*1099511628211ULL;k.y=(k.y+(unsigned char)*s+1)*14029467366897019727ULL;}
    return k;
}
static bool equal(Key a,Key b){return a.x==b.x && a.y==b.y;}
/* Fixed fingerprint table, not a launch-wide exact set. Eviction starts a new
 * observation interval; fingerprints never leave RAM or enter any report. */
static Asset *asset_locked(Key k) {
    if(!k.x){refusals++;return NULL;}
    for(unsigned i=0;i<ASSETS;i++)if(equal(assets[i].key,k))return &assets[i];
    Asset *a=&assets[next_asset++%ASSETS];if(a->key.x)evictions++;
    memset(a,0,sizeof(*a));a->key=k;unique_assets++;return a;
}
void tas_demand_event(unsigned event,unsigned scope,const char *url,double a,double b) {
    if(event>=TAS_DEMAND_EVENTS || scope>=TAS_DEMAND_SCOPES || !isfinite(a) || !isfinite(b))return;
    if(scope==0 && event>=27) {
        double values[CALC_VALUES];bool valid=event!=27 || calculation_values(url,values);
        pthread_mutex_lock(&lock);
        if(event==27) {
            if(!valid || !stage_current || a<1 || a>CALC_SLOTS || floor(a)!=a)calculation_refused++;
            else {unsigned slot=(unsigned)a-1,n=calculation_count[slot];
                if(n<CALC_ROWS){memcpy(calculations[slot][n].value,values,sizeof(values));calculations[slot][n].stage=stage;calculation_count[slot]++;}
                else calculation_refused++;
            }
        } else if(event==28 && a>=0 && a<=128 && b>=0 && b<=16) {calculation_calls+=(uint64_t)a;calculation_records+=(uint64_t)b;}
        else if(event==29 && a>=1 && a<8 && floor(a)==a)calculation_status[(unsigned)a]++;
        pthread_mutex_unlock(&lock);return;
    }
    Key k=key(url);pthread_mutex_lock(&lock);events[scope][event]++;
    if(event==22 && scope==0 && b>=1 && b<=9007199254740991.0 && a>=0 && a<=5 && floor(a)==a && floor(b)==b) {
        stage_current=(uint64_t)b>=epoch;
        if(!stage_current)late_stage++;
        else {
            if((uint64_t)b>epoch){epoch=(uint64_t)b;opens++;}
            stage=(unsigned)a; if(stage==0 && opens>1)stage=5;else if(stage==5)stage=6;
            Stage *s=&stages[stage];
            if(live[1]>s->peak)s->peak=live[1];if(live[2]>s->recent_peak)s->recent_peak=live[2];
            if(transport_active>s->active)s->active=transport_active;
            if(transport_queued>s->queued)s->queued=transport_queued;
            if(transport_consumers>s->consumers)s->consumers=transport_consumers;
        }
    }
    if(event==1){if(++live[scope]>peak[scope])peak[scope]=live[scope];}
    if(event==2 && live[scope])live[scope]--;
    if(scope==2 && stage_current){Stage *s=&stages[stage];if(event==1)s->recent_mount++;if(event==2)s->recent_unmount++;if(live[2]>s->recent_peak)s->recent_peak=live[2];}
    if(scope==1 && stage_current) {
        Stage *s=&stages[stage];
        if(event==1) {
            s->mount++; if(live[1]>s->peak)s->peak=live[1];
            Asset *v=asset_locked(k);
            if(v){if(v->library_live)s->duplicates++;else if(v->mounted&2)s->remount++;v->mounted|=2;v->library_live++;
                if(!(v->stages&(1U<<stage))){s->unique++;v->stages|=1U<<stage;}}
        }
        if(event==2)s->unmount++;
        if(event==5)s->starts++;
        if(event==6)s->loads++;
        if(event==7)s->errors++;
    }
    if(event==2 && scope==1 && k.x)for(unsigned i=0;i<ASSETS;i++)if(equal(assets[i].key,k)){if(assets[i].library_live)assets[i].library_live--;break;}
    if(event==3 && url){Asset *v=asset_locked(k);if(v){v->mask|=1U<<scope;
        if(scope==1 && stage_current && !(v->stages&(1U<<stage))){stages[stage].unique++;v->stages|=1U<<stage;}}}
    /* Geometry is aggregate maxima only; no scroll coordinates retained. */
    if(scope==0 && (event==8 || event==9 || event==10 || event==11)) {
        uint64_t x=a>0 && a<10000000 ? (uint64_t)a : 0,y=b>0 && b<10000000 ? (uint64_t)b : 0;
        if(x>geometry[event-8][0])geometry[event-8][0]=x;
        if(y>geometry[event-8][1])geometry[event-8][1]=y;
    }
    if(event==6)events[scope][bucket(a/1000.0)+8]++;
    if(scope==0 && event>=16 && event<=20) {
        Stage *s=&stages[stage];
        if(event==16){uint64_t n=a>=0 && b>=a && b<20000 ? (uint64_t)(b-a+1):0;if(n>s->range)s->range=n;s->samples++;}
        if(event==17){if(a>0 && a<20000 && a>s->mask)s->mask=(uint64_t)a;if(b>0 && b<20000 && b>s->items)s->items=(uint64_t)b;}
        if(event==18){if(a>0 && a<10000000 && a>s->visible)s->visible=(uint64_t)a;if(b>0 && b<10000000 && b>s->content)s->content=(uint64_t)b;}
        if(event==19){s->zero_zoom+=a==0;s->missing_zoom+=a<0;if(b>0 && b<20000 && b>s->pending)s->pending=(uint64_t)b;}
        if(event==20){s->nested+=a!=0;s->disabled+=b!=0;}
    }
    if(scope==0 && event==21){if(a>0 && a<20000 && a>stages[stage].initial)stages[stage].initial=(uint64_t)a;if(b>0 && b<20000 && b>stages[stage].window)stages[stage].window=(uint64_t)b;}
    if(scope==0 && event==24){if(a>0 && a<20000 && a>stages[stage].batch)stages[stage].batch=(uint64_t)a;stages[stage].nonzero_offset+=b!=0;}
    if(scope==0 && event==25)window_refused++;
    if(scope==0 && event==26)stable_timeouts++;
    pthread_mutex_unlock(&lock);
}
void tas_demand_transport(unsigned active,unsigned queued,unsigned consumers,uint64_t cancelled) {
    pthread_mutex_lock(&lock);Stage *s=&stages[stage];
    transport_active=active;transport_queued=queued;transport_consumers=consumers;
    if(active>s->active)s->active=active;if(queued>s->queued)s->queued=queued;if(consumers>s->consumers)s->consumers=consumers;
    if(cancelled>=transport_cancelled)s->cancelled+=cancelled-transport_cancelled;
    transport_cancelled=cancelled;pthread_mutex_unlock(&lock);
}
/* Header values are inspected transiently and never copied. This is a bounded
 * order-independent signature, not a new request key or a dedup decision. */
void tas_demand_request(void *object,unsigned scope) {
    id request=(id)object;const char *url=string(m0(m0(request,"URL"),"absoluteString"));Key k=key(url);
    id headers=m0(request,"allHTTPHeaderFields"),keys=m0(headers,"allKeys");unsigned long n=integer(keys,"count");
    uint64_t signature=0;size_t bytes=0;bool valid=n<=32;
    for(unsigned long i=0;valid && i<n;i++) {
        id name=((id (*)(id,SEL,unsigned long))objc_msgSend)(keys,sel_registerName("objectAtIndex:"),i);
        id value=m1(headers,"objectForKey:",name);
        if(!responds(name,"UTF8String") || !responds(value,"UTF8String")){valid=false;break;}
        const char *x=string(name),*y=string(value);size_t nx=x?strnlen(x,URL_BUDGET+1):0,ny=y?strnlen(y,URL_BUDGET+1):0;
        bytes+=nx+ny;if(!nx || nx>URL_BUDGET || ny>URL_BUDGET || bytes>HEADER_BUDGET){valid=false;break;}
        Key hx=key(x),hy=key(y);signature+=(hx.x*1099511628211ULL)^hy.y;
    }
    pthread_mutex_lock(&lock);
    if(!valid){refusals++;pthread_mutex_unlock(&lock);return;}
    Asset *a=asset_locked(k);
    if(a){
        if(a->requests++)repeated_assets++;else first_asset_requests++;
        if(a->requests>1 && a->headers!=signature)variants++;
        a->headers=signature;
        bool found=false;
        for(unsigned i=0;i<ASSETS;i++)if(requests[i].occupied && equal(requests[i].key,k) && requests[i].headers==signature){found=true;break;}
        if(found)repeated_requests++;
        else {Request *r=&requests[next_request++%ASSETS];if(r->occupied)evictions++;*r=(Request){k,signature,true};unique_requests++;}
        unsigned mask=scope && scope<TAS_DEMAND_SCOPES ? 1U<<scope : a->mask;
        source_masks[mask & 127]++;
    }
    pthread_mutex_unlock(&lock);
}
void tas_demand_mark_url(void *url,unsigned scope){
    if(url && scope<TAS_DEMAND_SCOPES)objc_setAssociatedObject((id)url,&scope_key,
        ((id (*)(id,SEL,unsigned))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithUnsignedInt:"),scope),1);
}
unsigned tas_demand_url_scope(void *url){return (unsigned)integer(objc_getAssociatedObject((id)url,&scope_key),"unsignedIntValue");}
/* Observe Foundation's actual fetch classification. No speculative cache
 * lookup and no cache contents, addresses, request or response retained. */
static void metrics(id self,SEL cmd,id session,id task,id report) {
    (void)self;(void)cmd;(void)session;(void)task;
    id rows=m0(report,"transactionMetrics");unsigned long n=integer(rows,"count");
    pthread_mutex_lock(&lock);metrics_calls++;if(!n)metrics_missing++;if(n>16)metrics_truncated++;pthread_mutex_unlock(&lock);
    if(n>16)n=16;
    for(unsigned long i=0;i<n;i++) {
        id row=((id (*)(id,SEL,unsigned long))objc_msgSend)(rows,sel_registerName("objectAtIndex:"),i);
        unsigned type=(unsigned)integer(row,"resourceFetchType");if(type>3)type=0;
        id start=m0(row,"fetchStartDate"),end=m0(row,"responseEndDate");
        double elapsed=start && end ? ((double (*)(id,SEL,id))objc_msgSend)(end,sel_registerName("timeIntervalSinceDate:"),start):-1;
        pthread_mutex_lock(&lock);fetches[type]++;if(elapsed>=0 && isfinite(elapsed))fetch_time[type][bucket(elapsed)]++;
        pthread_mutex_unlock(&lock);
    }
}
void *tas_demand_delegate(void) {
    Class cls=objc_getClass("TASProviderDemandMetrics");
    if(!cls) {
        cls=objc_allocateClassPair(objc_getClass("NSObject"),"TASProviderDemandMetrics",0);
        if(!cls)return NULL;
        if(!class_addMethod(cls,sel_registerName("URLSession:task:didFinishCollectingMetrics:"),(IMP)metrics,"v40@0:8@16@24@32")){
            objc_disposeClassPair(cls);return NULL;
        }
        objc_registerClassPair(cls);
    }
    return m0((id)cls,"new");
}
static unsigned view_scope(id view) {
    const char *s=string(m0(view,"accessibilityIdentifier"));
    if(!s)return 0;
    if(!strcmp(s,"provider"))return 1;if(!strcmp(s,"recents"))return 2;
    if(!strcmp(s,"emote"))return 3;if(!strcmp(s,"EmoteCard"))return 4;
    if(!strncmp(s,"chat-emote-",11))return 5;
    return 0;
}
static void sample(id view,bool remove) {
    unsigned scope=remove?0:view_scope(view);bool window=!remove && m0(view,"window")!=nil;
    pthread_mutex_lock(&lock);native_samples++;
    unsigned empty=VIEWS,index=VIEWS;
    for(unsigned i=0;i<VIEWS;i++) {if(views[i].view==view){index=i;break;}if(!views[i].view && empty==VIEWS)empty=i;}
    if(index!=VIEWS){View *v=&views[index];native_live[v->scope]--;if(v->window)native_window[v->scope]--;memset(v,0,sizeof(*v));}
    else index=empty;
    if(!remove && index!=VIEWS) {
        views[index]=(View){view,scope,window};native_live[scope]++;if(window)native_window[scope]++;
        if(native_live[scope]>native_peak[scope])native_peak[scope]=native_live[scope];
    }else if(!remove)native_refused++;
    pthread_mutex_unlock(&lock);
}
static void move(id self,SEL sel){((void (*)(id,SEL))move_original)(self,sel);sample(self,false);}
static void layout(id self,SEL sel){((void (*)(id,SEL))layout_original)(self,sel);sample(self,false);}
static void recycle(id self,SEL sel){sample(self,true);pthread_mutex_lock(&lock);native_recycles++;pthread_mutex_unlock(&lock);((void (*)(id,SEL))recycle_original)(self,sel);}
static void dealloc_view(id self,SEL sel){sample(self,true);((void (*)(id,SEL))dealloc_original)(self,sel);}
static void hook(Class cls,const char *name,IMP replacement,IMP *original) {
    if(*original)return;
    Method method=cls?class_getInstanceMethod(cls,sel_registerName(name)):NULL;
    if(!method || strcmp(method_getTypeEncoding(method),"v16@0:8"))return;
    *original=method_getImplementation(method);
    if(!class_addMethod(cls,sel_registerName(name),replacement,"v16@0:8"))method_setImplementation(method,replacement);
}
void tas_demand_install(void) {
    pthread_mutex_lock(&install_lock);
    Class cls=objc_getClass("RCTImageComponentView");
    hook(cls,"didMoveToWindow",(IMP)move,&move_original);hook(cls,"layoutSubviews",(IMP)layout,&layout_original);
    hook(cls,"prepareForRecycle",(IMP)recycle,&recycle_original);hook(cls,"dealloc",(IMP)dealloc_view,&dealloc_original);
    pthread_mutex_unlock(&install_lock);
}
void tas_demand_status(char *buffer,size_t capacity) {
    size_t used=0;pthread_mutex_lock(&lock);
#define APPEND(...) do {if(used<capacity){int n=snprintf(buffer+used,capacity-used,__VA_ARGS__);if(n>0)used+=(size_t)n;}}while(0)
    APPEND("Provider demand trace (passive; this launch)\nNative Fabric hooks window/layout/recycle/dealloc: %s/%s/%s/%s\n",
        move_original?"installed":"missing",layout_original?"installed":"missing",recycle_original?"installed":"missing",dealloc_original?"installed":"missing");
    const char *stage_names[]={"open","idle","scroll","scroll-back","close","reopen","filter/scope"};
    APPEND("Library stages: openings=%llu; window refusals/settle timeouts/late stage signals=%llu/%llu/%llu\n",(unsigned long long)opens,(unsigned long long)window_refused,(unsigned long long)stable_timeouts,(unsigned long long)late_stage);
    for(unsigned i=0;i<7;i++){Stage *s=&stages[i];
        APPEND("%s mounts/unmounts/peak live/unique assets/remounts/load starts/loads/errors: %llu/%llu/%llu/%llu/%llu/%llu/%llu/%llu; RN samples/max range/mask/catalog columns/visible/content: %llu/%llu/%llu/%llu/%llu/%llu; zero/missing zoom/nested/disabled: %llu/%llu/%llu/%llu; temporal transport peak active/queued/consumers/cancellations: %llu/%llu/%llu/%llu\n",stage_names[i],
            (unsigned long long)s->mount,(unsigned long long)s->unmount,(unsigned long long)s->peak,(unsigned long long)s->unique,(unsigned long long)s->remount,(unsigned long long)s->starts,(unsigned long long)s->loads,(unsigned long long)s->errors,
            (unsigned long long)s->samples,(unsigned long long)s->range,(unsigned long long)s->mask,(unsigned long long)s->items,(unsigned long long)s->visible,(unsigned long long)s->content,
            (unsigned long long)s->zero_zoom,(unsigned long long)s->missing_zoom,(unsigned long long)s->nested,(unsigned long long)s->disabled,
            (unsigned long long)s->active,(unsigned long long)s->queued,(unsigned long long)s->consumers,(unsigned long long)s->cancelled);
        APPEND("  recents mounts/unmounts/peak: %llu/%llu/%llu; RN max initial/window/batch/pending/nonzero-offset samples: %llu/%llu/%llu/%llu/%llu; concurrent duplicate assets: %llu\n",
            (unsigned long long)s->recent_mount,(unsigned long long)s->recent_unmount,(unsigned long long)s->recent_peak,(unsigned long long)s->initial,(unsigned long long)s->window,(unsigned long long)s->batch,(unsigned long long)s->pending,(unsigned long long)s->nonzero_offset,(unsigned long long)s->duplicates);
    }
    APPEND("Stages aggregate repeated openings. Transport stages are temporal ALL-provider observations, not library caller attribution. Asset uniqueness/remounts are bounded fingerprint observations; evictions qualify them.\n");
    APPEND("RN startup calculation boundary (first two owned lists; max 16 snapshots/128 calls/5 seconds each)\nInstalled/restored/unsupported/call limit/time limit/snapshot limit/original throws: %llu/%llu/%llu/%llu/%llu/%llu/%llu; finished calls/snapshots: %llu/%llu; packet refusals: %llu\n",
        (unsigned long long)calculation_status[1],(unsigned long long)calculation_status[2],(unsigned long long)calculation_status[3],(unsigned long long)calculation_status[4],(unsigned long long)calculation_status[5],(unsigned long long)calculation_status[6],(unsigned long long)calculation_status[7],(unsigned long long)calculation_calls,(unsigned long long)calculation_records,(unsigned long long)calculation_refused);
    APPEND("Branch: 1=window algorithm 2=missing dimensions 3=pending update 4=virtualization disabled. Zoom: 0=zero 1=unit 2=positive non-unit 3=negative 4=missing 5=non-finite. Offset: sign only, 2=invalid. Velocity: direction above unit threshold, 2=invalid. Cell samples are the first four distinct indices actually queried, not extra RN queries; -1=missing/invalid.\n");
    for(unsigned s=0;s<CALC_SLOTS;s++)for(unsigned row=0;row<calculation_count[s];row++) {
        Calculation *c=&calculations[s][row];double *v=c->value;
        APPEND("calc list=%u transition=%u stage=%s branch=%.0f prev=%.0f..%.0f result=%.0f..%.0f viewport/content=%.2f/%.2f zoom(code/value)=%.0f/%.4f offset/velocity=%.0f/%.0f pending/catalog=%.0f/%.0f initial/batch/window=%.0f/%.0f/%.0f nested/layout=%.0f/%.0f queries/invalid/mismatch=%.0f/%.0f/%.0f\n",
            s+1,row+1,stage_names[c->stage],v[15],v[0],v[1],v[2],v[3],v[4],v[5],v[6],v[7],v[8],v[9],v[10],v[11],v[12],v[13],v[14],v[19],v[20],v[16],v[17],v[18]);
        APPEND(" cells index:length/offset=>owned length/offset:");
        for(unsigned i=0;i<4;i++){unsigned k=21+5*i;APPEND(" %.0f:%.2f/%.2f=>%.2f/%.2f",v[k],v[k+1],v[k+2],v[k+3],v[k+4]);}
        APPEND("\n");
    }
    const char *names[]={"unknown","library","recents","suggestions","info","chat","URL input"};
    for(unsigned s=1;s<6;s++) APPEND("%s JS mount/unmount/live/peak/commits/source changes/same source/load starts/loads/errors: %llu/%llu/%llu/%llu/%llu/%llu/%llu/%llu/%llu/%llu\n",
        names[s],(unsigned long long)events[s][1],(unsigned long long)events[s][2],(unsigned long long)live[s],(unsigned long long)peak[s],
        (unsigned long long)events[s][0],(unsigned long long)events[s][3],(unsigned long long)events[s][4],(unsigned long long)events[s][5],(unsigned long long)events[s][6],(unsigned long long)events[s][7]);
    for(unsigned s=0;s<6;s++)APPEND("%s observed native views live/window/peak: %llu/%llu/%llu\n",names[s],(unsigned long long)native_live[s],(unsigned long long)native_window[s],(unsigned long long)native_peak[s]);
    for(unsigned s=1;s<6;s++)APPEND("%s source-to-onLoad <=250ms/<=1s/<=5s/>5s; unmatched callbacks: %llu/%llu/%llu/%llu; %llu\n",names[s],(unsigned long long)events[s][8],(unsigned long long)events[s][9],(unsigned long long)events[s][10],(unsigned long long)events[s][11],(unsigned long long)events[s][14]);
    APPEND("Library outer/inner layout/content/viewable callbacks: %llu/%llu/%llu/%llu; max outer width/height: %llu/%llu; max inner width/height: %llu/%llu; max content width/height: %llu/%llu; max viewable columns: %llu\n",
        (unsigned long long)events[0][8],(unsigned long long)events[0][9],(unsigned long long)events[0][10],(unsigned long long)events[0][11],
        (unsigned long long)geometry[0][0],(unsigned long long)geometry[0][1],(unsigned long long)geometry[1][0],(unsigned long long)geometry[1][1],(unsigned long long)geometry[2][0],(unsigned long long)geometry[2][1],(unsigned long long)geometry[3][0]);
    APPEND("Bounded asset fingerprints inserted; protocol asset requests first/repeat; URL+header requests first/repeat/header changes: %llu; %llu/%llu; %llu/%llu/%llu\nTable evictions/probe refusals/native refusals/recycles: %llu/%llu/%llu/%llu\n",
        (unsigned long long)unique_assets,(unsigned long long)first_asset_requests,(unsigned long long)repeated_assets,(unsigned long long)unique_requests,(unsigned long long)repeated_requests,(unsigned long long)variants,
        (unsigned long long)evictions,(unsigned long long)refusals,(unsigned long long)native_refused,(unsigned long long)native_recycles);
    for(unsigned s=0;s<7;s++)APPEND("Protocol asset correlation %s: %llu\n",s==5?"native redirect (not exclusively chat)":names[s],(unsigned long long)source_masks[s?1U<<s:0]);
    uint64_t multi=0;for(unsigned i=1;i<128;i++)if(i&(i-1))multi+=source_masks[i];
    APPEND("Protocol asset correlation multiple scopes: %llu (correlation is not caller proof)\nNative samples: %llu; Foundation metrics callbacks/empty/truncated: %llu/%llu/%llu; transactions unknown/network/push/local-cache: %llu/%llu/%llu/%llu\n",
        (unsigned long long)multi,(unsigned long long)native_samples,(unsigned long long)metrics_calls,(unsigned long long)metrics_missing,(unsigned long long)metrics_truncated,(unsigned long long)fetches[0],(unsigned long long)fetches[1],(unsigned long long)fetches[2],(unsigned long long)fetches[3]);
    APPEND("Foundation local-cache fetch <=250ms/<=1s/<=5s/>5s: %llu/%llu/%llu/%llu\nJS commits are not native mounts; native window membership is not viewport visibility. Fingerprint table: 2048; native observations: 4096. No asset values or fingerprints reported.\n",
        (unsigned long long)fetch_time[3][0],(unsigned long long)fetch_time[3][1],(unsigned long long)fetch_time[3][2],(unsigned long long)fetch_time[3][3]);
#undef APPEND
    pthread_mutex_unlock(&lock);
}
#endif
