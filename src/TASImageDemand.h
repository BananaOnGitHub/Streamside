#ifndef TAS_IMAGE_DEMAND_H
#define TAS_IMAGE_DEMAND_H
#include <stddef.h>
#include <stdint.h>
#ifndef TAS_IMAGE_DEMAND_DIAGNOSTIC
#define TAS_IMAGE_DEMAND_DIAGNOSTIC 0
#endif
/* Separate from legacy emote provenance probes. Only aggregate observations;
 * no loading decisions, cache queries, retries or retained request objects. */
enum { TAS_DEMAND_SCOPES=7, TAS_DEMAND_EVENTS=16 };
/* JS/native scopes: unknown/library/recents/suggestions/info/chat/URL-input.
 * Explicit request scope 5 means synthetic native redirect, not chat proof. */
#if TAS_IMAGE_DEMAND_DIAGNOSTIC
void tas_demand_event(unsigned event,unsigned scope,const char *asset,double a,double b);
void tas_demand_request(void *request,unsigned scope);
void tas_demand_mark_url(void *url,unsigned scope);
unsigned tas_demand_url_scope(void *url);
void *tas_demand_delegate(void);
void tas_demand_install(void);
void tas_demand_status(char *buffer,size_t capacity);
#else
static inline void tas_demand_event(unsigned e,unsigned s,const char *u,double a,double b) {(void)e;(void)s;(void)u;(void)a;(void)b;}
static inline void tas_demand_request(void *r,unsigned s) {(void)r;(void)s;}
static inline void tas_demand_mark_url(void *u,unsigned s) {(void)u;(void)s;}
static inline unsigned tas_demand_url_scope(void *u) {(void)u;return 0;}
static inline void *tas_demand_delegate(void) {return NULL;}
static inline void tas_demand_install(void) {}
static inline void tas_demand_status(char *b,size_t c) {if(c)b[0]=0;}
#endif
#endif
