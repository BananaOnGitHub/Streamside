/* Passive, fixed-size observation only. Values and keys remain local to this
 * invocation; no fallback values enter annotation or cache freshness logic. */
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
#define IMAGE_HEADER_FIELDS 4
#define IMAGE_HEADER_OUTCOMES 7
enum { IMAGE_HEADER_NEITHER, IMAGE_HEADER_ACCESSOR_ONLY,
       IMAGE_HEADER_DICTIONARY_ONLY, IMAGE_HEADER_EQUAL, IMAGE_HEADER_DIFFERENT,
       IMAGE_HEADER_AMBIGUOUS, IMAGE_HEADER_UNINSPECTABLE };
static uint64_t image_header_observations;
static uint64_t image_header_response_identity[3]; /* same / different / missing task response */
static uint64_t image_header_counts[2][IMAGE_HEADER_FIELDS][IMAGE_HEADER_OUTCOMES];
static const char *const image_header_names[IMAGE_HEADER_FIELDS]={"Date","Cache-Control","Age","Expires"};

static void image_header_inspect(id response,unsigned outcomes[IMAGE_HEADER_FIELDS]) {
    for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++)outcomes[i]=IMAGE_HEADER_UNINSPECTABLE;
    if(!response || !bmsg1(response,"isKindOfClass:",(id)objc_getClass("NSHTTPURLResponse")))return;
    id fields=msg0(response,"allHeaderFields");
    if(!fields || !bmsg1(fields,"isKindOfClass:",(id)objc_getClass("NSDictionary")))return;
    id keys=msg0(fields,"keyEnumerator");if(!keys)return;
    unsigned matches[IMAGE_HEADER_FIELDS]={0};id values[IMAGE_HEADER_FIELDS]={nil};
    bool refused=false;
    for(unsigned scanned=0;;scanned++) {
        id key=msg0(keys,"nextObject");if(!key)break;
        if(scanned==128){refused=true;break;}
        if(!bmsg1(key,"isKindOfClass:",(id)objc_getClass("NSString"))){refused=true;continue;}
        const char *name=utf8(key);if(!name){refused=true;continue;}
        for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++)if(!strcasecmp(name,image_header_names[i])) {
            matches[i]++;values[i]=msg1(fields,"objectForKey:",key);
        }
    }
    if(refused)return;
    for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++) {
        id accessor=image_cache_field(response,image_header_names[i]),dictionary=values[i];
        if(matches[i]>1){outcomes[i]=IMAGE_HEADER_AMBIGUOUS;continue;}
        if((accessor && !bmsg1(accessor,"isKindOfClass:",(id)objc_getClass("NSString"))) ||
           (matches[i] && (!dictionary || !bmsg1(dictionary,"isKindOfClass:",(id)objc_getClass("NSString")))))continue;
        outcomes[i]=accessor ? (dictionary ? (bmsg1(accessor,"isEqual:",dictionary) ? IMAGE_HEADER_EQUAL:IMAGE_HEADER_DIFFERENT):IMAGE_HEADER_ACCESSOR_ONLY):
                              (dictionary ? IMAGE_HEADER_DICTIONARY_ONLY:IMAGE_HEADER_NEITHER);
    }
}
static void image_header_observe(id proposed_response,id task) {
    id task_response=msg0(task,"response");unsigned outcomes[2][IMAGE_HEADER_FIELDS];
    image_header_inspect(proposed_response,outcomes[0]);image_header_inspect(task_response,outcomes[1]);
    pthread_mutex_lock(&image_cache_metadata_lock);
    image_header_observations++;
    image_header_response_identity[!task_response ? 2:task_response==proposed_response ? 0:1]++;
    for(unsigned scope=0;scope<2;scope++)for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++)image_header_counts[scope][i][outcomes[scope][i]]++;
    pthread_mutex_unlock(&image_cache_metadata_lock);
}
/* Called under the existing metadata lock. All labels are fixed. */
static void image_header_status(char *buffer,size_t capacity) {
    size_t used=strlen(buffer);
    if(used<capacity)snprintf(buffer+used,capacity-used,
        "Header probe proposals; task response same/different/missing: %llu; %llu/%llu/%llu\n"
        "Header probe outcomes: neither/accessor-only/dictionary-only/both-equal/both-different/ambiguous/uninspectable. Case-insensitive dictionary scan; max 128 keys.\n",
        (unsigned long long)image_header_observations,(unsigned long long)image_header_response_identity[0],
        (unsigned long long)image_header_response_identity[1],(unsigned long long)image_header_response_identity[2]);
    static const char *const labels[IMAGE_HEADER_FIELDS]={"Date","control","Age","Expires"};
    for(unsigned scope=0;scope<2;scope++)for(unsigned i=0;i<IMAGE_HEADER_FIELDS;i++) {
        used=strlen(buffer);if(used>=capacity)break;
        uint64_t *row=image_header_counts[scope][i];
        snprintf(buffer+used,capacity-used,"Header probe %s %s: %llu/%llu/%llu/%llu/%llu/%llu/%llu\n",
            scope ? "task":"proposed",labels[i],(unsigned long long)row[0],(unsigned long long)row[1],
            (unsigned long long)row[2],(unsigned long long)row[3],(unsigned long long)row[4],(unsigned long long)row[5],(unsigned long long)row[6]);
    }
}
#endif
