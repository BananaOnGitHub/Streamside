"""Run the production URL-protocol lifecycle against a deferred transport."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRELUDE = r'''
#include <assert.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <sys/time.h>
static int sysctlbyname(const char *name,void *value,size_t *length,void *new_value,size_t new_length) {
    assert(!strcmp(name,"kern.boottime") && !new_value && !new_length && *length==sizeof(struct timeval));
    struct timeval boot={12345,678};memcpy(value,&boot,sizeof(boot));return 0;
}
typedef struct Fake *id;
typedef id Class;
typedef const char *SEL;
typedef long NSInteger;
typedef unsigned long NSUInteger;
typedef signed char BOOL;
#define nil NULL
#define YES 1
#define NO 0
#define TAS_INTERNAL_HEADER "X-TAS-Internal"
#define TAS_DIAG_SYNTHETIC_SEGMENT 1
#define TAS_DIAG_HLS_INTERCEPTED 2
#define TAS_DIAG_HLS_FAILURE 3
struct Block { void *isa;int flags,reserved;void (*invoke)(void *,id,id,id);struct {uintptr_t reserved,size;} *descriptor; };
struct Fake {
    const char *text;
    id request,client,task,stopped,completed,consumer,url,header,session,headers,method,authorization,range,cache_start;
    id data,response,info,cache,epoch;
    id keys[32],values[32];unsigned entries;
    struct Block *completion;
    unsigned resumes,cancels,responses,loads,finishes,failures,cache_policy,status;
    bool stop_on_response,foreground,delegated;
    NSInteger error_code;
    pthread_mutex_t monitor;
};
static struct Fake objects[200000],session_class,config_class,error_class,config,cache_class,queue_class,other_class;
static size_t used;
static unsigned starts,results,rewrites,cancellations;
static bool block_manifest,manifest_entered,release_manifest;
static pthread_mutex_t manifest_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t manifest_condition=PTHREAD_COND_INITIALIZER;
static bool fail_task,fail_cached_response;
static bool complete_on_resume;
static id immediate_data,immediate_response;
static char g_protocol_task_key,g_protocol_stopped_key,g_protocol_completed_key,image_consumer_key,image_cache_start_key,image_cache_completion_key,image_cache_data_key;
static void image_cache_received_data(id,SEL,id,id,id);
static void image_cache_completed(id,SEL,id,id,id);
static id g_protocol_session;
void *_NSConcreteStackBlock[32];
static id fresh(const char *text) {
    size_t slot=__atomic_fetch_add(&used,1,__ATOMIC_RELAXED);assert(slot<200000);id o=&objects[slot];o->text=text ? strdup(text):NULL;
    pthread_mutexattr_t attr;pthread_mutexattr_init(&attr);
    pthread_mutexattr_settype(&attr,PTHREAD_MUTEX_RECURSIVE);
    pthread_mutex_init(&o->monitor,&attr);pthread_mutexattr_destroy(&attr);return o;
}
static id nsstr(const char *s) { return fresh(s); }
static const char *utf8(id o) { return o ? o->text : NULL; }
static id nsurl(const char *s) { return fresh(s); }
static SEL sel_registerName(const char *s) { return s; }
static Class objc_getClass(const char *s) {
    if(!strcmp(s,"NSURLSession"))return &session_class;
    if(!strcmp(s,"NSURLSessionConfiguration"))return &config_class;
    if(!strcmp(s,"NSURLCache"))return &cache_class;
    if(!strcmp(s,"NSOperationQueue"))return &queue_class;
    if(!strcmp(s,"NSError"))return &error_class;
    if(!strcmp(s,"TASProviderCacheDelegate"))return &other_class;
    if(!strcmp(s,"NSUUID") || !strcmp(s,"NSAutoreleasePool") || !strcmp(s,"NSMutableDictionary") || !strcmp(s,"NSCachedURLResponse"))return &other_class;
    assert(0);return nil;
}
typedef void (*IMP)(void);
static Class objc_allocateClassPair(Class c,const char *s,size_t n){(void)c;(void)s;(void)n;return &other_class;}
static BOOL class_addMethod(Class c,SEL s,IMP i,const char *t){(void)c;(void)s;(void)i;(void)t;return YES;}
static void objc_disposeClassPair(Class c){(void)c;}
static void objc_registerClassPair(Class c){(void)c;}
static bool cache_defer;
static void (*cache_work[2])(void *);static unsigned work_count;
static id cancel_during_lookup;
static bool cache_pause,cache_release;
static unsigned lookups_entered,lookups_live,lookups_live_peak;
static pthread_mutex_t lookup_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t lookup_condition=PTHREAD_COND_INITIALIZER;
#define DISPATCH_QUEUE_PRIORITY_DEFAULT 0
static void *dispatch_get_global_queue(long priority,unsigned long flags){assert(!priority && !flags);return NULL;}
static void dispatch_async_f(void *q,void *context,void (*work)(void *)) {
    assert(!q && !context);if(cache_defer){assert(work_count<2);cache_work[work_count++]=work;}else work(context);
}
static id objc_retain(id o) { return o; }
static void objc_release(id o) { (void)o; }
static int objc_sync_enter(id o) { return pthread_mutex_lock(&o->monitor); }
static int objc_sync_exit(id o) { return pthread_mutex_unlock(&o->monitor); }
static id objc_getAssociatedObject(id o,const void *k) {
    return k==&g_protocol_task_key ? o->task : k==&g_protocol_completed_key ? o->completed :
        k==&image_consumer_key ? o->consumer : k==&image_cache_start_key ? o->cache_start:
        k==&image_cache_completion_key ? (id)o->completion:k==&image_cache_data_key ? o->data:o->stopped;
}
static void objc_setAssociatedObject(id o,const void *k,id value,uintptr_t policy) {
    assert(policy==1 || policy==3);if(k==&g_protocol_task_key)o->task=value;
    else if(k==&g_protocol_completed_key)o->completed=value;
    else if(k==&image_consumer_key)o->consumer=value;
    else if(k==&image_cache_start_key)o->cache_start=value;
    else if(k==&image_cache_data_key)o->data=value;
    else if(k==&image_cache_completion_key) {
        if(value){struct Block *b=(struct Block *)value;assert(policy==3);o->completion=malloc(b->descriptor->size);memcpy(o->completion,b,b->descriptor->size);}
        else o->completion=NULL;
    }
    else { assert(k==&g_protocol_stopped_key);o->stopped=value; }
}
static void protocol_stop_loading(id,SEL);
static id dispatch(id o,SEL s,...) {
    if(!o)return nil;va_list a;va_start(a,s);id r=nil;
    if(!strcmp(s,"request"))r=o->request;
    else if(!strcmp(s,"client"))r=o->client;
    else if(!strcmp(s,"URL"))r=o->url;
    else if(!strcmp(s,"absoluteString"))r=o;
    else if(!strcmp(s,"mutableCopy")) { r=fresh(o->text);r->url=o->url;r->header=o->header;r->headers=o->headers;
        r->method=o->method;r->authorization=o->authorization;r->range=o->range;r->cache_policy=o->cache_policy;
        r->entries=o->entries;memcpy(r->keys,o->keys,sizeof(r->keys));memcpy(r->values,o->values,sizeof(r->values)); }
    else if(!strcmp(s,"setValue:forHTTPHeaderField:")) { o->header=va_arg(a,id);assert(!strcmp(va_arg(a,id)->text,TAS_INTERNAL_HEADER)); }
    else if(!strcmp(s,"valueForHTTPHeaderField:")) { id key=va_arg(a,id);
        r=!strcmp(key->text,TAS_INTERNAL_HEADER) ? o->header : !strcmp(key->text,"Authorization") ? o->authorization :
            !strcmp(key->text,"Range") ? o->range : nil;
        for(unsigned i=0;i<o->entries;i++)if(!strcasecmp(o->keys[i]->text,key->text))r=o->values[i]; }
    else if(!strcmp(s,"objectForKey:")) {id key=va_arg(a,id);for(unsigned i=0;i<o->entries;i++)if(!strcmp(o->keys[i]->text,key->text))r=o->values[i];}
    else if(!strcmp(s,"setObject:forKey:")) {id value=va_arg(a,id),key=va_arg(a,id);unsigned i=0;
        while(i<o->entries && strcmp(o->keys[i]->text,key->text))i++;assert(i<32);
        if(i==o->entries)o->entries++;o->keys[i]=key;o->values[i]=value;}
    else if(!strcmp(s,"UUID"))r=fresh("uuid");
    else if(!strcmp(s,"UUIDString"))r=fresh("test-epoch");
    else if(!strcmp(s,"drain")){}
    else if(!strcmp(s,"appendData:")){id data=va_arg(a,id);char *text=malloc(strlen(o->text)+strlen(data->text)+1);strcpy(text,o->text);strcat(text,data->text);o->text=text;}
    else if(!strcmp(s,"originalRequest"))r=o->request;
    else if(!strcmp(s,"response"))r=o->response;
    else if(!strcmp(s,"data"))r=o->data;
    else if(!strcmp(s,"userInfo"))r=o->info;
    else if(!strcmp(s,"storagePolicy"))r=(id)(uintptr_t)o->cache_policy;
    else if(!strcmp(s,"cachedResponseForRequest:")) {id request=va_arg(a,id);r=o->cache;
        pthread_mutex_lock(&lookup_lock);lookups_entered++;lookups_live++;
        if(lookups_live>lookups_live_peak)lookups_live_peak=lookups_live;
        pthread_cond_broadcast(&lookup_condition);
        while(cache_pause && !cache_release)pthread_cond_wait(&lookup_condition,&lookup_lock);
        lookups_live--;pthread_mutex_unlock(&lookup_lock);
        if(r && strcmp(r->response->url->text,request->url->text))r=nil;
        if(cancel_during_lookup){id p=cancel_during_lookup;cancel_during_lookup=nil;protocol_stop_loading(p,nil);}}
    else if(!strcmp(s,"initWithResponse:data:userInfo:storagePolicy:")) {
        o->response=va_arg(a,id);o->data=va_arg(a,id);o->info=va_arg(a,id);o->cache_policy=(unsigned)va_arg(a,NSUInteger);r=fail_cached_response ? nil:o;
    }
    else if(!strcmp(s,"allHTTPHeaderFields"))r=o->headers;
    else if(!strcmp(s,"HTTPMethod"))r=o->method;
    else if(!strcmp(s,"isEqual:")) { id other=va_arg(a,id);r=(id)(uintptr_t)(other && !strcmp(o->text,other->text)); }
    else if(!strcmp(s,"setCachePolicy:"))o->cache_policy=(unsigned)va_arg(a,NSUInteger);
    else if(!strcmp(s,"cachePolicy"))r=(id)(uintptr_t)o->cache_policy;
    else if(!strcmp(s,"setURL:"))o->url=va_arg(a,id);
    else if(!strcmp(s,"HTTPBody") || !strcmp(s,"HTTPBodyStream"))r=nil;
    else if(!strcmp(s,"defaultSessionConfiguration"))r=&config;
    else if(!strcmp(s,"alloc") || !strcmp(s,"new"))r=fresh("allocated");
    else if(!strcmp(s,"initWithMemoryCapacity:diskCapacity:diskPath:")) {
        assert(va_arg(a,NSUInteger)==32*1024*1024);assert(va_arg(a,NSUInteger)==128*1024*1024);
        assert(!strcmp(va_arg(a,id)->text,"StreamsideProviderImages"));r=o;
    } else if(!strcmp(s,"setURLCache:")){o->cache=va_arg(a,id);assert(o->cache);}
    else if(!strcmp(s,"setHTTPMaximumConnectionsPerHost:"))assert(va_arg(a,NSUInteger)==8);
    /* objc_msgSend uses a fixed floating-point ABI; a C variadic adapter
     * cannot portably read its FP arguments. Values are checked on Apple. */
    else if(!strcmp(s,"setTimeoutIntervalForRequest:") || !strcmp(s,"setTimeoutIntervalForResource:")){}
    else if(!strcmp(s,"setMaxConcurrentOperationCount:"))assert(va_arg(a,NSInteger)==4);
    else if(!strcmp(s,"sessionWithConfiguration:delegate:delegateQueue:")) {
        assert(va_arg(a,id)==&config);assert(va_arg(a,id));assert(va_arg(a,id));r=fresh("image-session");
    }
    else if(!strcmp(s,"sessionWithConfiguration:")) { assert(va_arg(a,id)==&config);r=fresh("session"); }
    else if(!strcmp(s,"dataTaskWithRequest:")) {
        id request=va_arg(a,id);assert(request->header && !strcmp(request->header->text,"1"));
        if(!fail_task){r=fresh("task");r->session=o;r->request=request;r->delegated=true;starts++;}
    }
    else if(!strcmp(s,"dataTaskWithRequest:completionHandler:")) {
        id request=va_arg(a,id);struct Block *b=va_arg(a,void *);
        assert(request->header && !strcmp(request->header->text,"1"));
        if(!fail_task) { r=fresh("task");r->session=o;r->request=request;r->completion=malloc(b->descriptor->size);
            memcpy(r->completion,b,b->descriptor->size);starts++; }
    } else if(!strcmp(s,"resume")) {o->resumes++;
        if(complete_on_resume){struct Block *b=o->completion;
            if(o->delegated){o->response=immediate_response;image_cache_received_data(nil,nil,o->session,o,immediate_data);image_cache_completed(nil,nil,o->session,o,nil);}
            else b->invoke(b,immediate_data,immediate_response,nil);free(b);o->completion=NULL;}}
    else if(!strcmp(s,"cancel"))o->cancels++;
    else if(!strcmp(s,"statusCode"))r=(id)(uintptr_t)(o->status ? o->status:200);
    else if(!strcmp(s,"code"))r=(id)(intptr_t)o->error_code;
    else if(!strcmp(s,"errorWithDomain:code:userInfo:")) {
        assert(!strcmp(va_arg(a,id)->text,"NSURLErrorDomain"));assert(va_arg(a,NSInteger)==-1);assert(!va_arg(a,id));r=fresh("error");
    } else if(!strcmp(s,"URLProtocol:didReceiveResponse:cacheStoragePolicy:")) {
        id protocol=va_arg(a,id);assert(va_arg(a,id));assert(!va_arg(a,NSInteger));o->responses++;
        if(o->stop_on_response)protocol_stop_loading(protocol,"stopLoading");
    } else if(!strcmp(s,"URLProtocol:didLoadData:")) { (void)va_arg(a,id);assert(va_arg(a,id));o->loads++; }
    else if(!strcmp(s,"URLProtocolDidFinishLoading:")) { (void)va_arg(a,id);o->finishes++; }
    else if(!strcmp(s,"URLProtocol:didFailWithError:")) { (void)va_arg(a,id);assert(va_arg(a,id));o->failures++; }
    else { fprintf(stderr,"unexpected selector %s\n",s);assert(0); }
    va_end(a);return r;
}
static void *objc_msgSend=(void *)dispatch;
static id msg0(id o,const char *s) { return dispatch(o,s); }
static id msg1(id o,const char *s,id a) { return dispatch(o,s,a); }
static void vmsg1(id o,const char *s,id a) { dispatch(o,s,a); }
static void vmsg2(id o,const char *s,id a,id b) { dispatch(o,s,a,b); }
static void vmsg3(id o,const char *s,id a,id b,NSInteger c) { dispatch(o,s,a,b,c); }
static NSInteger imsg0(id o,const char *s) { return (NSInteger)(uintptr_t)dispatch(o,s); }
static BOOL bmsg1(id o,const char *s,id a) { return (BOOL)(uintptr_t)dispatch(o,s,a); }
static bool contains(const char *s,const char *part) { return s && strstr(s,part); }
static bool starts_with(const char *s,const char *part) { return s && !strncmp(s,part,strlen(part)); }
static bool is_twitch_hls_url(const char *s) { return contains(s,".m3u8"); }
static bool is_cached_ad_segment(const char *s) { return contains(s,"blank-ad"); }
static bool tas_emotes_is_provider_image_url(const char *s) { return contains(s,"cdn.7tv.app"); }
static bool tas_emotes_is_redirected_image_url(id u) { return u && u->foreground; }
static void tas_emotes_image_result_for_url(const char *u,id d,id r,id e) {
    assert(tas_emotes_is_provider_image_url(u));(void)d;(void)r;(void)e;results++;
}
static void tas_emotes_image_protocol_request(const char *u) { assert(tas_emotes_is_provider_image_url(u)); }
static void tas_emotes_image_protocol_cancel(const char *u) { assert(tas_emotes_is_provider_image_url(u));cancellations++; }
static void tas_diag_metric(int k,int n) { (void)k;(void)n; }
static void tas_diag_log_url(const char *k,const char *u,const char *d) { (void)k;(void)u;(void)d; }
static void cache_twitch_headers(id r) { (void)r; }
static id normalized_graphql_body(id d) { return d; }
static char *remove_query_parameter(const char *s,const char *k) { (void)k;return strdup(s); }
static char *copy_data_text(id d) { return strdup(d->text); }
static char *process_manifest(const char *u,const char *s,bool custom) {
    assert(is_twitch_hls_url(u) && starts_with(s,"#EXTM3U") && !custom);
    pthread_mutex_lock(&manifest_lock);
    if(block_manifest) {
        manifest_entered=true;pthread_cond_broadcast(&manifest_condition);
        while(!release_manifest)pthread_cond_wait(&manifest_condition,&manifest_lock);
    }
    pthread_mutex_unlock(&manifest_lock);
    rewrites++;return strdup("rewritten");
}
static size_t data_length(id d) { return strlen(d->text); }
static id data_from_bytes(const void *p,size_t n) { (void)n;return fresh(p); }
static id http_response(const char *u,NSInteger s,const char *type,size_t n,id original) {
    (void)u;(void)n;assert(s==200 && type);return original ? original:fresh("response");
}
static id blank_video_data(void) { return fresh("blank"); }
'''
MAIN = r'''
static id protocol(const char *url) {
    id p=fresh("protocol");p->request=fresh("request");p->request->url=fresh(url);p->client=fresh("client");return p;
}
static id task_for(id p) {
    for(unsigned i=0;i<IMAGE_FLIGHTS;i++)
        for(unsigned j=0;j<image_flights[i].count;j++)
            if(image_flights[i].consumers[j]==p)return image_flights[i].task;
    return p->task;
}
static void complete(id task,id data,id response,id error) {
    /* Foundation serializes a session's completion handlers on its queue. */
    pthread_mutex_lock(&task->session->monitor);
    struct Block *b=task->completion;
    if(task->delegated){task->response=response;if(data)image_cache_received_data(nil,nil,task->session,task,data);image_cache_completed(nil,nil,task->session,task,error);}
    else b->invoke(b,data,response,error);free(b);task->completion=NULL;
    pthread_mutex_unlock(&task->session->monitor);
}
struct Completion { id task,data,response; };
static void *complete_hls(void *context) {
    struct Completion *c=context;complete(c->task,c->data,c->response,nil);return NULL;
}
int main(void) {
    id image=protocol("https://cdn.7tv.app/emote/a/2x.gif");
    assert(protocol_can_init(nil,nil,image->request));protocol_start_loading(image,nil);
    id task=image->task;assert(task && task->resumes==1 && !image->client->responses && !image->client->finishes);
    assert(!protocol_can_init(nil,nil,task->request)); /* inner request cannot recurse */
    id data=fresh("GIF89a"),response=fresh("response"),error=fresh("error");
    complete(task,data,response,nil);
    assert(!image->task && image->client->responses==1 && image->client->loads==1 && image->client->finishes==1 && results==1);
    id cancelled=protocol("https://cdn.7tv.app/emote/b/2x.gif");protocol_start_loading(cancelled,nil);task=cancelled->task;
    protocol_stop_loading(cancelled,nil);assert(!cancelled->task && task->cancels==0);
    complete(task,data,response,nil);assert(!cancelled->client->responses && !cancelled->client->finishes && results==1);
    protocol_stop_loading(cancelled,nil);assert(task->cancels==0 && cancellations==1); /* stop is idempotent */
    unsigned before=starts;id early=protocol("https://cdn.7tv.app/emote/c/2x.gif");
    protocol_stop_loading(early,nil);protocol_start_loading(early,nil);assert(starts==before && !early->task);
    id reentrant=protocol("https://cdn.7tv.app/emote/d/2x.gif");reentrant->client->stop_on_response=true;
    protocol_start_loading(reentrant,nil);task=reentrant->task;complete(task,data,response,nil);
    assert(reentrant->client->responses==1 && !reentrant->client->loads && !reentrant->client->finishes && task->cancels==0 && cancellations==1);
    id failed=protocol("https://cdn.7tv.app/emote/e/2x.gif");protocol_start_loading(failed,nil);
    complete(failed->task,nil,nil,error);assert(failed->client->failures==1 && !failed->client->finishes && !failed->task);
    fail_task=true;id unavailable=protocol("https://cdn.7tv.app/emote/f/2x.gif");protocol_start_loading(unavailable,nil);
    assert(unavailable->client->failures==1 && !unavailable->task);fail_task=false;
    id hls=protocol("https://video.example/live.m3u8");protocol_start_loading(hls,nil);
    assert(!hls->client->responses && !rewrites);id manifest=fresh("#EXTM3U\n#EXT-X-VERSION:3");
    complete(hls->task,manifest,response,nil);assert(rewrites==1 && hls->client->loads==1 && hls->client->finishes==1);
    id blank=protocol("https://video.example/blank-ad.ts");before=starts;protocol_start_loading(blank,nil);
    assert(starts==before && blank->client->loads==1 && blank->client->finishes==1);
    /* Hold an HLS completion in alternate-network processing. Images must
     * complete before we release it, with both sessions retaining reuse. The
     * alarm makes a shared-queue regression fail instead of hanging tests. */
    alarm(10);block_manifest=true;
    id blocked=protocol("https://video.example/ad.m3u8");protocol_start_loading(blocked,nil);
    struct Completion c={blocked->task,manifest,response};pthread_t thread;
    assert(!pthread_create(&thread,NULL,complete_hls,&c));
    pthread_mutex_lock(&manifest_lock);
    while(!manifest_entered)pthread_cond_wait(&manifest_condition,&manifest_lock);
    pthread_mutex_unlock(&manifest_lock);
    id independent=protocol("https://cdn.7tv.app/emote/independent/2x.gif");protocol_start_loading(independent,nil);
    assert(independent->task->session==task->session);
    assert(blocked->task->session==g_protocol_session);
    id image_transport=independent->task->session;
    complete(independent->task,data,response,nil);
    assert(independent->client->loads==1 && independent->client->finishes==1 && !blocked->client->finishes);
    assert(image_transport!=blocked->task->session);
    pthread_mutex_lock(&manifest_lock);release_manifest=true;pthread_cond_broadcast(&manifest_condition);pthread_mutex_unlock(&manifest_lock);
    assert(!pthread_join(thread,NULL) && blocked->client->finishes==1);alarm(0);
    /* Same asset across chat/composer/library has one task. Removing one
     * consumer does not cancel it; delivery skips just that consumer. */
    id one=protocol("https://cdn.7tv.app/emote/shared/2x.gif"),
       two=protocol("https://cdn.7tv.app/emote/shared/2x.gif"),
       three=protocol("https://cdn.7tv.app/emote/shared/2x.gif");
    before=starts;protocol_start_loading(one,nil);protocol_start_loading(two,nil);protocol_start_loading(three,nil);
    assert(starts==before+1 && one->task==two->task && two->task==three->task);
    task=one->task;protocol_stop_loading(one,nil);assert(!task->cancels);
    complete(task,data,response,nil);
    assert(!one->client->loads && two->client->finishes==1 && three->client->finishes==1);
    /* Last cancellation detaches the client but leaves the bounded transfer
     * running. A remounted view rejoins it instead of starting over. */
    one=protocol("https://cdn.7tv.app/emote/retry/2x.gif");
    two=protocol("https://cdn.7tv.app/emote/retry/2x.gif");
    protocol_start_loading(one,nil);protocol_start_loading(two,nil);task=one->task;
    protocol_stop_loading(one,nil);assert(!task->cancels);protocol_stop_loading(two,nil);assert(!task->cancels);
    before=starts;three=protocol("https://cdn.7tv.app/emote/retry/2x.gif");protocol_start_loading(three,nil);
    assert(three->task==task && starts==before && image_rejoined==1);
    complete(task,data,response,nil);assert(three->client->finishes==1 && !one->client->loads && !two->client->loads);
    /* Request normalization never alters the outer request, and keeps HLS on
     * its original caching path. Both cached and cold image requests use the
     * HTTP cache's validation/expiry rules rather than forced reloads. */
    one=protocol("https://cdn.7tv.app/emote/cache/2x.gif");one->request->cache_policy=1;
    protocol_start_loading(one,nil);assert(one->request->cache_policy==1 && one->task->request->cache_policy==0);
    complete(one->task,data,response,nil);
    /* Header variants must not share a task; non-GET/range/auth requests
     * retain their original cache policy and independent transport. */
    one=protocol("https://cdn.7tv.app/emote/vary/2x.gif");two=protocol("https://cdn.7tv.app/emote/vary/2x.gif");
    one->request->headers=fresh("Accept: image/gif");two->request->headers=fresh("Accept: image/webp");
    protocol_start_loading(one,nil);protocol_start_loading(two,nil);assert(one->task!=two->task);
    complete(one->task,data,response,nil);complete(two->task,data,response,nil);
    for(unsigned variant=0;variant<3;variant++) {
        one=protocol("https://cdn.7tv.app/emote/special/2x.gif");two=protocol("https://cdn.7tv.app/emote/special/2x.gif");
        one->request->cache_policy=two->request->cache_policy=1;
        if(variant==0)one->request->method=two->request->method=fresh("POST");
        if(variant==1)one->request->authorization=two->request->authorization=fresh("private");
        if(variant==2)one->request->range=two->request->range=fresh("bytes=0-9");
        protocol_start_loading(one,nil);protocol_start_loading(two,nil);assert(one->task!=two->task);
        assert(one->task->request->cache_policy==1 && two->task->request->cache_policy==1);
        complete(one->task,data,response,nil);complete(two->task,data,response,nil);
    }
    /* Library traffic cannot fill the two reserved foreground slots. Cancel a
     * queued view before admission: it must never create a download. */
    id background[8];char background_urls[8][96];before=starts;
    for(unsigned i=0;i<8;i++) {
        snprintf(background_urls[i],sizeof(background_urls[i]),"https://cdn.7tv.app/emote/background%u/2x.gif",i);
        background[i]=protocol(background_urls[i]);protocol_start_loading(background[i],nil);
    }
    assert(starts==before+6 && image_active==6 && image_background_active==6);
    assert(!task_for(background[6]) && !task_for(background[7]));
    protocol_stop_loading(background[7],nil);assert(image_queued_cancelled==1 && starts==before+6);
    id foreground[3];char foreground_urls[3][96];
    for(unsigned i=0;i<3;i++) {
        snprintf(foreground_urls[i],sizeof(foreground_urls[i]),"https://cdn.7tv.app/emote/foreground%u/2x.gif",i);
        foreground[i]=protocol(foreground_urls[i]);foreground[i]->request->url->foreground=true;
        protocol_start_loading(foreground[i],nil);
    }
    assert(starts==before+8 && image_active==8 && !task_for(foreground[2]));
    complete(task_for(background[0]),data,response,nil);
    assert(task_for(foreground[2]) && !task_for(background[6])); /* foreground goes first */
    for(unsigned i=1;i<7;i++) {assert(task_for(background[i]));complete(task_for(background[i]),data,response,nil);}
    for(unsigned i=0;i<3;i++)complete(task_for(foreground[i]),data,response,nil);
    assert(!image_active && !image_background_active && !background[7]->client->finishes);
    /* A foreground join promotes an existing queued library flight without
     * opening a duplicate task; reserved capacity is immediately usable. */
    for(unsigned i=0;i<7;i++) {background[i]=protocol(background_urls[i]);protocol_start_loading(background[i],nil);}
    assert(!task_for(background[6]));one=protocol(background_urls[6]);one->request->url->foreground=true;
    before=starts;protocol_start_loading(one,nil);
    assert(starts==before+1 && task_for(one)==task_for(background[6]) && image_active==7);
    for(unsigned i=0;i<7;i++)complete(task_for(background[i]),data,response,nil);
    assert(one->client->finishes==1 && !image_active);
    /* A full queue produces a normal client error, never unbounded independent
     * task fallback. Admission remains bounded as the queue drains. */
    id crowded[IMAGE_FLIGHTS+1];char urls[IMAGE_FLIGHTS+1][96];
    for(unsigned i=0;i<IMAGE_FLIGHTS+1;i++) {
        snprintf(urls[i],sizeof(urls[i]),"https://cdn.7tv.app/emote/budget%u/2x.gif",i);
        crowded[i]=protocol(urls[i]);protocol_start_loading(crowded[i],nil);
    }
    assert(image_active==6 && crowded[IMAGE_FLIGHTS]->client->failures==1 && image_refused==1);
    for(unsigned i=0;i<IMAGE_FLIGHTS;i++) {
        assert(task_for(crowded[i]));complete(task_for(crowded[i]),data,response,nil);
        assert(crowded[i]->client->finishes==1 && image_active<=6);
    }
    /* Consumer cap makes another bounded flight without starving requests. */
    id viewers[IMAGE_CONSUMERS+1];before=starts;
    for(unsigned i=0;i<IMAGE_CONSUMERS+1;i++) {
        viewers[i]=protocol("https://cdn.7tv.app/emote/consumer-budget/2x.gif");protocol_start_loading(viewers[i],nil);
    }
    assert(starts==before+2);
    complete(viewers[0]->task,data,response,nil);complete(viewers[IMAGE_CONSUMERS]->task,data,response,nil);
    for(unsigned i=0;i<IMAGE_CONSUMERS+1;i++)assert(viewers[i]->client->finishes==1);
    for(unsigned i=0;i<3;i++) {
        one=protocol("https://cdn.7tv.app/emote/errors/2x.gif");protocol_start_loading(one,nil);
        error->error_code=i==0 ? -999 : i==1 ? -1001 : -42;
        complete(one->task,nil,nil,error);assert(one->client->failures==1);
    }
    assert(image_error_cancelled==1 && image_error_timeout==1 && image_error_other==3);
    /* A late callback cannot consume a newly admitted generation in the same
     * slot. Missing-task callbacks must drain a queue without recursive pumps. */
    one=protocol("https://cdn.7tv.app/emote/generation-old/2x.gif");protocol_start_loading(one,nil);
    unsigned slot=0;while(image_flights[slot].consumers[0]!=one)slot++;
    uint64_t generation=image_flights[slot].generation;complete(task_for(one),data,response,nil);
    two=protocol("https://cdn.7tv.app/emote/generation-new/2x.gif");protocol_start_loading(two,nil);
    assert(image_flights[slot].consumers[0]==two);
    image_flight_complete(slot,generation,data,response,nil);
    assert(!two->client->loads && image_active==1);complete(task_for(two),data,response,nil);
    for(unsigned i=0;i<6;i++) {background[i]=protocol(background_urls[i]);protocol_start_loading(background[i],nil);}
    id no_tasks[32];char no_task_urls[32][96];
    for(unsigned i=0;i<32;i++) {
        snprintf(no_task_urls[i],sizeof(no_task_urls[i]),"https://cdn.7tv.app/emote/no-task%u/2x.gif",i);
        no_tasks[i]=protocol(no_task_urls[i]);protocol_start_loading(no_tasks[i],nil);assert(!task_for(no_tasks[i]));
    }
    before=starts;fail_task=true;complete(task_for(background[0]),data,response,nil);fail_task=false;
    assert(starts==before && image_active==5 && image_error_other==35);
    for(unsigned i=0;i<32;i++)assert(no_tasks[i]->client->failures==1 && !no_tasks[i]->client->loads);
    for(unsigned i=1;i<6;i++)complete(task_for(background[i]),data,response,nil);
    assert(!image_active && !image_background_active);
    char stats[2048];tas_image_transport_status(stats,sizeof(stats));
    assert(strstr(stats,"Shared loads/coalesced/completed/errors:") && strstr(stats,"excludes queue wait and image decoding"));
    assert(!strstr(stats,"shared/2x") && image_joined==5+IMAGE_CONSUMERS-1);
    return 0;
}
'''


class ProtocolTests(unittest.TestCase):
    def test_async_delivery_cancellation_recursion_errors_and_hls_rewrite(self):
        self.run_transport(False)

    def test_demand_probes_preserve_production_lifecycle_and_bounds(self):
        self.run_transport(True)

    def run_transport(self, diagnostic, main_override=None):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        source = (ROOT / "src/Streamside.c").read_text()
        functions = source[source.index("/* Callback delivery and stopLoading"):
                           source.index("static id protocol_canonical_request")]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            harness, binary = root / "protocol.c", root / "protocol"
            stubs = '''
void tas_demand_request(void *r,unsigned s){(void)r;(void)s;}
unsigned tas_demand_url_scope(void *u){(void)u;return 0;}
void *tas_demand_delegate(void){return NULL;}
void tas_demand_transport(unsigned a,unsigned q,unsigned c,uint64_t n){(void)a;(void)q;(void)c;(void)n;}
''' if diagnostic else ''
            main = main_override or MAIN
            if diagnostic and not main_override:
                main = main.replace('    return 0;\n}', '''
    assert(demand_flight_peak==512 && demand_queue_peak>=506 && demand_consumer_peak>=512);
    assert(demand_consumer_full && demand_header_mismatch && demand_url_matches);
    assert(demand_detached_time[0]+demand_detached_time[1]+demand_detached_time[2]+demand_detached_time[3]);
    assert(demand_rejoin_time[0]+demand_rejoin_time[1]+demand_rejoin_time[2]+demand_rejoin_time[3]);
    assert(strstr(stats,"Passive flight registry") && !strstr(stats,"cdn.7tv.app"));
    return 0;
}''')
            harness.write_text(PRELUDE + '\n#include "TASImageDemand.h"\n' + stubs + functions + main)
            built = subprocess.run([zig, "cc", "-fblocks", "-Wall", "-Wextra", "-Werror",
                                    '-DTAS_IMAGE_DEMAND_DIAGNOSTIC='+str(int(diagnostic)), '-I', str(ROOT/'src'),
                                    str(harness), "-pthread", "-o", str(binary)], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([binary], capture_output=True, text=True, timeout=60)
            self.assertEqual(ran.returncode, 0, ran.stderr)
