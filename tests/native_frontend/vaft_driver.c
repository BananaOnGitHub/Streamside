/* Executes the shared production engine on Linux. Only Foundation URL/value
 * helpers and network transport are synthetic; Apple CI also tests real ones. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#include "TASDiagnostics.h"
typedef void *id;
#define nil NULL
static uint64_t metrics[11];
static bool all_stitched;
static unsigned token_calls;
unsigned tas_diag_policy_word(void) { return 0; }
void tas_diag_metric(TASDiagnosticMetric m,uint64_t n) { metrics[m]+=n; }
void tas_diag_log(const char *e,const char *d) { (void)e;(void)d; }
void tas_diag_log_url(const char *e,const char *u,const char *d) { (void)e;(void)u;(void)d; }
void tas_diag_log_stream(const char *e,const char *c,const char *u,const char *d) { (void)e;(void)c;(void)u;(void)d; }
static id objc_getClass(const char *s) { (void)s;return nil; }
static id nsstr(const char *s) { return (id)s; }
static id nsurl(const char *s) { return (id)s; }
static const char *utf8(id s) { return s; }
static id msg0(id o,const char *s) { assert(!strcmp(s,"absoluteString"));return o; }
static id msg2(id o,const char *s,id relative,id base) {
    (void)o;assert(!strcmp(s,"URLWithString:relativeToURL:"));
    static char url[8192];const char *slash=strrchr(base,'/');assert(slash);
    snprintf(url,sizeof(url),"%.*s%s",(int)(slash-(const char *)base+1),(const char *)base,(const char *)relative);return url;
}
static long imsg0(id o,const char *s) { (void)o;assert(!strcmp(s,"statusCode"));return 200; }
static const uint8_t *data_bytes(id d) { return d; }
static size_t data_length(id d) { return strlen(d); }
#include "TASVAFT.h"
static const char *primary="https://usher.ttvnw.net/api/channel/hls/alpha.m3u8?token=original";
static const char *original_master="#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=100,RESOLUTION=1280x720,FRAME-RATE=60\nhttps://video.ttvnw.net/alpha/original.m3u8\n";
static const char *alternate_master="#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=100,RESOLUTION=1280x720,FRAME-RATE=60\nhttps://video.ttvnw.net/alternate/media.m3u8\n";
static const char *ad="#EXTM3U\n#EXT-X-DATERANGE:ID=\"stitched-ad\"\n#EXTINF:2.0,ad\nad.ts\n#EXT-X-TWITCH-PREFETCH:prefetch.ts\n";
static const char *clean="#EXTM3U\n#EXTINF:2.0,live\nlive.ts\n";
static bool fetch_bytes(const char *url,id *data,id *response) {
    *response=(id)1;
    if(strstr(url,"/channel/hls/")) *data=(id)alternate_master;
    else if(strstr(url,"/alternate/media.m3u8")) *data=(id)(all_stitched?ad:clean);
    else return false;
    return true;
}
static bool request_access_token(const char *channel,const char *type,char *sig,size_t sig_size,char *token,size_t token_size) {
    assert(!strcmp(channel,"alpha"));assert(!strcmp(type,g_player_types[token_calls%3]));token_calls++;
    snprintf(sig,sig_size,"signature");snprintf(token,token_size,"%s",type);return true;
}
static char *process(const char *url,const char *body) { char *result=process_manifest(url,body,false);assert(result);return result; }
int main(void) {
    assert(has_ad_markers(ad)&&has_ad_markers("\"MIDROLL\"")&&has_ad_markers("\"midroll\"")&&!has_ad_markers(clean));
    char *result=process(primary,original_master);free(result);
    result=process("https://video.ttvnw.net/alpha/original.m3u8",ad);
    assert(!strstr(result,"stitched")&&strstr(result,"https://video.ttvnw.net/alternate/live.ts"));free(result);
    assert(metrics[TAS_DIAG_CLEAN_ALTERNATE]==1&&token_calls==1);
    result=process("https://video.ttvnw.net/alpha/original.m3u8",ad);free(result);assert(token_calls==1);
    result=process("https://video.ttvnw.net/unmapped.m3u8",ad);
    assert(strstr(result,"https://video.ttvnw.net/ad.ts")&&!strstr(result,"alternate/live.ts"));free(result);assert(metrics[TAS_DIAG_UNMAPPED_VARIANT]==1);
    const char *beta="#EXTM3U\n#EXT-X-STREAM-INF:RESOLUTION=640x360,FRAME-RATE=30\nhttps://video.ttvnw.net/beta/media.m3u8\n";
    result=process("https://usher.ttvnw.net/api/channel/hls/beta.m3u8",beta);free(result);
    result=process("https://video.ttvnw.net/beta/media.m3u8",clean);
    assert(strstr(result,"https://video.ttvnw.net/beta/live.ts")&&!strstr(result,"alternate"));free(result);
    // Expired generations may not write into a slot reused by another stream.
    TASStreamRef stale={0};pthread_mutex_lock(&g_lock);stale=(TASStreamRef){0,g_streams[0].generation,true};clear_stream_context_locked(0,"test_replacement");pthread_mutex_unlock(&g_lock);
    assert(!stream_ref_matches_locked(stale));
    result=process(primary,original_master);free(result);all_stitched=true;token_calls=0;
    result=process("https://video.ttvnw.net/alpha/original.m3u8",ad);
    assert(token_calls==3&&!strstr(result,"PREFETCH")&&is_cached_ad_segment("https://video.ttvnw.net/alternate/ad.ts"));free(result);
    assert(metrics[TAS_DIAG_STRIPPED_SEGMENT]>0);
    // Closest rendition matching and exact metadata parsing stay in the engine.
    char resolution[64],fps[64];assert(variant_metadata(beta,"https://usher.ttvnw.net/a.m3u8","https://video.ttvnw.net/beta/media.m3u8",resolution,sizeof(resolution),fps,sizeof(fps)));
    assert(!strcmp(resolution,"640x360")&&!strcmp(fps,"30"));
    char *variant=variant_for_resolution(beta,"https://usher.ttvnw.net/a.m3u8","1280x720","60");
    assert(variant&&!strcmp(variant,"https://video.ttvnw.net/beta/media.m3u8"));free(variant);
    puts("VAFT_CORE PASS: markers; clean alternate/reuse; exact ownership; stale generation; ordered fallback/segments; rendition matching");return 0;
}
