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
    protocol_start_loading(protocol,NULL);return protocol;
}
static void wait_finished(CacheClient *client,double seconds) {
    double end=image_cache_clock(CLOCK_MONOTONIC)+seconds;
    while(image_cache_clock(CLOCK_MONOTONIC)<end){
        @synchronized(client){assert(!client->failures);if(client->finishes){assert(client->responses==1 && client->loads==1 && client->status==200);return;}}
        usleep(1000);
    }
    assert(!"Foundation fixture timed out");
}
int main(int argc,char **argv) {
    assert(argc==2);
    @autoreleasepool {
        CacheClient *warm;begin(argv[1],"/hot.gif",&warm);wait_finished(warm,10);
        NSURLSessionConfiguration *configuration=[protocol_session(true) configuration];
        assert(configuration.timeoutIntervalForRequest==15 && configuration.timeoutIntervalForResource==30);
        assert(configuration.HTTPMaximumConnectionsPerHost==8 && configuration.URLCache.memoryCapacity==32*1024*1024 && configuration.URLCache.diskCapacity==128*1024*1024);
        CacheClient *blocked[8];id protocols[8];char path[32];
        for(unsigned i=0;i<8;i++){snprintf(path,sizeof(path),"/blocked%u.gif",i);protocols[i]=begin(argv[1],path,&blocked[i]);}
        double end=image_cache_clock(CLOCK_MONOTONIC)+2;unsigned active=0;
        while(image_cache_clock(CLOCK_MONOTONIC)<end){pthread_mutex_lock(&image_transport_lock);active=image_active;pthread_mutex_unlock(&image_transport_lock);if(active==8)break;usleep(1000);}
        assert(active==8);
        CacheClient *hot;double start=image_cache_clock(CLOCK_MONOTONIC);begin(argv[1],"/hot.gif",&hot);wait_finished(hot,1.5);
        assert(image_cache_clock(CLOCK_MONOTONIC)-start<1.5 && image_cache_hits>=1);
        for(unsigned i=0;i<8;i++){wait_finished(blocked[i],10);protocol_stop_loading(protocols[i],NULL);}
        CacheClient *stale,*revalidated;begin(argv[1],"/revalidate.gif",&stale);wait_finished(stale,10);
        begin(argv[1],"/revalidate.gif",&revalidated);wait_finished(revalidated,10);
        CacheClient *a,*b;begin(argv[1],"/hot.gif",&a);begin(argv[1],"/hot.gif",&b);wait_finished(a,2);wait_finished(b,2);
        char report[4096];tas_image_transport_status(report,sizeof(report));puts(report);
    }
    return 0;
}
