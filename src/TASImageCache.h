/* Foundation owns cache storage and validation. This delegate annotates only
 * responses Foundation already elected to store; it never admits no-store.
 * Metadata is cache-internal, not diagnostic output. No response is copied to
 * another downloader/cache. Old, unannotated entries take Foundation's path. */
#include "TASHTTPCache.h"
static char image_cache_start_key;
static char image_cache_completion_key,image_cache_data_key;
static id image_cache_epoch;
static id image_cache_store;
/* Raw pointer permits the same acquire/release publication in C and ObjC. */
static void *image_cache_session;
static pthread_mutex_t image_cache_metadata_lock=PTHREAD_MUTEX_INITIALIZER;
static uint64_t image_cache_proposals,image_cache_annotations;
static uint64_t image_cache_rejections[IMAGE_CACHE_REJECTION_COUNT];
static bool image_cache_eligible(id request);
#ifdef __APPLE__
#define IMAGE_CACHE_AGE_CLOCK CLOCK_MONOTONIC_RAW
#else
#define IMAGE_CACHE_AGE_CLOCK CLOCK_BOOTTIME
#endif
static double image_cache_clock(clockid_t clock) {
    struct timespec t;if(clock_gettime(clock,&t))return -1;return t.tv_sec+t.tv_nsec/1e9;
}
static id image_cache_number(double value) {
    char text[64];snprintf(text,sizeof(text),"%.17g",value);return nsstr(text);
}
static double image_cache_value(id value) {
    const char *s=utf8(value);char *end=NULL;if(!s || !*s)return -1;
    double number=strtod(s,&end);return end && !*end && isfinite(number) ? number:-1;
}
static id image_cache_field(id response,const char *name) {
    /* NSHTTPURLResponse's accessor is case-insensitive (iOS 13+). */
    return msg1(response,"valueForHTTPHeaderField:",nsstr(name));
}
#include "TASCacheHeaderProbe.h"
static void image_cache_mark_task(id task) {
    objc_setAssociatedObject(task,&image_cache_start_key,image_cache_number(image_cache_clock(IMAGE_CACHE_AGE_CLOCK)),1);
}
static void image_cache_proposed(id self,SEL cmd,id session,id task,id proposed,id completion) {
    (void)self;(void)cmd;(void)session;
    id response=msg0(proposed,"response"),request=msg0(task,"originalRequest");
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
    image_header_observe(response,task);
#endif
    double lifetime,stamp,age=0,wall=image_cache_clock(CLOCK_REALTIME),tick=image_cache_clock(IMAGE_CACHE_AGE_CLOCK);
    id start_value=objc_getAssociatedObject(task,&image_cache_start_key);
    double start=image_cache_value(start_value);
    const char *age_text=utf8(image_cache_field(response,"Age"));
    id annotated=nil;
    unsigned rejection=IMAGE_CACHE_ACCEPTED;
    /* Preserve the original gate order and decisions. Each failed condition
     * has its own counter; a failure never evaluates later conditions. */
    if(!start_value)rejection=IMAGE_CACHE_START_MISSING;
    else if(!(start>=0))rejection=IMAGE_CACHE_START_INVALID;
    else if(!(start<=tick))rejection=IMAGE_CACHE_START_FUTURE;
    else if(!image_public_request(request))rejection=IMAGE_CACHE_REQUEST_PRIVATE;
    else if(imsg0(request,"cachePolicy")!=0)rejection=IMAGE_CACHE_REQUEST_POLICY;
    else if(!image_cache_eligible(request))rejection=IMAGE_CACHE_REQUEST_DIRECTIVES;
    else if(imsg0(response,"statusCode")!=200)rejection=IMAGE_CACHE_RESPONSE_STATUS;
    else if(!image_cache_lifetime_reason(utf8(image_cache_field(response,"Cache-Control")),utf8(image_cache_field(response,"Date")),
                                        utf8(image_cache_field(response,"Expires")),&lifetime,&stamp,&rejection)) { /* classified by parser */ }
    else if(!(stamp<=wall))rejection=IMAGE_CACHE_DATE_FUTURE;
    else if(age_text && !image_cache_seconds(age_text,&age))rejection=IMAGE_CACHE_AGE_INVALID;
    if(rejection==IMAGE_CACHE_ACCEPTED) {
        /* Age + entire task duration overestimates response delay and body
         * time. Never underestimate age by counting only lookup latency. */
        double current=fmax(wall-stamp,age+tick-start);
        id info=msg0(msg0(proposed,"userInfo"),"mutableCopy");
        if(!info)info=msg0((id)objc_getClass("NSMutableDictionary"),"new");
        vmsg2(info,"setObject:forKey:",image_cache_epoch,nsstr("TASCacheEpoch"));
        vmsg2(info,"setObject:forKey:",image_cache_number(tick),nsstr("TASCacheTick"));
        vmsg2(info,"setObject:forKey:",image_cache_number(wall),nsstr("TASCacheWall"));
        vmsg2(info,"setObject:forKey:",image_cache_number(lifetime-current),nsstr("TASCacheRemaining"));
        id headers=msg0(request,"allHTTPHeaderFields");
        if(headers)vmsg2(info,"setObject:forKey:",headers,nsstr("TASCacheHeaders"));
        annotated=((id (*)(id,SEL,id,id,id,NSUInteger))objc_msgSend)(
            msg0((id)objc_getClass("NSCachedURLResponse"),"alloc"),sel_registerName("initWithResponse:data:userInfo:storagePolicy:"),
            response,msg0(proposed,"data"),info,(NSUInteger)imsg0(proposed,"storagePolicy"));
        objc_release(info);
        if(!annotated)rejection=IMAGE_CACHE_CONSTRUCTION;
    }
    pthread_mutex_lock(&image_cache_metadata_lock);image_cache_proposals++;if(annotated)image_cache_annotations++;
    else image_cache_rejections[rejection]++;
    pthread_mutex_unlock(&image_cache_metadata_lock);
    ((void (^)(id))completion)(annotated ? annotated:proposed);
    objc_release(annotated);
}
static void image_cache_metrics(id self,SEL cmd,id session,id task,id report) {
    id observer=objc_getAssociatedObject(self,&image_cache_start_key);
    if(observer)((void (*)(id,SEL,id,id,id))objc_msgSend)(observer,cmd,session,task,report);
}
/* Completion-handler data tasks bypass Foundation's willCacheResponse hook.
 * Only bounded shared transfers use delegate data tasks; upstream delivery is
 * still one complete body/response/error through the existing flight callback.
 * Foundation keeps responsibility for storage decisions and HTTP validation. */
static void image_cache_received_data(id self,SEL cmd,id session,id task,id data) {
    (void)self;(void)cmd;(void)session;
    objc_sync_enter(task);
    id body=objc_getAssociatedObject(task,&image_cache_data_key);
    if(body)vmsg1(body,"appendData:",data);
    else {
        body=msg0(data,"mutableCopy");
        objc_setAssociatedObject(task,&image_cache_data_key,body,1);objc_release(body);
    }
    objc_sync_exit(task);
}
static void image_cache_completed(id self,SEL cmd,id session,id task,id error) {
    (void)self;(void)cmd;(void)session;
    objc_sync_enter(task);
    id callback=objc_retain(objc_getAssociatedObject(task,&image_cache_completion_key));
    id body=objc_retain(objc_getAssociatedObject(task,&image_cache_data_key));
    id response=objc_retain(msg0(task,"response"));
    objc_setAssociatedObject(task,&image_cache_completion_key,nil,1);
    objc_setAssociatedObject(task,&image_cache_data_key,nil,1);
    objc_sync_exit(task);
    if(callback)((void (^)(id,id,id))callback)(body,response,error);
    objc_release(response);objc_release(body);objc_release(callback);
}
static id image_cache_task(id session,id request,id callback) {
    id task=msg1(session,"dataTaskWithRequest:",request);
    if(task)objc_setAssociatedObject(task,&image_cache_completion_key,callback,3); /* copy non-atomic */
    return task;
}
static id image_cache_delegate(void) {
    Class cls=objc_getClass("TASProviderCacheDelegate");
    if(!cls) {
        cls=objc_allocateClassPair(objc_getClass("NSObject"),"TASProviderCacheDelegate",0);
        if(!cls)return nil;
        if(!class_addMethod(cls,sel_registerName("URLSession:dataTask:willCacheResponse:completionHandler:"),(IMP)image_cache_proposed,"v48@0:8@16@24@32@?40") ||
           !class_addMethod(cls,sel_registerName("URLSession:task:didFinishCollectingMetrics:"),(IMP)image_cache_metrics,"v40@0:8@16@24@32") ||
           !class_addMethod(cls,sel_registerName("URLSession:dataTask:didReceiveData:"),(IMP)image_cache_received_data,"v40@0:8@16@24@32") ||
           !class_addMethod(cls,sel_registerName("URLSession:task:didCompleteWithError:"),(IMP)image_cache_completed,"v40@0:8@16@24@32")) {
            objc_disposeClassPair(cls);return nil;
        }
        objc_registerClassPair(cls);
    }
    id delegate=msg0((id)cls,"new"),observer=tas_demand_delegate();
    objc_setAssociatedObject(delegate,&image_cache_start_key,observer,1);objc_release(observer);
    /* A boot-scoped epoch permits same-boot relaunch reuse with continuous
     * (sleep-inclusive) age. Reboots/uncertain metadata fall back to Foundation.
     * This value stays inside the HTTP cache, never diagnostics. */
    struct timeval boot;size_t size=sizeof(boot);char epoch[96];
    if(!sysctlbyname("kern.boottime",&boot,&size,NULL,0) && size==sizeof(boot) && boot.tv_sec>0) {
        snprintf(epoch,sizeof(epoch),"v1:%lld:%d",(long long)boot.tv_sec,(int)boot.tv_usec);
        image_cache_epoch=objc_retain(nsstr(epoch));
    } else image_cache_epoch=objc_retain(msg0(msg0((id)objc_getClass("NSUUID"),"UUID"),"UUIDString"));
    return delegate;
}
static bool image_cache_eligible(id request) {
    static const char *restricted[]={"Cache-Control","Pragma","If-Match","If-None-Match","If-Modified-Since","If-Unmodified-Since","If-Range"};
    for(unsigned i=0;i<sizeof(restricted)/sizeof(*restricted);i++)
        if(msg1(request,"valueForHTTPHeaderField:",nsstr(restricted[i])))return false;
    return !msg0(request,"HTTPBodyStream");
}
/* Reasons: hit / absent / untrusted metadata / expired clock / HTTP validation /
 * variant / forbidden storage / unusable body. No values leave this function. */
static bool image_cache_usable(id cached,id request,unsigned *reason) {
    *reason=1;if(!cached)return false;
    id response=msg0(cached,"response"),info=msg0(cached,"userInfo");
    id data=msg0(cached,"data");
    *reason=6;if(imsg0(cached,"storagePolicy")==2)return false;
    *reason=7;if(imsg0(response,"statusCode")!=200 || !data || !data_length(data))return false;
    *reason=2;
    id epoch=msg1(info,"objectForKey:",nsstr("TASCacheEpoch"));
    if(!epoch || !bmsg1(epoch,"isEqual:",image_cache_epoch))return false;
    *reason=5;
    id a=msg1(info,"objectForKey:",nsstr("TASCacheHeaders")),b=msg0(request,"allHTTPHeaderFields");
    if(a!=b && !bmsg1(a,"isEqual:",b))return false;
    id url=msg0(response,"URL");
    if(!bmsg1(url,"isEqual:",msg0(request,"URL")))return false; /* redirected/uncertain variant */
    *reason=4;
    const char *vary=utf8(image_cache_field(response,"Vary"));
    if(vary && strchr(vary,'*'))return false;
    /* Automatic cookies may change without appearing in originalRequest. */
    if(vary && (strcasestr(vary,"cookie") || strcasestr(vary,"authorization")))return false;
    if(vary && strcasestr(vary,"user-agent") && !msg1(request,"valueForHTTPHeaderField:",nsstr("User-Agent")))return false;
    if(image_cache_field(response,"Content-Range") || image_cache_field(response,"Pragma"))return false;
    double lifetime,stamp;
    if(!image_cache_lifetime(utf8(image_cache_field(response,"Cache-Control")),utf8(image_cache_field(response,"Date")),
                             utf8(image_cache_field(response,"Expires")),&lifetime,&stamp))return false;
    double tick=image_cache_value(msg1(info,"objectForKey:",nsstr("TASCacheTick")));
    double wall=image_cache_value(msg1(info,"objectForKey:",nsstr("TASCacheWall")));
    double remaining=image_cache_value(msg1(info,"objectForKey:",nsstr("TASCacheRemaining")));
    double elapsed=image_cache_clock(IMAGE_CACHE_AGE_CLOCK)-tick,wall_elapsed=image_cache_clock(CLOCK_REALTIME)-wall;
    *reason=3;
    if(!(tick>=0 && wall>=0 && elapsed>=0 && wall_elapsed>=0 && isfinite(remaining) && remaining>fmax(elapsed,wall_elapsed)))return false;
    *reason=0;return true;
}
