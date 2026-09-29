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
#define MAX_ROOM 1500
#define MAX_HISTORY 3000
#define ROOM_IDLE_SECONDS 1200
#define HISTORY_SECONDS 2700
#define RETRY_SECONDS 60
#define MAX_FRAME 65536
#define MAX_API_BYTES (2 * 1024 * 1024)
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
    uint64_t fake_id;
    unsigned char provider; /* 0: 7TV; 1: BTTV; 2: FFZ */
} Emote;
typedef struct {
    bool occupied;
    char id[32];
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
    uint64_t fake_id;
    char *url;
    time_t retired_at;
} OldImage;

static pthread_mutex_t g_emote_lock = PTHREAD_MUTEX_INITIALIZER;
static Room g_global;
static Room g_rooms[MAX_ROOMS];
static OldImage g_old[MAX_HISTORY];
static size_t g_old_next;
static time_t g_last_sweep;
static uint64_t g_next_id = FAKE_ID_START;
static uint64_t g_generation = 1;
static char g_last_room[32];
static bool g_enabled;
static IMP g_public_receive, g_private_receive;
static IMP g_private_request, g_private_request_completion;
static char g_wrapped_key;

static void drop_emote(Emote *e) {
    free(e->name);
    free(e->url);
    memset(e, 0, sizeof(*e));
}

static void retire_emote_locked(Emote *e, time_t now) {
    if (e->fake_id && e->url) {
        OldImage *old = &g_old[g_old_next++ % MAX_HISTORY];
        free(old->url);
        old->fake_id = e->fake_id;
        old->url = e->url;
        old->retired_at = now;
        e->url = NULL;
    }
    drop_emote(e);
}

static void reset_room_locked(Room *room, bool retire, time_t now) {
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
        if (old->url && now - old->retired_at > HISTORY_SECONDS) {
            free(old->url);
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

static bool permitted_url(const char *url, unsigned char provider) {
    const char *prefix = provider == 0 ? "https://cdn.7tv.app/emote/" :
                         provider == 1 ? "https://cdn.betterttv.net/emote/" :
                                         "https://cdn.frankerfacez.com/emote/";
    return url && strncmp(url, prefix, strlen(prefix)) == 0 && strlen(url) < 512;
}

/* API strings are copied while the JSON object is alive; only bounded entries
 * are retained. The fixed provider rank makes name collisions deterministic. */
static void add_emote_locked(Room *room, size_t max, const char *name,
                             const char *url, unsigned char provider) {
    if (!permitted_url(url, provider)) return;
    char *word = duplicate(name, 96);
    char *image = duplicate(url, 511);
    if (!word || !image || strchr(word, ' ') || strchr(word, '\t') || strchr(word, '\r') ||
        strchr(word, '\n') || strchr(word, ';')) {
        free(word);
        free(image);
        return;
    }
    Emote *existing = find_word(room, word);
    if (existing) {
        if (provider < existing->provider) {
            retire_emote_locked(existing, time(NULL));
            existing->name = word;
            existing->url = image;
            existing->fake_id = g_next_id++;
            existing->provider = provider;
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
    room->items[insert] = (Emote){word, image, g_next_id++, provider};
    room->size++;
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
        if (!name || !id_text || strlen(id_text) > 96) continue;
        if (provider == 0) {
            id data = dict(emote, "data");
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
        add_emote_locked(room, global ? MAX_GLOBAL : MAX_ROOM, name, url, provider);
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

static void fetch_provider(const char *room_id, uint64_t generation, unsigned char provider) {
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
    id room_string = room_id ? str(room_id) : nil;
    id session = call0((id)objc_getClass("NSURLSession"), "sharedSession");
    id endpoint = call1((id)objc_getClass("NSURL"), "URLWithString:", str(url));
    if (!session || !endpoint) return;
    id task = ((id (*)(id, SEL, id, id))objc_msgSend)(
        session, sel_registerName("dataTaskWithURL:completionHandler:"), endpoint,
        (id)^(id data, id response, id error) {
            id parsed = nil;
            NSInteger status = response ? ((NSInteger (*)(id, SEL))objc_msgSend)(
                response, sel_registerName("statusCode")) : 0;
            bool absent = !error && status == 404;
            bool okay = !error && data &&
                ((NSUInteger (*)(id, SEL))objc_msgSend)(data, sel_registerName("length")) <= MAX_API_BYTES &&
                status == 200;
            if (okay) {
                parsed = ((id (*)(id, SEL, id, NSUInteger, id *))objc_msgSend)(
                    (id)objc_getClass("NSJSONSerialization"), sel_registerName("JSONObjectWithData:options:error:"),
                    data, (NSUInteger)0, NULL);
                okay = parsed != nil;
            }
            pthread_mutex_lock(&g_emote_lock);
            const char *room_copy = text(room_string);
            Room *room = room_copy ? NULL : &g_global;
            if (room_copy) {
                for (size_t i = 0; i < MAX_ROOMS; i++)
                    if (g_rooms[i].occupied && strcmp(g_rooms[i].id, room_copy) == 0) {
                        room = &g_rooms[i];
                        break;
                    }
            }
            if (room && room->generation == generation) {
                room->pending[provider] = false;
                room->loaded[provider] = absent ||
                    (okay && parse_provider_locked(room, parsed, provider, !room_copy));
                if (room->loaded[provider]) room->failures[provider] = 0;
                else if (room->failures[provider] < 5) room->failures[provider]++;
            }
            pthread_mutex_unlock(&g_emote_lock);
        });
    if (task) call0(task, "resume");
    else {
        pthread_mutex_lock(&g_emote_lock);
        const char *room_copy = text(room_string);
        Room *room = room_copy ? NULL : &g_global;
        if (room_copy) for (size_t i = 0; i < MAX_ROOMS; i++)
            if (g_rooms[i].occupied && strcmp(g_rooms[i].id, room_copy) == 0) room = &g_rooms[i];
        if (room && room->generation == generation) {
            room->pending[provider] = false;
            if (room->failures[provider] < 5) room->failures[provider]++;
        }
        pthread_mutex_unlock(&g_emote_lock);
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

/* Returns a replacement for one IRC line, or NULL if it is unchanged. */
static char *rewrite_line(const char *line, size_t length) {
    if (length < 3 || line[0] != '@') return NULL;
    const char *end = line + length;
    const char *tags_end = strstr(line, " :");
    if (!tags_end || tags_end >= end) return NULL;
    char room_id[32];
    if (!tag_value(line + 1, tags_end, "room-id", room_id, sizeof(room_id)) ||
        !valid_room(room_id)) return NULL;
    const char *privmsg = strstr(tags_end, " PRIVMSG #");
    bool message = privmsg && privmsg < end;
    if (!message && !strstr(tags_end, " ROOMSTATE #")) return NULL;
    pthread_mutex_lock(&g_emote_lock);
    snprintf(g_last_room, sizeof(g_last_room), "%s", room_id);
    pthread_mutex_unlock(&g_emote_lock);
    ensure_loaded(NULL, false);
    ensure_loaded(room_id, false);
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
        if (bytes && bytes <= 96 && span && span <= 96) {
            char candidate[97];
            memcpy(candidate, word, bytes);
            candidate[bytes] = 0;
            Emote *emote = room ? find_word(room, candidate) : NULL;
            if (!emote) emote = find_word(&g_global, candidate);
            if (emote && !overlaps_native(line + 1, tags_end, position, position + span - 1)) {
                int n = snprintf(additions + written, sizeof(additions) - written,
                                 "%s%llu:%zu-%zu", written ? "/" : "",
                                 (unsigned long long)emote->fake_id, position, position + span - 1);
                if (n > 0 && (size_t)n < sizeof(additions) - written) written += (size_t)n;
                else break;
            }
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
    if (!message || ((NSInteger (*)(id, SEL))objc_msgSend)(message, sel_registerName("type")) != 1)
        return nil;
    const char *input = text(call0(message, "string"));
    if (!input) return nil;
    size_t length = strnlen(input, MAX_FRAME + 1);
    if (length > MAX_FRAME || input[0] != '@') return nil;
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

static char *url_for_id_locked(uint64_t id, time_t now) {
    for (size_t i = 0; i < g_global.size; i++)
        if (g_global.items[i].fake_id == id) return strdup(g_global.items[i].url);
    for (size_t r = 0; r < MAX_ROOMS; r++)
        for (size_t i = 0; i < g_rooms[r].size; i++)
            if (g_rooms[r].items[i].fake_id == id) return strdup(g_rooms[r].items[i].url);
    for (size_t i = 0; i < MAX_HISTORY; i++)
        if (g_old[i].fake_id == id && g_old[i].url &&
            now - g_old[i].retired_at < HISTORY_SECONDS) return strdup(g_old[i].url);
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
    if (!image) return nil;
    id destination = call1((id)objc_getClass("NSURL"), "URLWithString:", str(image));
    free(image);
    if (!destination) return nil;
    id mutable = call0(request, "mutableCopy");
    ((void (*)(id, SEL, id))objc_msgSend)(mutable, sel_registerName("setURL:"), destination);
    return mutable;
}

static id private_task(id self, SEL command, id request) {
    id replacement = tas_emotes_rewrite_request_copy(request);
    id result = ((id (*)(id, SEL, id))g_private_request)(self, command, replacement ?: request);
    if (replacement) objc_release(replacement);
    return result;
}
static id private_task_completion(id self, SEL command, id request, id completion) {
    id replacement = tas_emotes_rewrite_request_copy(request);
    id result = ((id (*)(id, SEL, id, id))g_private_request_completion)(
        self, command, replacement ?: request, completion);
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
        free(g_old[i].url);
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
        hook_own_method(objc_getClass("NSURLSessionWebSocketTask"),
                        "receiveMessageWithCompletionHandler:", (IMP)public_receive, &g_public_receive);
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
