#include "TASInvestigation.h"
#include "TASInvestigationRegistry.h"
#include <limits.h>
#include <pthread.h>
#include <string.h>

const uint32_t tas_inv_ceilings[TAS_INV_LIMITS] = {2, 128, 12,  2000, 10000, 2000,  8,
                                                   4, 4,   256, 64,   256,   65536, 65536};
static const char *const limit_names[] = {
    "max_lists",         "max_entries",         "max_cells",
    "snapshot_ms",       "js_work_us",          "callback_work_us",
    "events_per_second", "priority_per_second", "bridge_batches_per_second",
    "ordinary_events",   "priority_events",     "identity_aliases",
    "alias_bytes",       "report_bytes"};
static const char *const family_names[] = {
    "translation", "emission",      "local_echo",    "reconciliation", "store",
    "irc_reward",  "pubsub_reward", "reward_render", "list",           "layout"};
static const TASInvCapability capabilities[] = {
    {"rn.chat.snapshot", 1, TAS_INV_SNAPSHOT, 0, true},
    {"rn.chat.lifecycle", 1, TAS_INV_LIFECYCLE, 0x117, true},
    {"rn.rewards.observation", 1, TAS_INV_REWARDS, 0x60, true}};
const TASInvCapability *tas_inv_capability(unsigned i) {
    return i < TAS_INV_CAPABILITIES ? &capabilities[i] : NULL;
}

/* Bounded, allocation-free JSON reader. Every string is decoded before key
 * comparison, so escaped duplicate keys cannot bypass duplicate rejection.
 * This schema permits integer numbers only. It deliberately rejects fractional
 * and exponent spellings rather than accepting lossy conversions. */
enum { J_OBJECT = 1, J_ARRAY, J_STRING, J_NUMBER, J_TRUE, J_FALSE, J_NULL };
typedef struct {
    uint32_t kind, end, count, number;
    char text[257];
} Node;
typedef struct {
    const unsigned char *s;
    size_t n, p;
    unsigned used;
    Node nodes[256];
} JSON;
static void whitespace(JSON *j) {
    while (j->p < j->n &&
           (j->s[j->p] == ' ' || j->s[j->p] == '\n' || j->s[j->p] == '\r' || j->s[j->p] == '\t'))
        j->p++;
}
static bool utf8(const unsigned char *s, size_t n) {
    for (size_t i = 0; i < n;) {
        unsigned c = s[i++], need = 0;
        uint32_t v = 0, min = 0;
        if (c < 128)
            continue;
        if (c >= 0xc2 && c <= 0xdf) {
            need = 1;
            v = c & 31;
            min = 128;
        } else if (c >= 0xe0 && c <= 0xef) {
            need = 2;
            v = c & 15;
            min = 2048;
        } else if (c >= 0xf0 && c <= 0xf4) {
            need = 3;
            v = c & 7;
            min = 65536;
        } else
            return false;
        if (need > n - i)
            return false;
        for (unsigned k = 0; k < need; k++) {
            c = s[i++];
            if ((c & 0xc0) != 0x80)
                return false;
            v = (v << 6) | (c & 63);
        }
        if (v < min || v > 0x10ffff || (v >= 0xd800 && v <= 0xdfff))
            return false;
    }
    return true;
}
static int hex(unsigned c) {
    return c >= '0' && c <= '9'   ? (int)c - '0'
           : c >= 'a' && c <= 'f' ? (int)c - 'a' + 10
           : c >= 'A' && c <= 'F' ? (int)c - 'A' + 10
                                  : -1;
}
static bool u16(JSON *j, uint32_t *v) {
    *v = 0;
    if (j->n - j->p < 4)
        return false;
    for (unsigned k = 0; k < 4; k++) {
        int x = hex(j->s[j->p++]);
        if (x < 0)
            return false;
        *v = (*v << 4) | (unsigned)x;
    }
    return true;
}
static bool string(JSON *j, char out[257]) {
    if (j->p >= j->n || j->s[j->p++] != '"')
        return false;
    size_t used = 0;
    while (j->p < j->n) {
        unsigned c = j->s[j->p++];
        if (c == '"') {
            out[used] = 0;
            return true;
        }
        if (c < 32)
            return false;
        if (c == '\\') {
            if (j->p >= j->n)
                return false;
            c = j->s[j->p++];
            if (c == 'u') {
                uint32_t v = 0;
                if (!u16(j, &v) || v == 0)
                    return false;
                if (v >= 0xd800 && v <= 0xdbff) {
                    uint32_t low = 0;
                    if (j->n - j->p < 2 || j->s[j->p++] != '\\' || j->s[j->p++] != 'u' ||
                        !u16(j, &low) || low < 0xdc00 || low > 0xdfff)
                        return false;
                    v = 0x10000 + ((v - 0xd800) << 10) + (low - 0xdc00);
                } else if (v >= 0xdc00 && v <= 0xdfff)
                    return false;
                unsigned char bytes[4];
                unsigned n = 0;
                if (v < 128)
                    bytes[n++] = (unsigned char)v;
                else if (v < 2048) {
                    bytes[n++] = (unsigned char)(0xc0 | (v >> 6));
                    bytes[n++] = (unsigned char)(0x80 | (v & 63));
                } else if (v < 65536) {
                    bytes[n++] = (unsigned char)(0xe0 | (v >> 12));
                    bytes[n++] = (unsigned char)(0x80 | ((v >> 6) & 63));
                    bytes[n++] = (unsigned char)(0x80 | (v & 63));
                } else {
                    bytes[n++] = (unsigned char)(0xf0 | (v >> 18));
                    bytes[n++] = (unsigned char)(0x80 | ((v >> 12) & 63));
                    bytes[n++] = (unsigned char)(0x80 | ((v >> 6) & 63));
                    bytes[n++] = (unsigned char)(0x80 | (v & 63));
                }
                if (n > 256 - used)
                    return false;
                memcpy(out + used, bytes, n);
                used += n;
                continue;
            }
            if (c == 'b')
                c = '\b';
            else if (c == 'f')
                c = '\f';
            else if (c == 'n')
                c = '\n';
            else if (c == 'r')
                c = '\r';
            else if (c == 't')
                c = '\t';
            else if (c != '"' && c != '\\' && c != '/')
                return false;
        }
        if (!c || used >= 256)
            return false;
        out[used++] = (char)c;
    }
    return false;
}
static bool value(JSON *j, unsigned depth, unsigned *index) {
    if (depth > 8 || j->used >= 256)
        return false;
    whitespace(j);
    if (j->p >= j->n)
        return false;
    unsigned at = j->used++;
    Node *v = &j->nodes[at];
    *index = at;
    unsigned c = j->s[j->p];
    if (c == '{' || c == '[') {
        v->kind = c == '{' ? J_OBJECT : J_ARRAY;
        j->p++;
        whitespace(j);
        unsigned close = c == '{' ? '}' : ']';
        if (j->p < j->n && j->s[j->p] == close)
            j->p++;
        else
            for (;;) {
                unsigned child = 0;
                if (v->count >= 64)
                    return false;
                if (v->kind == J_OBJECT) {
                    whitespace(j);
                    if (j->used >= 256)
                        return false;
                    unsigned key = j->used++;
                    Node *k = &j->nodes[key];
                    k->kind = J_STRING;
                    if (!string(j, k->text) || strlen(k->text) > 63)
                        return false;
                    k->end = j->used;
                    for (unsigned old = at + 1; old < key; old = j->nodes[j->nodes[old].end].end)
                        if (!strcmp(j->nodes[old].text, k->text))
                            return false;
                    whitespace(j);
                    if (j->p >= j->n || j->s[j->p++] != ':')
                        return false;
                    if (!value(j, depth + 1, &child))
                        return false;
                    v->count += 2;
                } else {
                    if (!value(j, depth + 1, &child))
                        return false;
                    v->count++;
                }
                whitespace(j);
                if (j->p >= j->n)
                    return false;
                c = j->s[j->p++];
                if (c == close)
                    break;
                if (c != ',')
                    return false;
            }
    } else if (c == '"') {
        v->kind = J_STRING;
        if (!string(j, v->text))
            return false;
    } else if (c >= '0' && c <= '9') {
        v->kind = J_NUMBER;
        if (c == '0' && j->p + 1 < j->n && j->s[j->p + 1] >= '0' && j->s[j->p + 1] <= '9')
            return false;
        while (j->p < j->n && (c = j->s[j->p]) >= '0' && c <= '9') {
            if (v->number > (UINT32_MAX - (c - '0')) / 10)
                return false;
            v->number = v->number * 10 + c - '0';
            j->p++;
        }
    } else {
        const char *word = c == 't' ? "true" : c == 'f' ? "false" : c == 'n' ? "null" : NULL;
        if (!word)
            return false;
        size_t n = strlen(word);
        if (n > j->n - j->p || memcmp(j->s + j->p, word, n))
            return false;
        j->p += n;
        v->kind = c == 't' ? J_TRUE : c == 'f' ? J_FALSE : J_NULL;
    }
    v->end = j->used;
    return true;
}
static const Node *get(const JSON *j, const Node *o, const char *key) {
    if (!o || o->kind != J_OBJECT)
        return NULL;
    for (unsigned i = (unsigned)(o - j->nodes) + 1; i < o->end; i = j->nodes[j->nodes[i].end].end)
        if (!strcmp(j->nodes[i].text, key))
            return &j->nodes[j->nodes[i].end];
    return NULL;
}
static bool fields(const JSON *j, const Node *o, const char *const *names, unsigned count) {
    if (!o || o->kind != J_OBJECT || o->count != count * 2)
        return false;
    for (unsigned i = 0; i < count; i++)
        if (!get(j, o, names[i]))
            return false;
    return true;
}
#define FIELDS(j, o, ...)                                                                          \
    fields(j, o, (const char *const[]){__VA_ARGS__},                                               \
           sizeof((const char *const[]){__VA_ARGS__}) / sizeof(char *))
static bool eq(const Node *n, const char *s) {
    return n && n->kind == J_STRING && !strcmp(n->text, s);
}
static bool number(const Node *n, uint32_t min, uint32_t max) {
    return n && n->kind == J_NUMBER && n->number >= min && n->number <= max;
}
static bool only(const JSON *j, const Node *a, const char *s) {
    return a && a->kind == J_ARRAY && a->count == 1 &&
           eq(&j->nodes[(unsigned)(a - j->nodes) + 1], s);
}
static bool boolean(const Node *n, bool b) { return n && n->kind == (b ? J_TRUE : J_FALSE); }
bool tas_inv_parse(const void *bytes, size_t length, TASInvManifest *out) {
    if (out)
        memset(out, 0, sizeof(*out));
    if (!out || !bytes || !length || length > TAS_INV_MANIFEST_BYTES || !utf8(bytes, length))
        return false;
    JSON j = {.s = bytes, .n = length};
    unsigned at = 0;
    if (!value(&j, 0, &at))
        return false;
    whitespace(&j);
    if (j.p != length)
        return false;
    const Node *r = &j.nodes[at], *n, *a;
    TASInvManifest m = {0};
    if (!FIELDS(&j, r, "schema_version", "id", "manifest_version", "title", "description",
                "streamside", "capabilities", "donors", "categories", "activation", "snapshot",
                "sampling", "limits", "report"))
        return false;
    if (!number(get(&j, r, "schema_version"), 1, 1) || !eq(get(&j, r, "id"), "rn-chat-gaps") ||
        !number(get(&j, r, "manifest_version"), 1, UINT32_MAX))
        return false;
    m.version = get(&j, r, "manifest_version")->number;
    n = get(&j, r, "title");
    if (!n || n->kind != J_STRING || !n->text[0] || strlen(n->text) > 64)
        return false;
    memcpy(m.title, n->text, strlen(n->text) + 1);
    n = get(&j, r, "description");
    if (!n || n->kind != J_STRING || !n->text[0])
        return false;
    memcpy(m.description, n->text, strlen(n->text) + 1);
    n = get(&j, r, "streamside");
    if (!FIELDS(&j, n, "release_lines", "runtime_abi") ||
        !only(&j, get(&j, n, "release_lines"), "3.1.0") ||
        !number(get(&j, n, "runtime_abi"), 1, TAS_INV_ABI))
        return false;
    a = get(&j, r, "capabilities");
    if (!a || a->kind != J_ARRAY || !a->count || a->count > TAS_INV_CAPABILITIES)
        return false;
    for (unsigned i = (unsigned)(a - j.nodes) + 1; i < a->end; i = j.nodes[i].end) {
        n = &j.nodes[i];
        if (!FIELDS(&j, n, "id", "version") || !number(get(&j, n, "version"), 1, 1))
            return false;
        unsigned found = 0;
        for (unsigned k = 0; k < TAS_INV_CAPABILITIES; k++)
            if (eq(get(&j, n, "id"), capabilities[k].id))
                found = capabilities[k].mask;
        if (!found || (m.capabilities & found))
            return false;
        m.capabilities |= found;
    }
    if (!(m.capabilities & TAS_INV_SNAPSHOT) || !(m.capabilities & TAS_INV_LIFECYCLE))
        return false;
    a = get(&j, r, "donors");
    if (!a || a->kind != J_ARRAY || a->count != 1)
        return false;
    n = &j.nodes[(unsigned)(a - j.nodes) + 1];
    if (!FIELDS(&j, n, "version", "bundle_build", "native_profile", "hermes_version",
                "original_hbc_sha256") ||
        !eq(get(&j, n, "version"), "31.6.2") ||
        !eq(get(&j, n, "bundle_build"), "262872150334984303") ||
        !eq(get(&j, n, "native_profile"), "twitch-ios-31.6.2-arm64-v1") ||
        !number(get(&j, n, "hermes_version"), 98, 98) ||
        !eq(get(&j, n, "original_hbc_sha256"),
            "20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458"))
        return false;
    if (!only(&j, get(&j, r, "categories"), "chat"))
        return false;
    n = get(&j, r, "activation");
    if (!FIELDS(&j, n, "requires_restart", "after_capture") ||
        !boolean(get(&j, n, "requires_restart"), false))
        return false;
    a = get(&j, n, "after_capture");
    if (!eq(a, "armed") && !eq(a, "dormant"))
        return false;
    m.return_armed = eq(a, "armed");
    n = get(&j, r, "snapshot");
    if (!FIELDS(&j, n, "supported", "profile") || !boolean(get(&j, n, "supported"), true) ||
        !eq(get(&j, n, "profile"), "rn-chat-current-v3"))
        return false;
    n = get(&j, r, "sampling");
    if (!FIELDS(&j, n, "mode", "periodic_hz", "events") ||
        !eq(get(&j, n, "mode"), "event_driven") || !number(get(&j, n, "periodic_hz"), 0, 0))
        return false;
    a = get(&j, n, "events");
    if (!a || a->kind != J_ARRAY || !a->count || a->count > TAS_INV_EVENT_FAMILIES)
        return false;
    for (unsigned i = (unsigned)(a - j.nodes) + 1; i < a->end; i = j.nodes[i].end) {
        uint32_t bit = 0;
        for (unsigned k = 0; k < TAS_INV_EVENT_FAMILIES; k++)
            if (eq(&j.nodes[i], family_names[k]))
                bit = 1U << k;
        if (!bit || (m.events & bit))
            return false;
        m.events |= bit;
    }
    uint32_t allowed = 0;
    for (unsigned k = 0; k < TAS_INV_CAPABILITIES; k++)
        if (m.capabilities & capabilities[k].mask)
            allowed |= capabilities[k].events;
    if (m.events & ~allowed)
        return false;
    n = get(&j, r, "limits");
    if (!fields(&j, n, limit_names, TAS_INV_LIMITS))
        return false;
    for (unsigned k = 0; k < TAS_INV_LIMITS; k++) {
        a = get(&j, n, limit_names[k]);
        if (!number(a, 1, tas_inv_ceilings[k]))
            return false;
        m.limits[k] = a->number;
    }
    n = get(&j, r, "report");
    if (!FIELDS(&j, n, "profile", "max_bytes") || !eq(get(&j, n, "profile"), "numeric-chat-v3") ||
        !number(get(&j, n, "max_bytes"), 1, m.limits[TAS_INV_REPORT_BYTES]))
        return false;
    m.limits[TAS_INV_REPORT_BYTES] = get(&j, n, "max_bytes")->number;
    *out = m;
    return true;
}

static bool verified(const void *data, size_t n, TASInvSHA256 sha) {
    unsigned char hash[32];
    return data && n == sizeof(tas_inv_manifest_bytes) && sha && sha(data, n, hash) &&
           !memcmp(hash, tas_inv_manifest_sha256, 32);
}
bool tas_inv_registry(const void *cache, size_t n, TASInvSHA256 sha, TASInvManifest *out,
                      unsigned *source) {
    if (out)
        memset(out, 0, sizeof(*out));
    if (source)
        *source = cache ? TAS_INV_CACHE_REJECTED : TAS_INV_BUNDLED;
    if (cache && verified(cache, n, sha) && tas_inv_parse(cache, n, out)) {
        if (source)
            *source = TAS_INV_PINNED_CACHE;
        return true;
    }
    return verified(tas_inv_manifest_bytes, sizeof(tas_inv_manifest_bytes), sha) &&
           tas_inv_parse(tas_inv_manifest_bytes, sizeof(tas_inv_manifest_bytes), out);
}
static bool same(const char *a, const char *b) { return a && b && !strcmp(a, b); }
bool tas_inv_donor_matches(const TASInvDonor *d) {
    return d && same(d->version, "31.6.2") && same(d->build, "262872150334984303") &&
           same(d->main_uuid, "34613ae5d1e03658876de5e4d1cec6a6") &&
           same(d->main_text_sha256,
                "890c6daabeeeb69be3308337ef61d63deba489e396824d4774c1a8ebd84576f5") &&
           same(d->hermes_uuid, "be274a2347cc3f5a9e988474553df5a8") &&
           same(d->hermes_text_sha256,
                "9f5bc675604dfc430ef729bf1b875e5bdf6a9f327576b63987eca424d8cce02a") &&
           same(d->hbc_sha256,
                "20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458") &&
           d->hbc_version == 98 && d->hbc_bytes == 28682408;
}

static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static TASInvManifest config;
static TASInvStatus status = {
    .state = TAS_INV_UNSUPPORTED, .reason = TAS_INV_NO_RUNTIME, .generation = 1};
static bool initialized;
static uint32_t vm;
static void invalidate_locked(unsigned reason) {
    status.state = TAS_INV_UNSUPPORTED;
    status.reason = reason;
    status.pending = 0;
    status.ready_capabilities = 0;
    status.deadline_ms = 0;
    if (status.generation < UINT32_MAX)
        status.generation++;
}
bool tas_inv_initialize(TASInvSHA256 sha) {
    pthread_mutex_lock(&lock);
    if (!initialized) {
        unsigned source = 0;
        initialized = tas_inv_registry(NULL, 0, sha, &config, &source);
        status.registry_source = source;
        if (!initialized)
            status.reason = TAS_INV_BAD_INTEGRITY;
    }
    bool ok = initialized;
    pthread_mutex_unlock(&lock);
    return ok;
}
bool tas_inv_admit(const TASInvDonor *d, uint32_t ready, uint32_t generation) {
    pthread_mutex_lock(&lock);
    invalidate_locked(TAS_INV_NO_RUNTIME);
    vm = 0;
    bool valid = tas_inv_donor_matches(d);
    bool ok = initialized && valid && generation &&
              (ready & config.capabilities) == config.capabilities && (ready & ~7U) == 0 &&
              status.generation < UINT32_MAX;
    if (ok) {
        vm = generation;
        status.ready_capabilities = ready;
        status.state = TAS_INV_DORMANT;
        status.reason = TAS_INV_OK;
    } else
        status.reason = valid ? TAS_INV_NO_RUNTIME : TAS_INV_BAD_DONOR;
    pthread_mutex_unlock(&lock);
    return ok;
}
bool tas_inv_begin(unsigned operation, uint64_t now, TASInvCommand *out) {
    if (out)
        memset(out, 0, sizeof(*out));
    if (!out)
        return false;
    pthread_mutex_lock(&lock);
    bool ok = false;
    if (!initialized || !vm || status.state == TAS_INV_UNSUPPORTED) {
        status.reason = TAS_INV_NO_RUNTIME;
        goto done;
    }
    if ((status.ready_capabilities & config.capabilities) != config.capabilities) {
        status.reason = TAS_INV_NO_RUNTIME;
        goto done;
    }
    if (operation == TAS_INV_STOP) {
        if (status.generation == UINT32_MAX) {
            invalidate_locked(TAS_INV_NO_RUNTIME);
            goto done;
        }
        status.generation++;
        status.pending = 0;
        status.state = TAS_INV_DORMANT;
    } else {
        if (status.pending) {
            status.reason = TAS_INV_BUSY;
            goto done;
        }
        if ((operation == TAS_INV_ARM && status.state != TAS_INV_DORMANT) ||
            (operation == TAS_INV_CAPTURE && status.state != TAS_INV_ARMED) ||
            (operation != TAS_INV_ARM && operation != TAS_INV_CAPTURE)) {
            status.reason = TAS_INV_BAD_STATE;
            goto done;
        }
    }
    if (status.sequence == UINT32_MAX || now > UINT64_MAX - config.limits[TAS_INV_SNAPSHOT_MS]) {
        invalidate_locked(TAS_INV_NO_RUNTIME);
        goto done;
    }
    status.pending = operation;
    status.sequence++;
    status.deadline_ms = now + config.limits[TAS_INV_SNAPSHOT_MS];
    status.reason = TAS_INV_OK;
    if (operation == TAS_INV_CAPTURE)
        status.state = TAS_INV_CAPTURING;
    *out = (TASInvCommand){.operation = operation,
                           .generation = status.generation,
                           .sequence = status.sequence,
                           .manifest = config};
    ok = true;
done:
    pthread_mutex_unlock(&lock);
    return ok;
}
bool tas_inv_ack(uint32_t generation, uint32_t sequence, unsigned operation, bool success) {
    pthread_mutex_lock(&lock);
    bool ok = status.pending && status.pending == operation && status.generation == generation &&
              status.sequence == sequence && vm;
    if (ok) {
        status.pending = 0;
        status.deadline_ms = 0;
        status.reason = success ? TAS_INV_OK : TAS_INV_NO_RUNTIME;
        if (!success) {
            invalidate_locked(TAS_INV_NO_RUNTIME);
            vm = 0;
        } else if (operation == TAS_INV_ARM)
            status.state = TAS_INV_ARMED;
        else if (operation == TAS_INV_CAPTURE)
            status.state = config.return_armed ? TAS_INV_ARMED : TAS_INV_DORMANT;
        else
            status.state = TAS_INV_DORMANT;
    }
    pthread_mutex_unlock(&lock);
    return ok;
}
bool tas_inv_expire(uint64_t now) {
    pthread_mutex_lock(&lock);
    bool expired = status.pending && now >= status.deadline_ms;
    if (expired) {
        invalidate_locked(TAS_INV_TIMEOUT);
        vm = 0;
    }
    pthread_mutex_unlock(&lock);
    return expired;
}
void tas_inv_invalidate(unsigned reason) {
    pthread_mutex_lock(&lock);
    invalidate_locked(reason);
    vm = 0;
    pthread_mutex_unlock(&lock);
}
TASInvStatus tas_inv_status(void) {
    pthread_mutex_lock(&lock);
    TASInvStatus s = status;
    pthread_mutex_unlock(&lock);
    return s;
}
const char *tas_inv_state_name(unsigned i) {
    static const char *const names[] = {"Unsupported", "Dormant", "Armed", "Capturing"};
    return i < 4 ? names[i] : "Unsupported";
}
const char *tas_inv_reason_name(unsigned i) {
    static const char *const names[] = {
        "Available",           "Manifest rejected", "Integrity rejected", "Unsupported donor",
        "Runtime unavailable", "Command pending",   "Invalid state",      "Command timed out"};
    return i < 8 ? names[i] : "Unavailable";
}
