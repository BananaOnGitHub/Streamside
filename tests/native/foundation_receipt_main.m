/* Actual Date-less HTTP response, persisted URLCache userInfo, reopen and
 * conditional revalidation. No fabricated transaction metrics in this gate. */
static NSURLRequest *receipt_request(const char *base,const char *path) {
    NSMutableURLRequest *r=[NSMutableURLRequest requestWithURL:[NSURL URLWithString:[NSString stringWithFormat:@"%s%s",base,path]]];
    [r setValue:@"1" forHTTPHeaderField:@TAS_INTERNAL_HEADER];return r;
}
static void receipt_integration(const char *base) {
    CacheClient *first;begin(base,"/receipt.gif",&first);wait_finished(first,10);
    NSURLRequest *request=receipt_request(base,"/receipt.gif");
    NSCachedURLResponse *cached=[image_cache_store cachedResponseForRequest:request];
    assert(cached && ![(NSHTTPURLResponse *)cached.response valueForHTTPHeaderField:@"Date"]);
    NSDictionary *original=[[cached.userInfo copy] autorelease];
    assert([original[@"TASCacheNetworkReceipt"] isEqual:@"v1"]);
    double wall,age;assert(image_cache_receipt_info(original,&wall,&age) && age>=2);
    assert(image_cache_value(original[@"TASCacheRemaining"])<=3);
    unsigned reason;assert(image_cache_usable(cached,request,&reason));
    NSData *serialized=[NSPropertyListSerialization dataWithPropertyList:original format:NSPropertyListBinaryFormat_v1_0 options:0 error:NULL];
    NSDictionary *restored=[NSPropertyListSerialization propertyListWithData:serialized options:NSPropertyListImmutable format:NULL error:NULL];
    NSCachedURLResponse *roundtrip=[[[NSCachedURLResponse alloc] initWithResponse:cached.response data:cached.data userInfo:restored storagePolicy:cached.storagePolicy] autorelease];
    assert(serialized && [restored isEqual:original] && image_cache_usable(roundtrip,request,&reason));
    uint64_t hits=image_cache_hits,stored=image_receipt_stored;
    CacheClient *reopened;begin(base,"/receipt.gif",&reopened);wait_finished(reopened,2);
    assert(image_cache_hits==hits+1 && image_receipt_stored==stored);
    cached=[image_cache_store cachedResponseForRequest:request];
    assert([cached.userInfo isEqual:original]); /* read-only reopen */

    /* A fresh old Foundation entry, with no receipt provenance, is served by
     * Foundation and must not acquire a newly minted network receipt. */
    NSURLRequest *old=receipt_request(base,"/old-receipt.gif");
    NSHTTPURLResponse *r=[[[NSHTTPURLResponse alloc] initWithURL:old.URL statusCode:200 HTTPVersion:@"HTTP/1.1"
        headerFields:@{@"Cache-Control":@"public, max-age=3600",@"Age":@"0",@"Content-Type":@"image/gif"}] autorelease];
    NSCachedURLResponse *entry=[[[NSCachedURLResponse alloc] initWithResponse:r data:[@"GIF89a" dataUsingEncoding:NSUTF8StringEncoding]] autorelease];
    [image_cache_store storeCachedResponse:entry forRequest:old];
    CacheClient *legacy;begin(base,"/old-receipt.gif",&legacy);wait_finished(legacy,10);
    assert(image_receipt_stored==stored && ![[image_cache_store cachedResponseForRequest:old].userInfo objectForKey:@"TASCacheNetworkReceipt"]);

    /* Pump until both our conservative deadline and the server's full five
     * seconds have elapsed, then require a real Foundation conditional task. */
    double end=image_cache_value(original[@"TASCacheReceiptTick"])+5.2;
    while(image_cache_clock(IMAGE_CACHE_AGE_CLOCK)<end)
        [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:.01]];
    cached=[image_cache_store cachedResponseForRequest:request];
    assert(!image_cache_usable(cached,request,&reason) && reason==3);
    hits=image_cache_hits;CacheClient *expired;begin(base,"/receipt.gif",&expired);wait_finished(expired,10);
    assert(image_cache_hits==hits); /* validation is asserted by the server */
    fputs("Production missing-Date receipt passed: network proof, unchanged reopen clock, old-cache fallback and expired validation\n",stdout);
}
