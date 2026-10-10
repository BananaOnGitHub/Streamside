"""Production receipt lifecycle with controlled Foundation objects and clocks.
Real network/cache provenance and 304 behavior are also gated on Apple CI.
"""
import unittest
import test_protocol as protocol_tests

PRELUDE=protocol_tests.PRELUDE+r'''
static double fixture_tick=100,fixture_wall=1700000000;
static int fixture_clock_gettime(clockid_t clock,struct timespec *t) {
    double value=clock==CLOCK_REALTIME ? fixture_wall:fixture_tick;
    t->tv_sec=(time_t)value;t->tv_nsec=(long)((value-t->tv_sec)*1e9);return 0;
}
#define clock_gettime fixture_clock_gettime
'''
MAIN=protocol_tests.MAIN[:protocol_tests.MAIN.index('int main(void)')]+r'''
static void field(id object,const char *key,id value){vmsg2(object,"setObject:forKey:",value,nsstr(key));}
static id numeric(double n){return image_cache_number(n);}
static id date(double n){id d=numeric(n);d->probe_kind=4;return d;}
static void advance(double n){fixture_tick+=n;fixture_wall+=n;}
static id metrics(id task,id response) {
    id tx=fresh("transaction");tx->request=task->request;tx->response=response;tx->fetch_type=1;
    double start=image_cache_value(task->cache_start_wall);
    tx->metric_start=date(start+.1);tx->metric_received=date(start+1.8);tx->metric_ended=date(start+3.8);
    id report=fresh("report"),list=fresh("array");list->probe_kind=5;list->entries=1;list->values[0]=tx;report->transactions=list;return report;
}
static id network(unsigned mode,const char *control,const char *age) {
    image_cache_store->cache=nil;
    char url[96];snprintf(url,sizeof(url),"https://cdn.7tv.app/emote/receipt-%u/2x.gif",mode);
    id p=protocol(url);protocol_start_loading(p,nil);id task=task_for(p);assert(task);
    id r=fresh("response");r->probe_kind=1;r->url=task->request->url;r->probe_headers=fresh("headers");r->probe_headers->probe_kind=2;
    field(r,"Cache-Control",nsstr(control));field(r->probe_headers,"Cache-Control",nsstr(control));
    field(r,"Age",nsstr(age));field(r->probe_headers,"Age",nsstr(age));task->response=r;
    advance(2);unsigned allowed=0;unsigned *out=&allowed;
    image_cache_received_response(nil,nil,nil,task,r,(id)^(NSInteger result){assert(result==1);(*out)++;});assert(allowed==1);
    advance(2);id proposed=fresh("cached");proposed->response=r;proposed->data=fresh("GIF89a");proposed->cache_policy=1;
    uint64_t stored=image_receipt_stored;id candidate=nil;id *result=&candidate;
    image_cache_proposed(nil,nil,nil,task,proposed,(id)^(id value){*result=value;});assert(candidate==proposed && task->proposal==proposed);
    image_cache_store->cache=proposed;
    id report=metrics(task,r),tx=report->transactions->values[0];
    switch(mode) {
        case 1:report=nil;break;
        case 2:tx->fetch_type=0;break;
        case 3:tx->fetch_type=2;break;
        case 4:tx->fetch_type=3;break;
        case 5:report->transactions->entries=0;break;
        case 6:report->transactions->entries=2;break;
        case 7:report->redirects=1;break;
        case 8:tx->response=fresh("other");break;
        case 9:tx->metric_received=nil;break;
        case 10:tx->metric_received=date(fixture_wall+1);break;
        case 11:tx->metric_ended=date(fixture_wall+1);break;
        case 12:tx->metric_start=date(fixture_wall);break;
        case 13:task->receipt=nil;break;
        case 14:field(task->receipt,"tick",nsstr("NaN"));break;
        case 15:field(task->receipt,"wall",numeric(fixture_wall+10));break;
        case 16:field(task->receipt,"wall",numeric(fixture_wall-20));break;
        case 17:task->cache_start_wall=nsstr("bad");break;
        case 18:fixture_wall+=10;break;
        case 19:tx->request=protocol("https://cdn.7tv.app/emote/wrong/2x.gif")->request;break;
        case 20:tx->metric_received=nsstr("bad-type");break;
    }
    image_cache_receipt_metrics(task,report);
    if(mode==21)image_cache_receipt_metrics(task,nil); /* invalidate previous proof */
    if(mode==22)image_cache_store->cache=nil;
    if(mode==23){id other=fresh("other");other->response=r;other->data=fresh("OTHER-BODY");other->cache_policy=1;image_cache_store->cache=other;}
    if(mode==24)image_cache_store->cache->cache_policy=2;
    if(mode==25)task->request->cache_policy=3;
    complete(task,proposed->data,r,mode==26 ? fresh("cancelled-error"):nil);
    assert(!task->receipt && !task->proposal && !task->network && !task->cache_start_wall);
    if(mode || (strcmp(control,"public, max-age=12, must-revalidate") && strcmp(control,"public, max-age=12")) || !strcmp(age,"bad"))assert(image_receipt_stored==stored);
    else assert(image_receipt_stored==stored+1 && image_cache_store->cache!=proposed);
    return p;
}
int main(void) {
    (void)complete_hls;
    id boot=protocol("https://cdn.7tv.app/emote/boot/2x.gif");assert(protocol_can_init(nil,nil,boot->request));
    protocol_start_loading(boot,nil);complete(task_for(boot),fresh("GIF89a"),fresh("response"),nil);
    id p=network(0,"public, max-age=12, must-revalidate","3"),cached=image_cache_store->cache;
    id info=cached->info,tick=msg1(info,"objectForKey:",nsstr("TASCacheReceiptTick")),wall=msg1(info,"objectForKey:",nsstr("TASCacheReceiptWall"));
    assert(image_cache_value(tick)==102 && image_cache_value(wall)==1700000002);
    assert(image_cache_value(msg1(info,"objectForKey:",nsstr("TASCacheInitialAge")))==5);
    assert(image_cache_value(msg1(info,"objectForKey:",nsstr("TASCacheRemaining")))==7);
    advance(2);unsigned starts_before=starts;
    /* Library close/reopen uses the actual cache lane, creates no task and
     * does not write the receipt, even with an equivalent same-boot epoch. */
    image_cache_epoch=nsstr(image_cache_epoch->text);id reopened=protocol(p->request->url->text);
    protocol_start_loading(reopened,nil);assert(reopened->client->finishes==1 && starts==starts_before);
    assert(image_cache_store->cache==cached && msg1(info,"objectForKey:",nsstr("TASCacheReceiptTick"))==tick);
    advance(3);unsigned reason;assert(!image_cache_usable(cached,reopened->request,&reason) && reason==3);
    id expired=protocol(p->request->url->text);protocol_start_loading(expired,nil);assert(starts==starts_before+1 && !expired->client->finishes);
    id t=task_for(expired);t->response=cached->response;
    unsigned allowed=0;unsigned *out=&allowed;
    image_cache_received_response(nil,nil,nil,t,cached->response,(id)^(NSInteger v){assert(v==1);(*out)++;});assert(allowed==1);
    image_cache_proposed(nil,nil,nil,t,cached,(id)^(id v){assert(v==cached);});assert(!t->proposal);
    id report=metrics(t,cached->response);report->transactions->values[0]->fetch_type=3;
    image_cache_receipt_metrics(t,report);complete(t,cached->data,cached->response,nil);
    assert(image_cache_store->cache==cached && msg1(info,"objectForKey:",nsstr("TASCacheReceiptWall"))==wall);
    assert(!image_cache_usable(cached,expired->request,&reason) && reason==3); /* no renewal */
    /* Missing, forged-version, malformed, nonfinite, future or rebooted
     * timestamps never bypass Foundation; header Age remains a lower bound. */
    const char *keys[]={"TASCacheNetworkReceipt","TASCacheReceiptTick","TASCacheReceiptWall","TASCacheInitialAge","TASCacheEpoch"};
    for(unsigned i=0;i<5;i++){id saved=msg1(info,"objectForKey:",nsstr(keys[i]));field(info,keys[i],nsstr("bad"));assert(!image_cache_usable(cached,expired->request,&reason) && reason==2);field(info,keys[i],saved);}
    id age=msg1(info,"objectForKey:",nsstr("TASCacheInitialAge"));field(info,"TASCacheInitialAge",numeric(1));assert(!image_cache_usable(cached,expired->request,&reason) && reason==2);field(info,"TASCacheInitialAge",age);
    field(info,"TASCacheReceiptTick",numeric(fixture_tick+1));field(info,"TASCacheTick",numeric(fixture_tick+1));assert(!image_cache_usable(cached,expired->request,&reason) && reason==3);
    field(info,"TASCacheReceiptTick",tick);field(info,"TASCacheTick",tick);
    for(unsigned mode=1;mode<=26;mode++)network(mode,"public, max-age=12, must-revalidate","3");
    network(0,"no-store, max-age=12","3");network(0,"no-cache, max-age=12","3");
    network(0,"public, max-age=12","bad");network(0,"public, max-age=12","100");
    assert(!image_active && image_receipt_staged==image_receipt_stored+image_receipt_fallback);
    uint64_t rejected=0;for(unsigned i=1;i<IMAGE_CACHE_REJECTION_COUNT;i++)rejected+=image_cache_rejections[i];
    assert(image_cache_annotations+rejected==image_cache_proposals);
    char report_text[8192];tas_image_transport_status(report_text,sizeof(report_text));
    assert(strstr(report_text,"Missing-Date receipt proposals staged/stored/fallback") && !strstr(report_text,"1700000") && !strstr(report_text,"cdn.7tv.app"));
    return 0;
}
'''

class CacheReceiptTests(unittest.TestCase):
    def test_network_provenance_original_clock_and_expiration(self):
        # Clang 19 crashes on debug/builtin handling in this clock/block adapter.
        # Disable those transforms, never assertions or production build flags.
        protocol_tests.ProtocolTests().run_transport(False,MAIN,PRELUDE,('-g0','-fno-builtin'))

    def test_receipt_diagnostics_preserve_the_same_lifecycle(self):
        protocol_tests.ProtocolTests().run_transport(True,MAIN,PRELUDE,('-g0','-fno-builtin'))
