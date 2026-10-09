/* Real Apple Foundation adapter for the unchanged production lifecycle slice.
 * Only URL classification/HLS/UI diagnostic dependencies are fixture stubs. */
#import <Foundation/Foundation.h>
#include <objc/runtime.h>
#include <objc/message.h>
#include <objc/objc-sync.h>
#include <dispatch/dispatch.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/time.h>
#include <sys/sysctl.h>
#define TAS_INTERNAL_HEADER "X-TAS-Internal"
#define TAS_DIAG_SYNTHETIC_SEGMENT 1
#define TAS_DIAG_HLS_INTERCEPTED 2
#define TAS_DIAG_HLS_FAILURE 3
extern id objc_retain(id);
extern void objc_release(id);
static char g_protocol_task_key,g_protocol_stopped_key,g_protocol_completed_key;
static id g_protocol_session;
static id nsstr(const char *s){return s ? [NSString stringWithUTF8String:s]:nil;}
static const char *utf8(id o){return [o UTF8String];}
static id nsurl(const char *s){return [NSURL URLWithString:nsstr(s)];}
static id msg0(id o,const char *s){return ((id (*)(id,SEL))objc_msgSend)(o,sel_registerName(s));}
static id msg1(id o,const char *s,id a){return ((id (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),a);}
static void vmsg1(id o,const char *s,id a){((void (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),a);}
static void vmsg2(id o,const char *s,id a,id b){((void (*)(id,SEL,id,id))objc_msgSend)(o,sel_registerName(s),a,b);}
static void vmsg3(id o,const char *s,id a,id b,NSInteger c){((void (*)(id,SEL,id,id,NSInteger))objc_msgSend)(o,sel_registerName(s),a,b,c);}
static NSInteger imsg0(id o,const char *s){return ((NSInteger (*)(id,SEL))objc_msgSend)(o,sel_registerName(s));}
static BOOL bmsg1(id o,const char *s,id a){return ((BOOL (*)(id,SEL,id))objc_msgSend)(o,sel_registerName(s),a);}
static bool contains(const char *s,const char *p){return s && strstr(s,p);}
static bool starts_with(const char *s,const char *p){return s && !strncmp(s,p,strlen(p));}
static bool tas_emotes_is_provider_image_url(const char *s){return contains(s,"http://127.0.0.1:");}
static bool tas_emotes_is_redirected_image_url(id url){return contains(utf8([url absoluteString]),"/blocked");}
static bool is_twitch_hls_url(const char *s){(void)s;return false;}
static bool is_cached_ad_segment(const char *s){(void)s;return false;}
static size_t data_length(id d){return [d length];}
static void tas_emotes_image_result_for_url(const char *u,id d,id r,id e){(void)u;(void)d;(void)r;(void)e;}
static void tas_emotes_image_protocol_request(const char *u){(void)u;}
static void tas_emotes_image_protocol_cancel(const char *u){(void)u;}
static void tas_diag_metric(int k,int n){(void)k;(void)n;}
static void tas_diag_log_url(const char *k,const char *u,const char *d){(void)k;(void)u;(void)d;}
static void cache_twitch_headers(id r){(void)r;}
static id normalized_graphql_body(id d){return d;}
static char *remove_query_parameter(const char *s,const char *k){(void)k;return strdup(s);}
static char *copy_data_text(id d){(void)d;return NULL;}
static char *process_manifest(const char *u,const char *s,bool c){(void)u;(void)s;(void)c;return NULL;}
static id data_from_bytes(const void *p,size_t n){return [NSData dataWithBytes:p length:n];}
static id http_response(const char *u,NSInteger s,const char *t,size_t n,id o){(void)u;(void)s;(void)t;(void)n;return o;}
static id blank_video_data(void){return nil;}
#include "TASImageDemand.h"
