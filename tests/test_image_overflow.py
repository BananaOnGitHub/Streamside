"""Actual production overflow lifecycle with stalled tasks and controlled expiry."""
import unittest
import test_protocol as protocol
import test_cache_protocol as cache

HELPERS = cache.HELPERS + cache.CACHE_MAIN[:cache.CACHE_MAIN.index('int main(void)')] + r'''
static id crowded[IMAGE_FLIGHTS];
static void saturate(void) {
    char url[96];clear_cache();
    for(unsigned i=0;i<IMAGE_FLIGHTS;i++) {
        snprintf(url,sizeof(url),"https://cdn.7tv.app/emote/overflow-stalled%u/2x.gif",i);
        crowded[i]=protocol(url);protocol_start_loading(crowded[i],nil);
    }
    assert(image_active==6 && image_background_active==6 && !image_overflow_groups);
}
static void retire(id data,id response) {
    id tasks[6];for(unsigned i=0;i<6;i++)tasks[i]=task_for(crowded[i]);
    for(unsigned i=0;i<IMAGE_FLIGHTS;i++)protocol_stop_loading(crowded[i],nil);
    for(unsigned i=0;i<6;i++)if(tasks[i])complete(tasks[i],data,response,nil);
    assert(!image_active && !image_overflow_groups && !image_overflow_consumers);
}
static void fire_deadline(void) {
    assert(overflow_timer_work);void (*work)(void *)=overflow_timer_work;overflow_timer_work=NULL;work(NULL);
}
static pthread_barrier_t race_barrier;
static void *race_stop(void *consumer) {
    int wait=pthread_barrier_wait(&race_barrier);assert(!wait || wait==PTHREAD_BARRIER_SERIAL_THREAD);
    protocol_stop_loading((id)consumer,nil);return NULL;
}
static void *race_deadline(void *unused) {(void)unused;fire_deadline();return NULL;}
'''
RECOVERY = r'''
int main(void) {
    (void)complete_hls;(void)thread_cache;(void)drain_cache;(void)protocol_can_init;
    protocol_session(true);saturate();unsigned before=starts;
    id a=protocol("https://cdn.7tv.app/emote/deferred/2x.gif"),b=protocol(a->request->url->text);
    protocol_start_loading(a,nil);protocol_start_loading(b,nil);
    assert(image_overflow_groups==1 && image_overflow_consumers==2 && starts==before);
    assert(!a->client->failures && !b->client->failures && overflow_timer_arms==1);
    struct timespec original=image_overflow[0].queued;
    id c=protocol(a->request->url->text);protocol_start_loading(c,nil);
    assert(image_overflow[0].queued.tv_sec==original.tv_sec && image_overflow[0].queued.tv_nsec==original.tv_nsec);
    protocol_stop_loading(a,nil);protocol_stop_loading(a,nil);
    assert(image_overflow_cancelled==1 && image_overflow_consumers==2);
    id foreground=protocol("https://cdn.7tv.app/emote/foreground/2x.gif");foreground->request->url->foreground=true;
    protocol_start_loading(foreground,nil);assert(image_overflow_groups==2 && starts==before);
    protocol_stop_loading(crowded[511],nil);
    assert(!image_overflow[1].url && task_for(foreground) && starts==before+1 && image_active==7);
    protocol_stop_loading(crowded[510],nil);
    assert(!image_overflow_groups && !task_for(b) && image_overflow_recovered==3);
    id data=fresh("GIF89a"),response=fresh("response");complete(task_for(foreground),data,response,nil);
    id hot=protocol("https://cdn.7tv.app/emote/cache-bypass/2x.gif");id item=prime(hot,"max-age=3600","1");
    before=starts;protocol_start_loading(hot,nil);assert(hot->client->finishes==1 && starts==before);
    clear_cache();for(unsigned i=6;i<IMAGE_FLIGHTS;i++)protocol_stop_loading(crowded[i],nil);
    complete(task_for(crowded[0]),data,response,nil);
    assert(task_for(b)==task_for(c) && task_for(b) && image_active<=8 && image_background_active<=6);
    complete(task_for(b),item->data,item->response,nil);
    assert(!a->client->loads && b->client->finishes==1 && c->client->finishes==1);retire(data,response);
    saturate();id fast=protocol("https://cdn.7tv.app/emote/immediate/2x.gif");fast->request->url->foreground=true;
    protocol_start_loading(fast,nil);immediate_data=data;immediate_response=response;complete_on_resume=true;
    protocol_stop_loading(crowded[511],nil);complete_on_resume=false;
    assert(fast->client->finishes==1 && !fast->task && !image_overflow_groups);retire(data,response);
    saturate();id background=protocol("https://cdn.7tv.app/emote/promoted/2x.gif");protocol_start_loading(background,nil);
    uint64_t generation=image_overflow[0].generation;original=image_overflow[0].queued;
    id promoted=protocol(background->request->url->text);promoted->request->url->foreground=true;protocol_start_loading(promoted,nil);
    assert(image_overflow_groups==1 && image_overflow[0].foreground && image_overflow[0].generation==generation);
    assert(image_overflow[0].queued.tv_sec==original.tv_sec && image_overflow[0].queued.tv_nsec==original.tv_nsec);
    protocol_stop_loading(crowded[511],nil);assert(task_for(background)==task_for(promoted) && image_active==7 && image_background_active==6);
    complete(task_for(promoted),data,response,nil);assert(background->client->finishes==1 && promoted->client->finishes==1);retire(data,response);
    /* Actual cancellation versus recovery races: either ordering is valid. */
    saturate();
    for(unsigned cycle=0;cycle<32;cycle++) {
        unsigned slot=IMAGE_FLIGHTS-1-cycle;
        id pending=protocol("https://cdn.7tv.app/emote/racing/2x.gif");pending->request->url->foreground=true;
        protocol_start_loading(pending,nil);assert(image_overflow_groups==1);
        assert(!pthread_barrier_init(&race_barrier,NULL,2));pthread_t threads[2];
        assert(!pthread_create(&threads[0],NULL,race_stop,pending));assert(!pthread_create(&threads[1],NULL,race_stop,crowded[slot]));
        for(unsigned i=0;i<2;i++)assert(!pthread_join(threads[i],NULL));pthread_barrier_destroy(&race_barrier);
        assert(!image_overflow_groups && image_active<=8 && image_background_active<=6);
        for(unsigned i=0;i<IMAGE_FLIGHTS;i++)if(image_flights[i].url && strstr(image_flights[i].url,"/racing/")) {
            assert(image_flights[i].running && !image_flights[i].count);complete(image_flights[i].task,data,response,nil);
        }
        assert(!pending->client->responses && !pending->client->failures);
        char url[96];snprintf(url,sizeof(url),"https://cdn.7tv.app/emote/race-refill%u/2x.gif",cycle);
        crowded[slot]=protocol(url);protocol_start_loading(crowded[slot],nil);
    }
    retire(data,response);
    /* Stop wins delivery even after timeout extraction removed the registry. */
    saturate();id timed=protocol("https://cdn.7tv.app/emote/timer-race/2x.gif");protocol_start_loading(timed,nil);
    image_overflow[0].queued.tv_sec-=31;objc_sync_enter(timed);pthread_t timer;
    assert(!pthread_create(&timer,NULL,race_deadline,NULL));
    for(;;){pthread_mutex_lock(&image_transport_lock);bool empty=!image_overflow_groups;pthread_mutex_unlock(&image_transport_lock);if(empty)break;}
    protocol_stop_loading(timed,nil);objc_sync_exit(timed);assert(!pthread_join(timer,NULL));
    assert(!timed->client->failures && !timed->client->responses && !image_overflow_groups);retire(data,response);
    char report[8192];tas_image_transport_status(report,sizeof(report));
    assert(strstr(report,"Overflow recovery") && !strstr(report,"deferred/2x"));return 0;
}
'''
BOUNDS = r'''
int main(void) {
    (void)complete_hls;(void)thread_cache;(void)protocol_can_init;(void)race_stop;(void)race_deadline;
    protocol_session(true);saturate();unsigned before=starts;
    id pending[IMAGE_CONSUMERS+IMAGE_OVERFLOW_GROUPS];char url[96];
    for(unsigned i=0;i<IMAGE_CONSUMERS+1;i++) {
        pending[i]=protocol("https://cdn.7tv.app/emote/fanout/2x.gif");protocol_start_loading(pending[i],nil);
    }
    assert(image_overflow_groups==2 && image_overflow[0].count==64 && image_overflow[1].count==1);
    pending[65]=protocol(pending[0]->request->url->text);pending[65]->request->headers=fresh("Accept:variant");protocol_start_loading(pending[65],nil);
    pending[66]=protocol(pending[0]->request->url->text);pending[66]->request->cache_policy=2;protocol_start_loading(pending[66],nil);
    assert(image_overflow_groups==4);
    for(unsigned i=67;i<127;i++) {
        snprintf(url,sizeof(url),"https://cdn.7tv.app/emote/pending%u/2x.gif",i);pending[i]=protocol(url);protocol_start_loading(pending[i],nil);
    }
    assert(image_overflow_groups==64 && image_overflow_consumers==127 && starts==before && overflow_timer_arms==1);
    id excess=protocol("https://cdn.7tv.app/emote/overflow-limit/2x.gif");protocol_start_loading(excess,nil);
    assert(excess->client->failures==1 && excess->completed && image_overflow_rejected==1 && starts==before);
    id hot=protocol("https://cdn.7tv.app/emote/full-cache-bypass/2x.gif");prime(hot,"max-age=3600","1");protocol_start_loading(hot,nil);
    assert(hot->client->finishes==1 && starts==before && image_overflow_rejected==1);clear_cache();
    cache_defer=true;id lookups[IMAGE_CACHE_GROUPS];
    for(unsigned i=0;i<IMAGE_CACHE_GROUPS;i++) {
        snprintf(url,sizeof(url),"https://cdn.7tv.app/emote/lookup%u/2x.gif",i);lookups[i]=protocol(url);protocol_start_loading(lookups[i],nil);
    }
    assert(image_cache_groups==512 && work_count==2);protocol_stop_loading(pending[126],nil);
    id spill=protocol("https://cdn.7tv.app/emote/lookup-spill/2x.gif");protocol_start_loading(spill,nil);
    assert(image_cache_spill==1 && image_overflow_groups==64 && !spill->client->failures);protocol_stop_loading(spill,nil);
    for(unsigned i=0;i<IMAGE_CACHE_GROUPS;i++)protocol_stop_loading(lookups[i],nil);drain_cache();cache_defer=false;
    assert(starts==before && !image_cache_groups && !image_cache_workers);
    protocol_stop_loading(pending[0],nil);
    for(unsigned i=0;i<IMAGE_OVERFLOW_GROUPS;i++)if(image_overflow[i].url)image_overflow[i].queued.tv_sec-=31;
    fire_deadline();assert(!image_overflow_groups && !image_overflow_consumers && !overflow_timer_work && starts==before);
    for(unsigned i=1;i<126;i++)assert(pending[i]->client->failures==1 && pending[i]->completed);
    assert(!pending[0]->client->failures && !pending[126]->client->failures && !spill->client->failures);
    assert(image_overflow_expired==125 && !image_overflow_timer);
    id data=fresh("GIF89a"),response=fresh("response");retire(data,response);
    assert(starts==before && image_overflow_recovered==0);return 0;
}
'''
BOOTSTRAP = r'''
int main(void) {
    (void)complete_hls;(void)thread_cache;(void)protocol_can_init;(void)prime;(void)saturate;(void)race_stop;(void)race_deadline;
    cache_defer=true;id probes[IMAGE_CACHE_GROUPS];char url[96];
    for(unsigned i=0;i<IMAGE_CACHE_GROUPS;i++) {
        snprintf(url,sizeof(url),"https://cdn.7tv.app/emote/bootstrap-probe%u/2x.gif",i);probes[i]=protocol(url);protocol_start_loading(probes[i],nil);
    }
    for(unsigned i=0;i<IMAGE_FLIGHTS;i++) {
        snprintf(url,sizeof(url),"https://cdn.7tv.app/emote/bootstrap-flight%u/2x.gif",i);crowded[i]=protocol(url);protocol_start_loading(crowded[i],nil);
    }
    id pending=protocol("https://cdn.7tv.app/emote/bootstrap-pending/2x.gif");protocol_start_loading(pending,nil);
    assert(!image_cache_session && !image_cache_store && !starts && image_overflow_groups==1 && !image_overflow[0].session);
    for(unsigned i=0;i<IMAGE_CACHE_GROUPS;i++)protocol_stop_loading(probes[i],nil);drain_cache();cache_defer=false;
    assert(image_cache_session && image_overflow[0].session==image_cache_session && starts==6);
    for(unsigned i=6;i<IMAGE_FLIGHTS;i++)protocol_stop_loading(crowded[i],nil);
    id data=fresh("GIF89a"),response=fresh("response");complete(task_for(crowded[0]),data,response,nil);
    assert(!image_overflow_groups && task_for(pending));complete(task_for(pending),data,response,nil);
    assert(pending->client->finishes==1);retire(data,response);
    pthread_mutex_lock(&image_transport_lock);
    for(unsigned group=0;group<IMAGE_OVERFLOW_GROUPS;group++) {
        snprintf(url,sizeof(url),"https://cdn.7tv.app/emote/absolute-bound%u/2x.gif",group);
        for(unsigned consumer=0;consumer<IMAGE_CONSUMERS;consumer++) {
            id p=protocol(url);assert(image_overflow_admit_locked(p,image_cache_session,p->request,url,false));
        }
    }
    assert(image_overflow_groups==64 && image_overflow_consumers==4096);
    id excess=protocol(url);assert(!image_overflow_admit_locked(excess,image_cache_session,excess->request,url,false));
    for(unsigned i=0;i<IMAGE_OVERFLOW_GROUPS;i++)image_overflow[i].queued.tv_sec-=31;
    pthread_mutex_unlock(&image_transport_lock);unsigned before=starts;fire_deadline();
    assert(image_overflow_expired==4096 && !image_overflow_groups && !image_overflow_consumers && starts==before);return 0;
}
'''

class OverflowTests(unittest.TestCase):
    def run_case(self, diagnostic, main):
        protocol.ProtocolTests().run_transport(diagnostic, HELPERS+main, extra_cflags=('-g0',))

    def test_recovery_priority_cancellation_cache_and_immediate_completion(self):
        self.run_case(False, RECOVERY)

    def test_recovery_with_demand_diagnostics(self):
        self.run_case(True, RECOVERY)

    def test_hard_bounds_variants_expiry_and_lookup_spill(self):
        self.run_case(False, BOUNDS)

    def test_bounds_with_demand_diagnostics(self):
        self.run_case(True, BOUNDS)

    def test_preinitialization_spills_and_absolute_consumer_bound(self):
        self.run_case(False, BOOTSTRAP)

    def test_preinitialization_with_demand_diagnostics(self):
        self.run_case(True, BOOTSTRAP)
