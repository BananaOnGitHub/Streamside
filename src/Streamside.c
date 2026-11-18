#include "TASInvestigationHost.h"
/*
 * Streamside for Twitch iOS
 *
 * Native iOS adaptation of pixeltris/TwitchAdSolutions VAFT v24.
 *
 * This intentionally uses the Objective-C runtime instead of private Twitch
 * symbols. Twitch's Amazon IVS player and AVFoundation playback are both
 * covered: GraphQL and HLS requests are normalized through NSURLProtocol,
 * with AVAssetResourceLoader retained as a compatibility path.
 */

#include <objc/objc.h>
#include <objc/runtime.h>
#include <objc/message.h>

#include <dispatch/dispatch.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/time.h>
#include <sys/sysctl.h>

#include "TASDiagnostics.h"
#include "TASEmotes.h"
#include "TASImageTransport.h"

typedef unsigned long NSUInteger;
typedef long NSInteger;
#define TAS_INTERNAL_HEADER "X-TAS-Internal"
#define TAS_CLIENT_ID "kimne78kx3ncx6brgo4mv6wki5h1ko"
#define TAS_TOKEN_HASH "ed230aa1e33e07eebb8928504583da78a5173989fadfb1ac94be06a04f3cdbe9"

extern id objc_retain(id object);
extern void objc_release(id object);
extern id objc_getAssociatedObject(id object, const void *key);
extern void objc_setAssociatedObject(id object, const void *key, id value, uintptr_t policy);
extern int objc_sync_enter(id object);
extern int objc_sync_exit(id object);
extern uint32_t arc4random_uniform(uint32_t upper_bound);

static id msg0(id object, const char *selector) {
    return ((id (*)(id, SEL))objc_msgSend)(object, sel_registerName(selector));
}

static id msg1(id object, const char *selector, id a) {
    return ((id (*)(id, SEL, id))objc_msgSend)(object, sel_registerName(selector), a);
}

static id msg2(id object, const char *selector, id a, id b) {
    return ((id (*)(id, SEL, id, id))objc_msgSend)(object, sel_registerName(selector), a, b);
}

static void vmsg1(id object, const char *selector, id a) {
    ((void (*)(id, SEL, id))objc_msgSend)(object, sel_registerName(selector), a);
}

static void vmsg2(id object, const char *selector, id a, id b) {
    ((void (*)(id, SEL, id, id))objc_msgSend)(object, sel_registerName(selector), a, b);
}

static void vmsg3(id object, const char *selector, id a, id b, NSInteger c) {
    ((void (*)(id, SEL, id, id, NSInteger))objc_msgSend)(object, sel_registerName(selector), a, b, c);
}

static BOOL bmsg1(id object, const char *selector, id a) {
    return ((BOOL (*)(id, SEL, id))objc_msgSend)(object, sel_registerName(selector), a);
}

static NSInteger imsg0(id object, const char *selector) {
    return ((NSInteger (*)(id, SEL))objc_msgSend)(object, sel_registerName(selector));
}

static id nsstr(const char *value) {
    if (!value) return nil;
    return msg1((id)objc_getClass("NSString"), "stringWithUTF8String:", (id)value);
}

static const char *utf8(id value) {
    if (!value) return NULL;
    return ((const char *(*)(id, SEL))objc_msgSend)(value, sel_registerName("UTF8String"));
}

static id nsurl(const char *value) {
    return msg1((id)objc_getClass("NSURL"), "URLWithString:", nsstr(value));
}

static id data_from_bytes(const void *bytes, size_t length) {
    return ((id (*)(id, SEL, const void *, NSUInteger))objc_msgSend)(
        (id)objc_getClass("NSData"), sel_registerName("dataWithBytes:length:"), bytes, (NSUInteger)length);
}

static const uint8_t *data_bytes(id data) {
    return ((const uint8_t *(*)(id, SEL))objc_msgSend)(data, sel_registerName("bytes"));
}

static size_t data_length(id data) {
    return (size_t)((NSUInteger (*)(id, SEL))objc_msgSend)(data, sel_registerName("length"));
}

static char g_authorization[4096];
static char g_integrity[4096];
static char g_device_id[512];
static char g_client_version[512];
static char g_client_session[512];
static char g_association_key;
static char g_protocol_task_key, g_protocol_stopped_key, g_protocol_completed_key;
static id g_protocol_session;
static IMP g_original_asset_init;
static IMP g_original_default_configuration;
static IMP g_original_ephemeral_configuration;
static IMP g_original_session_with_configuration;
static IMP g_original_session_with_configuration_delegate_queue;
static IMP g_original_data_task_request;
static IMP g_original_data_task_request_completion;
static Class g_protocol_class;
static Class g_loader_class;

static char *absolute_url(const char *base, const char *relative);
static char *process_manifest(const char *url, const char *playlist, bool custom_scheme);

#include "TASVAFT.h"

static void cache_header(id request, const char *header, char *destination, size_t capacity) {
    id value = msg1(request, "valueForHTTPHeaderField:", nsstr(header));
    const char *string = utf8(value);
    if (string && string[0]) copy_string(destination, capacity, string);
}

static void cache_twitch_headers(id request) {
    pthread_mutex_lock(&g_lock);
    cache_header(request, "Authorization", g_authorization, sizeof(g_authorization));
    cache_header(request, "Client-Integrity", g_integrity, sizeof(g_integrity));
    cache_header(request, "X-Device-Id", g_device_id, sizeof(g_device_id));
    if (!g_device_id[0]) cache_header(request, "Device-ID", g_device_id, sizeof(g_device_id));
    cache_header(request, "Client-Version", g_client_version, sizeof(g_client_version));
    cache_header(request, "Client-Session-Id", g_client_session, sizeof(g_client_session));
    pthread_mutex_unlock(&g_lock);
}

static bool json_space(char value) {
    return value == ' ' || value == '\t' || value == '\r' || value == '\n';
}

static char *replace_json_string(char *source, const char *key, const char *replacement) {
    if (!source || !key || !replacement) return source;
    char needle[256];
    snprintf(needle, sizeof(needle), "\"%s\"", key);
    size_t source_length = strlen(source);
    size_t replacement_length = strlen(replacement);
    size_t capacity = source_length + 64;
    size_t length = 0;
    char *result = calloc(capacity, 1);
    if (!result) return source;

    const char *cursor = source;
    const char *match;
    bool changed = false;
    while ((match = strstr(cursor, needle))) {
        const char *colon = match + strlen(needle);
        while (json_space(*colon)) colon++;
        if (*colon != ':') {
            size_t chunk = (size_t)(colon - cursor);
            if (length + chunk + 1 > capacity) {
                capacity = (length + chunk + 1) * 2;
                result = realloc(result, capacity);
            }
            memcpy(result + length, cursor, chunk);
            length += chunk;
            cursor = colon;
            continue;
        }
        const char *quote = colon + 1;
        while (json_space(*quote)) quote++;
        if (*quote != '"') {
            size_t chunk = (size_t)(quote - cursor);
            if (length + chunk + 1 > capacity) {
                capacity = (length + chunk + 1) * 2;
                result = realloc(result, capacity);
            }
            memcpy(result + length, cursor, chunk);
            length += chunk;
            cursor = quote;
            continue;
        }
        const char *value = quote + 1;
        const char *end = value;
        while (*end && (*end != '"' || (end > value && end[-1] == '\\'))) end++;
        if (!*end) break;
        size_t prefix = (size_t)(value - cursor);
        size_t needed = length + prefix + replacement_length + 1;
        if (needed > capacity) {
            capacity = needed * 2;
            result = realloc(result, capacity);
        }
        memcpy(result + length, cursor, prefix);
        length += prefix;
        memcpy(result + length, replacement, replacement_length);
        length += replacement_length;
        cursor = end;
        changed = true;
    }
    size_t tail = strlen(cursor);
    if (length + tail + 1 > capacity) {
        capacity = length + tail + 1;
        result = realloc(result, capacity);
    }
    memcpy(result + length, cursor, tail + 1);
    if (!changed) {
        free(result);
        return source;
    }
    free(source);
    return result;
}

static id normalized_graphql_body(id body) {
    char *json = copy_data_text(body);
    if (!json) return body;
    if (!(contains(json, "PlaybackAccessToken") || contains(json, "StreamAccessToken") ||
          contains(json, "streamPlaybackAccessToken"))) {
        free(json);
        return body;
    }
    tas_diag_metric(TAS_DIAG_GRAPHQL_REWRITE, 1);
    tas_diag_log("GQL_REWRITE", "Playback access-token request playerType normalized to popout");
    json = replace_json_string(json, "playerType", "popout");
    id result = data_from_bytes(json, strlen(json));
    free(json);
    return result ?: body;
}

static id normalized_graphql_request_copy(id original) {
    if (!original) return nil;
    id url = msg0(original, "URL");
    const char *host = utf8(msg0(url, "host"));
    if (!host || strcmp(host, "gql.twitch.tv") != 0) return nil;

    cache_twitch_headers(original);
    id body = msg0(original, "HTTPBody");
    if (!body) return nil;
    char *json = copy_data_text(body);
    bool is_playback_token = json &&
        (contains(json, "PlaybackAccessToken") || contains(json, "StreamAccessToken") ||
         contains(json, "streamPlaybackAccessToken"));
    free(json);
    if (!is_playback_token) return nil;

    id request = msg0(original, "mutableCopy");
    vmsg1(request, "setHTTPBody:", normalized_graphql_body(body));
    return request;
}

static char *remove_query_parameter(const char *url, const char *name) {
    const char *question = strchr(url, '?');
    if (!question) return strdup(url);
    size_t base_length = (size_t)(question - url);
    char *result = calloc(strlen(url) + 1, 1);
    memcpy(result, url, base_length);
    char *query = strdup(question + 1);
    char *save = NULL;
    bool first = true;
    size_t name_length = strlen(name);
    for (char *item = strtok_r(query, "&", &save); item; item = strtok_r(NULL, "&", &save)) {
        if (strncmp(item, name, name_length) == 0 && item[name_length] == '=') continue;
        strcat(result, first ? "?" : "&");
        strcat(result, item);
        first = false;
    }
    free(query);
    return result;
}

static id make_internal_request(const char *url, const char *method) {
    id request = msg1((id)objc_getClass("NSMutableURLRequest"), "requestWithURL:", nsurl(url));
    vmsg1(request, "setHTTPMethod:", nsstr(method));
    vmsg2(request, "setValue:forHTTPHeaderField:", nsstr("1"), nsstr(TAS_INTERNAL_HEADER));
    return request;
}

static id synchronous_request(id request, id *response, id *error) {
    return ((id (*)(id, SEL, id, id *, id *))objc_msgSend)(
        (id)objc_getClass("NSURLConnection"),
        sel_registerName("sendSynchronousRequest:returningResponse:error:"),
        request, response, error);
}

#include "TASVAFTBlank.h"
static id blank_video_data(void) {
    id allocated=msg0((id)objc_getClass("NSData"),"alloc");
    id data=((id(*)(id,SEL,id,NSUInteger))objc_msgSend)(allocated,
        sel_registerName("initWithBase64EncodedString:options:"),nsstr(TAS_VAFT_BLANK_BASE64),0);
    return msg0(data,"autorelease");
}

static id http_response(const char *url, NSInteger status, const char *mime, size_t length, id original) {
    id original_headers = original ? msg0(original, "allHeaderFields") : nil;
    id headers = original_headers ? msg0(original_headers, "mutableCopy") :
                                   msg0((id)objc_getClass("NSMutableDictionary"), "dictionary");
    char length_string[64];
    snprintf(length_string, sizeof(length_string), "%zu", length);
    vmsg2(headers, "setObject:forKey:", nsstr(length_string), nsstr("Content-Length"));
    vmsg2(headers, "setObject:forKey:", nsstr(mime), nsstr("Content-Type"));
    id response = msg0((id)objc_getClass("NSHTTPURLResponse"), "alloc");
    response = ((id (*)(id, SEL, id, NSInteger, id, id))objc_msgSend)(
        response, sel_registerName("initWithURL:statusCode:HTTPVersion:headerFields:"),
        nsurl(url), status, nsstr("HTTP/1.1"), headers);
    if (original_headers) objc_release(headers);
    return response;
}

#include "TASImageDemand.h"
/* Callback delivery and stopLoading serialize on the protocol instance. The
 * ObjC monitor is recursive: a client may synchronously stop from a callback. */
static void protocol_deliver(id self, id data, id response, id error) {
    objc_sync_enter(self);
    if (!objc_getAssociatedObject(self, &g_protocol_stopped_key)) {
        id client = msg0(self, "client");
        if (error || !response) {
            if (!error) error = ((id (*)(id, SEL, id, NSInteger, id))objc_msgSend)(
                (id)objc_getClass("NSError"), sel_registerName("errorWithDomain:code:userInfo:"),
                nsstr("NSURLErrorDomain"), -1, nil);
            vmsg2(client, "URLProtocol:didFailWithError:", self, error);
        } else {
            vmsg3(client, "URLProtocol:didReceiveResponse:cacheStoragePolicy:", self, response, 0);
            if (data && !objc_getAssociatedObject(self, &g_protocol_stopped_key))
                vmsg2(client, "URLProtocol:didLoadData:", self, data);
            if (!objc_getAssociatedObject(self, &g_protocol_stopped_key))
                vmsg1(client, "URLProtocolDidFinishLoading:", self);
        }
    }
    objc_setAssociatedObject(self, &g_protocol_task_key, nil, 1);
    objc_sync_exit(self);
}

static void protocol_complete(id self, id data, id response, id error) {
    id original = msg0(self, "request");
    const char *original_url = utf8(msg0(msg0(original, "URL"), "absoluteString"));
    objc_sync_enter(self);
    bool stopped = objc_getAssociatedObject(self, &g_protocol_stopped_key) != nil;
    objc_setAssociatedObject(self, &g_protocol_completed_key, nsstr("completed"), 1);
    objc_sync_exit(self);
    if (stopped) return;

    if (original_url && tas_emotes_is_provider_image_url(original_url))
        tas_emotes_image_result_for_url(original_url, data, response, error);
    id output_data = data, output_response = response, rewritten_response = nil;
    if (original_url && is_twitch_hls_url(original_url)) {
        if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_DETAILED)) {
        char detail[256];
        snprintf(detail, sizeof(detail), "transport=NSURLProtocol status=%ld bytes=%zu error=%s",
                 response ? (long)imsg0(response, "statusCode") : 0L,
                 data ? data_length(data) : 0, error ? "yes" : "no");
        tas_diag_log_url("HLS_RESPONSE", original_url, detail);
        }
        if (error || !data || !response || imsg0(response, "statusCode") < 200 ||
            imsg0(response, "statusCode") >= 300) tas_diag_metric(TAS_DIAG_HLS_FAILURE, 1);
    }
    if (!error && data && response && original_url && is_twitch_hls_url(original_url)) {
        char *text = copy_data_text(data);
        if (text && starts_with(text, "#EXTM3U")) {
            char *processed = process_manifest(original_url, text, false);
            output_data = data_from_bytes(processed, strlen(processed));
            rewritten_response = http_response(original_url, imsg0(response, "statusCode"),
                                               "application/vnd.apple.mpegurl",
                                               data_length(output_data), response);
            output_response = rewritten_response;
            free(processed);
        }
        free(text);
    }
    protocol_deliver(self, output_data, output_response, error);
    if (rewritten_response) objc_release(rewritten_response);
}

static bool image_public_request(id);
#include "TASImageCache.h"
static id protocol_session(bool provider_image) {
    static id image_session;
    static pthread_mutex_t session_lock = PTHREAD_MUTEX_INITIALIZER;
    /* HLS completions synchronously fetch alternate tokens/manifests. A
     * separate session gives images their own bounded concurrent queue, so
     * those fetches cannot hold image delivery behind an ad-bearing playlist. */
    pthread_mutex_lock(&session_lock);
    id *slot = provider_image ? &image_session : &g_protocol_session;
    if (!*slot) {
        id config = msg0((id)objc_getClass("NSURLSessionConfiguration"), "defaultSessionConfiguration");
        if (provider_image) {
            /* The native input and RN image loader use different outer caches.
             * Both now share a dedicated HTTP cache, obeying CDN expiry/Vary/
             * no-store rules rather than inheriting Twitch's reload policy. */
            id cache = ((id (*)(id,SEL,NSUInteger,NSUInteger,id))objc_msgSend)(
                msg0((id)objc_getClass("NSURLCache"), "alloc"),
                sel_registerName("initWithMemoryCapacity:diskCapacity:diskPath:"),
                32*1024*1024, 128*1024*1024, nsstr("StreamsideProviderImages"));
            vmsg1(config, "setURLCache:", cache);
            image_cache_store=objc_retain(cache);
            objc_release(cache);
            ((void (*)(id,SEL,NSUInteger))objc_msgSend)(config,
                sel_registerName("setHTTPMaximumConnectionsPerHost:"), 8);
            ((void (*)(id,SEL,double))objc_msgSend)(config,
                sel_registerName("setTimeoutIntervalForRequest:"), 15.0);
            ((void (*)(id,SEL,double))objc_msgSend)(config,
                sel_registerName("setTimeoutIntervalForResource:"), 30.0);
            id queue = msg0((id)objc_getClass("NSOperationQueue"), "new");
            ((void (*)(id,SEL,NSInteger))objc_msgSend)(queue,
                sel_registerName("setMaxConcurrentOperationCount:"), 4);
            id demand_delegate=image_cache_delegate();
            *slot = objc_retain(((id (*)(id,SEL,id,id,id))objc_msgSend)(
                (id)objc_getClass("NSURLSession"),
                sel_registerName("sessionWithConfiguration:delegate:delegateQueue:"), config, demand_delegate, queue));
            objc_release(demand_delegate);
            objc_release(queue);
        } else {
            *slot = objc_retain(msg1((id)objc_getClass("NSURLSession"), "sessionWithConfiguration:", config));
        }
    }
    id session = *slot;
    if(provider_image)__atomic_store_n(&image_cache_session,(void *)session,__ATOMIC_RELEASE);
    pthread_mutex_unlock(&session_lock);
    return session;
}

/* Bounded, in-flight public-image fan-out. Each consumer retains its own
 * cancellation/delivery state. A stopped view must not cancel another view's
 * download. No client callbacks or cancel messages occur under this lock. */
#define IMAGE_FLIGHTS 512
#define IMAGE_CONSUMERS 64
#define IMAGE_ACTIVE 8
#define IMAGE_BACKGROUND_ACTIVE 6
typedef struct {
    char *url;
    id request, session, task, consumers[IMAGE_CONSUMERS];
    unsigned count;
    uint64_t generation;
    bool running, foreground;
    struct timespec queued, started;
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
    struct timespec detached;
#endif
} ImageFlight;
static ImageFlight image_flights[IMAGE_FLIGHTS];
static char image_consumer_key;
static pthread_mutex_t image_transport_lock = PTHREAD_MUTEX_INITIALIZER;
static uint64_t image_generation, image_downloads, image_joined, image_finished, image_errors;
static uint64_t image_latency[4], image_queue_latency[4], image_body_sizes[4];
static uint64_t image_queued_cancelled, image_orphans, image_rejoined, image_orphan_finished, image_refused;
static uint64_t image_error_cancelled, image_error_timeout, image_error_other;
static unsigned image_active, image_background_active;
static bool image_pumping;
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
static unsigned demand_flight_peak,demand_queue_peak,demand_consumer_peak;
static uint64_t demand_header_mismatch,demand_consumer_full,demand_url_matches;
static uint64_t demand_detached_time[4],demand_rejoin_time[4];
static void image_demand_occupancy(void) {
    if(!tas_diag_wants(TAS_DIAG_COMPOSER,TAS_DIAG_DETAILED))return;
    unsigned occupied=0,queued=0,consumers=0;
    for(unsigned i=0;i<IMAGE_FLIGHTS;i++)if(image_flights[i].url){occupied++;queued+=!image_flights[i].running;consumers+=image_flights[i].count;}
    if(occupied>demand_flight_peak)demand_flight_peak=occupied;
    if(queued>demand_queue_peak)demand_queue_peak=queued;
    if(consumers>demand_consumer_peak)demand_consumer_peak=consumers;
    tas_demand_transport(image_active,queued,consumers,image_queued_cancelled+image_orphans);
}
#endif

static unsigned image_bucket(double seconds) { return seconds<=.25 ? 0 : seconds<=1 ? 1 : seconds<=5 ? 2 : 3; }
static double image_elapsed(struct timespec from, struct timespec to) {
    return to.tv_sec-from.tv_sec+(to.tv_nsec-from.tv_nsec)/1000000000.0;
}
static void image_schedule(void);
static void image_cache_status(char *,size_t);
static void image_overflow_drain_locked(void);
static void image_overflow_status_locked(char *,size_t);

void tas_image_transport_status(char *buffer, size_t capacity) {
    pthread_mutex_lock(&image_transport_lock);
    snprintf(buffer, capacity,
        "Provider image transport (shared; this launch)\n"
        "Shared loads/coalesced/completed/errors: %llu/%llu/%llu/%llu\n"
        "Transport completions <=250ms/<=1s/<=5s/>5s: %llu/%llu/%llu/%llu\n"
        "Queue wait <=250ms/<=1s/<=5s/>5s: %llu/%llu/%llu/%llu\n"
        "Queued cancellations/active detached/rejoined/detached completions/budget refusals: %llu/%llu/%llu/%llu/%llu\n"
        "Transport errors cancelled/timeout/other: %llu/%llu/%llu\n"
        "Response bodies <=64KiB/<=256KiB/<=1MiB/>1MiB: %llu/%llu/%llu/%llu\n"
        "Active/background/limit: %u/%u/8 (background max 6); HTTP cache memory/disk: 32/128 MiB.\n"
        "Transport timing excludes queue wait and image decoding; CDN expiry respected.\n",
        (unsigned long long)image_downloads, (unsigned long long)image_joined,
        (unsigned long long)image_finished, (unsigned long long)image_errors,
        (unsigned long long)image_latency[0], (unsigned long long)image_latency[1],
        (unsigned long long)image_latency[2], (unsigned long long)image_latency[3],
        (unsigned long long)image_queue_latency[0], (unsigned long long)image_queue_latency[1],
        (unsigned long long)image_queue_latency[2], (unsigned long long)image_queue_latency[3],
        (unsigned long long)image_queued_cancelled, (unsigned long long)image_orphans,
        (unsigned long long)image_rejoined, (unsigned long long)image_orphan_finished, (unsigned long long)image_refused,
        (unsigned long long)image_error_cancelled, (unsigned long long)image_error_timeout, (unsigned long long)image_error_other,
        (unsigned long long)image_body_sizes[0], (unsigned long long)image_body_sizes[1],
        (unsigned long long)image_body_sizes[2], (unsigned long long)image_body_sizes[3], image_active, image_background_active);
    image_overflow_status_locked(buffer,capacity);
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
    unsigned queued=0,occupied=0,detached=0,consumers=0;double oldest=0,oldest_detached=0;
    struct timespec now;clock_gettime(CLOCK_MONOTONIC,&now);
    for(unsigned i=0;i<IMAGE_FLIGHTS;i++)if(image_flights[i].url){
        ImageFlight *f=&image_flights[i];occupied++;consumers+=f->count;
        if(!f->running){queued++;double age=image_elapsed(f->queued,now);if(age>oldest)oldest=age;}
        else if(!f->count){detached++;double age=image_elapsed(f->detached,now);if(age>oldest_detached)oldest_detached=age;}
    }
    size_t used=strlen(buffer);
    if(used<capacity)snprintf(buffer+used,capacity-used,
        "Passive flight registry current/peak queued current/peak consumers current/peak detached active: %u/%u %u/%u %u/%u %u\n"
        "Oldest queued/detached age (seconds): %.1f/%.1f; same URL comparisons/header mismatches/full consumer groups: %llu/%llu/%llu\n"
        "Detached duration to completion <=250ms/<=1s/<=5s/>5s: %llu/%llu/%llu/%llu; rejoin delay: %llu/%llu/%llu/%llu\n",
        occupied,demand_flight_peak,queued,demand_queue_peak,consumers,demand_consumer_peak,detached,oldest,oldest_detached,
        (unsigned long long)demand_url_matches,(unsigned long long)demand_header_mismatch,(unsigned long long)demand_consumer_full,
        (unsigned long long)demand_detached_time[0],(unsigned long long)demand_detached_time[1],(unsigned long long)demand_detached_time[2],(unsigned long long)demand_detached_time[3],
        (unsigned long long)demand_rejoin_time[0],(unsigned long long)demand_rejoin_time[1],(unsigned long long)demand_rejoin_time[2],(unsigned long long)demand_rejoin_time[3]);
#endif
    pthread_mutex_unlock(&image_transport_lock);
    size_t cache_used=strlen(buffer);
    if(cache_used<capacity)image_cache_status(buffer+cache_used,capacity-cache_used);
}

static bool image_public_request(id request) {
    const char *method = utf8(msg0(request, "HTTPMethod"));
    return (!method || !strcmp(method, "GET")) && !msg0(request, "HTTPBody") && !msg0(request,"HTTPBodyStream") &&
        !msg1(request, "valueForHTTPHeaderField:", nsstr("Authorization")) &&
        !msg1(request, "valueForHTTPHeaderField:", nsstr("Cookie")) &&
        !msg1(request, "valueForHTTPHeaderField:", nsstr("Range"));
}

static void image_flight_complete(unsigned index, uint64_t generation, id data, id response, id error) {
    id consumers[IMAGE_CONSUMERS], task = nil, request = nil;
    unsigned count = 0;
    pthread_mutex_lock(&image_transport_lock);
    ImageFlight *flight = &image_flights[index];
    /* Active detached loads finish into the HTTP cache. Stopped clients are
     * absent from this array; they receive no late callback. */
    if (flight->generation == generation && flight->url) {
        count = flight->count;
        memcpy(consumers, flight->consumers, count*sizeof(id));
        task = flight->task; request = flight->request;
        struct timespec now; clock_gettime(CLOCK_MONOTONIC, &now);
        double seconds = image_elapsed(flight->started, now);
        if (flight->running) { image_active--; if (!flight->foreground) image_background_active--; }
        image_finished++; if (error || !response) image_errors++;
        if (error) {
            NSInteger code=imsg0(error,"code");
            if (code==-999) image_error_cancelled++; else if (code==-1001) image_error_timeout++; else image_error_other++;
        } else if (!response) image_error_other++;
        image_latency[image_bucket(seconds)]++;
        if (data) { size_t bytes=data_length(data); image_body_sizes[bytes<=65536 ? 0 : bytes<=262144 ? 1 : bytes<=1048576 ? 2 : 3]++; }
        if (!count) image_orphan_finished++;
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
        if(!count)demand_detached_time[image_bucket(image_elapsed(flight->detached,now))]++;
#endif
        free(flight->url); memset(flight, 0, sizeof(*flight));
        image_overflow_drain_locked();
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
        image_demand_occupancy();
#endif
    }
    pthread_mutex_unlock(&image_transport_lock);
    for (unsigned i = 0; i < count; i++) {
        protocol_complete(consumers[i], data, response, error);
        objc_release(consumers[i]);
    }
    objc_release(task); objc_release(request);
    image_schedule();
}

/* Only eight transfers can be active, including detached ones. Two slots are
 * reserved from direct-library requests for synthetic-ID chat/input loads.
 * Queued consumers disappearing never start a network task. */
static void image_schedule(void) {
    pthread_mutex_lock(&image_transport_lock);
    if (image_pumping) { pthread_mutex_unlock(&image_transport_lock); return; }
    image_pumping=true;
    image_overflow_drain_locked();
    for (;;) {
        unsigned index=IMAGE_FLIGHTS;
        for (unsigned i=0;image_active<IMAGE_ACTIVE && i<IMAGE_FLIGHTS;i++) {
            ImageFlight *f=&image_flights[i];
            if (!f->url || !f->session || f->running || !f->count || (!f->foreground && image_background_active>=IMAGE_BACKGROUND_ACTIVE)) continue;
            if (index==IMAGE_FLIGHTS || (f->foreground && !image_flights[index].foreground) ||
                (f->foreground==image_flights[index].foreground && f->generation<image_flights[index].generation)) index=i;
        }
        if (index==IMAGE_FLIGHTS) break;
        ImageFlight *f=&image_flights[index]; uint64_t generation=f->generation;
        f->running=true; image_active++; if (!f->foreground) image_background_active++;
        clock_gettime(CLOCK_MONOTONIC,&f->started);
        image_queue_latency[image_bucket(image_elapsed(f->queued,f->started))]++;
        f->task=objc_retain(image_cache_task(f->session,f->request,
            (id)^(id data,id response,id error) { image_flight_complete(index,generation,data,response,error); }));
        id task=objc_retain(f->task); image_downloads++;
        pthread_mutex_unlock(&image_transport_lock);
        if (task) { image_cache_mark_task(task);msg0(task,"resume"); } else image_flight_complete(index,generation,nil,nil,nil);
        objc_release(task);
        pthread_mutex_lock(&image_transport_lock);
    }
    image_pumping=false;
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
    image_demand_occupancy();
#endif
    pthread_mutex_unlock(&image_transport_lock);
}

/* Caller owns transport lock. Cache handoff also owns the lookup lock, so a
 * cancelling consumer cannot disappear between the two registries. */
static unsigned image_flight_add_locked(id self,id session,id request,const char *url,bool foreground,bool allocate,bool task_pointer) {
    unsigned available = IMAGE_FLIGHTS;
    for (unsigned i = 0; i < IMAGE_FLIGHTS; i++) {
        ImageFlight *flight = &image_flights[i];
        if (!flight->url) { if (available == IMAGE_FLIGHTS) available = i; continue; }
        if (strcmp(flight->url, url)) continue;
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
        demand_url_matches++;
        if(flight->count==IMAGE_CONSUMERS)demand_consumer_full++;
#endif
        if(flight->count==IMAGE_CONSUMERS)continue;
        if(imsg0(flight->request,"cachePolicy")!=imsg0(request,"cachePolicy"))continue;
        /* Respect request variants; never conflate differing Accept/other
         * headers. Cache policy is normalized before this comparison. */
        id a = msg0(flight->request, "allHTTPHeaderFields"), b = msg0(request, "allHTTPHeaderFields");
        if (a != b && !bmsg1(a, "isEqual:", b)) {
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
            demand_header_mismatch++;
#endif
            continue;
        }
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
        if(!flight->count){struct timespec now;clock_gettime(CLOCK_MONOTONIC,&now);demand_rejoin_time[image_bucket(image_elapsed(flight->detached,now))]++;}
#endif
        if (!flight->count) image_rejoined++;
        if (foreground && !flight->foreground) {
            if (flight->running) image_background_active--;
            flight->foreground=true;
        }
        flight->consumers[flight->count++] = objc_retain(self);
        objc_setAssociatedObject(self, &image_consumer_key, nsstr("1"), 1);
        if(task_pointer)objc_setAssociatedObject(self, &g_protocol_task_key, flight->task, 1);
        image_joined++;
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
        image_demand_occupancy();
#endif
        return i;
    }
    if(!allocate)return IMAGE_FLIGHTS;
    if (available == IMAGE_FLIGHTS) { image_refused++;return IMAGE_FLIGHTS; }
    ImageFlight *flight = &image_flights[available];
    flight->url = strdup(url);
    if (!flight->url) { image_refused++;return IMAGE_FLIGHTS; }
    flight->generation = ++image_generation;
    flight->request = objc_retain(request);
    flight->session=session; flight->foreground=foreground;
    flight->consumers[flight->count++] = objc_retain(self);
    clock_gettime(CLOCK_MONOTONIC, &flight->queued);
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
    image_demand_occupancy();
#endif
    objc_setAssociatedObject(self, &image_consumer_key, nsstr("1"), 1);
    return available;
}
#include "TASImageOverflow.h"
static bool image_flight_admit(id self,id session,id request,const char *url,bool foreground,bool allocate) {
    pthread_mutex_lock(&image_transport_lock);
    unsigned index=image_flight_add_locked(self,session,request,url,foreground,allocate,true);
    bool deferred=index==IMAGE_FLIGHTS && allocate && image_overflow_admit_locked(self,session,request,url,foreground);
    uint64_t generation=index<IMAGE_FLIGHTS ? image_flights[index].generation:0;
    pthread_mutex_unlock(&image_transport_lock);
    if(index==IMAGE_FLIGHTS) {
        if(!allocate)return false;
        if(!deferred)protocol_complete(self,nil,nil,nil);
        return true;
    }
    image_schedule();
    /* The initiating consumer's monitor is held by startLoading. Queued
     * consumers are found by identity on stop, not by a future task pointer. */
    pthread_mutex_lock(&image_transport_lock);
    ImageFlight *flight=&image_flights[index];
    if (flight->url && flight->generation==generation)
        objc_setAssociatedObject(self, &g_protocol_task_key, flight->task, 1);
    pthread_mutex_unlock(&image_transport_lock);
    return true;
}

static bool image_flight_start(id self,id session,id request,const char *url,bool foreground) {
    return image_flight_admit(self,session,request,url,foreground,true);
}
/* Detach this consumer by identity, including queued consumers without tasks.
 * Completion may already have removed it; its stopped flag still blocks delivery. */
static bool image_flight_stop(id self) {
    bool shared = false;
    id request = nil, consumer = nil;char *overflow_url=NULL;
    pthread_mutex_lock(&image_transport_lock);
    shared=image_overflow_stop_locked(self,&request,&consumer,&overflow_url);
    for (unsigned i = 0; i < IMAGE_FLIGHTS && !shared; i++) {
        ImageFlight *flight = &image_flights[i];
        if (!flight->url) continue;
        for (unsigned j = 0; j < flight->count; j++) if (flight->consumers[j] == self) {
            shared = true; consumer = flight->consumers[j];
            memmove(&flight->consumers[j], &flight->consumers[j+1], (--flight->count-j)*sizeof(id));
            if (!flight->count) {
                if (flight->running) {
                    image_orphans++;
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
                    clock_gettime(CLOCK_MONOTONIC,&flight->detached);
#endif
                }
                else {
                    image_queued_cancelled++; request=flight->request;
                    free(flight->url); memset(flight,0,sizeof(*flight));
                }
            }
            break;
        }
    }
    image_overflow_drain_locked();
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
    image_demand_occupancy();
#endif
    pthread_mutex_unlock(&image_transport_lock);
    free(overflow_url);objc_release(request); objc_release(consumer);
    image_schedule();
    return shared;
}

#include "TASImageCacheLane.h"
static void protocol_start_loading(id self, SEL command) {
    (void)command;
    id original = msg0(self, "request");
    const char *original_url = utf8(msg0(msg0(original, "URL"), "absoluteString"));

    if (original_url && is_cached_ad_segment(original_url)) {
        tas_diag_metric(TAS_DIAG_SYNTHETIC_SEGMENT, 1);
        tas_diag_log_url("SYNTHETIC_SEGMENT", original_url, "transport=NSURLProtocol");
        id data = blank_video_data();
        id response = http_response(original_url, 200, "video/mp4", data_length(data), nil);
        protocol_deliver(self, data, response, nil);
        objc_release(response);
        return;
    }

    id request = msg0(original, "mutableCopy");
    vmsg2(request, "setValue:forHTTPHeaderField:", nsstr("1"), nsstr(TAS_INTERNAL_HEADER));
    if (original_url && contains(original_url, "/channel/hls/")) {
        char *network_url = remove_query_parameter(original_url, "parent_domains");
        vmsg1(request, "setURL:", nsurl(network_url));
        free(network_url);
    }
    cache_twitch_headers(request);
    id body = msg0(request, "HTTPBody");
    if (body) vmsg1(request, "setHTTPBody:", normalized_graphql_body(body));

    if (original_url && is_twitch_hls_url(original_url)) {
        tas_diag_metric(TAS_DIAG_HLS_INTERCEPTED, 1);
        tas_diag_log_url("HLS_REQUEST", original_url, "transport=NSURLProtocol");
    }

    bool provider_image = original_url && tas_emotes_is_provider_image_url(original_url);
    /* Keep ordinary Twitch reload normalization, not explicit cache-only or
     * conditional-request restrictions. Such requests remain Foundation-owned. */
    NSUInteger policy=(NSUInteger)imsg0(request,"cachePolicy");
    bool share_image = provider_image && image_public_request(request);
    if(provider_image)tas_demand_request(request,tas_demand_url_scope(msg0(original,"URL")));
    if (share_image && (policy==0 || policy==1)) ((void (*)(id,SEL,NSUInteger))objc_msgSend)(request,
        sel_registerName("setCachePolicy:"), 0); /* NSURLRequestUseProtocolCachePolicy */
    /* Mark the inner request before it enters our swizzled session factory,
     * so the protocol cannot intercept its own transport recursively. */
    /* Public-image cache/session initialization and disk lookup run only on
     * the bounded worker lane. Independent requests and HLS are unchanged. */
    id session = share_image ? (id)__atomic_load_n(&image_cache_session,__ATOMIC_ACQUIRE):protocol_session(provider_image);
    objc_sync_enter(self);
    if (!objc_getAssociatedObject(self, &g_protocol_stopped_key)) {
        if (provider_image) tas_emotes_image_protocol_request(original_url);
        if (share_image && image_cache_start(self, session, request, original_url,
                tas_emotes_is_redirected_image_url(msg0(original,"URL")))) {
            objc_sync_exit(self);
            objc_release(request);
            return;
        }
        id held = objc_retain(self);
        id task = ((id (*)(id, SEL, id, id))objc_msgSend)(session,
            sel_registerName("dataTaskWithRequest:completionHandler:"), request,
            (id)^(id data, id response, id error) {
                protocol_complete(held, data, response, error);
                objc_release(held);
            });
        if (task) {
            if(provider_image)image_cache_mark_task(task);
            objc_setAssociatedObject(self, &g_protocol_task_key, task, 1);
            msg0(task, "resume");
        } else {
            objc_release(held);
            if (provider_image) tas_emotes_image_result_for_url(original_url, nil, nil, nil);
            protocol_deliver(self, nil, nil, nil);
        }
    }
    objc_sync_exit(self);
    objc_release(request);
}

static void protocol_stop_loading(id self, SEL command) {
    (void)command;
    objc_sync_enter(self);
    bool was_stopped=objc_getAssociatedObject(self,&g_protocol_stopped_key)!=nil;
    objc_setAssociatedObject(self, &g_protocol_stopped_key, nsstr("stopped"), 1);
    id task = objc_retain(objc_getAssociatedObject(self, &g_protocol_task_key));
    objc_setAssociatedObject(self, &g_protocol_task_key, nil, 1);
    bool shared=objc_getAssociatedObject(self,&image_consumer_key)!=nil;
    if (!was_stopped && (task || shared) && !objc_getAssociatedObject(self, &g_protocol_completed_key)) {
        const char *url = utf8(msg0(msg0(msg0(self, "request"), "URL"), "absoluteString"));
        if (tas_emotes_is_provider_image_url(url)) tas_emotes_image_protocol_cancel(url);
    }
    if (shared) {image_cache_stop(self);image_flight_stop(self);} else msg0(task, "cancel");
    objc_release(task);
    objc_sync_exit(self);
}

static BOOL protocol_can_init(id self, SEL command, id request) {
    (void)self;
    (void)command;
    if (msg1(request, "valueForHTTPHeaderField:", nsstr(TAS_INTERNAL_HEADER))) return NO;
    id url = msg0(request, "URL");
    const char *absolute = utf8(msg0(url, "absoluteString"));
    return is_twitch_hls_url(absolute) || is_cached_ad_segment(absolute) ||
           tas_emotes_is_provider_image_url(absolute);
}

static id protocol_canonical_request(id self, SEL command, id request) {
    (void)self;
    (void)command;
    return request;
}

static id json_value(id object, const char *key) {
    return msg1(object, "objectForKeyedSubscript:", nsstr(key));
}

static bool fetch_bytes(const char *url, id *data, id *response) {
    id request = make_internal_request(url, "GET");
    id error = nil;
    *data = synchronous_request(request, response, &error);
    return *data && *response && !error && imsg0(*response, "statusCode") >= 200 && imsg0(*response, "statusCode") < 300;
}

static bool request_access_token(const char *channel, const char *player_type,
                                 char *signature, size_t signature_capacity,
                                 char *token, size_t token_capacity) {
    const char *platform = strcmp(player_type, "autoplay") == 0 ? "android" : "web";
    char json[8192];
    snprintf(json, sizeof(json),
        "{\"operationName\":\"PlaybackAccessToken\",\"variables\":{\"isLive\":true,"
        "\"login\":\"%s\",\"isVod\":false,\"vodID\":\"\",\"playerType\":\"%s\","
        "\"platform\":\"%s\"},\"extensions\":{\"persistedQuery\":{\"version\":1,"
        "\"sha256Hash\":\"%s\"}}}", channel, player_type, platform, TAS_TOKEN_HASH);

    id request = make_internal_request("https://gql.twitch.tv/gql", "POST");
    vmsg2(request, "setValue:forHTTPHeaderField:", nsstr("application/json"), nsstr("Content-Type"));
    pthread_mutex_lock(&g_lock);
    if (!g_device_id[0]) {
        static const char alphabet[] = "abcdefghijklmnopqrstuvwxyz0123456789";
        for (size_t i = 0; i < 32; i++) g_device_id[i] = alphabet[arc4random_uniform(36)];
        g_device_id[32] = '\0';
    }
    vmsg2(request, "setValue:forHTTPHeaderField:", nsstr(TAS_CLIENT_ID), nsstr("Client-Id"));
    if (g_device_id[0]) vmsg2(request, "setValue:forHTTPHeaderField:", nsstr(g_device_id), nsstr("X-Device-Id"));
    if (g_authorization[0]) vmsg2(request, "setValue:forHTTPHeaderField:", nsstr(g_authorization), nsstr("Authorization"));
    if (g_integrity[0]) vmsg2(request, "setValue:forHTTPHeaderField:", nsstr(g_integrity), nsstr("Client-Integrity"));
    if (g_client_version[0]) vmsg2(request, "setValue:forHTTPHeaderField:", nsstr(g_client_version), nsstr("Client-Version"));
    if (g_client_session[0]) vmsg2(request, "setValue:forHTTPHeaderField:", nsstr(g_client_session), nsstr("Client-Session-Id"));
    pthread_mutex_unlock(&g_lock);
    vmsg1(request, "setHTTPBody:", data_from_bytes(json, strlen(json)));

    id response = nil;
    id error = nil;
    id data = synchronous_request(request, &response, &error);
    if (!data || error || !response || imsg0(response, "statusCode") != 200) {
        tas_diag_metric(TAS_DIAG_TOKEN_FAILURE, 1);
        if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_SUMMARY)) {
        char detail[256];
        snprintf(detail, sizeof(detail), "player=%s status=%ld data=%s error=%s",
                 player_type, response ? (long)imsg0(response, "statusCode") : 0L,
                 data ? "yes" : "no", error ? "yes" : "no");
        tas_diag_log("TOKEN_FAILURE", detail);
        }
        return false;
    }
    id json_error = nil;
    id root = ((id (*)(id, SEL, id, NSUInteger, id *))objc_msgSend)(
        (id)objc_getClass("NSJSONSerialization"), sel_registerName("JSONObjectWithData:options:error:"),
        data, 0, &json_error);
    if (!root || json_error) {
        tas_diag_metric(TAS_DIAG_TOKEN_FAILURE, 1);
        tas_diag_log("TOKEN_FAILURE", "PlaybackAccessToken response was not valid JSON");
        return false;
    }
    id access = json_value(json_value(root, "data"), "streamPlaybackAccessToken");
    const char *sig = utf8(json_value(access, "signature"));
    const char *tok = utf8(json_value(access, "value"));
    if (!sig || !tok) {
        tas_diag_metric(TAS_DIAG_TOKEN_FAILURE, 1);
        if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_SUMMARY)) {
        char detail[160];
        snprintf(detail, sizeof(detail), "player=%s response missing signature or token", player_type);
        tas_diag_log("TOKEN_FAILURE", detail);
        }
        return false;
    }
    copy_string(signature, signature_capacity, sig);
    copy_string(token, token_capacity, tok);
    if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_DETAILED)) {
    char detail[96];
    snprintf(detail, sizeof(detail), "player=%s", player_type);
    tas_diag_log("TOKEN_SUCCESS", detail);
    }
    return true;
}

static BOOL loader_handle(id self, SEL command, id loading_request) {
    (void)self;
    (void)command;
    id request = msg0(loading_request, "request");
    id original_url = msg0(request, "URL");
    const char *custom_url = utf8(msg0(original_url, "absoluteString"));
    if (!custom_url) return NO;
    char *url = https_scheme_url(custom_url);
    if (is_twitch_hls_url(url)) {
        tas_diag_metric(TAS_DIAG_HLS_INTERCEPTED, 1);
        tas_diag_log_url("HLS_REQUEST", url, "transport=AVAssetResourceLoader");
    }
    id network_request = msg0(request, "mutableCopy");
    vmsg1(network_request, "setURL:", nsurl(url));
    vmsg2(network_request, "setValue:forHTTPHeaderField:", nsstr("1"), nsstr(TAS_INTERNAL_HEADER));

    id response = nil;
    id error = nil;
    bool is_synthetic = is_cached_ad_segment(url);
    id data = nil;
    if (is_synthetic) {
        tas_diag_metric(TAS_DIAG_SYNTHETIC_SEGMENT, 1);
        tas_diag_log_url("SYNTHETIC_SEGMENT", url, "transport=AVAssetResourceLoader");
        data = blank_video_data();
        response = http_response(url, 200, "video/mp4", data_length(data), nil);
    } else {
        data = synchronous_request(network_request, &response, &error);
    }
    if (error || !data || !response) {
        tas_diag_metric(TAS_DIAG_HLS_FAILURE, 1);
        if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_SUMMARY)) {
        char detail[192];
        snprintf(detail, sizeof(detail), "transport=AVAssetResourceLoader status=%ld data=%s error=%s",
                 response ? (long)imsg0(response, "statusCode") : 0L,
                 data ? "yes" : "no", error ? "yes" : "no");
        tas_diag_log_url("HLS_FAILURE", url, detail);
        }
        vmsg1(loading_request, "finishLoadingWithError:", error);
        objc_release(network_request);
        free(url);
        return YES;
    }

    const char *mime = utf8(msg0(response, "MIMEType"));
    if (is_twitch_hls_url(url)) {
        if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_DETAILED)) {
        char detail[224];
        snprintf(detail, sizeof(detail), "transport=AVAssetResourceLoader status=%ld bytes=%zu",
                 (long)imsg0(response, "statusCode"), data_length(data));
        tas_diag_log_url("HLS_RESPONSE", url, detail);
        }
        if (imsg0(response, "statusCode") < 200 || imsg0(response, "statusCode") >= 300) {
            tas_diag_metric(TAS_DIAG_HLS_FAILURE, 1);
        }
    }
    char *text = NULL;
    id output_data = data;
    if (contains(url, ".m3u8") || (mime && contains(mime, "mpegurl"))) {
        text = copy_data_text(data);
        if (text && starts_with(text, "#EXTM3U")) {
            char *processed = process_manifest(url, text, true);
            output_data = data_from_bytes(processed, strlen(processed));
            free(processed);
        }
        free(text);
    }

    id content = msg0(loading_request, "contentInformationRequest");
    if (content) {
        const char *type = contains(url, ".m3u8") ? "public.m3u-playlist" :
                           (contains(url, ".ts") ? "public.mpeg-2-transport-stream" : "public.mpeg-4");
        vmsg1(content, "setContentType:", nsstr(type));
        ((void (*)(id, SEL, long long))objc_msgSend)(content, sel_registerName("setContentLength:"), (long long)data_length(output_data));
        ((void (*)(id, SEL, BOOL))objc_msgSend)(content, sel_registerName("setByteRangeAccessSupported:"), YES);
    }
    id data_request = msg0(loading_request, "dataRequest");
    if (data_request) vmsg1(data_request, "respondWithData:", output_data);
    msg0(loading_request, "finishLoading");
    if (is_synthetic) objc_release(response);
    objc_release(network_request);
    free(url);
    return YES;
}

static BOOL loader_wait(id self, SEL command, id resource_loader, id loading_request) {
    (void)resource_loader;
    return loader_handle(self, command, loading_request);
}

static id asset_init(id self, SEL command, id url, id options) {
    const char *absolute = utf8(msg0(url, "absoluteString"));
    if (!absolute || !starts_with(absolute, "https://") || !contains(absolute, ".m3u8") ||
        !(contains(absolute, "ttvnw.net") || contains(absolute, "twitch.tv"))) {
        return ((id (*)(id, SEL, id, id))g_original_asset_init)(self, command, url, options);
    }
    tas_diag_log_url("ASSET_INTERCEPT", absolute, "transport=AVURLAsset");
    char *custom = custom_scheme_url(absolute);
    id asset = ((id (*)(id, SEL, id, id))g_original_asset_init)(self, command, nsurl(custom), options);
    free(custom);
    if (!asset) return asset;
    id delegate = msg0((id)g_loader_class, "new");
    id loader = msg0(asset, "resourceLoader");
    dispatch_queue_t queue = dispatch_queue_create("dev.tas.hls-loader", DISPATCH_QUEUE_SERIAL);
    ((void (*)(id, SEL, id, dispatch_queue_t))objc_msgSend)(
        loader, sel_registerName("setDelegate:queue:"), delegate, queue);
    objc_setAssociatedObject(asset, &g_association_key, delegate, 1);
    objc_release(delegate);
    return asset;
}

static void add_protocol_to_configuration(id configuration) {
    if (!configuration || !g_protocol_class) return;
    id classes = msg0(configuration, "protocolClasses");
    id mutable = classes ? msg0(classes, "mutableCopy") : msg0((id)objc_getClass("NSMutableArray"), "array");
    if (!bmsg1(mutable, "containsObject:", (id)g_protocol_class)) {
        ((void (*)(id, SEL, id, NSUInteger))objc_msgSend)(
            mutable, sel_registerName("insertObject:atIndex:"), (id)g_protocol_class, 0);
    }
    vmsg1(configuration, "setProtocolClasses:", mutable);
    if (classes) objc_release(mutable);
}

static id default_configuration(id self, SEL command) {
    id result = ((id (*)(id, SEL))g_original_default_configuration)(self, command);
    add_protocol_to_configuration(result);
    return result;
}

static id ephemeral_configuration(id self, SEL command) {
    id result = ((id (*)(id, SEL))g_original_ephemeral_configuration)(self, command);
    add_protocol_to_configuration(result);
    return result;
}

static id session_with_configuration(id self, SEL command, id configuration) {
    add_protocol_to_configuration(configuration);
    return ((id (*)(id, SEL, id))g_original_session_with_configuration)(self, command, configuration);
}

static id session_with_configuration_delegate_queue(id self, SEL command, id configuration,
                                                     id delegate, id queue) {
    add_protocol_to_configuration(configuration);
    return ((id (*)(id, SEL, id, id, id))g_original_session_with_configuration_delegate_queue)(
        self, command, configuration, delegate, queue);
}

static id data_task_with_request(id self, SEL command, id original) {
    id image = tas_emotes_rewrite_request_copy(original);
    if (image) tas_emotes_image_request(false);
    id replacement = normalized_graphql_request_copy(image ?: original);
    id task = ((id (*)(id, SEL, id))g_original_data_task_request)(
        self, command, replacement ?: image ?: original);
    if (replacement) objc_release(replacement);
    if (image) objc_release(image);
    return task;
}

static id data_task_with_request_completion(id self, SEL command, id original, id completion) {
    id image = tas_emotes_rewrite_request_copy(original);
    if (image) tas_emotes_image_request(true);
    id replacement = normalized_graphql_request_copy(image ?: original);
    id handler = completion;
    if (image && completion) {
        handler = (id)^(id data, id response, id error) {
            tas_emotes_image_result(data, response, error);
            ((void (^)(id, id, id))completion)(data, response, error);
        };
    }
    id task = ((id (*)(id, SEL, id, id))g_original_data_task_request_completion)(
        self, command, replacement ?: image ?: original, handler);
    if (replacement) objc_release(replacement);
    if (image) objc_release(image);
    return task;
}

static void swizzle_method(Class cls, const char *selector, IMP replacement, IMP *original, bool class_method) {
    Method method = class_method ? class_getClassMethod(cls, sel_registerName(selector)) :
                                   class_getInstanceMethod(cls, sel_registerName(selector));
    if (!method) return;
    if (original) *original = method_getImplementation(method);
    method_setImplementation(method, replacement);
}

__attribute__((constructor))
static void tas_initialize(void) {
    tas_diagnostics_load_preferences();
    if(tas_inv_host_initialize)tas_inv_host_initialize();
    tas_emotes_install_investigation_bootstrap();
    Class url_protocol = objc_getClass("NSURLProtocol");
    g_protocol_class = objc_allocateClassPair(url_protocol, "TASURLProtocol", 0);
    if (g_protocol_class) {
        class_addMethod(object_getClass((id)g_protocol_class), sel_registerName("canInitWithRequest:"), (IMP)protocol_can_init, "B@:@");
        class_addMethod(object_getClass((id)g_protocol_class), sel_registerName("canonicalRequestForRequest:"), (IMP)protocol_canonical_request, "@@:@");
        class_addMethod(g_protocol_class, sel_registerName("startLoading"), (IMP)protocol_start_loading, "v@:");
        class_addMethod(g_protocol_class, sel_registerName("stopLoading"), (IMP)protocol_stop_loading, "v@:");
        objc_registerClassPair(g_protocol_class);
        ((BOOL (*)(id, SEL, Class))objc_msgSend)((id)url_protocol, sel_registerName("registerClass:"), g_protocol_class);
    }

    g_loader_class = objc_allocateClassPair(objc_getClass("NSObject"), "TASAssetResourceLoaderDelegate", 0);
    if (g_loader_class) {
        class_addMethod(g_loader_class, sel_registerName("resourceLoader:shouldWaitForLoadingOfRequestedResource:"),
                        (IMP)loader_wait, "B@:@@");
        class_addMethod(g_loader_class, sel_registerName("resourceLoader:shouldWaitForRenewalOfRequestedResource:"),
                        (IMP)loader_wait, "B@:@@");
        objc_registerClassPair(g_loader_class);
    }

    Class asset = objc_getClass("AVURLAsset");
    swizzle_method(asset, "initWithURL:options:", (IMP)asset_init, &g_original_asset_init, false);

    Class configuration = objc_getClass("NSURLSessionConfiguration");
    swizzle_method(configuration, "defaultSessionConfiguration", (IMP)default_configuration,
                   &g_original_default_configuration, true);
    swizzle_method(configuration, "ephemeralSessionConfiguration", (IMP)ephemeral_configuration,
                   &g_original_ephemeral_configuration, true);

    Class session = objc_getClass("NSURLSession");
    swizzle_method(session, "sessionWithConfiguration:", (IMP)session_with_configuration,
                   &g_original_session_with_configuration, true);
    swizzle_method(session, "sessionWithConfiguration:delegate:delegateQueue:",
                   (IMP)session_with_configuration_delegate_queue,
                   &g_original_session_with_configuration_delegate_queue, true);
    swizzle_method(session, "dataTaskWithRequest:", (IMP)data_task_with_request,
                   &g_original_data_task_request, false);
    swizzle_method(session, "dataTaskWithRequest:completionHandler:",
                   (IMP)data_task_with_request_completion,
                   &g_original_data_task_request_completion, false);
    tas_emotes_initialize();
    tas_diagnostics_initialize();
    fprintf(stderr, "[TAS] TwitchAdSolutions VAFT v24 iOS port loaded\n");
}
