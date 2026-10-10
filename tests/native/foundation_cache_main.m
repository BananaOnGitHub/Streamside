@interface CacheClient : NSObject <NSURLProtocolClient> {
@public NSUInteger responses,loads,finishes,failures; NSInteger status;
}
@end
@implementation CacheClient
- (void)URLProtocol:(NSURLProtocol *)p didReceiveResponse:(NSURLResponse *)r cacheStoragePolicy:(NSURLCacheStoragePolicy)s {
    (void)p;(void)s;@synchronized(self){responses++;status=[(NSHTTPURLResponse *)r statusCode];}
}
- (void)URLProtocol:(NSURLProtocol *)p didLoadData:(NSData *)d {(void)p;assert([d length]);@synchronized(self){loads++;}}
- (void)URLProtocolDidFinishLoading:(NSURLProtocol *)p {(void)p;@synchronized(self){finishes++;}}
- (void)URLProtocol:(NSURLProtocol *)p didFailWithError:(NSError *)e {(void)p;(void)e;@synchronized(self){failures++;}}
- (void)URLProtocol:(NSURLProtocol *)p wasRedirectedToRequest:(NSURLRequest *)r redirectResponse:(NSURLResponse *)s {(void)p;(void)r;(void)s;abort();}
- (void)URLProtocol:(NSURLProtocol *)p cachedResponseIsValid:(NSCachedURLResponse *)r {(void)p;(void)r;}
- (void)URLProtocol:(NSURLProtocol *)p didReceiveAuthenticationChallenge:(NSURLAuthenticationChallenge *)c {(void)p;(void)c;abort();}
- (void)URLProtocol:(NSURLProtocol *)p didCancelAuthenticationChallenge:(NSURLAuthenticationChallenge *)c {(void)p;(void)c;}
@end
static id begin(const char *base,const char *path,CacheClient **client) {
    *client=[CacheClient new];NSString *url=[NSString stringWithFormat:@"%s%s",base,path];
    NSURLRequest *request=[NSURLRequest requestWithURL:[NSURL URLWithString:url]];
    assert(protocol_can_init(nil,NULL,request));
    id protocol=[[NSURLProtocol alloc] initWithRequest:request cachedResponse:nil client:*client];
    assert(protocol && [protocol request] && [protocol client]==*client);
    protocol_start_loading(protocol,NULL);return protocol;
}
static void wait_finished(CacheClient *client,double seconds) {
    double end=image_cache_clock(CLOCK_MONOTONIC)+seconds;
    while(image_cache_clock(CLOCK_MONOTONIC)<end){
        @synchronized(client){assert(!client->failures);if(client->finishes){assert(client->responses==1 && client->loads==1 && client->status==200);return;}}
        /* A command-line Foundation fixture must pump its main run loop, as
         * UIKit does on device; sleeping here can strand Foundation callbacks. */
        [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:.001]];
    }
    char report[4096];tas_image_transport_status(report,sizeof(report));fputs(report,stderr);
    @synchronized(client){fprintf(stderr,"Fixture callbacks response/data/finish/failure: %lu/%lu/%lu/%lu\n",(unsigned long)client->responses,(unsigned long)client->loads,(unsigned long)client->finishes,(unsigned long)client->failures);}
    assert(!"Foundation fixture timed out");
}
static CacheClient *overflow_integration(const char *base) {
    id queued[IMAGE_FLIGHTS-8];CacheClient *clients[IMAGE_FLIGHTS-8];
    id session=protocol_session(true);
    pthread_mutex_lock(&image_transport_lock);assert(image_active==8);
    for(unsigned i=0;i<IMAGE_FLIGHTS-8;i++) {
        NSString *url=[NSString stringWithFormat:@"%s/queued%u.gif",base,i];
        NSMutableURLRequest *request=[NSMutableURLRequest requestWithURL:[NSURL URLWithString:url]];
        [request setValue:@"1" forHTTPHeaderField:@TAS_INTERNAL_HEADER];
        clients[i]=[CacheClient new];
        queued[i]=[[NSURLProtocol alloc] initWithRequest:request cachedResponse:nil client:clients[i]];
        assert(image_flight_add_locked(queued[i],session,request,[url UTF8String],false,true,false)<IMAGE_FLIGHTS);
    }
    pthread_mutex_unlock(&image_transport_lock);
    CacheClient *cancelled,*survivor;
    id a=begin(base,"/overflow.gif",&cancelled);begin(base,"/overflow.gif",&survivor);
    double end=image_cache_clock(CLOCK_MONOTONIC)+2;unsigned consumers=0;
    while(image_cache_clock(CLOCK_MONOTONIC)<end) {
        pthread_mutex_lock(&image_transport_lock);consumers=image_overflow_consumers;pthread_mutex_unlock(&image_transport_lock);
        if(consumers==2)break;
        [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:.001]];
    }
    assert(consumers==2);
    protocol_stop_loading(a,NULL);
    protocol_stop_loading(queued[IMAGE_FLIGHTS-9],NULL);
    pthread_mutex_lock(&image_transport_lock);
    assert(image_active==8 && !image_overflow_groups && image_overflow_recovered==1);
    pthread_mutex_unlock(&image_transport_lock);
    for(unsigned i=0;i<IMAGE_FLIGHTS-8;i++)protocol_stop_loading(queued[i],NULL);
    @synchronized(cancelled){assert(!cancelled->responses && !cancelled->failures);}
    @synchronized(survivor){assert(!survivor->responses && !survivor->failures);}
    for(unsigned i=0;i<IMAGE_FLIGHTS-8;i++) {
        @synchronized(clients[i]){assert(!clients[i]->responses && !clients[i]->failures);}
        [queued[i] release];[clients[i] release];
    }
    return survivor;
}
#include "foundation_annotation_main.m"
#include "foundation_header_probe.m"
#include "foundation_receipt_main.m"
int main(int argc,char **argv) {
    assert(argc==2);
    @autoreleasepool {
        fputs("Fixture stage: warm\n",stderr);
        CacheClient *warm;begin(argv[1],"/hot.gif",&warm);wait_finished(warm,10);
        annotation_matrix(argv[1]);
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
        header_probe_matrix(argv[1]);
#endif
        receipt_integration(argv[1]);
        NSURLSessionConfiguration *configuration=[protocol_session(true) configuration];
        assert(configuration.timeoutIntervalForRequest==15 && configuration.timeoutIntervalForResource==30);
        assert(configuration.HTTPMaximumConnectionsPerHost==8 && configuration.URLCache.memoryCapacity==32*1024*1024 && configuration.URLCache.diskCapacity==128*1024*1024);
        fputs("Fixture stage: saturated transfers\n",stderr);
        CacheClient *blocked[8];id protocols[8];char path[32];
        for(unsigned i=0;i<8;i++){snprintf(path,sizeof(path),"/blocked%u.gif",i);protocols[i]=begin(argv[1],path,&blocked[i]);}
        double end=image_cache_clock(CLOCK_MONOTONIC)+2;unsigned active=0;
        while(image_cache_clock(CLOCK_MONOTONIC)<end){pthread_mutex_lock(&image_transport_lock);active=image_active;pthread_mutex_unlock(&image_transport_lock);if(active==8)break;usleep(1000);}
        assert(active==8);
        fputs("Fixture stage: saturated cache hit\n",stderr);
        CacheClient *hot;double start=image_cache_clock(CLOCK_MONOTONIC);begin(argv[1],"/hot.gif",&hot);wait_finished(hot,1.5);
        assert(image_cache_clock(CLOCK_MONOTONIC)-start<1.5 && image_cache_hits>=1);
        CacheClient *overflow=overflow_integration(argv[1]);
        assert(([[NSData dataWithContentsOfURL:[NSURL URLWithString:[NSString stringWithFormat:@"%s/release-blocked",argv[1]]]] length]==6));
        for(unsigned i=0;i<8;i++){wait_finished(blocked[i],10);protocol_stop_loading(protocols[i],NULL);}
        wait_finished(overflow,10);
        assert(!image_overflow_groups && !image_overflow_consumers && image_active<=8);
        puts("Production overflow recovery passed with real Foundation objects and HTTP");
        fputs("Fixture stage: revalidation\n",stderr);
        CacheClient *stale,*revalidated;begin(argv[1],"/revalidate.gif",&stale);wait_finished(stale,10);
        begin(argv[1],"/revalidate.gif",&revalidated);wait_finished(revalidated,10);
        CacheClient *a,*b;begin(argv[1],"/hot.gif",&a);begin(argv[1],"/hot.gif",&b);wait_finished(a,2);wait_finished(b,2);
        char report[8192];tas_image_transport_status(report,sizeof(report));puts(report);
    }
    return 0;
}
