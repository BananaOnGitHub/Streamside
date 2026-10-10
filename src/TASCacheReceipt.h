/* Missing-Date receipts are committed only for a complete, non-redirected
 * network transaction that Foundation elected to cache. No local-cache task
 * can mint a receipt, and lookup never writes or renews the original clock. */
static bool image_cache_same_response(id a,id b) {
    if(!a || !b || !bmsg1(a,"isKindOfClass:",(id)objc_getClass("NSHTTPURLResponse")) ||
       !bmsg1(b,"isKindOfClass:",(id)objc_getClass("NSHTTPURLResponse")))return false;
    id x=msg0(a,"URL"),y=msg0(b,"URL"),h=msg0(a,"allHeaderFields"),k=msg0(b,"allHeaderFields");
    return x && y && h && k && imsg0(a,"statusCode")==imsg0(b,"statusCode") &&
           bmsg1(x,"isEqual:",y) && (h==k || bmsg1(h,"isEqual:",k));
}
static bool image_cache_receipt_info(id info,double *wall,double *age) {
    id proof=msg1(info,"objectForKey:",nsstr("TASCacheNetworkReceipt"));
    if(!proof || !bmsg1(proof,"isEqual:",nsstr("v1")))return false;
    double tick=image_cache_value(msg1(info,"objectForKey:",nsstr("TASCacheReceiptTick")));
    *wall=image_cache_value(msg1(info,"objectForKey:",nsstr("TASCacheReceiptWall")));
    *age=image_cache_value(msg1(info,"objectForKey:",nsstr("TASCacheInitialAge")));
    return tick>=0 && *wall>0 && *age>=0 &&
           tick==image_cache_value(msg1(info,"objectForKey:",nsstr("TASCacheTick"))) &&
           *wall==image_cache_value(msg1(info,"objectForKey:",nsstr("TASCacheWall")));
}
static void image_cache_received_response(id self,SEL cmd,id session,id task,id response,id completion) {
    (void)self;(void)cmd;(void)session;
    /* This alone is NOT network proof: Foundation also calls it for cache. */
    if(response && bmsg1(response,"isKindOfClass:",(id)objc_getClass("NSHTTPURLResponse"))) {
        id info=msg0((id)objc_getClass("NSMutableDictionary"),"new");
        vmsg2(info,"setObject:forKey:",response,nsstr("response"));
        vmsg2(info,"setObject:forKey:",image_cache_number(image_cache_clock(IMAGE_CACHE_AGE_CLOCK)),nsstr("tick"));
        vmsg2(info,"setObject:forKey:",image_cache_number(image_cache_clock(CLOCK_REALTIME)),nsstr("wall"));
        objc_sync_enter(task);
        if(!objc_getAssociatedObject(task,&image_cache_receipt_key))objc_setAssociatedObject(task,&image_cache_receipt_key,info,1);
        objc_sync_exit(task);objc_release(info);
    }
    ((void (^)(NSInteger))completion)(1); /* NSURLSessionResponseAllow */
}
static void image_cache_stage_receipt(id task,id proposed) {
    /* One proposal per bounded active task, sharing its existing body bytes.
     * Existing network receipts are never staged again from local cache. */
    if(imsg0(proposed,"storagePolicy")==2 || !data_length(msg0(proposed,"data")) ||
       msg1(msg0(proposed,"userInfo"),"objectForKey:",nsstr("TASCacheNetworkReceipt")))return;
    objc_sync_enter(task);
    if(!objc_getAssociatedObject(task,&image_cache_proposal_key)) {
        objc_setAssociatedObject(task,&image_cache_proposal_key,proposed,1);
        pthread_mutex_lock(&image_cache_metadata_lock);image_receipt_staged++;pthread_mutex_unlock(&image_cache_metadata_lock);
    }
    objc_sync_exit(task);
}
static double image_cache_metric_date(id date) {
    if(!date || !bmsg1(date,"isKindOfClass:",(id)objc_getClass("NSDate")))return -1;
    /* KVC boxes this scalar as NSNumber; the string keeps the existing C/ObjC
     * message adapter ABI and finite numeric validation shared across tests. */
    return image_cache_value(msg0(msg1(date,"valueForKey:",nsstr("timeIntervalSince1970")),"stringValue"));
}
static void image_cache_receipt_metrics(id task,id report) {
    objc_sync_enter(task);
    id proposal=objc_getAssociatedObject(task,&image_cache_proposal_key),receipt=objc_getAssociatedObject(task,&image_cache_receipt_key);
    id list=msg0(report,"transactionMetrics"),transaction=nil,response=msg0(proposal,"response");
    if(proposal && receipt && list && bmsg1(list,"isKindOfClass:",(id)objc_getClass("NSArray")) &&
       imsg0(list,"count")==1 && imsg0(report,"redirectCount")==0)transaction=msg0(list,"lastObject");
    double start=image_cache_value(objc_getAssociatedObject(task,&image_cache_start_key));
    double start_wall=image_cache_value(objc_getAssociatedObject(task,&image_cache_start_wall_key));
    double tick=image_cache_value(msg1(receipt,"objectForKey:",nsstr("tick")));
    double wall=image_cache_value(msg1(receipt,"objectForKey:",nsstr("wall")));
    double now=image_cache_clock(IMAGE_CACHE_AGE_CLOCK),now_wall=image_cache_clock(CLOCK_REALTIME);
    double requested=transaction ? image_cache_metric_date(msg0(transaction,"requestStartDate")):-1;
    double received=transaction ? image_cache_metric_date(msg0(transaction,"responseStartDate")):-1;
    double ended=transaction ? image_cache_metric_date(msg0(transaction,"responseEndDate")):-1;
    bool proven=transaction && imsg0(transaction,"resourceFetchType")==1 && /* networkLoad */
        image_cache_same_response(msg0(transaction,"response"),response) &&
        image_cache_same_response(msg1(receipt,"objectForKey:",nsstr("response")),response) &&
        bmsg1(msg0(msg0(transaction,"request"),"URL"),"isEqual:",msg0(msg0(task,"originalRequest"),"URL")) &&
        start>=0 && start_wall>0 && tick>=start && wall>=start_wall && now>=tick && now_wall>=wall &&
        fabs((wall-start_wall)-(tick-start))<=1 && fabs((now_wall-start_wall)-(now-start))<=1 &&
        requested>=start_wall && received>=requested && ended>=received && ended<=now_wall && received<=wall &&
        wall-received<=tick-start+1;
    /* A malformed second callback must not leave a previous proof behind. */
    objc_setAssociatedObject(task,&image_cache_network_key,proven ? nsstr("v1"):nil,1);
    objc_sync_exit(task);
}
static void image_cache_finish_receipt(id task,id error) {
    objc_sync_enter(task);
    id proposal=objc_retain(objc_getAssociatedObject(task,&image_cache_proposal_key));
    id receipt=objc_retain(objc_getAssociatedObject(task,&image_cache_receipt_key));
    id proof=objc_retain(objc_getAssociatedObject(task,&image_cache_network_key));
    double start_wall=image_cache_value(objc_getAssociatedObject(task,&image_cache_start_wall_key));
    objc_setAssociatedObject(task,&image_cache_proposal_key,nil,1);
    objc_setAssociatedObject(task,&image_cache_receipt_key,nil,1);
    objc_setAssociatedObject(task,&image_cache_network_key,nil,1);
    objc_setAssociatedObject(task,&image_cache_start_wall_key,nil,1);
    objc_sync_exit(task);
    if(proposal) {
        id response=msg0(proposal,"response"),request=msg0(task,"originalRequest"),annotated=nil;
        double tick=image_cache_value(msg1(receipt,"objectForKey:",nsstr("tick")));
        double wall=image_cache_value(msg1(receipt,"objectForKey:",nsstr("wall")));
        double start=image_cache_value(objc_getAssociatedObject(task,&image_cache_start_key));
        double age=0,lifetime,stamp;unsigned reason;
        const char *age_text=utf8(image_cache_field(response,"Age"));
        id current=nil;
        if(!error && proof && receipt && start>=0 && tick>=start && wall>0 && image_cache_epoch && image_cache_store &&
           imsg0(proposal,"storagePolicy")!=2 &&
           image_public_request(request) && imsg0(request,"cachePolicy")==0 && image_cache_eligible(request) &&
           imsg0(response,"statusCode")==200 && !image_cache_field(response,"Date") &&
           image_cache_same_response(msg0(task,"response"),response) &&
           bmsg1(msg0(response,"URL"),"isEqual:",msg0(request,"URL")) &&
           (!age_text || image_cache_seconds(age_text,&age)) &&
           image_cache_lifetime_at_reason(utf8(image_cache_field(response,"Cache-Control")),NULL,
                                         utf8(image_cache_field(response,"Expires")),wall,&lifetime,&stamp,&reason)) {
            current=objc_retain(msg1(image_cache_store,"cachedResponseForRequest:",request));
            id a=msg0(current,"userInfo"),b=msg0(proposal,"userInfo");
            /* Never force an absent/evicted/nonmatching response into cache,
             * overwrite another variant, or change Foundation's storage policy. */
            if(current && imsg0(current,"storagePolicy")==imsg0(proposal,"storagePolicy") &&
               image_cache_same_response(msg0(current,"response"),response) &&
               bmsg1(msg0(current,"data"),"isEqual:",msg0(proposal,"data")) && (a==b || bmsg1(a,"isEqual:",b))) {
                age+=fmax(tick-start,wall-start_wall);
                id info=msg0(b,"mutableCopy");if(!info)info=msg0((id)objc_getClass("NSMutableDictionary"),"new");
                vmsg2(info,"setObject:forKey:",image_cache_epoch,nsstr("TASCacheEpoch"));
                vmsg2(info,"setObject:forKey:",nsstr("v1"),nsstr("TASCacheNetworkReceipt"));
                vmsg2(info,"setObject:forKey:",image_cache_number(tick),nsstr("TASCacheReceiptTick"));
                vmsg2(info,"setObject:forKey:",image_cache_number(wall),nsstr("TASCacheReceiptWall"));
                vmsg2(info,"setObject:forKey:",image_cache_number(age),nsstr("TASCacheInitialAge"));
                vmsg2(info,"setObject:forKey:",image_cache_number(tick),nsstr("TASCacheTick"));
                vmsg2(info,"setObject:forKey:",image_cache_number(wall),nsstr("TASCacheWall"));
                vmsg2(info,"setObject:forKey:",image_cache_number(lifetime-age),nsstr("TASCacheRemaining"));
                id headers=msg0(request,"allHTTPHeaderFields");if(headers)vmsg2(info,"setObject:forKey:",headers,nsstr("TASCacheHeaders"));
                annotated=((id (*)(id,SEL,id,id,id,NSUInteger))objc_msgSend)(
                    msg0((id)objc_getClass("NSCachedURLResponse"),"alloc"),sel_registerName("initWithResponse:data:userInfo:storagePolicy:"),
                    response,msg0(proposal,"data"),info,(NSUInteger)imsg0(proposal,"storagePolicy"));
                objc_release(info);
                if(annotated)vmsg2(image_cache_store,"storeCachedResponse:forRequest:",annotated,request);
            }
        }
        pthread_mutex_lock(&image_cache_metadata_lock);
        if(annotated){image_receipt_stored++;image_cache_annotations++;image_cache_rejections[IMAGE_CACHE_DATE_MISSING]--;}
        else image_receipt_fallback++;
        pthread_mutex_unlock(&image_cache_metadata_lock);objc_release(annotated);objc_release(current);
    }
    objc_release(proof);objc_release(receipt);objc_release(proposal);
}
