/* The same policy matrix against real NSHTTPURLResponse/NSCachedURLResponse,
 * with production image_cache_proposed and metadata preservation. */
#include "cache_annotation_cases.h"
static NSString *annotation_date(const char *value,NSDate *now) {
    if(!value || *value!='@')return nsstr(value);
    NSDateFormatter *format=[NSDateFormatter new];
    format.locale=[NSLocale localeWithLocaleIdentifier:@"en_US_POSIX"];
    format.timeZone=[NSTimeZone timeZoneForSecondsFromGMT:0];
    format.dateFormat=@"EEE, dd MMM yyyy HH:mm:ss 'GMT'";
    NSString *date=[format stringFromDate:[now dateByAddingTimeInterval:!strcmp(value,"@now") ? -2:7200]];
    [format release];return date;
}
static void annotation_matrix(const char *base) {
    NSURLSession *session=protocol_session(true);
    for(unsigned i=0;i<sizeof(annotation_cases)/sizeof(*annotation_cases);i++) {
        const AnnotationCase *c=&annotation_cases[i];
        NSMutableURLRequest *request=[NSMutableURLRequest requestWithURL:[NSURL URLWithString:[NSString stringWithFormat:@"%s/annotation-fixture.gif",base]]];
        [request setValue:@"image/gif" forHTTPHeaderField:@"Accept"];
        NSURLSessionDataTask *task=[session dataTaskWithRequest:request];image_cache_mark_task(task);
        NSDate *now=[NSDate date];NSMutableDictionary *fields=[NSMutableDictionary dictionary];
        if(c->control)fields[@"Cache-Control"]=nsstr(c->control);
        if(c->date)fields[@"Date"]=annotation_date(c->date,now);
        if(c->expires)fields[@"Expires"]=annotation_date(c->expires,now);
        if(c->age)fields[@"Age"]=nsstr(c->age);
        NSHTTPURLResponse *response=[[[NSHTTPURLResponse alloc] initWithURL:request.URL statusCode:200 HTTPVersion:@"HTTP/1.1" headerFields:fields] autorelease];
        NSData *data=[@"GIF89a" dataUsingEncoding:NSUTF8StringEncoding];
        NSDictionary *info=@{@"fixture-marker":@"retained"};
        NSCachedURLResponse *proposed=[[[NSCachedURLResponse alloc] initWithResponse:response data:data userInfo:info storagePolicy:NSURLCacheStorageAllowedInMemoryOnly] autorelease];
        uint64_t counts[IMAGE_CACHE_REJECTION_COUNT];
        pthread_mutex_lock(&image_cache_metadata_lock);
        memcpy(counts,image_cache_rejections,sizeof(counts));uint64_t proposals=image_cache_proposals,annotations=image_cache_annotations;
        pthread_mutex_unlock(&image_cache_metadata_lock);
        __block NSCachedURLResponse *stored=nil;__block unsigned calls=0;
        image_cache_proposed(nil,NULL,session,task,proposed,^(id result){stored=[result retain];calls++;});
        assert(calls==1 && proposed.userInfo.count==1);
        pthread_mutex_lock(&image_cache_metadata_lock);
        bool counters=image_cache_proposals==proposals+1 && image_cache_annotations==annotations+(c->rejection==IMAGE_CACHE_ACCEPTED);
        for(unsigned j=0;j<IMAGE_CACHE_REJECTION_COUNT;j++)
            counters=counters && image_cache_rejections[j]==counts[j]+(j==c->rejection && c->rejection!=IMAGE_CACHE_ACCEPTED);
        pthread_mutex_unlock(&image_cache_metadata_lock);
        if(!counters)fprintf(stderr,"Annotation fixture failure: %s\n",c->name);
        assert(counters);
        if(c->rejection==IMAGE_CACHE_ACCEPTED) {
            assert(stored!=proposed && stored.response==proposed.response && [stored.data isEqual:proposed.data] && stored.storagePolicy==proposed.storagePolicy);
            assert([stored.userInfo[@"fixture-marker"] isEqual:info[@"fixture-marker"]]);
            assert([stored.userInfo[@"TASCacheEpoch"] isEqual:image_cache_epoch]);
            assert([stored.userInfo[@"TASCacheHeaders"] isEqual:request.allHTTPHeaderFields]);
        } else assert(stored==proposed);
        [stored release];[task cancel];
    }
    fputs("Production annotation policy matrix passed with real Foundation objects\n",stdout);
}
