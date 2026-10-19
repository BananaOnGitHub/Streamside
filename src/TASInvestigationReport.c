#include "TASInvestigationReport.h"
#include "TASInvestigationRegistry.h"
#include <pthread.h>
#include <stdio.h>
#include <string.h>
enum { ROWS = 640, FIELDS = 9, PACKET_ROWS = 65, WIRE = 65536 };
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static int32_t frozen[ROWS][FIELDS];
static uint32_t count, generation, sequence, part, wire;
static uint64_t previous;
static bool final, complete, interrupted;
typedef struct {
    const unsigned char *p, *end;
} Reader;
static void space(Reader *r) {
    while (r->p < r->end && (*r->p == ' ' || *r->p == '\n' || *r->p == '\r' || *r->p == '\t'))
        r->p++;
}
static bool symbol(Reader *r, unsigned char c) {
    space(r);
    if (r->p == r->end || *r->p != c)
        return false;
    r->p++;
    return true;
}
static bool integer(Reader *r, int32_t *out) {
    space(r);
    bool neg = false;
    if (r->p < r->end && *r->p == '-') {
        neg = true;
        r->p++;
    }
    if (r->p == r->end || *r->p < '0' || *r->p > '9')
        return false;
    unsigned n = 0;
    bool zero = *r->p == '0';
    do {
        n = n * 10 + *r->p++ - '0';
        if (n > 10000000)
            return false;
        if (zero && r->p < r->end && *r->p >= '0' && *r->p <= '9')
            return false;
    } while (r->p < r->end && *r->p >= '0' && *r->p <= '9');
    if (neg && n > 1)
        return false;
    *out = neg ? -(int32_t)n : (int32_t)n;
    return true;
}
bool tas_inv_report_accept(uint32_t g, uint32_t s, const void *input, size_t size, uint64_t now) {
    if (!input || !size || size > 8192 || !g || !s)
        return false;
    Reader r = {input, (const unsigned char *)input + size};
    int32_t version, p, f;
    int32_t rows[PACKET_ROWS][FIELDS];
    unsigned n = 0;
    if (!symbol(&r, '[') || !integer(&r, &version) || version != 1 || !symbol(&r, ',') ||
        !integer(&r, &p) || p < 0 || p >= 8 || !symbol(&r, ',') || !integer(&r, &f) || f < 0 ||
        f > 1 || !symbol(&r, ',') || !symbol(&r, '['))
        return false;
    space(&r);
    if (r.p < r.end && *r.p != ']')
        for (;;) {
            if (n == PACKET_ROWS || !symbol(&r, '['))
                return false;
            for (unsigned k = 0; k < FIELDS; k++)
                if ((k && !symbol(&r, ',')) || !integer(&r, &rows[n][k]))
                    return false;
            if (!symbol(&r, ']'))
                return false;
            if (rows[n][0] < 0 || rows[n][0] > 9 || (rows[n][0] == 0 && (p || n)) ||
                rows[n][1] < 0 || rows[n][2] < 0 || rows[n][2] > 9 || rows[n][3] < 0 ||
                rows[n][4] < 0 || rows[n][5] < 0 || rows[n][5] > 1023)
                return false;
            n++;
            space(&r);
            if (r.p == r.end)
                return false;
            if (*r.p != ',')
                break;
            r.p++;
        }
    if (!symbol(&r, ']') || !symbol(&r, ']'))
        return false;
    space(&r);
    if (r.p != r.end || !n || (!p && rows[0][0] != 0))
        return false;
    pthread_mutex_lock(&lock);
    bool ok = false;
    if (!p) {
        if (g == generation && s <= sequence)
            goto done;
        generation = g;
        sequence = s;
        count = part = wire = 0;
        final = complete = interrupted = false;
        previous = 0;
    }
    if (g != generation || s != sequence || (uint32_t)p != part || final || count + n > ROWS ||
        wire + size > WIRE || (part && (now < previous || now - previous < 240)))
        goto done;
    memcpy(frozen[count], rows, n * sizeof(rows[0]));
    count += n;
    wire += (uint32_t)size;
    part++;
    previous = now;
    final = f != 0;
    ok = true;
done:
    pthread_mutex_unlock(&lock);
    return ok;
}
bool tas_inv_report_complete(uint32_t g, uint32_t s) {
    pthread_mutex_lock(&lock);
    bool ok = g == generation && s == sequence && final && count && !interrupted;
    if (ok)
        complete = true;
    pthread_mutex_unlock(&lock);
    return ok;
}
void tas_inv_report_interrupt(void) {
    pthread_mutex_lock(&lock);
    if (count && !complete)
        interrupted = true;
    pthread_mutex_unlock(&lock);
}
bool tas_inv_report_started(uint32_t g, uint32_t s) {
    pthread_mutex_lock(&lock);
    bool begun = count && generation == g && sequence == s;
    pthread_mutex_unlock(&lock);
    return begun;
}
bool tas_inv_report_available(void) {
    pthread_mutex_lock(&lock);
    bool available = count > 0;
    pthread_mutex_unlock(&lock);
    return available;
}
size_t tas_inv_report_format(char *out, size_t cap) {
    if (!out || cap < 1024)
        return 0;
    pthread_mutex_lock(&lock);
    size_t used = 0;
#define ADD(...)                                                                                   \
    do {                                                                                           \
        int z = snprintf(out + used, cap - used, __VA_ARGS__);                                     \
        if (z < 0 || (size_t)z >= cap - used) {                                                    \
            out[0] = 0;                                                                            \
            used = 0;                                                                              \
            goto done;                                                                             \
        }                                                                                          \
        used += (size_t)z;                                                                         \
    } while (0)
    ADD("Streamside 3.1.0-build.19 development / numeric-chat-v1\nDonor Twitch 31.6.2 "
        "(262872150334984303), HBC98, runtime ABI1\nManifest SHA256: %s\nCapture "
        "generation=%u sequence=%u rows=%u wire_bytes=%u complete=%u interrupted=%u\n",
        TAS_INV_MANIFEST_SHA256, generation, sequence, count, wire, complete, interrupted);
    ADD("No contents or raw identities. Labels are ephemeral per arm. Missing observations do not "
        "prove dropped messages.\nKinds: 0 frozen header; 1 ordinary; 2 priority; 3 store; 4 list; "
        "5 coverage; 6 snapshot status; 7 viewport; 8 store member; 9 list member.\nColumns: "
        "kind,elapsed_ms,family,scope,label,flags,a,b,c. Families: 0 translation,1 emission,2 "
        "local_echo,3 reconciliation,4 store,5 IRC_reward,6 reward_store_route,7 reward_render,8 "
        "list,9 "
        "layout.\nUnobserved: per-message filtering/deduplication, server acknowledgments, "
        "confirmed nonce reconciliation, reward renderer/catalog, row layout/native geometry. "
        "Estimated row sizes unavailable; direct store reward observations do not independently "
        "establish PubSub provenance. Non-atomic JS snapshot; viewport values are donor state. "
        "Coverage flags are the actually installed family mask; header a/b/c are ordinary "
        "drops/priority drops/alias evictions. Snapshot flags: 1 store unavailable,2 list "
        "unavailable,4 work budget,8 changed,16 transfer truncated,32 membership sample "
        "truncated.\n");
    for (unsigned i = 0; i < count; i++)
        ADD("%d,%d,%d,%d,%d,%d,%d,%d,%d\n", frozen[i][0], frozen[i][1], frozen[i][2], frozen[i][3],
            frozen[i][4], frozen[i][5], frozen[i][6], frozen[i][7], frozen[i][8]);
done:
    pthread_mutex_unlock(&lock);
    return used;
#undef ADD
}
