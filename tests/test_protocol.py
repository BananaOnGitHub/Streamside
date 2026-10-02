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
    id request,client,task,stopped,url,header;
    struct Block *completion;
    unsigned resumes,cancels,responses,loads,finishes,failures;
    bool stop_on_response;
    pthread_mutex_t monitor;
};
static struct Fake objects[128],session_class,config_class,error_class,session,config;
static size_t used;
static unsigned starts,results,rewrites;
static bool fail_task;
static char g_protocol_task_key,g_protocol_stopped_key;
static id g_protocol_session;
static pthread_mutex_t g_lock=PTHREAD_MUTEX_INITIALIZER;
void *_NSConcreteStackBlock[32];
static id fresh(const char *text) {
    assert(used<128);id o=&objects[used++];o->text=text;
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
    assert(!strcmp(s,"NSError"));return &error_class;
}
static id objc_retain(id o) { return o; }
static void objc_release(id o) { (void)o; }
static int objc_sync_enter(id o) { return pthread_mutex_lock(&o->monitor); }
static int objc_sync_exit(id o) { return pthread_mutex_unlock(&o->monitor); }
static id objc_getAssociatedObject(id o,const void *k) { return k==&g_protocol_task_key ? o->task:o->stopped; }
static void objc_setAssociatedObject(id o,const void *k,id value,uintptr_t policy) {
    assert(policy==1);if(k==&g_protocol_task_key)o->task=value;else { assert(k==&g_protocol_stopped_key);o->stopped=value; }
}
static void protocol_stop_loading(id,SEL);
static id dispatch(id o,SEL s,...) {
    if(!o)return nil;va_list a;va_start(a,s);id r=nil;
    if(!strcmp(s,"request"))r=o->request;
    else if(!strcmp(s,"client"))r=o->client;
    else if(!strcmp(s,"URL"))r=o->url;
    else if(!strcmp(s,"absoluteString"))r=o;
    else if(!strcmp(s,"mutableCopy")) { r=fresh(o->text);r->url=o->url;r->header=o->header; }
    else if(!strcmp(s,"setValue:forHTTPHeaderField:")) { o->header=va_arg(a,id);assert(!strcmp(va_arg(a,id)->text,TAS_INTERNAL_HEADER)); }
    else if(!strcmp(s,"valueForHTTPHeaderField:")) { (void)va_arg(a,id);r=o->header; }
    else if(!strcmp(s,"setURL:"))o->url=va_arg(a,id);
    else if(!strcmp(s,"HTTPBody"))r=nil;
    else if(!strcmp(s,"defaultSessionConfiguration"))r=&config;
    else if(!strcmp(s,"sessionWithConfiguration:")) { assert(va_arg(a,id)==&config);r=&session; }
    else if(!strcmp(s,"dataTaskWithRequest:completionHandler:")) {
        id request=va_arg(a,id);struct Block *b=va_arg(a,void *);
        assert(request->header && !strcmp(request->header->text,"1"));
        if(!fail_task) { r=fresh("task");r->request=request;r->completion=malloc(b->descriptor->size);
            memcpy(r->completion,b,b->descriptor->size);starts++; }
    } else if(!strcmp(s,"resume"))o->resumes++;
    else if(!strcmp(s,"cancel"))o->cancels++;
    else if(!strcmp(s,"statusCode"))r=(id)(uintptr_t)200;
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
static id (*objc_msgSend)(id,SEL,...)=dispatch;
static id msg0(id o,const char *s) { return dispatch(o,s); }
static id msg1(id o,const char *s,id a) { return dispatch(o,s,a); }
static void vmsg1(id o,const char *s,id a) { dispatch(o,s,a); }
static void vmsg2(id o,const char *s,id a,id b) { dispatch(o,s,a,b); }
static void vmsg3(id o,const char *s,id a,id b,NSInteger c) { dispatch(o,s,a,b,c); }
static NSInteger imsg0(id o,const char *s) { return (NSInteger)(uintptr_t)dispatch(o,s); }
static bool contains(const char *s,const char *part) { return s && strstr(s,part); }
static bool starts_with(const char *s,const char *part) { return s && !strncmp(s,part,strlen(part)); }
static bool is_twitch_hls_url(const char *s) { return contains(s,".m3u8"); }
static bool is_cached_ad_segment(const char *s) { return contains(s,"blank-ad"); }
static bool tas_emotes_is_provider_image_url(const char *s) { return contains(s,"cdn.7tv.app"); }
static void tas_emotes_image_result(id d,id r,id e) { (void)d;(void)r;(void)e;results++; }
static void tas_emotes_image_protocol_request(void) {}
static void tas_diag_metric(int k,int n) { (void)k;(void)n; }
static void tas_diag_log_url(const char *k,const char *u,const char *d) { (void)k;(void)u;(void)d; }
static void cache_twitch_headers(id r) { (void)r; }
static id normalized_graphql_body(id d) { return d; }
static char *remove_query_parameter(const char *s,const char *k) { (void)k;return strdup(s); }
static char *copy_data_text(id d) { return strdup(d->text); }
static char *process_manifest(const char *u,const char *s,bool custom) {
    assert(is_twitch_hls_url(u) && starts_with(s,"#EXTM3U") && !custom);rewrites++;return strdup("rewritten");
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
static void complete(id task,id data,id response,id error) {
    struct Block *b=task->completion;b->invoke(b,data,response,error);free(b);task->completion=NULL;
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
    protocol_stop_loading(cancelled,nil);assert(!cancelled->task && task->cancels==1);
    complete(task,data,response,nil);assert(!cancelled->client->responses && !cancelled->client->finishes && results==1);
    protocol_stop_loading(cancelled,nil);assert(task->cancels==1); /* stop is idempotent */
    unsigned before=starts;id early=protocol("https://cdn.7tv.app/emote/c/2x.gif");
    protocol_stop_loading(early,nil);protocol_start_loading(early,nil);assert(starts==before && !early->task);
    id reentrant=protocol("https://cdn.7tv.app/emote/d/2x.gif");reentrant->client->stop_on_response=true;
    protocol_start_loading(reentrant,nil);task=reentrant->task;complete(task,data,response,nil);
    assert(reentrant->client->responses==1 && !reentrant->client->loads && !reentrant->client->finishes && task->cancels==1);
    id failed=protocol("https://cdn.7tv.app/emote/e/2x.gif");protocol_start_loading(failed,nil);
    complete(failed->task,nil,nil,error);assert(failed->client->failures==1 && !failed->client->finishes && !failed->task);
    fail_task=true;id unavailable=protocol("https://cdn.7tv.app/emote/f/2x.gif");protocol_start_loading(unavailable,nil);
    assert(unavailable->client->failures==1 && !unavailable->task);fail_task=false;
    id hls=protocol("https://video.example/live.m3u8");protocol_start_loading(hls,nil);
    assert(!hls->client->responses && !rewrites);id manifest=fresh("#EXTM3U\n#EXT-X-VERSION:3");
    complete(hls->task,manifest,response,nil);assert(rewrites==1 && hls->client->loads==1 && hls->client->finishes==1);
    id blank=protocol("https://video.example/blank-ad.ts");before=starts;protocol_start_loading(blank,nil);
    assert(starts==before && blank->client->loads==1 && blank->client->finishes==1);
    return 0;
}
'''


class ProtocolTests(unittest.TestCase):
    def test_async_delivery_cancellation_recursion_errors_and_hls_rewrite(self):
        zig = os.environ.get("ZIG") or shutil.which("zig")
        self.assertTrue(zig)
        source = (ROOT / "src/Streamside.c").read_text()
        functions = source[source.index("/* Callback delivery and stopLoading"):
                           source.index("static id protocol_canonical_request")]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            harness, binary = root / "protocol.c", root / "protocol"
            harness.write_text(PRELUDE + functions + MAIN)
            built = subprocess.run([zig, "cc", "-fblocks", "-Wall", "-Wextra", "-Werror",
                                    str(harness), "-pthread", "-o", str(binary)], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([binary], capture_output=True, text=True)
            self.assertEqual(ran.returncode, 0, ran.stderr)
