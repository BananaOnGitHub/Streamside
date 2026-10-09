/* Two worker blocks maximum. This separate registry owns no network tasks;
 * misses enter the original scheduler. Client callbacks never hold its lock. */
#define IMAGE_CACHE_GROUPS 512
#define IMAGE_CACHE_WORKERS 2
static ImageFlight image_lookups[IMAGE_CACHE_GROUPS];
static pthread_mutex_t image_cache_lock=PTHREAD_MUTEX_INITIALIZER;
static unsigned image_cache_workers,image_cache_groups,image_cache_peak,image_cache_worker_peak;
static unsigned image_cache_consumers,image_cache_consumer_peak;
static uint64_t image_cache_generation,image_cache_checks,image_cache_hits,image_cache_misses,image_cache_joined;
static uint64_t image_cache_cancelled,image_cache_spill,image_cache_hit_time[4],image_cache_lookup_time[4];
static uint64_t image_cache_wait_time[4],image_cache_reasons[8],image_cache_delivered;
static uint64_t image_cache_bypassed;
static void image_cache_worker(void *unused) {
    (void)unused;
    id initial_pool=msg0((id)objc_getClass("NSAutoreleasePool"),"new");
    id session=protocol_session(true);
    /* Pre-initialization spills use the existing bounded registry, never
     * constructing a cache/session on the initiating (possibly main) thread. */
    pthread_mutex_lock(&image_transport_lock);
    for(unsigned i=0;i<IMAGE_FLIGHTS;i++)if(image_flights[i].url && !image_flights[i].session)image_flights[i].session=session;
    pthread_mutex_unlock(&image_transport_lock);image_schedule();msg0(initial_pool,"drain");
    for(;;) {
        pthread_mutex_lock(&image_cache_lock);
        unsigned index=IMAGE_CACHE_GROUPS;
        for(unsigned i=0;i<IMAGE_CACHE_GROUPS;i++) {
            ImageFlight *f=&image_lookups[i];if(!f->url || f->running || !f->count)continue;
            if(index==IMAGE_CACHE_GROUPS || (f->foreground && !image_lookups[index].foreground) ||
               (f->foreground==image_lookups[index].foreground && f->generation<image_lookups[index].generation))index=i;
        }
        if(index==IMAGE_CACHE_GROUPS){image_cache_workers--;pthread_mutex_unlock(&image_cache_lock);return;}
        ImageFlight *f=&image_lookups[index];f->running=true;
        id request=f->request;
        pthread_mutex_unlock(&image_cache_lock);
        id pool=msg0((id)objc_getClass("NSAutoreleasePool"),"new");
        struct timespec started,ended;clock_gettime(CLOCK_MONOTONIC,&started);
        bool lookup=imsg0(request,"cachePolicy")==0 && image_cache_eligible(request);
        id cached=lookup ? objc_retain(msg1(image_cache_store,"cachedResponseForRequest:",request)):nil;
        unsigned reason=4;bool hit=lookup && image_cache_usable(cached,request,&reason);
        clock_gettime(CLOCK_MONOTONIC,&ended);
        id consumers[IMAGE_CONSUMERS];unsigned count;
        pthread_mutex_lock(&image_cache_lock);
        count=f->count;memcpy(consumers,f->consumers,count*sizeof(id));
        image_cache_consumers-=count;
        bool foreground=f->foreground;char *url=f->url;struct timespec queued=f->queued;
        bool refused[IMAGE_CONSUMERS]={false};
        if(!hit) {
            /* One atomic group admission BEFORE starting any task. A fast
             * completion cannot outrun the rest of this group's consumers.
             * Lock order: cache -> transport; neither takes consumer monitors. */
            pthread_mutex_lock(&image_transport_lock);
            for(unsigned i=0;i<count;i++)if(!objc_getAssociatedObject(consumers[i],&g_protocol_stopped_key))
                refused[i]=image_flight_add_locked(consumers[i],session,request,url,foreground,true,false)==IMAGE_FLIGHTS;
            pthread_mutex_unlock(&image_transport_lock);
        }
        memset(f,0,sizeof(*f));image_cache_groups--;
        image_cache_wait_time[image_bucket(image_elapsed(queued,started))]++;
        if(lookup){image_cache_checks++;image_cache_lookup_time[image_bucket(image_elapsed(started,ended))]++;image_cache_reasons[reason]++;if(hit)image_cache_hits++;else image_cache_misses++;}
        else image_cache_bypassed++;
        pthread_mutex_unlock(&image_cache_lock);
        if(!hit)image_schedule();
        unsigned delivered=0;
        for(unsigned i=0;i<count;i++) {
            objc_sync_enter(consumers[i]);
            if(!objc_getAssociatedObject(consumers[i],&g_protocol_stopped_key)) {
                if(hit){protocol_complete(consumers[i],msg0(cached,"data"),msg0(cached,"response"),nil);delivered++;}
                else if(refused[i])protocol_deliver(consumers[i],nil,nil,nil);
                else if(!objc_getAssociatedObject(consumers[i],&g_protocol_completed_key)) {
                    pthread_mutex_lock(&image_transport_lock);
                    for(unsigned j=0;j<IMAGE_FLIGHTS;j++)for(unsigned k=0;k<image_flights[j].count;k++)
                        if(image_flights[j].consumers[k]==consumers[i])objc_setAssociatedObject(consumers[i],&g_protocol_task_key,image_flights[j].task,1);
                    pthread_mutex_unlock(&image_transport_lock);
                }
            }
            objc_sync_exit(consumers[i]);objc_release(consumers[i]);
        }
        if(delivered) {
            clock_gettime(CLOCK_MONOTONIC,&ended);pthread_mutex_lock(&image_cache_lock);
            image_cache_hit_time[image_bucket(image_elapsed(queued,ended))]++;image_cache_delivered+=delivered;pthread_mutex_unlock(&image_cache_lock);
        }
        free(url);objc_release(request);objc_release(cached);msg0(pool,"drain");
    }
}
static bool image_cache_start(id self,id session,id request,const char *url,bool foreground) {
    /* Immediately preserve existing foreground promotion/detached reuse. */
    if(image_flight_admit(self,session,request,url,foreground,false))return true;
    unsigned index=IMAGE_CACHE_GROUPS;bool joined=false;
    pthread_mutex_lock(&image_cache_lock);
    for(unsigned i=0;i<IMAGE_CACHE_GROUPS;i++) {
        ImageFlight *f=&image_lookups[i];if(!f->url){if(index==IMAGE_CACHE_GROUPS)index=i;continue;}
        id a=msg0(f->request,"allHTTPHeaderFields"),b=msg0(request,"allHTTPHeaderFields");
        if(f->count<IMAGE_CONSUMERS && !strcmp(f->url,url) && imsg0(f->request,"cachePolicy")==imsg0(request,"cachePolicy") && (a==b || bmsg1(a,"isEqual:",b))) {
            index=i;joined=true;break;
        }
    }
    if(index==IMAGE_CACHE_GROUPS) {
        image_cache_spill++;bool spawn=image_cache_workers<IMAGE_CACHE_WORKERS;
        if(spawn){image_cache_workers++;if(image_cache_workers>image_cache_worker_peak)image_cache_worker_peak=image_cache_workers;}
        pthread_mutex_unlock(&image_cache_lock);
        /* Existing bounded admission/refusal; Phase 3 owns overflow recovery. */
        bool result=image_flight_start(self,session,request,url,foreground);
        if(spawn)dispatch_async_f(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT,0),NULL,image_cache_worker);
        return result;
    }
    ImageFlight *f=&image_lookups[index];
    if(!joined) {
        f->url=strdup(url);
        if(!f->url){image_cache_spill++;bool spawn=image_cache_workers<IMAGE_CACHE_WORKERS;
            if(spawn){image_cache_workers++;if(image_cache_workers>image_cache_worker_peak)image_cache_worker_peak=image_cache_workers;}
            pthread_mutex_unlock(&image_cache_lock);bool result=image_flight_start(self,session,request,url,foreground);
            if(spawn)dispatch_async_f(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT,0),NULL,image_cache_worker);
            return result;
        }
        f->request=objc_retain(request);f->session=session;f->generation=++image_cache_generation;
        clock_gettime(CLOCK_MONOTONIC,&f->queued);
        image_cache_groups++;if(image_cache_groups>image_cache_peak)image_cache_peak=image_cache_groups;
    }else image_cache_joined++;
    f->foreground|=foreground;f->consumers[f->count++]=objc_retain(self);
    image_cache_consumers++;if(image_cache_consumers>image_cache_consumer_peak)image_cache_consumer_peak=image_cache_consumers;
    objc_setAssociatedObject(self,&image_consumer_key,nsstr("1"),1);
    bool spawn=image_cache_workers<IMAGE_CACHE_WORKERS;
    if(spawn){image_cache_workers++;if(image_cache_workers>image_cache_worker_peak)image_cache_worker_peak=image_cache_workers;}
    pthread_mutex_unlock(&image_cache_lock);
    if(spawn)dispatch_async_f(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT,0),NULL,image_cache_worker);
    return true;
}
static void image_cache_stop(id self) {
    id consumer=nil,request=nil;char *url=NULL;
    pthread_mutex_lock(&image_cache_lock);
    for(unsigned i=0;i<IMAGE_CACHE_GROUPS && !consumer;i++) {
        ImageFlight *f=&image_lookups[i];
        for(unsigned j=0;f->url && j<f->count;j++)if(f->consumers[j]==self) {
            consumer=f->consumers[j];memmove(&f->consumers[j],&f->consumers[j+1],(--f->count-j)*sizeof(id));image_cache_cancelled++;image_cache_consumers--;
            if(!f->count && !f->running){request=f->request;url=f->url;memset(f,0,sizeof(*f));image_cache_groups--;}
            break;
        }
    }
    pthread_mutex_unlock(&image_cache_lock);free(url);objc_release(request);objc_release(consumer);
}
static void image_cache_status(char *buffer,size_t capacity) {
    pthread_mutex_lock(&image_cache_lock);
    snprintf(buffer,capacity,
        "Cache-first checks/hits/misses/coalesced/cancelled/spilled/bypassed: %llu/%llu/%llu/%llu/%llu/%llu/%llu\n"
        "Cache lookup groups current/peak/limit, workers current/peak/limit: %u/%u/512 %u/%u/2\n"
        "Cache registry consumers current/peak/limit: %u/%u/32768; fixed lookup registry bytes: %zu\n"
        "Cache-hit admission-to-delivery <=250ms/<=1s/<=5s/>5s: %llu/%llu/%llu/%llu\n"
        "Cache lookup operation <=250ms/<=1s/<=5s/>5s: %llu/%llu/%llu/%llu\n"
        "Cache lane wait <=250ms/<=1s/<=5s/>5s: %llu/%llu/%llu/%llu\n"
        "Cache miss absent/metadata/expired/validation/variant/storage/body; delivered consumers: %llu/%llu/%llu/%llu/%llu/%llu/%llu; %llu\n"
        "Cache hits bypass transfer admission; task completions above include Foundation cache responses. Decode/display latency excluded.\n",
        (unsigned long long)image_cache_checks,(unsigned long long)image_cache_hits,(unsigned long long)image_cache_misses,
        (unsigned long long)image_cache_joined,(unsigned long long)image_cache_cancelled,(unsigned long long)image_cache_spill,(unsigned long long)image_cache_bypassed,
        image_cache_groups,image_cache_peak,image_cache_workers,image_cache_worker_peak,
        image_cache_consumers,image_cache_consumer_peak,sizeof(image_lookups),
        (unsigned long long)image_cache_hit_time[0],(unsigned long long)image_cache_hit_time[1],(unsigned long long)image_cache_hit_time[2],(unsigned long long)image_cache_hit_time[3],
        (unsigned long long)image_cache_lookup_time[0],(unsigned long long)image_cache_lookup_time[1],(unsigned long long)image_cache_lookup_time[2],(unsigned long long)image_cache_lookup_time[3],
        (unsigned long long)image_cache_wait_time[0],(unsigned long long)image_cache_wait_time[1],(unsigned long long)image_cache_wait_time[2],(unsigned long long)image_cache_wait_time[3],
        (unsigned long long)image_cache_reasons[1],(unsigned long long)image_cache_reasons[2],(unsigned long long)image_cache_reasons[3],(unsigned long long)image_cache_reasons[4],
        (unsigned long long)image_cache_reasons[5],(unsigned long long)image_cache_reasons[6],(unsigned long long)image_cache_reasons[7],(unsigned long long)image_cache_delivered);
    pthread_mutex_unlock(&image_cache_lock);
    size_t used=strlen(buffer);pthread_mutex_lock(&image_cache_metadata_lock);
    if(used<capacity)snprintf(buffer+used,capacity-used,"Foundation cache proposals/annotated: %llu/%llu (old or unverifiable entries use Foundation validation).\n",
        (unsigned long long)image_cache_proposals,(unsigned long long)image_cache_annotations);
    pthread_mutex_unlock(&image_cache_metadata_lock);
}
