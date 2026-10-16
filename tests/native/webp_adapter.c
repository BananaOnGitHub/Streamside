/* Fake UIKit/ImageIO boundary; the complete production adapter is compiled. */
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <objc/runtime.h>
static id test_number(id,SEL,double);
#include "TASAnimatedImage.c"
struct Fake {
    const char *name;Class cls;unsigned char *bytes;U length,width,height,index;
    id value,keys[300],values[300];unsigned count;Animation *context;double seconds;
    int refs;
};
static struct Fake objects[4096],classes[32];static unsigned used,class_count;
static BOOL is_main,enabled=YES,broken_source,bad_canvas,decode_fails;
static BOOL abi_ready;static unsigned hook_installs;
static unsigned source_creates,decoded,source_releases,original_calls,callback_calls,native_buffers,limited_buffers,legacy_calls;
static id received_error,received_value,received_response,expected_request,expected_progress;
static void *queued,*pending_reply;static int block_allocs,block_frees;
static struct Fake class_animation={.name="StreamsideAnimatedWebP"};
static struct Fake source_fixture={.name="ImageIO",.width=4,.height=3};
static id fresh(const char *name){assert(used<4096);id o=&objects[used++];o->name=name;o->refs=1;o->cls=objc_getClass(name);return o;}
Class objc_getClass(const char *name){
    if(!strcmp(name,"StreamsideAnimatedWebP"))return &class_animation;
    for(unsigned i=0;i<class_count;i++)if(!strcmp(classes[i].name,name))return &classes[i];
    assert(class_count<32);classes[class_count].name=name;return &classes[class_count++];
}
Class object_getClass(id o){return o?o->cls:nil;}
SEL sel_registerName(const char *s){return s;}
id objc_retain(id o){if(o)o->refs++;return o;}
void objc_release(id o){if(o){o->refs--;assert(o->refs>=0);}}
static BOOL equal(id a,id b){return a==b || (a && b && a->bytes && b->bytes && a->length==b->length && !memcmp(a->bytes,b->bytes,a->length));}
static id dispatch(id o,SEL sel,...){
    if(!o)return nil;va_list ap;va_start(ap,sel);id r=nil;
    if(!strcmp(sel,"isMainThread"))r=(id)(uintptr_t)is_main;
    else if(!strcmp(sel,"alloc")){r=fresh(o->name);r->cls=o;}
    else if(!strcmp(sel,"initWithCGImage:scale:orientation:")){id cg=va_arg(ap,id);o->width=cg->width;o->height=cg->height;r=o;}
    else if(!strcmp(sel,"new"))r=fresh(o->name);
    else if(!strcmp(sel,"length"))r=(id)(uintptr_t)o->length;
    else if(!strcmp(sel,"bytes"))r=(id)o->bytes;
    else if(!strcmp(sel,"copy"))r=objc_retain(o);
    else if(!strcmp(sel,"autorelease")){r=o;objc_release(o);}
    else if(!strcmp(sel,"objectForKey:")){id key=va_arg(ap,id);for(unsigned i=0;i<o->count;i++)if(equal(key,o->keys[i])){r=o->values[i];break;}}
    else if(!strcmp(sel,"setObject:forKey:cost:") || !strcmp(sel,"setObject:forKey:")){
        id v=va_arg(ap,id),k=va_arg(ap,id);assert(o->count<300);o->keys[o->count]=k;o->values[o->count++]=v;
    }
    else if(!strcmp(sel,"numberWithUnsignedInteger:")){r=fresh("NSNumber");r->index=va_arg(ap,U);}
    else if(!strcmp(sel,"imageWithCGImage:")){id cg=va_arg(ap,id);r=fresh("UIImage");r->width=cg->width;r->height=cg->height;}
    else if(!strcmp(sel,"addOperationWithBlock:")){assert(!queued);queued=_Block_copy(va_arg(ap,id));}
    else if(!strcmp(sel,"URL") || !strcmp(sel,"absoluteString"))r=o->value?:o;
    else if(!strcmp(sel,"UTF8String"))r=(id)o->name;
    else if(!strcmp(sel,"isKindOfClass:"))r=(id)(uintptr_t)(o->cls==va_arg(ap,Class));
    else if(!strcmp(sel,"animatedImage"))r=o->value;
    else if(!strcmp(sel,"setMaxBufferCount:")){assert(va_arg(ap,U)==4);limited_buffers++;}
    else {fprintf(stderr,"unexpected %s on %s\n",sel,o->name);assert(0);}
    va_end(ap);return r;
}
id (*objc_msgSend)(id,SEL,...)=dispatch;
static id test_number(id o,SEL cmd,double value){(void)o;(void)cmd;id n=fresh("NSNumber");n->seconds=value;return n;}

struct Block {void *isa;int flags,reserved;void (*invoke)(void *,...);struct Desc {uintptr_t reserved,size;void (*copy)(void *,void *);void (*dispose)(void *);} *desc;};
void *_NSConcreteStackBlock[32];
void *_Block_copy(const void *input){
    const struct Block *b=input;if(!b)return NULL;
    if(b->flags&(1<<28))return (void *)input;
    struct Block *copy=malloc(b->desc->size);memcpy(copy,b,b->desc->size);copy->flags|=1<<24;block_allocs++;
    if(b->flags&(1<<25))b->desc->copy(copy,(void *)b);return copy;
}
void _Block_release(const void *input){
    const struct Block *b=input;if(!b || !(b->flags&(1<<24)))return;
    if(b->flags&(1<<25))b->desc->dispose((void *)b);block_frees++;free((void *)b);
}
void _Block_object_assign(void *dst,const void *src,int flags){assert(flags==7);*(void **)dst=_Block_copy(src);}
void _Block_object_dispose(const void *src,int flags){assert(flags==7);_Block_release(src);}
static void invoke_job(void){struct Block *b=queued;queued=NULL;is_main=NO;b->invoke(b);_Block_release(b);is_main=YES;}
static const void *fake_source(id data,id options){assert(data && options);source_creates++;return broken_source?NULL:&source_fixture;}
static U fake_count(const void *s){assert(s==&source_fixture);return 3;}
static const void *fake_frame(const void *s,U index,id options){assert(s==&source_fixture && options);decoded++;if(decode_fails)return NULL;id cg=fresh("CGImage");cg->width=bad_canvas?2:4;cg->height=3;cg->index=index;return cg;}
static U fake_width(const void *p){return ((id)p)->width;}
static U fake_height(const void *p){return ((id)p)->height;}
static void fake_release(const void *p){assert(p);source_releases++;}
static const void *fake_color(void){return &source_fixture;}
static const void *fake_bitmap(void *data,U w,U h,U depth,U stride,const void *color,unsigned flags){
    assert(!data && depth==8 && stride==w*4 && color && flags==16385);id ctx=fresh("CGContext");ctx->width=w;ctx->height=h;return ctx;
}
static void fake_draw(const void *ctx,Rect rect,const void *image){assert(!is_main && ctx && image && rect.size.width==4 && rect.size.height==3);}
static const void *fake_bitmap_image(const void *ctx){return ctx;}
static void original_dealloc(id o,SEL cmd){(void)o;(void)cmd;}
bool tas_emotes_enabled_this_launch(void){return enabled;}
id tas_emotes_rewrite_request_copy(id request){
    if(strcmp(request->name,"synthetic-provider"))return nil;
    return fresh("https://cdn.7tv.app/emote/fixture/2x.webp");
}
bool tas_emotes_is_provider_image_url(const char *s){return s && strstr(s,"https://cdn.7tv.app/emote/")==s;}
static struct Desc cancel_desc={0,sizeof(struct Block),NULL,NULL};
static struct Block cancel_block={_NSConcreteStackBlock,1<<28,0,NULL,&cancel_desc};
static id original_load(id self,SEL cmd,id request,id progress,id completion){
    (void)self;(void)cmd;assert(request==expected_request && progress==expected_progress);original_calls++;
    pending_reply=_Block_copy(completion);return (id)&cancel_block;
}
static void callback(void *b,id e,id v,id r){(void)b;callback_calls++;received_error=e;received_value=v;received_response=r;}
static struct Desc callback_desc={0,sizeof(struct Block),NULL,NULL};
static struct Block callback_block={_NSConcreteStackBlock,0,0,(void (*)(void *,...))callback,&callback_desc};
static void deliver(id e,id v,id r){struct Block *b=pending_reply;pending_reply=NULL;b->invoke(b,e,v,r);_Block_release(b);}
static void original_buffer(id o,SEL cmd){(void)o;(void)cmd;native_buffers++;}
static id original_legacy(id o,SEL cmd,id data){(void)cmd;(void)data;legacy_calls++;return o;}
Class objc_allocateClassPair(Class c,const char *n,size_t z){(void)c;(void)n;(void)z;return nil;}
BOOL class_addIvar(Class c,const char *n,size_t z,uint8_t a,const char *t){(void)c;(void)n;(void)z;(void)a;(void)t;return NO;}
BOOL class_addMethod(Class c,SEL s,IMP i,const char *t){(void)c;(void)s;(void)i;(void)t;return NO;}
void objc_registerClassPair(Class c){(void)c;}
void objc_disposeClassPair(Class c){(void)c;}
Ivar class_getInstanceVariable(Class c,const char *s){(void)c;(void)s;return NULL;}
ptrdiff_t ivar_getOffset(Ivar v){(void)v;return 0;}
IMP class_getMethodImplementation(Class c,SEL s){(void)c;(void)s;return NULL;}
struct MockMethod {const char *encoding;IMP original;};
static struct MockMethod load_method={"@?40@0:8@16@?24@?32",(IMP)original_load},buffer_method={"v16@0:8",(IMP)original_buffer},getter_method={"@16@0:8",NULL},setter_method={"v24@0:8Q16",NULL},legacy_method={"@24@0:8@16",(IMP)original_legacy};
Method class_getInstanceMethod(Class c,SEL s){
 if(c==objc_getClass("FLAnimatedImage") && !strcmp(s,"initWithAnimatedGIFData:"))return &legacy_method;
 if(c==objc_getClass("RCTImageLoader") && !strcmp(s,"_loadURLRequest:progressBlock:completionBlock:"))return &load_method;
 if(c==objc_getClass("RCTUIImageViewAnimated")){
  if(!strcmp(s,"calculateMaxBufferCount"))return &buffer_method;
  if(!strcmp(s,"setMaxBufferCount:"))return &setter_method;
  if(!strcmp(s,"animatedImage"))return &getter_method;
 }
 return NULL;
}
IMP method_getImplementation(Method m){return ((struct MockMethod *)m)->original;}
const char *method_getTypeEncoding(Method m){return abi_ready?((struct MockMethod *)m)->encoding:"unsupported";}
IMP method_setImplementation(Method m,IMP i){(void)m;assert(i);hook_installs++;return NULL;}

int main(void){
    animation_class=&class_animation;state_offset=offsetof(struct Fake,context);
    templates=fresh("NSCache");queue=fresh("NSOperationQueue");source_options=fresh("NSDictionary");
    color_create=fake_color;color_release=fake_release;bitmap_create=fake_bitmap;draw_image=fake_draw;bitmap_image=fake_bitmap_image;context_release=fake_release;
    source_create=fake_source;source_count=fake_count;source_image=fake_frame;cg_width=fake_width;cg_height=fake_height;cg_release=fake_release;cf_release=fake_release;super_dealloc=(IMP)original_dealloc;
    id encoded=fresh("NSData");encoded->bytes=fixture;encoded->length=sizeof(fixture);
    is_main=YES;assert(!tas_animated_image_create(encoded) && !decoded);
    is_main=NO;id image=tas_animated_image_create(encoded);assert(image && decoded==1 && source_creates==1);
    assert(frame_count(image,0)==3 && duration(image,0,1)==12.5 && duration(image,0,2)==0.6 && !duration(image,0,3));
    assert(state(image)->data==encoded && zero(image,0)==0 && bytes_per_frame(image,0)==48);
    is_main=YES;id same=tas_animated_image_create(encoded);assert(same==image && source_creates==1);objc_release(same);
    /* Legacy GIF-named factory substitutes only a provider-admitted template.
     * The Swift Data bridge can hand back a new, equal NSData object. */
    legacy_original=(IMP)original_legacy;id allocation=fresh("FLAnimatedImage");
    assert(legacy_image_init(allocation,0,encoded)==allocation && legacy_calls==1 && allocation->refs==1);
    tas_animated_image_prepare(encoded);assert(state(image)->legacy_admitted);
    id bridged=fresh("NSData");bridged->bytes=fixture;bridged->length=sizeof(fixture);
    assert(legacy_image_init(allocation,0,bridged)==image && !allocation->refs && legacy_calls==1);objc_release(image);
    allocation=fresh("FLAnimatedImage");enabled=NO;
    assert(legacy_image_init(allocation,0,bridged)==allocation && legacy_calls==2);enabled=YES;
    id gif=fresh("NSData");gif->bytes=(unsigned char *)"GIF89a";gif->length=6;
    assert(legacy_image_init(allocation,0,gif)==allocation && legacy_calls==3);
    unsigned cached=templates->count;templates->count=0;
    assert(legacy_image_init(allocation,0,bridged)==allocation && legacy_calls==4);templates->count=cached;
    assert(frame_at(image,0,0)==state(image)->poster && !queued);
    assert(!frame_at(image,0,1) && queued && jobs==1);assert(!frame_at(image,0,1) && jobs==1);
    invoke_job();assert(jobs==0 && !state(image)->pending && decoded==2);
    assert(frame_at(image,0,1) && decoded==2);
    assert(!frame_at(image,0,999) && !queued);
    is_main=NO;bad_canvas=YES;assert(!frame_at(image,0,2));unsigned before=decoded;assert(!frame_at(image,0,2) && decoded==before);state(image)->retry_after=0;bad_canvas=NO;decode_fails=YES;assert(!frame_at(image,0,2));state(image)->retry_after=0;decode_fails=NO;
    assert(frame_at(image,0,2));
    /* Our frame cache stays hard bounded even with many active animation objects. */
    Animation big={.info={.width=512,.height=512}};id pixel=fresh("UIImage");
    for(unsigned a=0;a<40;a++){
        big.identity=100+a;for(U index=0;index<8;index++)store_frame(&big,index,pixel);
        unsigned own=0;for(unsigned i=0;i<FRAME_SLOTS;i++)own+=frames[i].image && frames[i].identity==big.identity;
        assert(own==4 && frame_bytes<=FRAME_BYTES);
    }
    /* Native HTTP request/progress/cancellation ownership and response identity. */
    load_original=(IMP)original_load;buffer_original=(IMP)original_buffer;expected_progress=fresh("progress");id response=fresh("response"),error=fresh("error");
    expected_request=fresh("synthetic-provider");
    assert(load_provider(nil,0,expected_request,expected_progress,(id)&callback_block)==(id)&cancel_block);
    deliver(nil,encoded,response);assert(received_value==image && received_response==response && !received_error);
    expected_request=fresh("https://cdn.7tv.app/emote/fixture/2x.webp");
    load_provider(nil,0,expected_request,expected_progress,(id)&callback_block);deliver(error,encoded,response);assert(received_value==encoded && received_error==error);
    expected_request=fresh("https://static-cdn.jtvnw.net/native");
    load_provider(nil,0,expected_request,expected_progress,(id)&callback_block);deliver(nil,encoded,response);assert(received_value==encoded);
    enabled=NO;expected_request=fresh("synthetic-provider");load_provider(nil,0,expected_request,expected_progress,(id)&callback_block);deliver(nil,encoded,response);assert(received_value==encoded);enabled=YES;
    load_provider(nil,0,expected_request,expected_progress,(id)&callback_block);_Block_release(pending_reply);pending_reply=NULL;assert(callback_calls==4);
    assert(block_allocs==block_frees);
    buffer_original=(IMP)original_buffer;id view=fresh("RCTUIImageViewAnimated");view->value=image;provider_buffer_limit(view,0);assert(limited_buffers==1 && !native_buffers);
    view->value=state(image)->poster;provider_buffer_limit(view,0);assert(native_buffers==1);
    load_original=NULL;buffer_original=NULL;legacy_original=NULL;tas_animated_image_retry_hooks();assert(!load_original && !buffer_original && !legacy_original && !hook_installs);
    abi_ready=YES;tas_animated_image_retry_hooks();assert(load_original==(IMP)original_load && buffer_original==(IMP)original_buffer && legacy_original==(IMP)original_legacy && hook_installs==3);
    tas_animated_image_retry_hooks();assert(hook_installs==3);
    /* Source and all retained state are released without queued jobs. */
    animation_dealloc(image,0);image->context=NULL;
    assert(source_releases && !jobs);
    puts("WebP factory, async frame misses, cache bounds, provider scope, callback/cancel ownership and native fallback passed");
    return 0;
}
