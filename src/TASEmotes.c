/*
 * Optional third-party chat emotes. No emote hooks or requests are installed
 * unless the saved preference was enabled before this app launch.
 *
 * The word registries are bounded by room and by entry count. The separate
 * synthetic-ID history outlives evicted rooms briefly so visible chat cells
 * can still redraw their images. Images are fetched by Twitch's image loader;
 * this module does not keep its own image files or decoded bitmaps.
 */
#include "TASEmotes.h"
#include "SSComposerModel.h"
#include "TASEmoteGeometry.h"
#include "TASEmoteFetch.h"
#include "TASDiagnostics.h"
#include "TASEmoteProbe.h"
#include "TASEmoteImageProbe.h"

#include <objc/runtime.h>
#include <objc/message.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef unsigned long NSUInteger;
typedef long NSInteger;

#define EMOTE_KEY "TASThirdPartyEmotesEnabled"
#define MAX_ROOMS 6
#define MAX_GLOBAL 2500
#define MAX_ROOM TAS_EMOTE_MAX_ROOM
#define MAX_HISTORY 3000
#define ROOM_IDLE_SECONDS 1200
#define HISTORY_SECONDS 2700
#define RETRY_SECONDS 60
#define MAX_FRAME 65536
#define FAKE_ID_START 9000000000ULL

extern id objc_retain(id object);
extern void objc_release(id object);
extern id objc_getAssociatedObject(id object, const void *key);
extern void objc_setAssociatedObject(id object, const void *key, id value, uintptr_t policy);
extern void *_Block_copy(const void *block);
extern void _Block_release(const void *block);

static id call0(id o, const char *s) {
    return ((id (*)(id, SEL))objc_msgSend)(o, sel_registerName(s));
}
static id call1(id o, const char *s, id a) {
    return ((id (*)(id, SEL, id))objc_msgSend)(o, sel_registerName(s), a);
}
static const char *text(id o) {
    return o ? ((const char *(*)(id, SEL))objc_msgSend)(o, sel_registerName("UTF8String")) : NULL;
}
static id str(const char *s) {
    return s ? call1((id)objc_getClass("NSString"), "stringWithUTF8String:", (id)s) : nil;
}
static id dict(id o, const char *key) {
    return o && ((BOOL (*)(id, SEL, Class))objc_msgSend)(o, sel_registerName("isKindOfClass:"),
                                                         objc_getClass("NSDictionary"))
               ? call1(o, "objectForKey:", str(key)) : nil;
}
static bool kind(id o, const char *cls) {
    return o && ((BOOL (*)(id, SEL, Class))objc_msgSend)(o, sel_registerName("isKindOfClass:"),
                                                         objc_getClass(cls));
}
static NSUInteger count(id o) {
    return o ? ((NSUInteger (*)(id, SEL))objc_msgSend)(o, sel_registerName("count")) : 0;
}
static id at(id o, NSUInteger index) {
    return ((id (*)(id, SEL, NSUInteger))objc_msgSend)(o, sel_registerName("objectAtIndex:"), index);
}
static char *duplicate(const char *s, size_t max) {
    if (!s) return NULL;
    size_t n = strnlen(s, max + 1);
    if (!n || n > max) return NULL;
    char *copy = malloc(n + 1);
    if (copy) memcpy(copy, s, n + 1);
    return copy;
}

typedef struct {
    char *name;
    char *url;
    char *owner;
    double aspect;
    uint64_t fake_id;
    unsigned char provider; /* 0: 7TV; 1: BTTV; 2: FFZ */
    bool global;
} Emote;
typedef struct {
    bool occupied;
    char id[32];
    char login[97];
    time_t last_used;
    time_t attempted[3];
    unsigned char failures[3];
    bool loaded[3];
    bool pending[3];
    Emote *items;
    size_t size;
    uint64_t generation;
} Room;
typedef struct {
    Emote emote;
    time_t retired_at;
} OldImage;

static pthread_mutex_t g_emote_lock = PTHREAD_MUTEX_INITIALIZER;
static Room g_global;
static Room g_rooms[MAX_ROOMS];
static OldImage g_old[MAX_HISTORY];
static size_t g_old_next;
static time_t g_last_sweep;
static uint64_t g_generation = 1;
static uint64_t g_catalog_revision = 1;
static void catalog_changed_locked(void) {
    /* Writers already hold g_emote_lock; only publication needs to be atomic. */
    uint64_t next = __atomic_load_n(&g_catalog_revision, __ATOMIC_RELAXED) + 1;
    __atomic_store_n(&g_catalog_revision, next, __ATOMIC_RELEASE);
}
uint64_t tas_emotes_catalog_revision(void) {
    return __atomic_load_n(&g_catalog_revision, __ATOMIC_ACQUIRE);
}
static char g_last_room[32];
static bool g_enabled;
static IMP g_public_receive, g_private_receive;
static IMP g_private_request, g_private_request_completion;
static char g_wrapped_key;
/* Aggregate counters contain no room IDs, message text, or request URLs. */
static uint64_t g_receive_calls, g_text_frames, g_tagged_frames, g_room_frames;
static uint64_t g_rewritten_frames, g_image_rewrites;
static uint64_t g_image_with_completion, g_image_without_completion;
static uint64_t g_image_protocol_requests, g_image_protocol_cancelled, g_match_words, g_native_overlaps;
static uint64_t g_words_scanned, g_punctuation_matches;
static uint64_t g_image_http_ok, g_image_http_error, g_image_transport_error;
static uint64_t g_image_empty, g_image_gif, g_image_webp, g_image_other;
static uint64_t g_fetch_started[3][2], g_fetch_loaded[3][2], g_fetch_failed[3][2];
static uint64_t g_fetch_http_error[3][2], g_fetch_parse_error[3][2];
static uint64_t g_fetch_transport_error[3][2], g_fetch_body_error[3][2], g_fetch_absent[3][2];
static char g_fetch_last[3][2][160]; /* Status/counts only; never identifiers or URLs. */
#define PROBE_INC(value) ((void)__atomic_add_fetch(&(value), 1, __ATOMIC_RELAXED))
#define PROBE_GET(value) __atomic_load_n(&(value), __ATOMIC_RELAXED)

static void drop_emote(Emote *e) {
    free(e->name);
    free(e->url);
    free(e->owner);
    memset(e, 0, sizeof(*e));
}

static void retire_emote_locked(Emote *e, time_t now) {
    if (e->fake_id && e->url) {
        OldImage *old = &g_old[g_old_next++ % MAX_HISTORY];
        drop_emote(&old->emote);
        old->emote = *e;
        old->retired_at = now;
        memset(e, 0, sizeof(*e));
    }
    drop_emote(e);
}

static void reset_room_locked(Room *room, bool retire, time_t now) {
    catalog_changed_locked();
    for (size_t i = 0; i < room->size; i++) {
        if (retire) retire_emote_locked(&room->items[i], now);
        else drop_emote(&room->items[i]);
    }
    free(room->items);
    memset(room, 0, sizeof(*room));
}

static void expire_locked(time_t now) {
    if (now - g_last_sweep < 30) return;
    g_last_sweep = now;
    for (size_t i = 0; i < MAX_ROOMS; i++) {
        Room *r = &g_rooms[i];
        if (r->occupied && now - r->last_used > ROOM_IDLE_SECONDS) {
            reset_room_locked(r, true, now);
        }
    }
    for (size_t i = 0; i < MAX_HISTORY; i++) {
        OldImage *old = &g_old[i];
        if (old->emote.url && now - old->retired_at > HISTORY_SECONDS) {
            drop_emote(&old->emote);
            memset(old, 0, sizeof(*old));
        }
    }
}

static Room *room_locked(const char *id, time_t now) {
    Room *empty = NULL, *eldest = NULL;
    for (size_t i = 0; i < MAX_ROOMS; i++) {
        Room *r = &g_rooms[i];
        if (r->occupied && strcmp(r->id, id) == 0) {
            r->last_used = now;
            return r;
        }
        if (!r->occupied) empty = r;
        else if (!eldest || r->last_used < eldest->last_used) eldest = r;
    }
    Room *r = empty ? empty : eldest;
    if (!r) return NULL;
    if (r->occupied) reset_room_locked(r, true, now);
    r->occupied = true;
    r->last_used = now;
    r->generation = ++g_generation;
    memcpy(r->id, id, strlen(id) + 1);
    catalog_changed_locked();
    return r;
}

/* A sorted lookup prevents a linear scan of every channel emote per word. */
static Emote *find_word(Room *room, const char *word) {
    size_t lo = 0, hi = room->size;
    while (lo < hi) {
        size_t mid = lo + (hi - lo) / 2;
        int comparison = strcmp(word, room->items[mid].name);
        if (comparison == 0) return &room->items[mid];
        if (comparison < 0) hi = mid;
        else lo = mid + 1;
    }
    return NULL;
}

#if TAS_EMOTE_DIAGNOSTIC
#define PROBE_TRACE_LIMIT 48
/* Only the explicitly selected code is retained. No message bodies, user
 * identities, channel names/IDs or image URLs are copied into the report. */
static char g_probe_code[97], g_probe_room[32];
static char g_probe_trace[PROBE_TRACE_LIMIT][224];
static char g_probe_last[192];
static bool g_probe_observed;
static uint64_t g_probe_events;
static uint64_t g_probe_last_id;
static unsigned g_probe_trace_count, g_probe_trace_next;
static struct { char stage[40], outcome[96]; uint64_t count; } g_probe_counts[24];
static unsigned g_probe_count_used;
static uint64_t g_probe_generation;
#define PLAYBACK_EMOTES 32
#define PLAYBACK_ROWS 16
#define PLAYBACK_VISIBLE 4
#define PLAYBACK_SECONDS 600
typedef struct { uint64_t sequence; unsigned layer; time_t time; char text[896]; } PlaybackRow;
static struct {
    uint64_t number, samples, events, sequence, denials, evictions;
    time_t touched;
    unsigned sample_count, sample_next, event_count, event_next, image_count, image_next, assignment_count, assignment_next;
    PlaybackRow samples_ring[PLAYBACK_ROWS], events_ring[PLAYBACK_ROWS], visible[PLAYBACK_VISIBLE];
    PlaybackRow images[PLAYBACK_ROWS], assignments[PLAYBACK_ROWS], progress[PLAYBACK_VISIBLE];
    PlaybackRow decodes[PLAYBACK_ROWS], handoffs[PLAYBACK_ROWS];
    PlaybackRow results[PLAYBACK_ROWS];
    unsigned decode_count,decode_next,handoff_count,handoff_next;
    unsigned result_count,result_next;
} g_playback[PLAYBACK_EMOTES];
static uint64_t g_playback_sequence;
static time_t playback_now(void) {
    struct timespec now; clock_gettime(CLOCK_MONOTONIC,&now); return now.tv_sec;
}
/* Independent per-emote rings. Chat pruning cannot erase copied observations;
 * cleanup cannot replace the last-visible snapshots. No object is retained. */
static uint64_t probe_generation_locked(uint64_t number) {
    if (!number) return 0;
    uint64_t result=0;
    if (g_probe_code[0]) for (size_t r=0;r<=MAX_ROOMS;r++) {
        Emote *emote=find_word(r==MAX_ROOMS ? &g_global : &g_rooms[r],g_probe_code);
        if (emote && emote->fake_id==number) { result=g_probe_generation; break; }
    }
    if (!result && g_probe_code[0] && number==g_probe_last_id) result=g_probe_generation;
    return result;
}
uint64_t tas_emote_probe_generation(uint64_t number) {
    pthread_mutex_lock(&g_emote_lock);
    uint64_t result=probe_generation_locked(number);
    pthread_mutex_unlock(&g_emote_lock);
    return result;
}
static void playback_record_locked(uint64_t number,unsigned layer,const char *event,const char *state,bool visible) {
    if (number<9000000000ULL || !event || !state) return;
    time_t now=playback_now(); unsigned slot=0;
    for (unsigned i=0;i<PLAYBACK_EMOTES;i++) {
        if (g_playback[i].number==number) {
            slot=i;
            if (now-g_playback[i].touched>=PLAYBACK_SECONDS) memset(&g_playback[i],0,sizeof(g_playback[i]));
            goto found;
        }
        if (g_playback[i].sequence<g_playback[slot].sequence) slot=i;
    }
    memset(&g_playback[slot],0,sizeof(g_playback[slot])); g_playback[slot].number=number;
found:
    g_playback[slot].number=number;
    g_playback[slot].touched=now;
    PlaybackRow row={.sequence=++g_playback_sequence,.layer=layer,.time=now};
    g_playback[slot].sequence=row.sequence;
    snprintf(row.text,sizeof(row.text),"Playback #%llu id=%llu event=%s %s",
        (unsigned long long)row.sequence,(unsigned long long)number,event,state);
    if (!strcmp(event,"tracking-limited")) g_playback[slot].denials++;
    if (!strcmp(event,"tracking-evicted")) g_playback[slot].evictions++;
    if (!strncmp(event,"result-",7)) {
        g_playback[slot].results[g_playback[slot].result_next]=row;
        g_playback[slot].result_next=(g_playback[slot].result_next+1)%PLAYBACK_ROWS;
        if (g_playback[slot].result_count<PLAYBACK_ROWS) g_playback[slot].result_count++;
    } else if (!strcmp(event,"decode-handoff")) {
        g_playback[slot].handoffs[g_playback[slot].handoff_next]=row;
        g_playback[slot].handoff_next=(g_playback[slot].handoff_next+1)%PLAYBACK_ROWS;
        if (g_playback[slot].handoff_count<PLAYBACK_ROWS) g_playback[slot].handoff_count++;
    } else if (!strncmp(event,"decode-",7)) {
        g_playback[slot].decodes[g_playback[slot].decode_next]=row;
        g_playback[slot].decode_next=(g_playback[slot].decode_next+1)%PLAYBACK_ROWS;
        if (g_playback[slot].decode_count<PLAYBACK_ROWS) g_playback[slot].decode_count++;
    } else if (!strncmp(event,"image-assign-",13)) {
        g_playback[slot].assignments[g_playback[slot].assignment_next]=row;
        g_playback[slot].assignment_next=(g_playback[slot].assignment_next+1)%PLAYBACK_ROWS;
        if (g_playback[slot].assignment_count<PLAYBACK_ROWS) g_playback[slot].assignment_count++;
    } else if (!strncmp(event,"image-",6)) {
        g_playback[slot].images[g_playback[slot].image_next]=row;
        g_playback[slot].image_next=(g_playback[slot].image_next+1)%PLAYBACK_ROWS;
        if (g_playback[slot].image_count<PLAYBACK_ROWS) g_playback[slot].image_count++;
    } else if (!strcmp(event,"last-frame-progress")) {
        unsigned v=0;
        for (unsigned i=0;i<PLAYBACK_VISIBLE;i++) {
            if (g_playback[slot].progress[i].sequence && g_playback[slot].progress[i].layer==layer) { v=i; goto last_progress; }
            if (g_playback[slot].progress[i].sequence<g_playback[slot].progress[v].sequence) v=i;
        }
last_progress:
        g_playback[slot].progress[v]=row;
    } else if (!strcmp(event,"sample")) {
        g_playback[slot].samples++;
        if (visible) {
            g_playback[slot].samples_ring[g_playback[slot].sample_next]=row;
            g_playback[slot].sample_next=(g_playback[slot].sample_next+1)%PLAYBACK_ROWS;
            if (g_playback[slot].sample_count<PLAYBACK_ROWS) g_playback[slot].sample_count++;
        }
    } else {
        g_playback[slot].events++;
        g_playback[slot].events_ring[g_playback[slot].event_next]=row;
        g_playback[slot].event_next=(g_playback[slot].event_next+1)%PLAYBACK_ROWS;
        if (g_playback[slot].event_count<PLAYBACK_ROWS) g_playback[slot].event_count++;
    }
    if (visible) {
        unsigned v=0;
        for (unsigned i=0;i<PLAYBACK_VISIBLE;i++) {
            if (g_playback[slot].visible[i].sequence && g_playback[slot].visible[i].layer==layer) { v=i; goto last_visible; }
            if (g_playback[slot].visible[i].sequence<g_playback[slot].visible[v].sequence) v=i;
        }
last_visible:
        g_playback[slot].visible[v]=row;
    }
}
void tas_emote_probe_record(uint64_t number,unsigned layer,const char *event,const char *state,bool visible) {
    pthread_mutex_lock(&g_emote_lock);
    playback_record_locked(number,layer,event,state,visible);
    pthread_mutex_unlock(&g_emote_lock);
}
void tas_emote_probe_image(uint64_t number,unsigned layer,const char *event,const char *state) {
    /* Callers supply whitelisted facts only, never native object descriptions. */
    char name[48]; snprintf(name,sizeof(name),"image-%s",event);
    tas_emote_probe_record(number,layer,name,state,false);
}
void tas_emote_probe_playback(uint64_t generation,uint64_t number,const char *state) {
    pthread_mutex_lock(&g_emote_lock);
    if (generation && generation==probe_generation_locked(number)) playback_record_locked(number,0,"sample",state,true);
    pthread_mutex_unlock(&g_emote_lock);
}
static void probe_append_locked(const char *stage, const char *outcome,
                                Room *room, Emote *emote, size_t bytes,
                                size_t position) {
    g_probe_events++;
    for (unsigned i=0;i<=g_probe_count_used && i<24;i++) {
        if (i==g_probe_count_used) {
            snprintf(g_probe_counts[i].stage,sizeof(g_probe_counts[i].stage),"%s",stage);
            snprintf(g_probe_counts[i].outcome,sizeof(g_probe_counts[i].outcome),"%s",outcome);
            g_probe_count_used++;
        }
        if (!strcmp(g_probe_counts[i].stage,stage) && !strcmp(g_probe_counts[i].outcome,outcome)) {
            g_probe_counts[i].count++; break;
        }
    }
    char detail[192];
    snprintf(detail, sizeof(detail),
        "%s %s room=%s entries=%zu loaded=%d%d%d pending=%d%d%d id=%llu bytes=%zu pos=%zu rev=%llu",
        stage, outcome, room ? "resolved" : "missing",
        room ? room->size : 0, room ? room->loaded[0] : 0, room ? room->loaded[1] : 0,
        room ? room->loaded[2] : 0, room ? room->pending[0] : 0, room ? room->pending[1] : 0,
        room ? room->pending[2] : 0, (unsigned long long)(emote ? emote->fake_id : 0),
        bytes, position, (unsigned long long)tas_emotes_catalog_revision());
    /* Repeated layout/refresh observations must not evict the useful path. */
    if (!strcmp(detail,g_probe_last)) return;
    snprintf(g_probe_last,sizeof(g_probe_last),"%s",detail);
    snprintf(g_probe_trace[g_probe_trace_next],sizeof(g_probe_trace[0]),"#%llu %s",(unsigned long long)g_probe_events,detail);
    g_probe_trace_next=(g_probe_trace_next+1)%PROBE_TRACE_LIMIT;
    if (g_probe_trace_count<PROBE_TRACE_LIMIT) g_probe_trace_count++;
}
static void probe_word_locked(const char *stage, const char *word, size_t bytes,
                              Room *room, Emote *emote, const char *outcome,
                              size_t position) {
    if (!g_probe_code[0] || bytes!=strlen(g_probe_code) || memcmp(word,g_probe_code,bytes)) return;
    snprintf(g_probe_room,sizeof(g_probe_room),"%s",room ? room->id : "");
    g_probe_observed=true;
    if (emote) g_probe_last_id=emote->fake_id;
    probe_append_locked(stage,outcome,room,emote,bytes,position);
}
bool tas_emote_probe_set(const char *code) {
    size_t bytes=code ? strnlen(code,97) : 0;
    if (!bytes || bytes>96) return false;
    for (size_t i=0;i<bytes;i++) if ((unsigned char)code[i]<=32 || (unsigned char)code[i]==127) return false;
    pthread_mutex_lock(&g_emote_lock);
    memcpy(g_probe_code,code,bytes+1); g_probe_room[0]=0; g_probe_last[0]=0; g_probe_observed=false;
    memset(g_probe_trace,0,sizeof(g_probe_trace));
    memset(g_probe_counts,0,sizeof(g_probe_counts)); g_probe_count_used=0;
    g_probe_events=0; g_probe_last_id=0; g_probe_trace_count=0; g_probe_trace_next=0;
    g_probe_generation++; if (!g_probe_generation) g_probe_generation++;
    pthread_mutex_unlock(&g_emote_lock); return true;
}
void tas_emote_probe_observe(const char *stage,const char *code,const char *channel,const char *outcome) {
    if (!code) return;
    pthread_mutex_lock(&g_emote_lock);
    Room *room=NULL;
    if (channel) for (size_t i=0;i<MAX_ROOMS;i++)
        if (g_rooms[i].occupied && (!strcmp(g_rooms[i].id,channel) || !strcmp(g_rooms[i].login,channel))) room=&g_rooms[i];
    Emote *emote=room ? find_word(room,code) : NULL;
    if (!emote) emote=find_word(&g_global,code);
    probe_word_locked(stage,code,strlen(code),room,emote,outcome,0);
    pthread_mutex_unlock(&g_emote_lock);
}
void tas_emote_probe_stage(uint64_t number, const char *stage) {
    if (!number) return;
    pthread_mutex_lock(&g_emote_lock);
    bool found=false;
    if (g_probe_code[0]) for (size_t r=0;r<=MAX_ROOMS;r++) {
        Room *room=r==MAX_ROOMS ? &g_global : &g_rooms[r];
        Emote *emote=find_word(room,g_probe_code);
        if (emote && emote->fake_id==number) {
            probe_append_locked(stage,"reached",r==MAX_ROOMS ? NULL : room,emote,strlen(g_probe_code),0);
            found=true;
            break;
        }
    }
    if (!found && g_probe_code[0] && number==g_probe_last_id) {
        Emote retired={.fake_id=number};
        probe_append_locked(stage,"target-no-longer-in-catalog",NULL,&retired,strlen(g_probe_code),0);
    }
    pthread_mutex_unlock(&g_emote_lock);
}
/* Case variants are evidence only, never used to replace exact lookup. */
static bool probe_case_equal(const char *a,const char *b) {
    for (;*a && *b;a++,b++) {
        unsigned char x=(unsigned char)*a,y=(unsigned char)*b;
        if (x>='A' && x<='Z') x+='a'-'A';
        if (y>='A' && y<='Z') y+='a'-'A';
        if (x!=y) return false;
    }
    return *a==*b;
}
void tas_emote_probe_status(char *buffer,size_t capacity) {
    if (!buffer || !capacity) return;
    pthread_mutex_lock(&g_emote_lock);
    if (!g_probe_code[0]) {
        snprintf(buffer,capacity,"\nTemporary emote rendering probe: enabled\nRolling playback recorder active before selection. Select Inspect Emote after a failure, then copy this report.\n");
        pthread_mutex_unlock(&g_emote_lock); return;
    }
    Room *room=NULL;
    const char *context=g_probe_observed ? g_probe_room : g_last_room;
    for (size_t r=0;r<MAX_ROOMS;r++) if (g_rooms[r].occupied && !strcmp(g_rooms[r].id,context)) room=&g_rooms[r];
    Emote *local=room ? find_word(room,g_probe_code) : NULL,*global=find_word(&g_global,g_probe_code);
    size_t elsewhere=0,case_variants=0;
    for (size_t r=0;r<=MAX_ROOMS;r++) {
        Room *other=r==MAX_ROOMS ? &g_global : &g_rooms[r];
        if (other!=room && other!=&g_global && find_word(other,g_probe_code)) elsewhere++;
        if (other==room || other==&g_global) for (size_t i=0;i<other->size;i++)
            if (strcmp(other->items[i].name,g_probe_code) && probe_case_equal(other->items[i].name,g_probe_code)) case_variants++;
    }
    int n=snprintf(buffer,capacity,
        "\nTemporary emote rendering probe\nSelected code (entered by tester): %s\n"
        "Emotes enabled: %s; context: %s\n"
        "Exact catalog hit channel/global: %s/%s; provider channel/global: %d/%d (0=7TV,1=BTTV,2=FFZ)\n"
        "Other cached rooms with code: %zu; case variants in current scope: %zu\n"
        "Context entries: %zu; loaded 7TV/BTTV/FFZ: %d/%d/%d; pending: %d/%d/%d; failures: %u/%u/%u\n"
        "Global entries: %zu; loaded: %d/%d/%d; pending: %d/%d/%d\n"
        "Target events: %llu; retained: %u (oldest first)\n",
        g_probe_code,g_enabled ? "yes" : "no",room ? "resolved" : "missing",
        local ? "yes" : "no",global ? "yes" : "no",local ? local->provider : -1,global ? global->provider : -1,
        elsewhere,case_variants,room ? room->size : 0,
        room ? room->loaded[0] : 0,room ? room->loaded[1] : 0,room ? room->loaded[2] : 0,
        room ? room->pending[0] : 0,room ? room->pending[1] : 0,room ? room->pending[2] : 0,
        room ? room->failures[0] : 0,room ? room->failures[1] : 0,room ? room->failures[2] : 0,
        g_global.size,g_global.loaded[0],g_global.loaded[1],g_global.loaded[2],
        g_global.pending[0],g_global.pending[1],g_global.pending[2],(unsigned long long)g_probe_events,g_probe_trace_count);
    size_t used=n>0 && (size_t)n<capacity ? (size_t)n : capacity-1;
    n=snprintf(buffer+used,capacity-used,"Rolling playback: up to 600s; 32 emotes; per ID 16 visible samples + 16 transitions + 4 last-visible layers + 16 image events + 16 assignments + 4 last-progress layers + 16 decodes + 16 handoffs + 16 result origins. Capacity eviction may shorten history. Selection does not reset playback.\n");
    if (n<0 || (size_t)n>=capacity-used) { pthread_mutex_unlock(&g_emote_lock); return; }
    used+=(size_t)n;
    time_t now=playback_now(); unsigned matched=0;
    /* At most four matching IDs per report, leaving room for rendering stages. */
    for (unsigned s=0;s<PLAYBACK_EMOTES && matched<4;s++) {
        if (!probe_generation_locked(g_playback[s].number) || now-g_playback[s].touched>=PLAYBACK_SECONDS) continue;
        matched++;
        n=snprintf(buffer+used,capacity-used,"Retained id=%llu samples=%u transitions=%u images=%u assignments=%u decodes=%u handoffs=%u origins=%u (counts include rows awaiting expiry filtering)\n",
            (unsigned long long)g_playback[s].number,g_playback[s].sample_count,g_playback[s].event_count,g_playback[s].image_count,g_playback[s].assignment_count,g_playback[s].decode_count,g_playback[s].handoff_count,g_playback[s].result_count);
        if (n<0 || (size_t)n>=capacity-used) goto playback_done;
        used+=(size_t)n;
        n=snprintf(buffer+used,capacity-used,"Observed id=%llu visible-polls=%llu admission-denials=%llu observer-evictions=%llu (since retained entry began)\n",
            (unsigned long long)g_playback[s].number,(unsigned long long)g_playback[s].samples,
            (unsigned long long)g_playback[s].denials,(unsigned long long)g_playback[s].evictions);
        if (n<0 || (size_t)n>=capacity-used) goto playback_done;
        used+=(size_t)n;
        for (unsigned category=0;category<9;category++) {
            unsigned limit=category==2 || category==4 ? PLAYBACK_VISIBLE : PLAYBACK_ROWS;
            unsigned count=category==0 ? g_playback[s].sample_count : category==1 ? g_playback[s].event_count : category==3 ? g_playback[s].image_count : category==5 ? g_playback[s].assignment_count : category==6 ? g_playback[s].decode_count : category==7 ? g_playback[s].handoff_count : category==8 ? g_playback[s].result_count : limit;
            unsigned next=category==0 ? g_playback[s].sample_next : category==3 ? g_playback[s].image_next : category==5 ? g_playback[s].assignment_next : category==6 ? g_playback[s].decode_next : category==7 ? g_playback[s].handoff_next : category==8 ? g_playback[s].result_next : g_playback[s].event_next;
            for (unsigned i=0;i<count;i++) {
                unsigned j=category==2 || category==4 ? i : (next+limit-count+i)%limit;
                PlaybackRow *row=category==0 ? &g_playback[s].samples_ring[j] : category==1 ? &g_playback[s].events_ring[j] : category==2 ? &g_playback[s].visible[j] : category==3 ? &g_playback[s].images[j] : category==4 ? &g_playback[s].progress[j] : category==5 ? &g_playback[s].assignments[j] : category==6 ? &g_playback[s].decodes[j] : category==7 ? &g_playback[s].handoffs[j] : &g_playback[s].results[j];
                if (!row->sequence || now-row->time>=PLAYBACK_SECONDS) continue;
                n=snprintf(buffer+used,capacity-used,"%s age=%llds %s\n",category==8 ? "Result origin" : category==7 ? "Handoff" : category==6 ? "Decode" : category==5 ? "Assignment" : category==4 ? "Last-progress" : category==3 ? "Image history" : category==2 ? "Last-visible" : category==1 ? "Transition" : "Visible sample",(long long)(now-row->time),row->text);
                if (n<0 || (size_t)n>=capacity-used) goto playback_done;
                used+=(size_t)n;
            }
        }
    }
    if (!matched) {
        n=snprintf(buffer+used,capacity-used,"No retained playback for this code; it may not have been observed, may have expired/been evicted, or its catalog identity may be unavailable.\n");
        if (n>0 && (size_t)n<capacity-used) used+=(size_t)n;
    }
playback_done:
    for (unsigned i=0;i<g_probe_count_used && used<capacity-1;i++) {
        n=snprintf(buffer+used,capacity-used,"Stage %s %s: %llu\n",g_probe_counts[i].stage,g_probe_counts[i].outcome,
                   (unsigned long long)g_probe_counts[i].count);
        if (n<0 || (size_t)n>=capacity-used) break;
        used+=(size_t)n;
    }
    for (unsigned i=0;i<g_probe_trace_count && used<capacity-1;i++) {
        unsigned slot=(g_probe_trace_next+PROBE_TRACE_LIMIT-g_probe_trace_count+i)%PROBE_TRACE_LIMIT;
        n=snprintf(buffer+used,capacity-used,"%s\n",g_probe_trace[slot]);
        if (n<0 || (size_t)n>=capacity-used) break;
        used+=(size_t)n;
    }
    pthread_mutex_unlock(&g_emote_lock);
}
#endif

static bool permitted_url(const char *url, unsigned char provider) {
    const char *prefix = provider == 0 ? "https://cdn.7tv.app/emote/" :
                         provider == 1 ? "https://cdn.betterttv.net/emote/" :
                                         "https://cdn.frankerfacez.com/emote/";
    return url && strncmp(url, prefix, strlen(prefix)) == 0 && strlen(url) < 512;
}

bool tas_emotes_is_provider_image_url(const char *url) {
    if (!g_enabled || !url) return false;
    for (unsigned char provider = 0; provider < 3; provider++)
        if (permitted_url(url, provider)) return true;
    return false;
}

static void image_probe_url(const char *url, const char *stage, const char *outcome);
void tas_emotes_image_protocol_request(const char *url) {
    PROBE_INC(g_image_protocol_requests);
    image_probe_url(url,"image-protocol-start","reached");
}
void tas_emotes_image_protocol_cancel(const char *url) {
    PROBE_INC(g_image_protocol_cancelled);
    image_probe_url(url,"image-protocol-cancel","cancelled-before-completion");
}

/* Twitch persists decoded images under the synthetic CDN URL, before our
 * request rewrite. Launch-order counters therefore reused yesterday's bitmap
 * for today's different emote. Keep identity deterministic across processes,
 * independent of fetch order, and disjoint from the old counter namespace.
 * Fifteen decimal digits stay exact even through a double-backed number. */
static uint64_t image_identity(const char *scope, const char *name, const char *url) {
    uint64_t hash = 14695981039346656037ULL;
    const char *parts[] = {"Streamside-image-v1", scope, name, url};
    for (size_t i = 0; i < sizeof(parts) / sizeof(parts[0]); i++) {
        for (const unsigned char *p = (const unsigned char *)parts[i]; *p; p++) {
            hash ^= *p; hash *= 1099511628211ULL;
        }
        hash ^= 0; hash *= 1099511628211ULL;
    }
    return 900000000000000ULL + hash % 100000000000000ULL;
}
static bool identity_available_locked(uint64_t number, const char *name, const char *url) {
    for (size_t r = 0; r <= MAX_ROOMS; r++) {
        Room *room = r == MAX_ROOMS ? &g_global : &g_rooms[r];
        for (size_t i = 0; i < room->size; i++) {
            Emote *e = &room->items[i];
            if (e->fake_id == number && (strcmp(e->name,name) || strcmp(e->url,url))) return false;
        }
    }
    for (size_t i = 0; i < MAX_HISTORY; i++) {
        Emote *e = &g_old[i].emote;
        if (e->fake_id == number && e->url && (strcmp(e->name,name) || strcmp(e->url,url))) return false;
    }
    return true; /* A collision fails closed; never assign another URL to it. */
}

/* API strings are copied while the JSON object is alive; only bounded entries
 * are retained. The fixed provider rank makes name collisions deterministic. */
static void add_emote_locked(Room *room, size_t max, const char *name,
                             const char *url, unsigned char provider,
                             bool global, const char *owner, double aspect) {
    if (!permitted_url(url, provider)) return;
    char *word = duplicate(name, 96);
    char *image = duplicate(url, 511);
    if (!word || !image || strchr(word, ' ') || strchr(word, '\t') || strchr(word, '\r') ||
        strchr(word, '\n') || strchr(word, ';')) {
        free(word);
        free(image);
        return;
    }
    uint64_t number = image_identity(room->id, word, image);
    if (!identity_available_locked(number, word, image)) {
        free(word); free(image); return;
    }
    Emote *existing = find_word(room, word);
    if (existing) {
        if (provider < existing->provider) {
            retire_emote_locked(existing, time(NULL));
            existing->name = word;
            existing->url = image;
            existing->fake_id = number;
            existing->provider = provider;
            existing->global = global;
            existing->owner = duplicate(owner, 128);
            existing->aspect = aspect;
            catalog_changed_locked();
        } else {
            free(word);
            free(image);
        }
        return;
    }
    if (room->size >= max) {
        size_t victim = room->size;
        for (size_t i = 0; i < room->size; i++) {
            if (room->items[i].provider > provider &&
                (victim == room->size || room->items[i].provider > room->items[victim].provider))
                victim = i;
        }
        if (victim == room->size) {
            free(word);
            free(image);
            return;
        }
        retire_emote_locked(&room->items[victim], time(NULL));
        memmove(&room->items[victim], &room->items[victim + 1],
                (room->size - victim - 1) * sizeof(*room->items));
        room->size--;
        catalog_changed_locked();
    }
    Emote *larger = realloc(room->items, (room->size + 1) * sizeof(*larger));
    if (!larger) {
        free(word);
        free(image);
        return;
    }
    room->items = larger;
    size_t insert = 0;
    while (insert < room->size && strcmp(room->items[insert].name, word) < 0) insert++;
    memmove(&room->items[insert + 1], &room->items[insert],
            (room->size - insert) * sizeof(*room->items));
    room->items[insert] = (Emote){.name = word, .url = image,
        .owner = duplicate(owner, 128), .aspect = aspect,
        .fake_id = number, .provider = provider, .global = global};
    room->size++;
    catalog_changed_locked();
}

static const char *json_string(id value) {
    return kind(value, "NSString") ? text(value) : NULL;
}
static const char *json_id(id value) {
    return kind(value, "NSString") || kind(value, "NSNumber") ? text(call0(value, "description")) : NULL;
}

static bool seven_tv_has_file(id data, const char *filename) {
    id files = dict(dict(data, "host"), "files");
    if (!kind(files, "NSArray")) return false;
    for (NSUInteger i = 0; i < count(files); i++) {
        const char *candidate = json_string(dict(at(files, i), "name"));
        if (candidate && strcmp(candidate, filename) == 0) return true;
    }
    return false;
}

static void parse_list_locked(Room *room, id array, unsigned char provider, bool global) {
    if (!kind(array, "NSArray")) return;
    NSUInteger n = count(array);
    for (NSUInteger i = 0; i < n; i++) {
        id emote = at(array, i);
        if (!kind(emote, "NSDictionary")) continue;
        const char *name = json_string(dict(emote, provider == 1 ? "code" : "name"));
        const char *id_text = json_id(dict(emote, "id"));
        char url[512];
        id dimensions = emote, owner = dict(emote, provider == 1 ? "user" : "owner");
        if (!name || !id_text || strlen(id_text) > 96) continue;
        if (provider == 0) {
            id data = dict(emote, "data");
            owner = dict(data, "owner");
            id files = dict(dict(data, "host"), "files");
            dimensions = kind(files, "NSArray") && count(files) ? at(files, 0) : nil;
            id animated = dict(data, "animated");
            bool gif = animated && ((BOOL (*)(id, SEL))objc_msgSend)(animated, sel_registerName("boolValue"));
            const char *formats[] = {"2x.gif", "2x.webp", "2x.png",
                                     "1x.gif", "1x.webp", "1x.png"};
            const unsigned char order[] = {0, 1, 2, 3, 4, 5};
            const unsigned char still_order[] = {1, 2, 4, 5, 0, 3};
            const unsigned char *choices = gif ? order : still_order;
            const char *chosen = NULL;
            for (size_t f = 0; f < 6; f++)
                if (seven_tv_has_file(data, formats[choices[f]])) {
                    chosen = formats[choices[f]];
                    break;
                }
            if (!chosen) continue;
            snprintf(url, sizeof(url), "https://cdn.7tv.app/emote/%s/%s", id_text, chosen);
        } else if (provider == 1) {
            snprintf(url, sizeof(url), "https://cdn.betterttv.net/emote/%s/2x", id_text);
        } else {
            id urls = dict(emote, "urls");
            id animation = dict(emote, "animated");
            const char *provided = json_string(dict(animation, "2"));
            if (!provided) provided = json_string(dict(urls, "2"));
            if (!provided) provided = json_string(dict(urls, "1"));
            if (!provided) continue;
            if (strncmp(provided, "//", 2) == 0)
                snprintf(url, sizeof(url), "https:%s", provided);
            else snprintf(url, sizeof(url), "%s", provided);
        }
        const char *credit = json_string(dict(owner, "display_name"));
        if (!credit) credit = json_string(dict(owner, "displayName"));
        if (!credit) credit = json_string(dict(owner, "username"));
        if (!credit) credit = json_string(dict(owner, "name"));
        id width = dict(dimensions, "width"), height = dict(dimensions, "height");
        double w = kind(width, "NSNumber") ? ((double (*)(id, SEL))objc_msgSend)(width, sel_registerName("doubleValue")) : 0;
        double h = kind(height, "NSNumber") ? ((double (*)(id, SEL))objc_msgSend)(height, sel_registerName("doubleValue")) : 0;
        double aspect = w > 0 && h > 0 && w <= 4096 && h <= 4096 ? w / h : 1;
        add_emote_locked(room, global ? MAX_GLOBAL : MAX_ROOM, name, url, provider,
                         global, credit, aspect);
    }
}

static bool parse_provider_locked(Room *room, id root, unsigned char provider, bool global) {
    if (provider == 0) {
        if (!kind(root, "NSDictionary")) return false;
        id set = global ? root : dict(root, "emote_set");
        if (!kind(set, "NSDictionary")) return false;
        id emotes = dict(set, "emotes");
        if (!kind(emotes, "NSArray")) return false;
        parse_list_locked(room, emotes, provider, global);
        return true;
    }
    if (provider == 1) {
        if (global) {
            if (!kind(root, "NSArray")) return false;
            parse_list_locked(room, root, provider, global);
        } else {
            if (!kind(root, "NSDictionary")) return false;
            id own = dict(root, "channelEmotes"), shared = dict(root, "sharedEmotes");
            if (!kind(own, "NSArray") || !kind(shared, "NSArray")) return false;
            parse_list_locked(room, own, provider, global);
            parse_list_locked(room, shared, provider, global);
        }
        return true;
    }
    if (!kind(root, "NSDictionary")) return false;
    id sets = dict(root, "sets");
    if (!kind(sets, "NSDictionary")) return false;
    if (global) {
        id defaults = dict(root, "default_sets");
        if (!kind(defaults, "NSArray")) return false;
        for (NSUInteger i = 0; i < count(defaults); i++) {
            id key = call0(at(defaults, i), "description");
            parse_list_locked(room, dict(call1(sets, "objectForKey:", key), "emoticons"),
                              provider, global);
        }
    } else {
        id keys = call0(sets, "allKeys");
        for (NSUInteger i = 0; i < count(keys); i++)
            parse_list_locked(room, dict(call1(sets, "objectForKey:", at(keys, i)), "emoticons"),
                              provider, global);
    }
    return true;
}

/* All exits release pending state, including an unavailable session/task. */
static void finish_provider(id room_string, uint64_t generation, unsigned char provider,
                            NSInteger status, NSUInteger bytes, NSInteger error_code,
                            TASEmoteFetchResult result, id parsed) {
    int scope = room_string ? 1 : 0;
    char detail[256];
    bool current = false;
    pthread_mutex_lock(&g_emote_lock);
    const char *room_copy = text(room_string);
    Room *room = room_copy ? NULL : &g_global;
    if (room_copy) for (size_t i = 0; i < MAX_ROOMS; i++)
        if (g_rooms[i].occupied && strcmp(g_rooms[i].id, room_copy) == 0) room = &g_rooms[i];
    if (room && room->generation == generation) {
        current = true;
        room->pending[provider] = false;
        if (result == TAS_FETCH_READY) {
            if (!parsed) result = TAS_FETCH_JSON;
            else if (!parse_provider_locked(room, parsed, provider, !scope)) result = TAS_FETCH_SCHEMA;
        }
        room->loaded[provider] = result == TAS_FETCH_READY || result == TAS_FETCH_ABSENT;
        if (room->loaded[provider]) {
            PROBE_INC(g_fetch_loaded[provider][scope]);
            if (result == TAS_FETCH_ABSENT) PROBE_INC(g_fetch_absent[provider][scope]);
            room->failures[provider] = 0;
        } else {
            PROBE_INC(g_fetch_failed[provider][scope]);
            if (result == TAS_FETCH_HTTP) PROBE_INC(g_fetch_http_error[provider][scope]);
            else if (result == TAS_FETCH_JSON || result == TAS_FETCH_SCHEMA)
                PROBE_INC(g_fetch_parse_error[provider][scope]);
            else if (result == TAS_FETCH_TRANSPORT || result == TAS_FETCH_UNAVAILABLE)
                PROBE_INC(g_fetch_transport_error[provider][scope]);
            else PROBE_INC(g_fetch_body_error[provider][scope]);
            if (room->failures[provider] < 5) room->failures[provider]++;
        }
        size_t entries = 0;
        for (size_t i = 0; i < room->size; i++)
            if (room->items[i].provider == provider) entries++;
        snprintf(g_fetch_last[provider][scope], sizeof(g_fetch_last[provider][scope]),
                 "status=%ld bytes=%lu error=%ld result=%s entries=%zu",
                 (long)status, (unsigned long)bytes, (long)error_code,
                 tas_emote_fetch_result_name(result), entries);
        const char *providers[] = {"7TV", "BTTV", "FFZ"};
        snprintf(detail, sizeof(detail), "provider=%s scope=%s %s", providers[provider],
                 scope ? "channel" : "global", g_fetch_last[provider][scope]);
    }
    pthread_mutex_unlock(&g_emote_lock);
    /* Log after unlocking: diagnostics never sees API bodies or room IDs. */
    if (current) tas_diag_log("EMOTE_FETCH", detail);
}

static void fetch_provider(const char *room_id, uint64_t generation, unsigned char provider) {
    int scope = room_id ? 1 : 0;
    PROBE_INC(g_fetch_started[provider][scope]);
    char url[256];
    if (!room_id) {
        const char *globals[] = {"https://7tv.io/v3/emote-sets/global",
                                 "https://api.betterttv.net/3/cached/emotes/global",
                                 "https://api.frankerfacez.com/v1/set/global"};
        snprintf(url, sizeof(url), "%s", globals[provider]);
    } else {
        const char *formats[] = {"https://7tv.io/v3/users/twitch/%s",
                                 "https://api.betterttv.net/3/cached/users/twitch/%s",
                                 "https://api.frankerfacez.com/v1/room/id/%s"};
        snprintf(url, sizeof(url), formats[provider], room_id);
    }
    /* Plain C blocks borrow captured id pointers. Own the autoreleased room
     * string until completion, including cancellation and stale responses. */
    id room_string = room_id ? objc_retain(str(room_id)) : nil;
    id session = call0((id)objc_getClass("NSURLSession"), "sharedSession");
    id endpoint = call1((id)objc_getClass("NSURL"), "URLWithString:", str(url));
    if (!session || !endpoint) {
        finish_provider(room_string, generation, provider, 0, 0, 0, TAS_FETCH_UNAVAILABLE, nil);
        objc_release(room_string);
        return;
    }
    id task = ((id (*)(id, SEL, id, id))objc_msgSend)(
        session, sel_registerName("dataTaskWithURL:completionHandler:"), endpoint,
        (id)^(id data, id response, id error) {
            id parsed = nil;
            NSInteger status = kind(response, "NSHTTPURLResponse")
                ? ((NSInteger (*)(id, SEL))objc_msgSend)(response, sel_registerName("statusCode")) : 0;
            NSUInteger bytes = kind(data, "NSData")
                ? ((NSUInteger (*)(id, SEL))objc_msgSend)(data, sel_registerName("length")) : 0;
            NSInteger code = error ? ((NSInteger (*)(id, SEL))objc_msgSend)(error, sel_registerName("code")) : 0;
            TASEmoteFetchResult result = tas_emote_fetch_result(status, bytes, error != nil, !scope);
            if (result == TAS_FETCH_READY)
                parsed = ((id (*)(id, SEL, id, NSUInteger, id *))objc_msgSend)(
                    (id)objc_getClass("NSJSONSerialization"), sel_registerName("JSONObjectWithData:options:error:"),
                    data, (NSUInteger)0, NULL);
            finish_provider(room_string, generation, provider, status, bytes, code, result, parsed);
            objc_release(room_string);
        });
    if (task) call0(task, "resume");
    else {
        finish_provider(room_string, generation, provider, 0, 0, 0, TAS_FETCH_UNAVAILABLE, nil);
        objc_release(room_string);
    }
}

static void ensure_loaded(const char *room_id, bool force) {
    time_t now = time(NULL);
    bool fetch[3] = {false, false, false};
    uint64_t generation;
    pthread_mutex_lock(&g_emote_lock);
    expire_locked(now);
    Room *room = room_id ? room_locked(room_id, now) : &g_global;
    generation = room ? room->generation : 0;
    if (room) for (unsigned char p = 0; p < 3; p++) {
        unsigned shift = room->failures[p] ? room->failures[p] - 1 : 0;
        time_t retry_after = RETRY_SECONDS << (shift > 3 ? 3 : shift);
        if (!room->pending[p] &&
            (force || (!room->loaded[p] &&
                       (!room->attempted[p] || now - room->attempted[p] >= retry_after)))) {
            room->pending[p] = true;
            room->attempted[p] = now;
            fetch[p] = true;
        }
    }
    pthread_mutex_unlock(&g_emote_lock);
    for (unsigned char p = 0; p < 3; p++)
        if (fetch[p]) fetch_provider(room_id, generation, p);
}

static bool valid_room(const char *room) {
    if (!room || !*room || strlen(room) >= sizeof(g_last_room)) return false;
    for (const char *p = room; *p; p++) if (*p < '0' || *p > '9') return false;
    return true;
}

static bool tag_value(const char *start, const char *end, const char *key,
                      char *out, size_t capacity) {
    size_t key_length = strlen(key);
    const char *p = start;
    while (p < end) {
        const char *next = memchr(p, ';', (size_t)(end - p));
        if (!next) next = end;
        if ((size_t)(next - p) > key_length && !strncmp(p, key, key_length) &&
            p[key_length] == '=') {
            size_t n = (size_t)(next - p) - key_length - 1;
            if (n >= capacity) return false;
            memcpy(out, p + key_length + 1, n);
            out[n] = 0;
            return true;
        }
        p = next + (next < end);
    }
    return false;
}

static size_t codepoints(const char *p, size_t n) {
    size_t count = 0;
    for (size_t i = 0; i < n; i++)
        if (((unsigned char)p[i] & 0xc0) != 0x80) count++;
    return count;
}

static bool overlaps_native(const char *tags, const char *end, size_t first, size_t last) {
    char value[4096];
    if (!tag_value(tags, end, "emotes", value, sizeof(value))) return false;
    const char *p = value;
    while ((p = strchr(p, ':'))) {
        p++;
        while (*p) {
            char *after;
            unsigned long a = strtoul(p, &after, 10);
            if (after == p || *after != '-') break;
            p = after + 1;
            unsigned long b = strtoul(p, &after, 10);
            if (after == p) break;
            if (a <= last && b >= first) return true;
            p = after;
            if (*p != ',') break;
            p++;
        }
    }
    return false;
}

static bool boundary_punctuation(unsigned char c) {
    return c == '.' || c == ',' || c == '!' || c == '?' || c == ';' || c == ':' ||
           c == '(' || c == ')' || c == '[' || c == ']' || c == '{' || c == '}' ||
           c == '\'' || c == '"' || c == '<' || c == '>';
}

#if TAS_EMOTE_DIAGNOSTIC
void tas_emote_probe_text(const char *stage,const char *body,const char *channel,const char *outcome) {
    if (!body || strnlen(body,MAX_FRAME+1)>MAX_FRAME) return;
    pthread_mutex_lock(&g_emote_lock);
    Room *room=NULL;
    if (channel) for (size_t i=0;i<MAX_ROOMS;i++)
        if (g_rooms[i].occupied && (!strcmp(g_rooms[i].id,channel) || !strcmp(g_rooms[i].login,channel))) room=&g_rooms[i];
    Emote *emote=g_probe_code[0] && room ? find_word(room,g_probe_code) : NULL;
    if (!emote && g_probe_code[0]) emote=find_word(&g_global,g_probe_code);
    if (g_probe_code[0]) for (const char *p=body;*p;) {
        while (*p==' ' || *p=='\t' || *p=='\r' || *p=='\n') p++;
        const char *word=p;
        while (*p && *p!=' ' && *p!='\t' && *p!='\r' && *p!='\n') p++;
        size_t bytes=(size_t)(p-word),start=0,finish=bytes;
        probe_word_locked(stage,word,bytes,room,emote,outcome,(size_t)(word-body));
        while (start<finish && boundary_punctuation((unsigned char)word[start])) start++;
        while (finish>start && boundary_punctuation((unsigned char)word[finish-1])) finish--;
        if (start || finish!=bytes) probe_word_locked(stage,word+start,finish-start,room,emote,outcome,(size_t)(word-body)+start);
    }
    pthread_mutex_unlock(&g_emote_lock);
}
/* Observe a rejected IRC line only when its PRIVMSG body contains the selected
 * code. Never collect the rest of the line, or create a replacement here. */
static void probe_gate_line(const char *line,size_t length,const char *outcome) {
    const char *command=strstr(line," PRIVMSG #"),*end=line+length;
    const char *body=command ? strstr(command," :") : NULL;
    if (!body || body+2>=end) return;
    body+=2;
    pthread_mutex_lock(&g_emote_lock);
    if (g_probe_code[0]) for (const char *p=body;p<end;) {
        while (p<end && (*p==' ' || *p=='\t')) p++;
        const char *word=p;
        while (p<end && *p!=' ' && *p!='\t') p++;
        size_t bytes=(size_t)(p-word),start=0,finish=bytes;
        probe_word_locked("incoming-gate",word,bytes,NULL,NULL,outcome,(size_t)(word-body));
        while (start<finish && boundary_punctuation((unsigned char)word[start])) start++;
        while (finish>start && boundary_punctuation((unsigned char)word[finish-1])) finish--;
        if (start || finish!=bytes) probe_word_locked("incoming-gate",word+start,finish-start,NULL,NULL,outcome,(size_t)(word-body)+start);
    }
    pthread_mutex_unlock(&g_emote_lock);
}
#endif

/* Returns a replacement for one IRC line, or NULL if it is unchanged. */
static char *rewrite_line(const char *line, size_t length) {
    if (length < 3 || line[0] != '@') {
#if TAS_EMOTE_DIAGNOSTIC
        probe_gate_line(line,length,"untagged-line");
#endif
        return NULL;
    }
    const char *end = line + length;
    const char *tags_end = strstr(line, " :");
    if (!tags_end || tags_end >= end) {
#if TAS_EMOTE_DIAGNOSTIC
        probe_gate_line(line,length,"tag-boundary-missing");
#endif
        return NULL;
    }
    char room_id[32];
    if (!tag_value(line + 1, tags_end, "room-id", room_id, sizeof(room_id)) ||
        !valid_room(room_id)) {
#if TAS_EMOTE_DIAGNOSTIC
        probe_gate_line(line,length,"room-id-missing-or-invalid");
#endif
        return NULL;
    }
    const char *privmsg = strstr(tags_end, " PRIVMSG #");
    bool message = privmsg && privmsg < end;
    if (!message && !strstr(tags_end, " ROOMSTATE #")) return NULL;
    PROBE_INC(g_room_frames);
    pthread_mutex_lock(&g_emote_lock);
    snprintf(g_last_room, sizeof(g_last_room), "%s", room_id);
    pthread_mutex_unlock(&g_emote_lock);
    ensure_loaded(NULL, false);
    ensure_loaded(room_id, false);
    const char *channel_start = strstr(tags_end, message ? " PRIVMSG #" : " ROOMSTATE #");
    channel_start = channel_start ? strchr(channel_start, '#') + 1 : NULL;
    const char *channel_end = channel_start ? strchr(channel_start, ' ') : NULL;
    if (channel_end && channel_end - channel_start <= 96) {
        pthread_mutex_lock(&g_emote_lock);
        for (size_t i = 0; i < MAX_ROOMS; i++)
            if (g_rooms[i].occupied && !strcmp(g_rooms[i].id, room_id)) {
                size_t n = (size_t)(channel_end - channel_start);
                if (strlen(g_rooms[i].login) != n || memcmp(g_rooms[i].login, channel_start, n)) {
                    memcpy(g_rooms[i].login, channel_start, n);
                    g_rooms[i].login[n] = 0;
                    catalog_changed_locked();
                }
            }
        pthread_mutex_unlock(&g_emote_lock);
    }
    if (!message) return NULL;
    const char *separator = strstr(privmsg, " :");
    if (!separator || separator >= end) return NULL;
    const char *body = separator + 2;
    char additions[4096] = "";
    size_t written = 0, position = 0;
    pthread_mutex_lock(&g_emote_lock);
    Room *room = NULL;
    for (size_t i = 0; i < MAX_ROOMS; i++)
        if (g_rooms[i].occupied && strcmp(g_rooms[i].id, room_id) == 0) room = &g_rooms[i];
    for (const char *p = body; p < end;) {
        if (*p == ' ' || *p == '\t') { position++; p++; continue; }
        const char *word = p;
        while (p < end && *p != ' ' && *p != '\t') p++;
        size_t bytes = (size_t)(p - word), span = codepoints(word, bytes);
        if (bytes) PROBE_INC(g_words_scanned);
        size_t trim_start = 0, trim_end = bytes;
        Emote *emote = NULL;
        if (bytes && bytes <= 96 && span && span <= 96) {
            char candidate[97];
            memcpy(candidate, word, bytes);
            candidate[bytes] = 0;
            emote = room ? find_word(room, candidate) : NULL;
            if (!emote) emote = find_word(&g_global, candidate);
            if (!emote) {
                while (trim_start < trim_end && boundary_punctuation((unsigned char)word[trim_start]))
                    trim_start++;
                while (trim_end > trim_start && boundary_punctuation((unsigned char)word[trim_end - 1]))
                    trim_end--;
                size_t candidate_bytes = trim_end - trim_start;
                size_t candidate_span = codepoints(word + trim_start, candidate_bytes);
                if (candidate_bytes && candidate_bytes <= 96 && candidate_span <= 96) {
                    memcpy(candidate, word + trim_start, candidate_bytes);
                    candidate[candidate_bytes] = 0;
                    emote = room ? find_word(room, candidate) : NULL;
                    if (!emote) emote = find_word(&g_global, candidate);
                    if (emote) PROBE_INC(g_punctuation_matches);
                }
            }
            if (emote) {
                size_t first = position + codepoints(word, trim_start);
                size_t matched_span = codepoints(word + trim_start, trim_end - trim_start);
                if (overlaps_native(line + 1, tags_end, first, first + matched_span - 1)) {
#if TAS_EMOTE_DIAGNOSTIC
                    probe_word_locked("incoming",word+trim_start,trim_end-trim_start,room,emote,"native-overlap",first);
#endif
                    PROBE_INC(g_native_overlaps);
                    position += span;
                    continue;
                }
                PROBE_INC(g_match_words);
                int n = snprintf(additions + written, sizeof(additions) - written,
                                 "%s%llu:%zu-%zu", written ? "/" : "",
                                 (unsigned long long)emote->fake_id, first, first + matched_span - 1);
                if (n > 0 && (size_t)n < sizeof(additions) - written) {
                    written += (size_t)n;
#if TAS_EMOTE_DIAGNOSTIC
                    probe_word_locked("incoming",word+trim_start,trim_end-trim_start,room,emote,"tag-appended",first);
#endif
                } else {
#if TAS_EMOTE_DIAGNOSTIC
                    probe_word_locked("incoming",word+trim_start,trim_end-trim_start,room,emote,"tag-capacity",first);
#endif
                    break;
                }
            }
#if TAS_EMOTE_DIAGNOSTIC
            else {
                probe_word_locked("incoming",word,bytes,room,NULL,"catalog-miss",position);
                if (trim_start || trim_end!=bytes)
                    probe_word_locked("incoming-trimmed",word+trim_start,trim_end-trim_start,room,NULL,"catalog-miss",position+codepoints(word,trim_start));
            }
#endif
        }
        position += span;
    }
    pthread_mutex_unlock(&g_emote_lock);
    if (!written) return NULL;
    const char *old_tag = strstr(line, "emotes=");
    if (old_tag && old_tag < tags_end && old_tag != line + 1 && old_tag[-1] != ';') old_tag = NULL;
    const char *value_end = NULL;
    if (old_tag) {
        value_end = memchr(old_tag, ';', (size_t)(tags_end - old_tag));
        if (!value_end) value_end = tags_end;
    }
    size_t capacity = length + written + 16;
    char *result = malloc(capacity);
    if (!result) return NULL;
    size_t prefix = (size_t)((old_tag ? value_end : tags_end) - line);
    memcpy(result, line, prefix);
    size_t offset = prefix;
    if (old_tag && value_end > old_tag + 7) result[offset++] = '/';
    else if (!old_tag) {
        memcpy(result + offset, ";emotes=", 8);
        offset += 8;
    }
    memcpy(result + offset, additions, written);
    offset += written;
    const char *tail = old_tag ? value_end : tags_end;
    memcpy(result + offset, tail, (size_t)(end - tail));
    offset += (size_t)(end - tail);
    result[offset] = 0;
    return result;
}

static id rewrite_message(id message) {
    PROBE_INC(g_receive_calls);
    if (!message || ((NSInteger (*)(id, SEL))objc_msgSend)(message, sel_registerName("type")) != 1)
        return nil;
    PROBE_INC(g_text_frames);
    const char *input = text(call0(message, "string"));
    if (!input) return nil;
    size_t length = strnlen(input, MAX_FRAME + 1);
    if (length > MAX_FRAME || input[0] != '@') {
#if TAS_EMOTE_DIAGNOSTIC
        if (length<=MAX_FRAME) probe_gate_line(input,length,"untagged-frame");
#endif
        return nil;
    }
    PROBE_INC(g_tagged_frames);
    char *output = malloc(length * 2 + 4096);
    if (!output) return nil;
    size_t used = 0;
    bool changed = false, complete = true;
    const char *line = input;
    while (*line) {
        const char *break_at = strstr(line, "\r\n");
        size_t line_length = break_at ? (size_t)(break_at - line) : strlen(line);
        char *temporary = malloc(line_length + 1);
        if (!temporary) { complete = false; break; }
        memcpy(temporary, line, line_length);
        temporary[line_length] = 0;
        char *replacement = rewrite_line(temporary, line_length);
        const char *chosen = replacement ? replacement : temporary;
        size_t n = strlen(chosen);
        if (used + n + 3 > length * 2 + 4096) {
            free(replacement);
            free(temporary);
            complete = false;
            break;
        }
        memcpy(output + used, chosen, n);
        used += n;
        changed |= replacement != NULL;
        free(replacement);
        free(temporary);
        if (!break_at) break;
        output[used++] = '\r';
        output[used++] = '\n';
        line = break_at + 2;
    }
    id rewritten = nil;
    if (changed && complete) {
        PROBE_INC(g_rewritten_frames);
        output[used] = 0;
        id value = str(output);
        if (value) {
            rewritten = ((id (*)(id, SEL, id))objc_msgSend)(
                call0((id)objc_getClass("NSURLSessionWebSocketMessage"), "alloc"),
                sel_registerName("initWithString:"), value);
            rewritten = call0(rewritten, "autorelease");
        }
    }
    free(output);
    return rewritten;
}

typedef void (^ReceiveHandler)(id, id);
static ReceiveHandler wrap_handler(ReceiveHandler original) {
    if (!original || objc_getAssociatedObject((id)original, &g_wrapped_key)) return original;
    ReceiveHandler wrapped = ^(id message, id error) {
        id replacement = error ? nil : rewrite_message(message);
        original(replacement ? replacement : message, error);
    };
    wrapped = (__typeof__(wrapped))_Block_copy(wrapped);
    objc_setAssociatedObject((id)wrapped, &g_wrapped_key, str("yes"), 1);
    return wrapped;
}

static void public_receive(id self, SEL command, ReceiveHandler handler) {
    ReceiveHandler wrapped = wrap_handler(handler);
    ((void (*)(id, SEL, ReceiveHandler))g_public_receive)(self, command, wrapped);
    if (wrapped != handler) _Block_release(wrapped);
}
static void private_receive(id self, SEL command, ReceiveHandler handler) {
    ReceiveHandler wrapped = wrap_handler(handler);
    ((void (*)(id, SEL, ReceiveHandler))g_private_receive)(self, command, wrapped);
    if (wrapped != handler) _Block_release(wrapped);
}

bool tas_emotes_enabled_this_launch(void) { return g_enabled; }

static Emote *emote_for_id_locked(uint64_t synthetic_id) {
    if (synthetic_id < FAKE_ID_START) return NULL;
    for (size_t i = 0; i < g_global.size; i++)
        if (g_global.items[i].fake_id == synthetic_id) return &g_global.items[i];
    for (size_t r = 0; r < MAX_ROOMS; r++)
        for (size_t i = 0; i < g_rooms[r].size; i++)
            if (g_rooms[r].items[i].fake_id == synthetic_id) return &g_rooms[r].items[i];
    for (size_t i = 0; i < MAX_HISTORY; i++)
        if (g_old[i].emote.fake_id == synthetic_id && g_old[i].emote.url &&
            time(NULL) - g_old[i].retired_at < HISTORY_SECONDS) return &g_old[i].emote;
    return NULL;
}

double tas_emotes_aspect(uint64_t synthetic_id) {
    if (!g_enabled || synthetic_id < FAKE_ID_START) return 0;
    pthread_mutex_lock(&g_emote_lock);
    Emote *e = emote_for_id_locked(synthetic_id);
    double aspect = e ? e->aspect : 0;
    pthread_mutex_unlock(&g_emote_lock);
    return aspect;
}

/* Immutable value snapshots: no pointers into the mutable provider registry. */
static id metadata_locked(const Emote *e) {
    id metadata = call0((id)objc_getClass("NSMutableDictionary"), "new");
    const char *keys[] = {"name", "url", "subtitle"};
    const char *providers[] = {"7TV", "BTTV", "FFZ"};
    char subtitle[200];
    snprintf(subtitle,sizeof(subtitle),"%s %s emote%s%s",providers[e->provider],
             e->global ? "global" : "channel",e->owner ? "\nby " : "",e->owner ?: "");
    id values[] = {str(e->name),str(e->url),str(subtitle)};
    for (size_t i=0;i<3;i++) ((void (*)(id,SEL,id,id))objc_msgSend)(metadata,sel_registerName("setObject:forKey:"),values[i],str(keys[i]));
    id number = ((id (*)(id,SEL,uint64_t))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithUnsignedLongLong:"),e->fake_id);
    ((void (*)(id,SEL,id,id))objc_msgSend)(metadata,sel_registerName("setObject:forKey:"),number,str("id"));
    number = ((id (*)(id,SEL,double))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithDouble:"),e->aspect);
    ((void (*)(id,SEL,id,id))objc_msgSend)(metadata,sel_registerName("setObject:forKey:"),number,str("aspect"));
    number = ((id (*)(id,SEL,int))objc_msgSend)((id)objc_getClass("NSNumber"),sel_registerName("numberWithInt:"),e->provider);
    ((void (*)(id,SEL,id,id))objc_msgSend)(metadata,sel_registerName("setObject:forKey:"),number,str("provider"));
    id result = call0(metadata,"copy"); objc_release(metadata); return result;
}

id tas_emotes_metadata_copy(uint64_t synthetic_id) {
    if (!g_enabled || synthetic_id < FAKE_ID_START) return nil;
    pthread_mutex_lock(&g_emote_lock);
    Emote *e = emote_for_id_locked(synthetic_id);
    id metadata = e ? metadata_locked(e) : nil;
    pthread_mutex_unlock(&g_emote_lock); return metadata;
}

static Room *picker_room_locked(id channel) {
    if (!kind(channel,"NSString")) return NULL;
    const char *value = text(channel);
    if (!value) return NULL;
    for (size_t i=0;i<MAX_ROOMS;i++)
        if (g_rooms[i].occupied && (!strcmp(value,g_rooms[i].id) || !strcmp(value,g_rooms[i].login)))
            return &g_rooms[i];
    return NULL;
}

id tas_emotes_picker_copy(id channel, int provider, int scope, id query, size_t limit) {
    if (!g_enabled || provider < 0 || provider > 3 || scope < -1 || scope > 1) return nil;
    const char *fragment = kind(query,"NSString") ? text(query) : "";
    if (!fragment || strlen(fragment) > 96) return nil;
    if (limit > MAX_ROOM + MAX_GLOBAL) limit = MAX_ROOM + MAX_GLOBAL;
    id result = call0((id)objc_getClass("NSMutableArray"),"new");
    if (!limit) return result;
    pthread_mutex_lock(&g_emote_lock);
    Room *room = picker_room_locked(channel);
    Room *libraries[] = {room, &g_global};
    for (int library=0;library<2;library++) {
        Room *r=libraries[library];
        if (!r || (scope >= 0 && scope != library)) continue;
        for (size_t i=0;i<r->size;i++) {
            Emote *e=&r->items[i];
            if (!ss_provider_matches(e->provider,provider) || !ss_ascii_contains(e->name,fragment)) continue;
            /* Suggestions use the same channel-over-global precedence as chat. */
            if (scope == -1 && library && room && find_word(room,e->name)) continue;
            id metadata=metadata_locked(e); ((void (*)(id,SEL,id))objc_msgSend)(result,sel_registerName("addObject:"),metadata);
            objc_release(metadata);
        }
    }
    pthread_mutex_unlock(&g_emote_lock);
    /* The lookup registry must keep exact byte ordering for case-sensitive
     * chat codes. Sort only these immutable display snapshots, across every
     * included provider/scope, so uppercase A-Z cannot precede lowercase a-z. */
    ((void (*)(id,SEL,id))objc_msgSend)(result,sel_registerName("sortUsingComparator:"),(id)^NSInteger(id a,id b) {
        id left=dict(a,"name"),right=dict(b,"name");
        NSInteger order=((NSInteger (*)(id,SEL,id))objc_msgSend)(left,sel_registerName("caseInsensitiveCompare:"),right);
        return order ? order : ((NSInteger (*)(id,SEL,id))objc_msgSend)(left,sel_registerName("compare:"),right);
    });
    /* Apply the limit after sorting, so a small result window starts at A. */
    while (count(result)>limit) call0(result,"removeLastObject");
    return result;
}

id tas_emotes_named_copy(id channel, id name) {
    if (!g_enabled || !kind(name,"NSString")) return nil;
    const char *word=text(name);
    if (!word || !*word || strlen(word)>96) return nil;
    pthread_mutex_lock(&g_emote_lock);
    Room *room=picker_room_locked(channel);
    Emote *e=room ? find_word(room,word) : NULL;
    if (!e) e=find_word(&g_global,word);
#if TAS_EMOTE_DIAGNOSTIC
    probe_word_locked("named-lookup",word,strlen(word),room,e,e ? "catalog-hit" : "catalog-miss",0);
#endif
    id result=e ? metadata_locked(e) : nil;
    pthread_mutex_unlock(&g_emote_lock); return result;
}


id tas_emotes_local_matches_copy(id channel, id content) {
    if (!g_enabled || !kind(channel, "NSString") || !kind(content, "NSString")) return nil;
    const char *login = text(channel), *body = text(content);
    if (!login || !body || strlen(login) > 96 || strnlen(body, MAX_FRAME + 1) > MAX_FRAME) return nil;
    if (*login == '#') login++;
    id matches = call0((id)objc_getClass("NSMutableDictionary"), "new");
    pthread_mutex_lock(&g_emote_lock);
    Room *room = NULL;
    for (size_t i = 0; i < MAX_ROOMS; i++)
        if (g_rooms[i].occupied && (!strcmp(g_rooms[i].login, login) || !strcmp(g_rooms[i].id, login))) {
            room = &g_rooms[i];
            room->last_used = time(NULL);
            break;
        }
    for (const char *p = body; *p;) {
        if (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') { p++; continue; }
        const char *start = p;
        while (*p && *p != ' ' && *p != '\t' && *p != '\r' && *p != '\n') p++;
        size_t n = (size_t)(p - start);
        if (!n || n > 96) continue;
        char word[97]; memcpy(word, start, n); word[n] = 0;
        Emote *e = room ? find_word(room, word) : NULL;
        if (!e) e = find_word(&g_global, word);
#if TAS_EMOTE_DIAGNOSTIC
        probe_word_locked("local-match",word,n,room,e,e ? "catalog-hit" : "catalog-miss",(size_t)(start-body));
#endif
        if (e) {
            char number[32]; snprintf(number, sizeof(number), "%llu", (unsigned long long)e->fake_id);
            ((void (*)(id, SEL, id, id))objc_msgSend)(matches, sel_registerName("setObject:forKey:"), str(number), str(e->name));
        }
    }
    pthread_mutex_unlock(&g_emote_lock);
    return matches;
}

static char *url_for_id_locked(uint64_t id, time_t now) {
    for (size_t i = 0; i < g_global.size; i++)
        if (g_global.items[i].fake_id == id) return strdup(g_global.items[i].url);
    for (size_t r = 0; r < MAX_ROOMS; r++)
        for (size_t i = 0; i < g_rooms[r].size; i++)
            if (g_rooms[r].items[i].fake_id == id) return strdup(g_rooms[r].items[i].url);
    for (size_t i = 0; i < MAX_HISTORY; i++)
        if (g_old[i].emote.fake_id == id && g_old[i].emote.url &&
            now - g_old[i].retired_at < HISTORY_SECONDS) return strdup(g_old[i].emote.url);
    return NULL;
}

id tas_emotes_rewrite_request_copy(id request) {
    if (!g_enabled || !request) return nil;
    id url = call0(request, "URL");
    const char *host = text(call0(url, "host"));
    const char *path = text(call0(url, "path"));
    const char *prefix = "/emoticons/v2/";
    if (!host || strcmp(host, "static-cdn.jtvnw.net") || !path ||
        strncmp(path, prefix, strlen(prefix))) return nil;
    const char *digits = path + strlen(prefix);
    if (strncmp(digits, "9", 1)) return nil;
    char *end;
    uint64_t fake_id = strtoull(digits, &end, 10);
    if (end == digits || *end != '/' || fake_id < FAKE_ID_START) return nil;
    pthread_mutex_lock(&g_emote_lock);
    char *image = url_for_id_locked(fake_id, time(NULL));
    pthread_mutex_unlock(&g_emote_lock);
    tas_emote_probe_stage(fake_id,image ? "image-request-mapped" : "image-request-missing");
#if TAS_EMOTE_DIAGNOSTIC
    char mapping[96];
    snprintf(mapping,sizeof(mapping),"mapped=%s request-kind=%s asset=%s",image ? "yes" : "no",
        !strncmp(end,"/static/",8) ? "static" : !strncmp(end,"/animated/",10) ? "animated" : !strncmp(end,"/default/",9) ? "default" : "unknown",
        image && strstr(image,".gif") ? "GIF" : image && strstr(image,".webp") ? "WebP" : image && strstr(image,".png") ? "PNG" : "other");
    tas_emote_probe_image(fake_id,0,"request-map",mapping);
#endif
    if (!image) return nil;
    PROBE_INC(g_image_rewrites);
    id destination = call1((id)objc_getClass("NSURL"), "URLWithString:", str(image));
    free(image);
    if (!destination) return nil;
    id mutable = call0(request, "mutableCopy");
    ((void (*)(id, SEL, id))objc_msgSend)(mutable, sel_registerName("setURL:"), destination);
    return mutable;
}

void tas_emotes_image_request(bool has_completion) {
    if (has_completion) PROBE_INC(g_image_with_completion);
    else PROBE_INC(g_image_without_completion);
}

static void update_image_aspect(id data, id response) {
    const char *url = text(call0(call0(response, "URL"), "absoluteString"));
    if (!tas_emotes_is_provider_image_url(url) || !kind(data, "NSData")) return;
    const unsigned char *bytes = ((const unsigned char *(*)(id, SEL))objc_msgSend)(data, sel_registerName("bytes"));
    double aspect = tas_emote_image_aspect(bytes, ((NSUInteger (*)(id, SEL))objc_msgSend)(data, sel_registerName("length")));
    if (!aspect) return;
    pthread_mutex_lock(&g_emote_lock);
    for (size_t r = 0; r <= MAX_ROOMS; r++) {
        Room *room = r == MAX_ROOMS ? &g_global : &g_rooms[r];
        for (size_t i = 0; i < room->size; i++)
            if (!strcmp(room->items[i].url, url)) room->items[i].aspect = aspect;
    }
    for (size_t i = 0; i < MAX_HISTORY; i++)
        if (g_old[i].emote.url && !strcmp(g_old[i].emote.url, url)) g_old[i].emote.aspect = aspect;
    pthread_mutex_unlock(&g_emote_lock);
}

static void image_probe_url(const char *url, const char *stage, const char *outcome) {
#if TAS_EMOTE_DIAGNOSTIC
    if (!url) return;
    pthread_mutex_lock(&g_emote_lock);
    /* A late selection must still see earlier transport evidence. A shared
     * asset can map to several numeric identities; record each once. */
    uint64_t recorded[PLAYBACK_EMOTES]; unsigned recorded_count=0;
    time_t now=time(NULL);
    for (size_t r=0;r<=MAX_ROOMS+1;r++) {
        size_t n=r==MAX_ROOMS+1 ? MAX_HISTORY : (r==MAX_ROOMS ? g_global.size : g_rooms[r].size);
        for (size_t i=0;i<n;i++) {
            Emote *e=r==MAX_ROOMS+1 ? &g_old[i].emote : &(r==MAX_ROOMS ? &g_global : &g_rooms[r])->items[i];
            if (!e->url || (r==MAX_ROOMS+1 && now-g_old[i].retired_at>=HISTORY_SECONDS) || strcmp(e->url,url)) continue;
            unsigned j=0; for (;j<recorded_count;j++) if (recorded[j]==e->fake_id) break;
            if (j<recorded_count) continue;
            if (recorded_count==PLAYBACK_EMOTES) break;
            recorded[recorded_count++]=e->fake_id;
            playback_record_locked(e->fake_id,0,stage,outcome,false);
        }
    }
    if (g_probe_code[0]) for (size_t r=0;r<=MAX_ROOMS;r++) {
        Room *room=r==MAX_ROOMS ? &g_global : &g_rooms[r];
        Emote *emote=find_word(room,g_probe_code);
        if (emote && !strcmp(emote->url,url)) {
            probe_word_locked(stage,emote->name,strlen(emote->name),r==MAX_ROOMS ? NULL : room,emote,outcome,0);
            break;
        }
    }
    pthread_mutex_unlock(&g_emote_lock);
#else
    (void)url; (void)stage; (void)outcome;
#endif
}

#if TAS_EMOTE_DIAGNOSTIC
static void image_probe_body(const char *url,id data) {
    if (!url || !data) return;
    uint64_t ids[PLAYBACK_EMOTES]; unsigned used=0; time_t t=time(NULL);
    pthread_mutex_lock(&g_emote_lock);
    for (size_t r=0;r<=MAX_ROOMS+1;r++) {
        size_t count=r==MAX_ROOMS+1 ? MAX_HISTORY : (r==MAX_ROOMS ? g_global.size : g_rooms[r].size);
        for (size_t i=0;i<count;i++) {
            Emote *e=r==MAX_ROOMS+1 ? &g_old[i].emote : &(r==MAX_ROOMS ? &g_global : &g_rooms[r])->items[i];
            if (!e->url || (r==MAX_ROOMS+1 && t-g_old[i].retired_at>=HISTORY_SECONDS) || strcmp(e->url,url)) continue;
            unsigned j=0; for (;j<used;j++) if (ids[j]==e->fake_id) break;
            if (j==used && used<PLAYBACK_EMOTES) ids[used++]=e->fake_id;
        }
    }
    pthread_mutex_unlock(&g_emote_lock);
    /* The image-provenance mutex is never nested under the catalog mutex. */
    for (unsigned i=0;i<used;i++) tas_image_probe_response(ids[i],data);
}
#endif

void tas_emotes_image_result(id data, id response, id error) {
    tas_emotes_image_result_for_url(text(call0(call0(response,"URL"),"absoluteString")),data,response,error);
}
void tas_emotes_image_result_for_url(const char *request_url, id data, id response, id error) {
    if (error) PROBE_INC(g_image_transport_error);
    else {
        NSInteger status = response && ((BOOL (*)(id, SEL, SEL))objc_msgSend)(
            response, sel_registerName("respondsToSelector:"), sel_registerName("statusCode"))
            ? ((NSInteger (*)(id, SEL))objc_msgSend)(response, sel_registerName("statusCode")) : 0;
        if (status >= 200 && status < 300) { PROBE_INC(g_image_http_ok); update_image_aspect(data, response); }
        else PROBE_INC(g_image_http_error);
    }
    NSUInteger length = data ? ((NSUInteger (*)(id, SEL))objc_msgSend)(
        data, sel_registerName("length")) : 0;
    if (!length) PROBE_INC(g_image_empty);
    const char *mime = text(call0(response, "MIMEType"));
    if (mime && strcmp(mime, "image/gif") == 0) PROBE_INC(g_image_gif);
    else if (mime && strcmp(mime, "image/webp") == 0) PROBE_INC(g_image_webp);
    else PROBE_INC(g_image_other);
#if TAS_EMOTE_DIAGNOSTIC
    NSInteger status=response && ((BOOL (*)(id,SEL,SEL))objc_msgSend)(response,sel_registerName("respondsToSelector:"),sel_registerName("statusCode"))
        ? ((NSInteger (*)(id,SEL))objc_msgSend)(response,sel_registerName("statusCode")) : 0;
    NSInteger code=error ? ((NSInteger (*)(id,SEL))objc_msgSend)(error,sel_registerName("code")) : 0;
    char result[96];
    snprintf(result,sizeof(result),"http=%ld error=%ld body=%lu type=%s",(long)status,(long)code,(unsigned long)length,
             mime && !strcmp(mime,"image/gif") ? "GIF" : mime && !strcmp(mime,"image/webp") ? "WebP" : "other");
    image_probe_url(request_url,"image-response",result);
    image_probe_body(request_url,data);
#else
    (void)request_url;
#endif
}

static id private_task(id self, SEL command, id request) {
    id replacement = tas_emotes_rewrite_request_copy(request);
    if (replacement) tas_emotes_image_request(false);
    id result = ((id (*)(id, SEL, id))g_private_request)(self, command, replacement ?: request);
    if (replacement) objc_release(replacement);
    return result;
}
static id private_task_completion(id self, SEL command, id request, id completion) {
    id replacement = tas_emotes_rewrite_request_copy(request);
    if (replacement) tas_emotes_image_request(true);
    id handler = completion;
    if (replacement && completion) {
        handler = (id)^(id data, id response, id error) {
            tas_emotes_image_result(data, response, error);
            ((void (^)(id, id, id))completion)(data, response, error);
        };
    }
    id result = ((id (*)(id, SEL, id, id))g_private_request_completion)(
        self, command, replacement ?: request, handler);
    if (replacement) objc_release(replacement);
    return result;
}

/* Only override methods implemented directly by the concrete class. Replacing
 * an inherited method here would modify NSURLSession's existing VAFT hook. */
static void hook_own_method(Class cls, const char *selector, IMP replacement, IMP *original) {
    if (!cls) return;
    unsigned int n = 0;
    Method *methods = class_copyMethodList(cls, &n);
    SEL target = sel_registerName(selector);
    for (unsigned int i = 0; i < n; i++) {
        if (method_getName(methods[i]) == target) {
            *original = method_getImplementation(methods[i]);
            method_setImplementation(methods[i], replacement);
            break;
        }
    }
    free(methods);
}

static void hook_method_including_inherited(Class cls, const char *selector,
                                             IMP replacement, IMP *original) {
    if (!cls || *original) return;
    SEL target = sel_registerName(selector);
    Method method = class_getInstanceMethod(cls, target);
    if (!method) return;
    IMP implementation = method_getImplementation(method);
    if (class_addMethod(cls, target, replacement, method_getTypeEncoding(method))) {
        *original = implementation;
    } else {
        hook_own_method(cls, selector, replacement, original);
    }
}

void tas_emotes_reload(void) {
    if (!g_enabled) return;
    char current[32];
    pthread_mutex_lock(&g_emote_lock);
    time_t now = time(NULL);
    reset_room_locked(&g_global, true, now);
    g_global.generation = ++g_generation;
    for (size_t i = 0; i < MAX_ROOMS; i++) reset_room_locked(&g_rooms[i], true, now);
    snprintf(current, sizeof(current), "%s", g_last_room);
    pthread_mutex_unlock(&g_emote_lock);
    ensure_loaded(NULL, false);
    if (valid_room(current)) ensure_loaded(current, false);
}

void tas_emotes_clear_cache(void) {
    pthread_mutex_lock(&g_emote_lock);
    time_t now = time(NULL);
    reset_room_locked(&g_global, false, now);
    g_global.generation = ++g_generation;
    for (size_t i = 0; i < MAX_ROOMS; i++) reset_room_locked(&g_rooms[i], false, now);
    for (size_t i = 0; i < MAX_HISTORY; i++) {
        drop_emote(&g_old[i].emote);
        memset(&g_old[i], 0, sizeof(g_old[i]));
    }
    g_last_room[0] = 0;
    pthread_mutex_unlock(&g_emote_lock);
    /* The next ROOMSTATE or PRIVMSG lazily refetches its channel. */
}

void tas_emotes_initialize(void) {
    id prefs = call0((id)objc_getClass("NSUserDefaults"), "standardUserDefaults");
    g_enabled = ((BOOL (*)(id, SEL, id))objc_msgSend)(prefs, sel_registerName("boolForKey:"), str(EMOTE_KEY));
    if (!g_enabled) return;
    pthread_mutex_lock(&g_emote_lock);
    g_global.generation = ++g_generation;
    pthread_mutex_unlock(&g_emote_lock);
    tas_emotes_retry_hooks();
    ensure_loaded(NULL, false);
}

void tas_emotes_retry_hooks(void) {
    if (!g_enabled) return;
    if (!g_public_receive)
        hook_method_including_inherited(objc_getClass("NSURLSessionWebSocketTask"),
                                        "receiveMessageWithCompletionHandler:",
                                        (IMP)public_receive, &g_public_receive);
    if (!g_private_receive)
        hook_own_method(objc_getClass("__NSURLSessionWebSocketTask"),
                        "receiveMessageWithCompletionHandler:", (IMP)private_receive, &g_private_receive);
    if (!g_private_request)
        hook_own_method(objc_getClass("__NSURLSessionLocal"), "dataTaskWithRequest:",
                        (IMP)private_task, &g_private_request);
    if (!g_private_request_completion)
        hook_own_method(objc_getClass("__NSURLSessionLocal"),
                        "dataTaskWithRequest:completionHandler:",
                        (IMP)private_task_completion, &g_private_request_completion);
}

void tas_emotes_status(char *buffer, size_t capacity) {
    if (!buffer || !capacity) return;
    pthread_mutex_lock(&g_emote_lock);
    size_t global_count = g_global.size, room_count = 0;
    char last[3][2][160];
    memcpy(last, g_fetch_last, sizeof(last));
    for (size_t i = 0; i < MAX_ROOMS; i++) room_count += g_rooms[i].size;
    pthread_mutex_unlock(&g_emote_lock);
    snprintf(buffer, capacity,
        "\nThird-party emotes (this launch)\n"
        "Active: %s\n"
        "WebSocket hooks (public/private): %s/%s\n"
        "Image hooks (private task/completion): %s/%s\n"
        "WebSocket callbacks/text/tagged/room: %llu/%llu/%llu/%llu\n"
        "Rewritten frames/image requests: %llu/%llu\n"
        "Image tasks (completion/delegate): %llu/%llu\n"
        "Provider image protocol requests: %llu\n"
        "Provider image protocol cancellations before completion: %llu\n"
        "Image responses (HTTP 2xx/other/transport error/empty): %llu/%llu/%llu/%llu\n"
        "Image MIME (GIF/WebP/other): %llu/%llu/%llu\n"
        "Matched emote words/native overlaps: %llu/%llu\n"
        "Message words scanned/punctuation matches: %llu/%llu\n"
        "Registry entries (global/active rooms): %zu/%zu\n"
        "7TV fetches global/channel (started/loaded/failed): %llu/%llu/%llu, %llu/%llu/%llu\n"
        "BTTV fetches global/channel (started/loaded/failed): %llu/%llu/%llu, %llu/%llu/%llu\n"
        "FFZ fetches global/channel (started/loaded/failed): %llu/%llu/%llu, %llu/%llu/%llu\n"
        "Provider failures (HTTP/parse): %llu/%llu, %llu/%llu, %llu/%llu\n"
        "Provider failures (transport/body): %llu/%llu, %llu/%llu, %llu/%llu\n"
        "Absent channels (7TV/BTTV/FFZ): %llu/%llu/%llu\n"
        "7TV last global/channel: %s; %s\n"
        "BTTV last global/channel: %s; %s\n"
        "FFZ last global/channel: %s; %s\n",
        g_enabled ? "yes" : "no", g_public_receive ? "installed" : "missing",
        g_private_receive ? "installed" : "missing",
        g_private_request ? "installed" : "missing",
        g_private_request_completion ? "installed" : "missing",
        (unsigned long long)PROBE_GET(g_receive_calls),
        (unsigned long long)PROBE_GET(g_text_frames),
        (unsigned long long)PROBE_GET(g_tagged_frames),
        (unsigned long long)PROBE_GET(g_room_frames),
        (unsigned long long)PROBE_GET(g_rewritten_frames),
        (unsigned long long)PROBE_GET(g_image_rewrites),
        (unsigned long long)PROBE_GET(g_image_with_completion),
        (unsigned long long)PROBE_GET(g_image_without_completion),
        (unsigned long long)PROBE_GET(g_image_protocol_requests),
        (unsigned long long)PROBE_GET(g_image_protocol_cancelled),
        (unsigned long long)PROBE_GET(g_image_http_ok),
        (unsigned long long)PROBE_GET(g_image_http_error),
        (unsigned long long)PROBE_GET(g_image_transport_error),
        (unsigned long long)PROBE_GET(g_image_empty),
        (unsigned long long)PROBE_GET(g_image_gif),
        (unsigned long long)PROBE_GET(g_image_webp),
        (unsigned long long)PROBE_GET(g_image_other),
        (unsigned long long)PROBE_GET(g_match_words),
        (unsigned long long)PROBE_GET(g_native_overlaps),
        (unsigned long long)PROBE_GET(g_words_scanned),
        (unsigned long long)PROBE_GET(g_punctuation_matches),
        global_count, room_count,
        (unsigned long long)PROBE_GET(g_fetch_started[0][0]),
        (unsigned long long)PROBE_GET(g_fetch_loaded[0][0]),
        (unsigned long long)PROBE_GET(g_fetch_failed[0][0]),
        (unsigned long long)PROBE_GET(g_fetch_started[0][1]),
        (unsigned long long)PROBE_GET(g_fetch_loaded[0][1]),
        (unsigned long long)PROBE_GET(g_fetch_failed[0][1]),
        (unsigned long long)PROBE_GET(g_fetch_started[1][0]),
        (unsigned long long)PROBE_GET(g_fetch_loaded[1][0]),
        (unsigned long long)PROBE_GET(g_fetch_failed[1][0]),
        (unsigned long long)PROBE_GET(g_fetch_started[1][1]),
        (unsigned long long)PROBE_GET(g_fetch_loaded[1][1]),
        (unsigned long long)PROBE_GET(g_fetch_failed[1][1]),
        (unsigned long long)PROBE_GET(g_fetch_started[2][0]),
        (unsigned long long)PROBE_GET(g_fetch_loaded[2][0]),
        (unsigned long long)PROBE_GET(g_fetch_failed[2][0]),
        (unsigned long long)PROBE_GET(g_fetch_started[2][1]),
        (unsigned long long)PROBE_GET(g_fetch_loaded[2][1]),
        (unsigned long long)PROBE_GET(g_fetch_failed[2][1]),
        (unsigned long long)(PROBE_GET(g_fetch_http_error[0][0]) + PROBE_GET(g_fetch_http_error[0][1])),
        (unsigned long long)(PROBE_GET(g_fetch_parse_error[0][0]) + PROBE_GET(g_fetch_parse_error[0][1])),
        (unsigned long long)(PROBE_GET(g_fetch_http_error[1][0]) + PROBE_GET(g_fetch_http_error[1][1])),
        (unsigned long long)(PROBE_GET(g_fetch_parse_error[1][0]) + PROBE_GET(g_fetch_parse_error[1][1])),
        (unsigned long long)(PROBE_GET(g_fetch_http_error[2][0]) + PROBE_GET(g_fetch_http_error[2][1])),
        (unsigned long long)(PROBE_GET(g_fetch_parse_error[2][0]) + PROBE_GET(g_fetch_parse_error[2][1])),
        (unsigned long long)(PROBE_GET(g_fetch_transport_error[0][0]) + PROBE_GET(g_fetch_transport_error[0][1])),
        (unsigned long long)(PROBE_GET(g_fetch_body_error[0][0]) + PROBE_GET(g_fetch_body_error[0][1])),
        (unsigned long long)(PROBE_GET(g_fetch_transport_error[1][0]) + PROBE_GET(g_fetch_transport_error[1][1])),
        (unsigned long long)(PROBE_GET(g_fetch_body_error[1][0]) + PROBE_GET(g_fetch_body_error[1][1])),
        (unsigned long long)(PROBE_GET(g_fetch_transport_error[2][0]) + PROBE_GET(g_fetch_transport_error[2][1])),
        (unsigned long long)(PROBE_GET(g_fetch_body_error[2][0]) + PROBE_GET(g_fetch_body_error[2][1])),
        (unsigned long long)PROBE_GET(g_fetch_absent[0][1]),
        (unsigned long long)PROBE_GET(g_fetch_absent[1][1]),
        (unsigned long long)PROBE_GET(g_fetch_absent[2][1]),
        last[0][0][0] ? last[0][0] : "none", last[0][1][0] ? last[0][1] : "none",
        last[1][0][0] ? last[1][0] : "none", last[1][1][0] ? last[1][1] : "none",
        last[2][0][0] ? last[2][0] : "none", last[2][1][0] ? last[2][1] : "none");
}
