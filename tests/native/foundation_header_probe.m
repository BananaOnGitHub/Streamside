#if TAS_IMAGE_DEMAND_DIAGNOSTIC
/* Real Foundation dictionaries and HTTP responses. This subclass models only
 * the accessor/dictionary disagreement; it does not claim CFNetwork does so. */
@interface HeaderProbeFixture : NSHTTPURLResponse {
@public BOOL hideDate;
}
@end
@implementation HeaderProbeFixture
- (NSString *)valueForHTTPHeaderField:(NSString *)name {
    if(hideDate && [name caseInsensitiveCompare:@"Date"]==NSOrderedSame)return nil;
    return [super valueForHTTPHeaderField:name];
}
@end
static void header_probe_matrix(const char *base) {
    NSMutableURLRequest *request=[NSMutableURLRequest requestWithURL:[NSURL URLWithString:[NSString stringWithFormat:@"%s/probe.gif",base]]];
    NSDate *now=[NSDate date];
    NSDictionary *fields=@{@"dAtE":annotation_date("@now",now),@"cache-control":@"max-age=3600",@"AGE":@"0",@"eXpIrEs":annotation_date("@expiry",now)};
    HeaderProbeFixture *response=[[[HeaderProbeFixture alloc] initWithURL:request.URL statusCode:200 HTTPVersion:@"HTTP/1.1" headerFields:fields] autorelease];
    unsigned outcomes[IMAGE_HEADER_FIELDS];image_header_inspect(response,outcomes);
    for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++)assert(outcomes[i]==IMAGE_HEADER_EQUAL);
    response->hideDate=YES;image_header_inspect(response,outcomes);
    assert(outcomes[0]==IMAGE_HEADER_DICTIONARY_ONLY);
    for(unsigned i=1;i<IMAGE_HEADER_FIELDS;i++)assert(outcomes[i]==IMAGE_HEADER_EQUAL);
    NSURLSessionDataTask *task=[protocol_session(true) dataTaskWithRequest:request];image_cache_mark_task(task);
    NSCachedURLResponse *proposed=[[[NSCachedURLResponse alloc] initWithResponse:response data:[@"GIF89a" dataUsingEncoding:NSUTF8StringEncoding] userInfo:@{@"fixture-marker":@"retained"} storagePolicy:NSURLCacheStorageAllowedInMemoryOnly] autorelease];
    pthread_mutex_lock(&image_cache_metadata_lock);
    uint64_t rejected=image_cache_rejections[IMAGE_CACHE_DATE_MISSING],count=image_header_counts[0][0][IMAGE_HEADER_DICTIONARY_ONLY];
    pthread_mutex_unlock(&image_cache_metadata_lock);
    __block unsigned calls=0;
    image_cache_proposed(nil,NULL,protocol_session(true),task,proposed,^(id result){assert(result==proposed);calls++;});
    assert(calls==1 && proposed.userInfo.count==1);
    pthread_mutex_lock(&image_cache_metadata_lock);
    assert(image_cache_rejections[IMAGE_CACHE_DATE_MISSING]==rejected+1 && image_header_counts[0][0][IMAGE_HEADER_DICTIONARY_ONLY]==count+1);
    for(unsigned scope=0;scope<2;scope++)for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++) {
        uint64_t total=0;for(unsigned j=0;j<IMAGE_HEADER_OUTCOMES;j++)total+=image_header_counts[scope][i][j];
        assert(total==image_header_observations);
    }
    pthread_mutex_unlock(&image_cache_metadata_lock);
    [task cancel];
    NSHTTPURLResponse *empty=[[[NSHTTPURLResponse alloc] initWithURL:request.URL statusCode:200 HTTPVersion:@"HTTP/1.1" headerFields:@{}] autorelease];
    image_header_inspect(empty,outcomes);for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++)assert(outcomes[i]==IMAGE_HEADER_NEITHER);
    image_header_inspect(nil,outcomes);for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++)assert(outcomes[i]==IMAGE_HEADER_UNINSPECTABLE);
    fputs("Production header probe passed with real Foundation objects; missing accessor remains rejected\n",stdout);
}
#endif
