"""Actual cache delegate, lookup lane, flight scheduler and protocol callbacks.

The runtime adapter controls Foundation cache results and worker execution;
it does not replace the production snapshot/cache/HTTP decision logic.
No Apple Foundation/URLCache integration is claimed by these Linux tests.
"""
import unittest
import test_protocol as protocol_tests

HELPERS = protocol_tests.MAIN[:protocol_tests.MAIN.index('int main(void)')]
CACHE_MAIN = r'''
static void drain_cache(void) {
    while(work_count){void (*work)(void *)=cache_work[--work_count];work(NULL);}
    assert(!image_cache_workers && !image_cache_groups);
}
static void header(id object,const char *key,const char *value) {
    vmsg2(object,"setObject:forKey:",nsstr(value),nsstr(key));
}
static id prime(id p,const char *control,const char *age) {
    id request=msg0(p->request,"mutableCopy");vmsg2(request,"setValue:forHTTPHeaderField:",nsstr("1"),nsstr(TAS_INTERNAL_HEADER));
    id task=fresh("prime-task");task->request=request;image_cache_mark_task(task);
    id proposed=fresh("cached"),response=fresh("response");proposed->response=response;response->url=request->url;
    proposed->data=fresh("GIF89a");header(response,"Cache-Control",control);
    time_t now=time(NULL);struct tm date;gmtime_r(&now,&date);char text[64];
    strftime(text,sizeof(text),"%a, %d %b %Y %H:%M:%S GMT",&date);header(response,"Date",text);
    if(age)header(response,"Age",age);
    id stored=nil;id *output=&stored;
    image_cache_proposed(nil,nil,nil,task,proposed,(id)^(id result){*output=result;});
    assert(stored);image_cache_store->cache=stored;return stored;
}
static void clear_cache(void){image_cache_store->cache=nil;}
static void *thread_cache(void *work){((void (*)(void *))work)(NULL);return NULL;}
int main(void) {
    (void)complete_hls;
    assert(protocol_can_init(nil,nil,protocol("https://cdn.7tv.app/emote/probe/2x.gif")->request));
    cache_defer=true;id bootstrap=protocol("https://cdn.7tv.app/emote/bootstrap/2x.gif");
    protocol_start_loading(bootstrap,nil);assert(!image_cache_store && !image_cache_session && !config.cache && !starts);
    protocol_stop_loading(bootstrap,nil);drain_cache();cache_defer=false;
    assert(image_cache_store && !starts && !bootstrap->client->responses);
    /* All eight tasks remain deliberately stalled. Two foreground tasks
     * consume reserved slots; neither hits nor cache probes make a ninth. */
    id stalled[IMAGE_FLIGHTS];char urls[IMAGE_FLIGHTS][96];
    for(unsigned i=0;i<IMAGE_FLIGHTS;i++) {
        snprintf(urls[i],sizeof(urls[i]),"https://cdn.7tv.app/emote/stalled%u/2x.gif",i);
        stalled[i]=protocol(urls[i]);stalled[i]->request->url->foreground=i>=6 && i<8;
        protocol_start_loading(stalled[i],nil);
    }
    assert(image_active==8 && image_background_active==6 && image_refused==0);
    id hot=protocol("https://cdn.7tv.app/emote/hot/2x.gif");id cached=prime(hot,"public, max-age=3600, must-revalidate","1");
    unsigned before=starts;uint64_t refusals=image_refused,checks=image_cache_checks;
    protocol_start_loading(hot,nil);
    assert(hot->client->loads==1 && hot->client->finishes==1 && !hot->task && !hot->client->failures);
    assert(starts==before && image_active==8 && image_refused==refusals && image_cache_checks==checks+1 && image_cache_hits==1);
    /* Retire all stalled consumers: queued flights do not start, detached
     * eight still occupy exactly eight slots until their completions. */
    id tasks[8];for(unsigned i=0;i<8;i++)tasks[i]=task_for(stalled[i]);
    for(unsigned i=0;i<IMAGE_FLIGHTS;i++)protocol_stop_loading(stalled[i],nil);
    for(unsigned i=0;i<8;i++)complete(tasks[i],cached->data,cached->response,nil);
    assert(!image_active && starts==before);
    /* Concurrent cached consumers share ONE deferred operation. Stopping one
     * cannot cancel the other. Deliver exactly once; no URLSessionTask. */
    cache_defer=true;hot=protocol("https://cdn.7tv.app/emote/hot/2x.gif");
    id other=protocol(hot->request->url->text);checks=image_cache_checks;before=starts;
    protocol_start_loading(hot,nil);protocol_start_loading(other,nil);
    assert(image_cache_groups==1 && image_cache_joined==1 && work_count<=2);
    protocol_stop_loading(hot,nil);drain_cache();
    assert(!hot->client->responses && other->client->finishes==1 && other->client->loads==1 && starts==before && image_cache_checks==checks+1);
    /* Cancellation before lookup releases its queued group. During lookup
     * removes its consumer; a miss must not subsequently admit networking. */
    hot=protocol(other->request->url->text);protocol_start_loading(hot,nil);protocol_stop_loading(hot,nil);
    checks=image_cache_checks;drain_cache();assert(image_cache_checks==checks && !hot->client->responses);
    hot=protocol(other->request->url->text);protocol_start_loading(hot,nil);cancel_during_lookup=hot;
    drain_cache();assert(!hot->client->responses && !task_for(hot) && starts==before);
    clear_cache();hot=protocol("https://cdn.7tv.app/emote/cancel-miss/2x.gif");protocol_start_loading(hot,nil);cancel_during_lookup=hot;
    drain_cache();assert(!task_for(hot) && starts==before && !hot->client->failures);
    /* Two simultaneous misses converge on one existing flight, independently
     * cancellable and with foreground promotion retained across handoff. */
    hot=protocol("https://cdn.7tv.app/emote/miss/2x.gif");other=protocol(hot->request->url->text);other->request->url->foreground=true;
    protocol_start_loading(hot,nil);protocol_start_loading(other,nil);drain_cache();
    assert(starts==before+1 && task_for(hot)==task_for(other) && image_active==1 && image_background_active==0);
    protocol_stop_loading(hot,nil);complete(task_for(other),cached->data,cached->response,nil);
    assert(!hot->client->loads && other->client->finishes==1);
    /* HTTP uncertainty/revalidation never delivers a candidate directly.
     * Actual conditional/304 processing is still Foundation's responsibility. */
    cache_defer=false;
    const char *controls[]={"max-age=0","max-age=3600, no-cache","max-age=3600, no-store","max-age=3600, unknown-extension","max-age=3600, max-age=3600"};
    for(unsigned i=0;i<5;i++) {
        hot=protocol("https://cdn.7tv.app/emote/stale/2x.gif");prime(hot,controls[i],NULL);before=starts;
        protocol_start_loading(hot,nil);assert(starts==before+1 && !hot->client->loads && task_for(hot)->request->cache_policy==0);
        complete(task_for(hot),cached->data,cached->response,nil);assert(hot->client->finishes==1);
    }
    const char *fields[]={"Vary","Content-Range","Age","Pragma"};const char *values[]={"*","bytes 0-2/3","invalid","no-cache"};
    for(unsigned i=0;i<4;i++) {
        hot=protocol("https://cdn.7tv.app/emote/restricted/2x.gif");id item=prime(hot,"max-age=3600",i==2 ? "invalid":NULL);header(item->response,fields[i],values[i]);
        before=starts;protocol_start_loading(hot,nil);assert(starts==before+1 && !hot->client->loads);
        complete(task_for(hot),cached->data,cached->response,nil);
    }
    /* Equal explicit Vary headers are reusable; differing headers never are. */
    hot=protocol("https://cdn.7tv.app/emote/variant/2x.gif");hot->request->headers=fresh("Accept:image/gif");
    id item=prime(hot,"max-age=3600",NULL);header(item->response,"Vary","Accept");
    before=starts;protocol_start_loading(hot,nil);assert(hot->client->finishes==1 && starts==before);
    other=protocol(hot->request->url->text);other->request->headers=fresh("Accept:image/webp");protocol_start_loading(other,nil);
    assert(starts==before+1 && !other->client->loads);complete(task_for(other),cached->data,cached->response,nil);
    /* Unannotated, old epoch, expired metadata and backward clock cannot hit. */
    const char *metadata[]={"TASCacheEpoch","TASCacheRemaining","TASCacheTick","TASCacheWall"};
    for(unsigned i=0;i<5;i++) {
        hot=protocol("https://cdn.7tv.app/emote/metadata/2x.gif");item=prime(hot,"max-age=3600",NULL);
        if(i==0)item->info=nil;else header(item->info,metadata[i-1],i==1 ? "old-epoch":i==2 ? "0":"999999999999");
        before=starts;protocol_start_loading(hot,nil);assert(starts==before+1);complete(task_for(hot),cached->data,cached->response,nil);
    }
    /* Explicit request restrictions bypass lookup, keep their original policy,
     * remain bounded/coalesced when public, and never borrow cached bytes. */
    const char *request_fields[]={"Cache-Control","Pragma","If-None-Match","If-Modified-Since","If-Range"};
    for(unsigned i=0;i<5;i++) {
        hot=protocol("https://cdn.7tv.app/emote/request/2x.gif");prime(hot,"max-age=3600",NULL);header(hot->request,request_fields[i],"restricted");
        checks=image_cache_checks;before=starts;protocol_start_loading(hot,nil);
        assert(starts==before+1 && image_cache_checks==checks && !hot->client->loads);
        complete(task_for(hot),cached->data,cached->response,nil);
    }
    for(unsigned policy=2;policy<=5;policy++) {
        hot=protocol("https://cdn.7tv.app/emote/policy/2x.gif");prime(hot,"max-age=3600",NULL);hot->request->cache_policy=policy;
        checks=image_cache_checks;protocol_start_loading(hot,nil);assert(image_cache_checks==checks && task_for(hot)->request->cache_policy==policy);
        complete(task_for(hot),cached->data,cached->response,nil);
    }
    /* Reentrant stop from cached response must suppress data and finish. */
    hot=protocol("https://cdn.7tv.app/emote/reentrant/2x.gif");prime(hot,"max-age=3600",NULL);hot->client->stop_on_response=true;
    protocol_start_loading(hot,nil);assert(hot->client->responses==1 && !hot->client->loads && !hot->client->finishes);
    /* Saturate the bounded cache registry with workers paused. Cancellation
     * recovers capacity immediately; neither retries nor extra workers spawn. */
    clear_cache();cache_defer=true;
    for(unsigned i=0;i<IMAGE_CACHE_GROUPS;i++){stalled[i]=protocol(urls[i]);protocol_start_loading(stalled[i],nil);}
    assert(image_cache_groups==512 && image_cache_workers==2 && work_count==2);
    for(unsigned i=0;i<IMAGE_CACHE_GROUPS;i++)protocol_stop_loading(stalled[i],nil);
    assert(!image_cache_groups);hot=protocol("https://cdn.7tv.app/emote/recovered/2x.gif");prime(hot,"max-age=3600",NULL);
    protocol_start_loading(hot,nil);drain_cache();assert(hot->client->finishes==1 && !image_active);
    assert(image_cache_worker_peak==2 && image_cache_peak==512);
    /* Real pthread execution of both bounded worker pumps. Cancel active
     * probes, rejoin one, then release them: no late/duplicate delivery and
     * no transfer for the abandoned miss. Repeat open/close/remount churn. */
    for(unsigned cycle=0;cycle<20;cycle++) {
        hot=protocol("https://cdn.7tv.app/emote/thread-hot/2x.gif");prime(hot,"max-age=3600",NULL);
        other=protocol("https://cdn.7tv.app/emote/thread-miss/2x.gif");before=starts;
        pthread_mutex_lock(&lookup_lock);cache_pause=true;cache_release=false;lookups_entered=0;pthread_mutex_unlock(&lookup_lock);
        protocol_start_loading(hot,nil);protocol_start_loading(other,nil);assert(work_count==2);
        pthread_t workers[2];for(unsigned i=0;i<2;i++)assert(!pthread_create(&workers[i],NULL,thread_cache,(void *)cache_work[--work_count]));
        pthread_mutex_lock(&lookup_lock);while(lookups_entered<2)pthread_cond_wait(&lookup_condition,&lookup_lock);pthread_mutex_unlock(&lookup_lock);
        protocol_stop_loading(hot,nil);protocol_stop_loading(other,nil);
        id rejoined=protocol(hot->request->url->text);protocol_start_loading(rejoined,nil);
        assert(!work_count && image_cache_workers==2);
        pthread_mutex_lock(&lookup_lock);cache_release=true;pthread_cond_broadcast(&lookup_condition);pthread_mutex_unlock(&lookup_lock);
        for(unsigned i=0;i<2;i++)assert(!pthread_join(workers[i],NULL));
        assert(!hot->client->responses && !other->client->responses && rejoined->client->loads==1 && rejoined->client->finishes==1);
        assert(starts==before && !image_cache_groups && !image_cache_workers && !image_active);
    }
    assert(lookups_live_peak==2);
    clear_cache();hot=protocol("https://cdn.7tv.app/emote/instant-miss/2x.gif");other=protocol(hot->request->url->text);
    before=starts;protocol_start_loading(hot,nil);protocol_start_loading(other,nil);
    immediate_data=cached->data;immediate_response=cached->response;complete_on_resume=true;
    drain_cache();complete_on_resume=false;
    assert(starts==before+1 && hot->client->loads==1 && other->client->loads==1);
    assert(hot->client->finishes==1 && other->client->finishes==1 && !image_active && !image_cache_consumers);
    char status[4096];tas_image_transport_status(status,sizeof(status));assert(strstr(status,"Cache-hit admission-to-delivery"));
    assert(!strstr(status,"cdn.7tv.app") && !strstr(status,"Accept:") && !strstr(status,"test-epoch"));
    return 0;
}
'''

class CacheProtocolTests(unittest.TestCase):
    def test_production_cache_first_lifecycle(self):
        protocol_tests.ProtocolTests().run_transport(False, HELPERS+CACHE_MAIN)

    def test_production_cache_first_with_demand_probes(self):
        protocol_tests.ProtocolTests().run_transport(True, HELPERS+CACHE_MAIN)
