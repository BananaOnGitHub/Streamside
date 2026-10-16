/* Provider WebP bridge. Encoded HTTP caching, requests and cancellation remain
 * owned by Twitch/Streamside. Only an admitted provider response is replaced. */
#include "TASAnimatedImage.h"
#include "TASWebPModel.h"
#include "TASEmotes.h"
#include <objc/runtime.h>
#include <objc/message.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>

typedef unsigned long U;
typedef struct { double x,y; } Point;
typedef struct { double width,height; } Size;
typedef struct { Point origin;Size size; } Rect;
extern id objc_retain(id);
extern void objc_release(id);
extern void *_Block_copy(const void *);
extern void _Block_release(const void *);
extern void *_NSConcreteStackBlock[];
static id m0(id o,const char *s){return ((id (*)(id,SEL))objc_msgSend)(o,sel_registerName(s));}
static id m1(id o,const char *s,id v){return ((id (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),v);}
static void v1(id o,const char *s,id v){((void (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),v);}
static U integer(id o,const char *s){return ((U (*)(id,SEL))objc_msgSend)(o,sel_registerName(s));}
static BOOL main_thread(void){return ((BOOL (*)(id,SEL))objc_msgSend)((id)objc_getClass("NSThread"),sel_registerName("isMainThread"));}
static BOOL kind(id o,const char *name){Class c=objc_getClass(name);return o && c && ((BOOL (*)(id,SEL,Class))objc_msgSend)(o,sel_registerName("isKindOfClass:"),c);}

typedef struct {
    TASWebPInfo info;
    id data,poster,delays;
    const void *source;
    uint64_t identity;
    BOOL legacy_admitted;
    BOOL pending;
    U failed_index;uint64_t retry_after;
} Animation;
typedef struct { uint64_t identity,age;U index,cost;id image; } CachedFrame;
/* Hard limits for our decoded-frame retention. UIKit/RN may independently own
 * displayed images. ImageIO's private working memory is not this cache. */
enum { FRAME_SLOTS=256, FRAME_BYTES=32*1024*1024, FRAMES_PER_ASSET=4, JOBS=64 };
static CachedFrame frames[FRAME_SLOTS];
static U frame_bytes,jobs;
static uint64_t serial,age,created,refused,decoded_frames,frame_failures;
static pthread_mutex_t cache_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t init_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t decode_lock=PTHREAD_MUTEX_INITIALIZER;
static Class animation_class;
static ptrdiff_t state_offset;
static IMP super_dealloc,load_original,buffer_original,legacy_original;
static id templates,queue,source_options;
static const void *(*source_create)(id,id);
static U (*source_count)(const void *);
static const void *(*source_image)(const void *,U,id);
static U (*cg_width)(const void *),(*cg_height)(const void *);
static void (*cf_release)(const void *),(*cg_release)(const void *);
static const void *(*color_create)(void);
static const void *(*bitmap_image)(const void *);
static void (*color_release)(const void *),(*context_release)(const void *);
static const void *(*bitmap_create)(void *,U,U,U,U,const void *,unsigned);
static void (*draw_image)(const void *,Rect,const void *);
static Animation *state(id o){Animation *s=NULL;if(o && state_offset)memcpy(&s,(char *)o+state_offset,sizeof(s));return s;}
static void forget_frame(unsigned slot){id image=frames[slot].image;frame_bytes-=frames[slot].cost;memset(&frames[slot],0,sizeof(frames[slot]));objc_release(image);}
static id cached_frame(uint64_t identity,U index){
    id result=nil;pthread_mutex_lock(&cache_lock);
    for(unsigned i=0;i<FRAME_SLOTS;i++)if(frames[i].image && frames[i].identity==identity && frames[i].index==index){
        frames[i].age=++age;result=objc_retain(frames[i].image);break;
    }
    pthread_mutex_unlock(&cache_lock);return result;
}
static void store_frame(Animation *s,U index,id image){
    U cost=(U)s->info.width*s->info.height*4;
    pthread_mutex_lock(&cache_lock);unsigned slot=FRAME_SLOTS,owned=0,oldest=FRAME_SLOTS;
    for(unsigned i=0;i<FRAME_SLOTS;i++) {
        if(!frames[i].image){slot=i;continue;}
        if(frames[i].identity==s->identity){
            if(frames[i].index==index){pthread_mutex_unlock(&cache_lock);return;}
            owned++;if(oldest==FRAME_SLOTS || frames[i].age<frames[oldest].age)oldest=i;
        }
    }
    if(owned>=FRAMES_PER_ASSET){forget_frame(oldest);slot=oldest;}
    while(slot==FRAME_SLOTS || frame_bytes+cost>FRAME_BYTES){
        unsigned victim=FRAME_SLOTS;
        for(unsigned i=0;i<FRAME_SLOTS;i++)if(frames[i].image && (victim==FRAME_SLOTS || frames[i].age<frames[victim].age))victim=i;
        if(victim==FRAME_SLOTS)break;
        forget_frame(victim);slot=victim;
    }
    if(slot<FRAME_SLOTS){frames[slot]=(CachedFrame){s->identity,++age,index,cost,objc_retain(image)};frame_bytes+=cost;}
    pthread_mutex_unlock(&cache_lock);
}
static const void *render_frame(const void *source,U index,const TASWebPInfo *info){
    const void *cg=source_image(source,index,source_options);
    if(!cg)return NULL;
    const void *output=NULL;
    if(cg_width(cg)==info->width && cg_height(cg)==info->height){
        const void *color=color_create();
        const void *context=color?bitmap_create(NULL,info->width,info->height,8,(U)info->width*4,color,16385):NULL;
        if(context){
            /* Materialize RGBA pixels here on the decode worker. A UIImage
             * around a lazy CGImage alone can defer decompression to display. */
            draw_image(context,(Rect){{0,0},{info->width,info->height}},cg);
            output=bitmap_image(context);context_release(context);
        }
        if(color)color_release(color);
    }
    cg_release(cg);return output;
}
static uint64_t monotonic_millis(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;}
static BOOL may_retry(Animation *s,U index){
    pthread_mutex_lock(&cache_lock);BOOL ready=s->failed_index!=index || !s->retry_after || monotonic_millis()>=s->retry_after;pthread_mutex_unlock(&cache_lock);return ready;
}
static id decode_frame(id self,U index){
    Animation *s=state(self);if(!s || index>=s->info.count)return nil;
    id image=cached_frame(s->identity,index);if(image)return image;
    /* Only background callers enter this lock; main-thread misses are queued.
     * Serialized ImageIO access also bounds concurrent decoder working sets. */
    pthread_mutex_lock(&decode_lock);image=cached_frame(s->identity,index);
    if(!image && may_retry(s,index)){
        const void *cg=render_frame(s->source,index,&s->info);
        if(cg && cg_width(cg)==s->info.width && cg_height(cg)==s->info.height)
            image=objc_retain(m1((id)objc_getClass("UIImage"),"imageWithCGImage:",(id)cg));
        if(cg)cg_release(cg);
        if(image){store_frame(s,index,image);__atomic_add_fetch(&decoded_frames,1,__ATOMIC_RELAXED);}
        else {
            __atomic_add_fetch(&frame_failures,1,__ATOMIC_RELAXED);
            pthread_mutex_lock(&cache_lock);s->failed_index=index;s->retry_after=monotonic_millis()+1000;pthread_mutex_unlock(&cache_lock);
        }
    }
    pthread_mutex_unlock(&decode_lock);return image;
}
static id frame_at(id self,SEL cmd,U index){
    (void)cmd;Animation *s=state(self);if(!s || index>=s->info.count)return nil;
    if(index==0)return s->poster;
    id image=cached_frame(s->identity,index);
    if(image)return m0(image,"autorelease");
    if(!may_retry(s,index))return nil;
    if(!main_thread())return m0(decode_frame(self,index),"autorelease");
    pthread_mutex_lock(&cache_lock);BOOL schedule=!s->pending && jobs<JOBS;
    if(schedule){s->pending=YES;jobs++;}pthread_mutex_unlock(&cache_lock);
    if(schedule){
        id held=objc_retain(self);
        v1(queue,"addOperationWithBlock:",(id)^{
            id decoded=decode_frame(held,index);objc_release(decoded);
            pthread_mutex_lock(&cache_lock);state(held)->pending=NO;jobs--;pthread_mutex_unlock(&cache_lock);
            objc_release(held);
        });
    }
    return nil;
}
static U frame_count(id self,SEL cmd){(void)cmd;Animation *s=state(self);return s?s->info.count:0;}
static U zero(id self,SEL cmd){(void)self;(void)cmd;return 0;}
static id poster(id self,SEL cmd){(void)cmd;Animation *s=state(self);return s?s->poster:nil;}
static id data(id self,SEL cmd){(void)cmd;Animation *s=state(self);return s?s->data:nil;}
static id delays(id self,SEL cmd){(void)cmd;Animation *s=state(self);return s?s->delays:nil;}
static double duration(id self,SEL cmd,U index){(void)cmd;Animation *s=state(self);return s && index<s->info.count?s->info.delay_ms[index]/1000.0:0;}
static U bytes_per_frame(id self,SEL cmd){(void)cmd;Animation *s=state(self);return s?(U)s->info.width*s->info.height*4:0;}
static void cache_limit(id self,SEL cmd,U count){(void)self;(void)cmd;(void)count;/* fixed global/per-asset limits */}
static void animation_dealloc(id self,SEL cmd){
    Animation *s=state(self);
    if(s){
        pthread_mutex_lock(&cache_lock);for(unsigned i=0;i<FRAME_SLOTS;i++)if(frames[i].image && frames[i].identity==s->identity)forget_frame(i);pthread_mutex_unlock(&cache_lock);
        cf_release(s->source);objc_release(s->poster);objc_release(s->data);objc_release(s->delays);free(s);
    }
    ((void (*)(id,SEL))super_dealloc)(self,cmd);
}
static BOOL initialize(void){
    pthread_mutex_lock(&init_lock);
    if(!animation_class){
        dlopen("/System/Library/Frameworks/ImageIO.framework/ImageIO",RTLD_LAZY);
        dlopen("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics",RTLD_LAZY);
        source_create=dlsym(RTLD_DEFAULT,"CGImageSourceCreateWithData");source_count=dlsym(RTLD_DEFAULT,"CGImageSourceGetCount");
        source_image=dlsym(RTLD_DEFAULT,"CGImageSourceCreateImageAtIndex");cg_width=dlsym(RTLD_DEFAULT,"CGImageGetWidth");cg_height=dlsym(RTLD_DEFAULT,"CGImageGetHeight");
        cg_release=dlsym(RTLD_DEFAULT,"CGImageRelease");cf_release=dlsym(RTLD_DEFAULT,"CFRelease");
        color_create=dlsym(RTLD_DEFAULT,"CGColorSpaceCreateDeviceRGB");color_release=dlsym(RTLD_DEFAULT,"CGColorSpaceRelease");
        bitmap_create=dlsym(RTLD_DEFAULT,"CGBitmapContextCreate");draw_image=dlsym(RTLD_DEFAULT,"CGContextDrawImage");
        bitmap_image=dlsym(RTLD_DEFAULT,"CGBitmapContextCreateImage");context_release=dlsym(RTLD_DEFAULT,"CGContextRelease");
        id *cache_key=dlsym(RTLD_DEFAULT,"kCGImageSourceShouldCache");
        Class parent=objc_getClass("UIImage");
        if(parent && source_create && source_count && source_image && cg_width && cg_height && cg_release && cf_release && cache_key && color_create && color_release && bitmap_create && draw_image && bitmap_image && context_release){
            Class cls=objc_allocateClassPair(parent,"StreamsideAnimatedWebP",0);
            if(cls && class_addIvar(cls,"_streamsideAnimation",sizeof(Animation *),3,"^v")){
#define METHOD(name,fn,encoding) class_addMethod(cls,sel_registerName(name),(IMP)fn,encoding)
                METHOD("frameCount",frame_count,"Q16@0:8");METHOD("animatedImageFrameCount",frame_count,"Q16@0:8");
                METHOD("loopCount",zero,"Q16@0:8");METHOD("animatedImageLoopCount",zero,"Q16@0:8");METHOD("posterImageFrameIndex",zero,"Q16@0:8");
                METHOD("posterImage",poster,"@16@0:8");METHOD("data",data,"@16@0:8");METHOD("delayTimesForIndexes",delays,"@16@0:8");
                METHOD("imageLazilyCachedAtIndex:",frame_at,"@24@0:8Q16");METHOD("animatedImageFrameAtIndex:",frame_at,"@24@0:8Q16");
                METHOD("animatedImageDurationAtIndex:",duration,"d24@0:8Q16");METHOD("animatedImageBytesPerFrame",bytes_per_frame,"Q16@0:8");
                METHOD("setFrameCacheSizeMax:",cache_limit,"v24@0:8Q16");METHOD("dealloc",animation_dealloc,"v16@0:8");
#undef METHOD
                objc_registerClassPair(cls);state_offset=ivar_getOffset(class_getInstanceVariable(cls,"_streamsideAnimation"));
                super_dealloc=class_getMethodImplementation(parent,sel_registerName("dealloc"));animation_class=cls;
                source_options=objc_retain(((id (*)(id,SEL,id,id))objc_msgSend)((id)objc_getClass("NSDictionary"),sel_registerName("dictionaryWithObject:forKey:"),
                    ((id (*)(id,SEL,BOOL))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithBool:"),NO),*cache_key));
                templates=m0((id)objc_getClass("NSCache"),"new");
                ((void (*)(id,SEL,U))objc_msgSend)(templates,sel_registerName("setTotalCostLimit:"),(U)16*1024*1024);
                ((void (*)(id,SEL,U))objc_msgSend)(templates,sel_registerName("setCountLimit:"),(U)128);
                queue=m0((id)objc_getClass("NSOperationQueue"),"new");
                ((void (*)(id,SEL,long))objc_msgSend)(queue,sel_registerName("setMaxConcurrentOperationCount:"),2L);
            }else if(cls)objc_disposeClassPair(cls);
        }
    }
    BOOL ready=animation_class && queue && templates && source_options;pthread_mutex_unlock(&init_lock);return ready;
}
id tas_animated_image_create(id encoded){
    if(!encoded || !initialize())return nil;
    U length=integer(encoded,"length");if(length<12 || length>TAS_WEBP_MAX_BYTES)return nil;
    const unsigned char *p=(const unsigned char *)m0(encoded,"bytes");
    if(!tas_webp_header(p,length))return nil;
    id existing=m1(templates,"objectForKey:",encoded);if(existing)return objc_retain(existing);
    /* Poster decode and source validation never run on the UI thread. The
     * transport warms this template before composer hydration notifications. */
    if(main_thread())return nil;
    id snapshot=m0(encoded,"copy");if(!snapshot)return nil;
    U size=integer(snapshot,"length");const unsigned char *stable=(const unsigned char *)m0(snapshot,"bytes");
    TASWebPInfo info;
    if(!tas_webp_info(stable,size,&info) || info.count<2){objc_release(snapshot);return nil;}
    length=size;const void *source=source_create(snapshot,source_options);
    if(!source || source_count(source)!=info.count){__atomic_add_fetch(&refused,1,__ATOMIC_RELAXED);if(source)cf_release(source);objc_release(snapshot);return nil;}
    pthread_mutex_lock(&decode_lock);const void *cg=render_frame(source,0,&info);pthread_mutex_unlock(&decode_lock);
    if(!cg || cg_width(cg)!=info.width || cg_height(cg)!=info.height){__atomic_add_fetch(&refused,1,__ATOMIC_RELAXED);if(cg)cg_release(cg);cf_release(source);objc_release(snapshot);return nil;}
    id image=((id (*)(id,SEL,const void *,double,long))objc_msgSend)(m0((id)animation_class,"alloc"),sel_registerName("initWithCGImage:scale:orientation:"),cg,1.0,0L);
    id first=objc_retain(m1((id)objc_getClass("UIImage"),"imageWithCGImage:",(id)cg));cg_release(cg);
    if(!image || object_getClass(image)!=animation_class || !first){__atomic_add_fetch(&refused,1,__ATOMIC_RELAXED);objc_release(image);objc_release(first);cf_release(source);objc_release(snapshot);return nil;}
    Animation *s=calloc(1,sizeof(*s));
    if(!s){objc_release(image);objc_release(first);cf_release(source);objc_release(snapshot);return nil;}
    s->info=info;s->data=snapshot;s->source=source;s->poster=first;s->identity=__atomic_add_fetch(&serial,1,__ATOMIC_RELAXED);
    id times=m0((id)objc_getClass("NSMutableDictionary"),"new");
    for(U i=0;i<info.count;i++){
        id key=((id (*)(id,SEL,U))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithUnsignedInteger:"),i);
        id value=((id (*)(id,SEL,double))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithDouble:"),info.delay_ms[i]/1000.0);
        ((void (*)(id,SEL,id,id))objc_msgSend)(times,sel_registerName("setObject:forKey:"),value,key);
    }
    s->delays=times;memcpy((char *)image+state_offset,&s,sizeof(s));
    ((void (*)(id,SEL,id,id,U))objc_msgSend)(templates,sel_registerName("setObject:forKey:cost:"),image,snapshot,length+(U)info.width*info.height*4);
    __atomic_add_fetch(&created,1,__ATOMIC_RELAXED);return image;
}
void tas_animated_image_prepare(id encoded){
    /* Called only after a successful admitted provider HTTP response. Swift's
     * Data/NSData bridge may recreate the object before the legacy factory;
     * NSCache compares the immutable encoded value, not transient pointers.
     * Admission lives only as long as this bounded decoded template. */
    id image=tas_animated_image_create(encoded);
    Animation *s=state(image);if(s)__atomic_store_n(&s->legacy_admitted,YES,__ATOMIC_RELEASE);
    objc_release(image);
}

static id legacy_image_init(id self,SEL cmd,id encoded){
    id image=nil;
    if(encoded && tas_emotes_enabled_this_launch() && integer(encoded,"length")<=TAS_WEBP_MAX_BYTES &&
       tas_webp_header((const unsigned char *)m0(encoded,"bytes"),integer(encoded,"length"))){
        pthread_mutex_lock(&init_lock);id cache=objc_retain(templates);pthread_mutex_unlock(&init_lock);
        id candidate=objc_retain(m1(cache,"objectForKey:",encoded));objc_release(cache);
        Animation *s=candidate && animation_class && object_getClass(candidate)==animation_class?state(candidate):NULL;
        if(s && __atomic_load_n(&s->legacy_admitted,__ATOMIC_ACQUIRE))image=candidate;
        else objc_release(candidate);
    }
    /* An ObjC initializer may return a replacement object. Preserve its +1
     * ownership, release the unused allocation, and supply the same indexed
     * interface to TWAnimatedImageLayer without invoking a GIF decoder. */
    if(image){objc_release(self);return image;}
    return ((id (*)(id,SEL,id))legacy_original)(self,cmd,encoded);
}

static id load_provider(id self,SEL cmd,id request,id progress,id completion){
    if(!tas_emotes_enabled_this_launch())return ((id (*)(id,SEL,id,id,id))load_original)(self,cmd,request,progress,completion);
    id replacement=tas_emotes_rewrite_request_copy(request);
    id url=m0(m0(replacement?:request,"URL"),"absoluteString");
    const char *text=url?((const char *(*)(id,SEL))objc_msgSend)(url,sel_registerName("UTF8String")):NULL;
    BOOL provider=text && tas_emotes_is_provider_image_url(text);objc_release(replacement);
    if(!provider || !completion)return ((id (*)(id,SEL,id,id,id))load_original)(self,cmd,request,progress,completion);
    /* Capturing a typed block (not id) emits Block copy/dispose helpers. */
    void (^callback)(id,id,id)=(void (^)(id,id,id))completion;
    void (^wrapped)(id,id,id)=^(id error,id value,id response){
        id animation=nil;
        pthread_mutex_lock(&init_lock);BOOL bounded=buffer_original!=NULL;pthread_mutex_unlock(&init_lock);
        if(!error && bounded && tas_emotes_enabled_this_launch() && kind(value,"NSData"))animation=tas_animated_image_create(value);
        callback(error,animation?:value,response);objc_release(animation);
    };
    return ((id (*)(id,SEL,id,id,id))load_original)(self,cmd,request,progress,(id)wrapped);
}
static void provider_buffer_limit(id self,SEL cmd){
    id image=m0(self,"animatedImage");
    if(image && animation_class && object_getClass(image)==animation_class)
        ((void (*)(id,SEL,U))objc_msgSend)(self,sel_registerName("setMaxBufferCount:"),(U)4);
    else ((void (*)(id,SEL))buffer_original)(self,cmd);
}
void tas_animated_image_retry_hooks(void){
    if(!tas_emotes_enabled_this_launch())return;
    pthread_mutex_lock(&init_lock);
    if(!legacy_original){
        Class cls=objc_getClass("FLAnimatedImage");SEL sel=sel_registerName("initWithAnimatedGIFData:");
        Method method=cls?class_getInstanceMethod(cls,sel):NULL;
        if(method && !strcmp(method_getTypeEncoding(method),"@24@0:8@16")){
            legacy_original=method_getImplementation(method);
            if(!class_addMethod(cls,sel,(IMP)legacy_image_init,method_getTypeEncoding(method)))method_setImplementation(method,(IMP)legacy_image_init);
        }
    }
    if(!load_original){
        Class cls=objc_getClass("RCTImageLoader");SEL sel=sel_registerName("_loadURLRequest:progressBlock:completionBlock:");
        Method method=cls?class_getInstanceMethod(cls,sel):NULL;
        if(method && !strcmp(method_getTypeEncoding(method),"@?40@0:8@16@?24@?32")){
            load_original=method_getImplementation(method);
            if(!class_addMethod(cls,sel,(IMP)load_provider,method_getTypeEncoding(method)))method_setImplementation(method,(IMP)load_provider);
        }
    }
    if(!buffer_original){
        Class cls=objc_getClass("RCTUIImageViewAnimated");
        Method method=cls?class_getInstanceMethod(cls,sel_registerName("calculateMaxBufferCount")):NULL;
        Method setter=cls?class_getInstanceMethod(cls,sel_registerName("setMaxBufferCount:")):NULL;
        Method getter=cls?class_getInstanceMethod(cls,sel_registerName("animatedImage")):NULL;
        if(method && setter && getter && !strcmp(method_getTypeEncoding(method),"v16@0:8") &&
            !strcmp(method_getTypeEncoding(setter),"v24@0:8Q16") && !strcmp(method_getTypeEncoding(getter),"@16@0:8")){
            buffer_original=method_getImplementation(method);
            if(!class_addMethod(cls,sel_registerName("calculateMaxBufferCount"),(IMP)provider_buffer_limit,method_getTypeEncoding(method)))
                method_setImplementation(method,(IMP)provider_buffer_limit);
        }
    }
    pthread_mutex_unlock(&init_lock);
}

void tas_animated_image_status(char *buffer,size_t capacity){
    pthread_mutex_lock(&cache_lock);U bytes=frame_bytes,pending=jobs;pthread_mutex_unlock(&cache_lock);
    pthread_mutex_lock(&init_lock);BOOL loader=load_original!=NULL,limit=buffer_original!=NULL,legacy=legacy_original!=NULL,backend=animation_class!=NULL;pthread_mutex_unlock(&init_lock);
    snprintf(buffer,capacity,"Provider WebP loader/buffer hooks: %s/%s; legacy factory=%s; ImageIO adapter=%s\n"
        "WebP assets created/refused; frames decoded/failed: %llu/%llu; %llu/%llu\n"
        "WebP owned frame cache: %lu/33554432 bytes; background jobs=%lu/64; per-asset/RN-view frames=4/4\n",
        loader?"installed":"missing",limit?"installed":"missing",legacy?"installed":"missing",backend?"ready":"not initialized",
        (unsigned long long)__atomic_load_n(&created,__ATOMIC_RELAXED),(unsigned long long)__atomic_load_n(&refused,__ATOMIC_RELAXED),
        (unsigned long long)__atomic_load_n(&decoded_frames,__ATOMIC_RELAXED),(unsigned long long)__atomic_load_n(&frame_failures,__ATOMIC_RELAXED),bytes,pending);
}
