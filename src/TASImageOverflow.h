/* Refused admissions only: fixed recovery storage, no independent downloader. */
#define IMAGE_OVERFLOW_GROUPS 64
#define IMAGE_OVERFLOW_SECONDS 30
static ImageFlight image_overflow[IMAGE_OVERFLOW_GROUPS];
static unsigned image_overflow_groups,image_overflow_peak,image_overflow_consumers,image_overflow_consumer_peak;
static uint64_t image_overflow_waited,image_overflow_joined,image_overflow_recovered,image_overflow_cancelled;
static uint64_t image_overflow_expired,image_overflow_rejected;
static bool image_overflow_timer;
static void image_overflow_timeout(void *unused);
/* One timer expires waiters; it does not poll, retry or create transfers. */
static void image_overflow_arm_locked(void) {
    if(image_overflow_timer || !image_overflow_groups)return;
    struct timespec now;clock_gettime(CLOCK_MONOTONIC,&now);double delay=IMAGE_OVERFLOW_SECONDS;
    for(unsigned i=0;i<IMAGE_OVERFLOW_GROUPS;i++)if(image_overflow[i].url) {
        double remaining=IMAGE_OVERFLOW_SECONDS-image_elapsed(image_overflow[i].queued,now);
        if(remaining<delay)delay=remaining;
    }
    if(delay<.001)delay=.001;
    image_overflow_timer=true;
    dispatch_after_f(dispatch_time(DISPATCH_TIME_NOW,(int64_t)(delay*1000000000.0)),
                     dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT,0),NULL,image_overflow_timeout);
}
static bool image_overflow_admit_locked(id self,id session,id request,const char *url,bool foreground) {
    unsigned slot=IMAGE_OVERFLOW_GROUPS;bool joined=false;
    struct timespec now;clock_gettime(CLOCK_MONOTONIC,&now);
    for(unsigned i=0;i<IMAGE_OVERFLOW_GROUPS;i++) {
        ImageFlight *f=&image_overflow[i];
        if(!f->url){if(slot==IMAGE_OVERFLOW_GROUPS)slot=i;continue;}
        if(f->count==IMAGE_CONSUMERS || image_elapsed(f->queued,now)>=IMAGE_OVERFLOW_SECONDS ||
           strcmp(f->url,url) || imsg0(f->request,"cachePolicy")!=imsg0(request,"cachePolicy"))continue;
        id a=msg0(f->request,"allHTTPHeaderFields"),b=msg0(request,"allHTTPHeaderFields");
        if(a!=b && !bmsg1(a,"isEqual:",b))continue;
        slot=i;joined=true;break;
    }
    if(slot==IMAGE_OVERFLOW_GROUPS){image_overflow_rejected++;return false;}
    ImageFlight *f=&image_overflow[slot];
    if(!joined) {
        f->url=strdup(url);if(!f->url){image_overflow_rejected++;return false;}
        f->request=objc_retain(request);f->session=session;f->generation=++image_generation;f->queued=now;
        image_overflow_groups++;if(image_overflow_groups>image_overflow_peak)image_overflow_peak=image_overflow_groups;
    }else image_overflow_joined++;
    f->foreground|=foreground;f->consumers[f->count++]=objc_retain(self);
    image_overflow_waited++;image_overflow_consumers++;
    if(image_overflow_consumers>image_overflow_consumer_peak)image_overflow_consumer_peak=image_overflow_consumers;
    objc_setAssociatedObject(self,&image_consumer_key,nsstr("1"),1);
    image_overflow_arm_locked();return true;
}
/* Caller holds the existing transport lock. Transfer ownership directly to
 * normal admission, preserving original FIFO, priority and queue timestamp. */
static void image_overflow_drain_locked(void) {
    if(!image_overflow_groups)return;
    struct timespec now;clock_gettime(CLOCK_MONOTONIC,&now);
    for(unsigned slot=0;slot<IMAGE_FLIGHTS;slot++) {
        if(image_flights[slot].url)continue;
        unsigned pick=IMAGE_OVERFLOW_GROUPS;
        for(unsigned i=0;i<IMAGE_OVERFLOW_GROUPS;i++) {
            ImageFlight *f=&image_overflow[i];
            if(!f->url || !f->count || image_elapsed(f->queued,now)>=IMAGE_OVERFLOW_SECONDS)continue;
            if(pick==IMAGE_OVERFLOW_GROUPS || (f->foreground && !image_overflow[pick].foreground) ||
               (f->foreground==image_overflow[pick].foreground && f->generation<image_overflow[pick].generation))pick=i;
        }
        if(pick==IMAGE_OVERFLOW_GROUPS)break;
        ImageFlight *f=&image_overflow[pick];
        image_overflow_recovered+=f->count;image_overflow_consumers-=f->count;image_overflow_groups--;
        image_flights[slot]=*f;memset(f,0,sizeof(*f));
    }
}
static void image_overflow_timeout(void *unused) {
    (void)unused;ImageFlight expired[IMAGE_OVERFLOW_GROUPS];unsigned count=0;
    struct timespec now;clock_gettime(CLOCK_MONOTONIC,&now);
    pthread_mutex_lock(&image_transport_lock);image_overflow_timer=false;
    for(unsigned i=0;i<IMAGE_OVERFLOW_GROUPS;i++) {
        ImageFlight *f=&image_overflow[i];
        if(!f->url || image_elapsed(f->queued,now)<IMAGE_OVERFLOW_SECONDS)continue;
        expired[count++]=*f;image_overflow_expired+=f->count;
        image_overflow_consumers-=f->count;image_overflow_groups--;memset(f,0,sizeof(*f));
    }
    image_overflow_arm_locked();pthread_mutex_unlock(&image_transport_lock);
    if(!count)return;
    id pool=msg0((id)objc_getClass("NSAutoreleasePool"),"new");
    id error=((id (*)(id,SEL,id,NSInteger,id))objc_msgSend)((id)objc_getClass("NSError"),
        sel_registerName("errorWithDomain:code:userInfo:"),nsstr("NSURLErrorDomain"),-1001,nil);
    for(unsigned i=0;i<count;i++) {
        ImageFlight *f=&expired[i];
        for(unsigned j=0;j<f->count;j++){protocol_complete(f->consumers[j],nil,nil,error);objc_release(f->consumers[j]);}
        free(f->url);objc_release(f->request);
    }
    msg0(pool,"drain");
}
static bool image_overflow_stop_locked(id self,id *request,id *consumer,char **url) {
    if(!image_overflow_groups)return false;
    for(unsigned i=0;i<IMAGE_OVERFLOW_GROUPS;i++) {
        ImageFlight *f=&image_overflow[i];
        for(unsigned j=0;f->url && j<f->count;j++)if(f->consumers[j]==self) {
            *consumer=f->consumers[j];memmove(&f->consumers[j],&f->consumers[j+1],(--f->count-j)*sizeof(id));
            image_overflow_cancelled++;image_overflow_consumers--;
            if(!f->count){*request=f->request;*url=f->url;image_overflow_groups--;memset(f,0,sizeof(*f));}
            return true;
        }
    }
    return false;
}
static void image_overflow_status_locked(char *buffer,size_t capacity) {
    size_t used=strlen(buffer);
    if(used<capacity)snprintf(buffer+used,capacity-used,
        "Overflow recovery waiting/joined/recovered/cancelled/expired/rejected: %llu/%llu/%llu/%llu/%llu/%llu\n"
        "Overflow groups current/peak/limit, consumers current/peak/limit: %u/%u/64 %u/%u/4096; wait deadline: 30s; timer pending: %u\n",
        (unsigned long long)image_overflow_waited,(unsigned long long)image_overflow_joined,
        (unsigned long long)image_overflow_recovered,(unsigned long long)image_overflow_cancelled,
        (unsigned long long)image_overflow_expired,(unsigned long long)image_overflow_rejected,
        image_overflow_groups,image_overflow_peak,image_overflow_consumers,image_overflow_consumer_peak,(unsigned)image_overflow_timer);
}
