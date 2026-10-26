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
static TASInvReportMetadata prepared_metadata, frozen_metadata;
static uint32_t prepared_generation, prepared_sequence, stop_reason;
static uint64_t first_received_ms;
typedef struct {
    int32_t frozen[ROWS][FIELDS];
    uint32_t count, generation, sequence, wire, stop_reason;
    uint64_t first_received_ms, last_received_ms;
    bool complete, interrupted;
    TASInvReportMetadata metadata;
} ReportCopy;
static ReportCopy export_copy;
static bool export_busy, export_cancelled;
void tas_inv_report_prepare(uint32_t g, uint32_t s, const TASInvReportMetadata *m) {
    pthread_mutex_lock(&lock);
    prepared_generation = g;
    prepared_sequence = s;
    prepared_metadata = m ? *m : (TASInvReportMetadata){0};
    pthread_mutex_unlock(&lock);
}
void tas_inv_report_stop(unsigned reason) {
    pthread_mutex_lock(&lock);
    if (count && !complete) {
        interrupted = true;
        stop_reason = reason;
    }
    pthread_mutex_unlock(&lock);
}
bool tas_inv_report_export_begin(void) {
    if (__atomic_exchange_n(&export_busy, true, __ATOMIC_ACQ_REL))
        return false;
    __atomic_store_n(&export_cancelled, false, __ATOMIC_RELEASE);
    pthread_mutex_lock(&lock);
    bool available = count != 0;
    if (available) {
        export_copy = (ReportCopy){.count = count,
                                   .generation = generation,
                                   .sequence = sequence,
                                   .wire = wire,
                                   .stop_reason = stop_reason,
                                   .first_received_ms = first_received_ms,
                                   .last_received_ms = previous,
                                   .complete = complete,
                                   .interrupted = interrupted,
                                   .metadata = frozen_metadata};
        memcpy(export_copy.frozen, frozen, sizeof(frozen));
    }
    pthread_mutex_unlock(&lock);
    if (!available)
        __atomic_store_n(&export_busy, false, __ATOMIC_RELEASE);
    return available;
}
void tas_inv_report_export_end(void) { __atomic_store_n(&export_busy, false, __ATOMIC_RELEASE); }
void tas_inv_report_export_cancel(void) {
    __atomic_store_n(&export_cancelled, true, __ATOMIC_RELEASE);
}
bool tas_inv_report_export_cancelled(void) {
    return __atomic_load_n(&export_cancelled, __ATOMIC_ACQUIRE);
}
size_t tas_inv_report_owned_bytes(void) {
    return sizeof(frozen) + sizeof(export_copy) + sizeof(prepared_metadata) +
           sizeof(frozen_metadata);
}
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
    if (!symbol(&r, '[') || !integer(&r, &version) || version != 4 || !symbol(&r, ',') ||
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
            if (rows[n][0] < 0 || rows[n][0] > 12 || (rows[n][0] == 0 && (p || n)) ||
                rows[n][1] < 0 || rows[n][2] < 0 || rows[n][2] > 9 || rows[n][3] < 0 ||
                rows[n][4] < 0 || rows[n][5] < 0 || rows[n][5] > 2047)
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
        first_received_ms = now;
        stop_reason = 0;
        frozen_metadata = prepared_generation == g && prepared_sequence == s
                              ? prepared_metadata
                              : (TASInvReportMetadata){0};
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
size_t tas_inv_report_export_format(char *out, size_t cap) {
    if (!out || cap < 1024 || !__atomic_load_n(&export_busy, __ATOMIC_ACQUIRE))
        return 0;
    if (cap > WIRE)
        cap = WIRE;
    const ReportCopy *report = &export_copy;
    const int32_t(*frozen)[FIELDS] = report->frozen;
    uint32_t count = report->count, generation = report->generation, sequence = report->sequence,
             wire = report->wire;
    bool complete = report->complete, interrupted = report->interrupted;
    size_t used = 0, limit = cap - 128;
#define ADD(...)                                                                                   \
    do {                                                                                           \
        if (__atomic_load_n(&export_cancelled, __ATOMIC_ACQUIRE)) {                                \
            out[0] = 0;                                                                            \
            used = 0;                                                                              \
            goto done;                                                                             \
        }                                                                                          \
        int z = snprintf(out + used, limit - used, __VA_ARGS__);                                   \
        if (z < 0 || (size_t)z >= limit - used) {                                                  \
            int tail = snprintf(out + used, cap - used,                                            \
                                "\nEXPORT_TRUNCATED: text limit reached; retained numeric "        \
                                "capture is unchanged.\n");                                        \
            if (tail > 0 && (size_t)tail < cap - used)                                             \
                used += (size_t)tail;                                                              \
            goto done;                                                                             \
        }                                                                                          \
        used += (size_t)z;                                                                         \
    } while (0)
    ADD("Streamside 3.1.0-build.25 development / numeric-chat-v4\nDonor Twitch 31.6.2 "
        "(262872150334984303), HBC98, runtime ABI1\nManifest SHA256: %s\nCapture "
        "generation=%u sequence=%u rows=%u wire_bytes=%u complete=%u interrupted=%u\n",
        report->metadata.available ? report->metadata.manifest_sha256 : "unavailable", generation,
        sequence, count, wire, complete, interrupted);
    const TASInvReportMetadata *m = &report->metadata;
    if (m->available) {
        ADD("Configuration id=rn-chat-gaps revision=%u source=%s schema=1 "
            "snapshot=rn-chat-current-v4 "
            "report=numeric-chat-v4 runtime-ABI=1\n",
            m->manifest_version,
            m->registry_source == TAS_INV_BUNDLED        ? "bundled-pinned"
            : m->registry_source == TAS_INV_PINNED_CACHE ? "identical-pinned-cache"
                                                         : "bundled-after-cache-rejection");
        ADD("Compiled capabilities: rn.chat.snapshot/1 rn.chat.lifecycle/1 "
            "rn.rewards.observation/1; "
            "selected=%u\nNative profile=%.64s main=%.32s/%.64s react=%.32s/%.64s "
            "hermes=%.32s/%.64s\n"
            "Original HBC SHA256=%.64s\nAdmitted patched HBC SHA256=%.64s\n",
            m->capabilities, m->native_profile, m->main_uuid, m->main_text, m->react_uuid,
            m->react_text, m->hermes_uuid, m->hermes_text, m->original_hbc,
            m->patched_hbc[0] ? m->patched_hbc : "unavailable");
        ADD("VM epoch=%u arm generation=%u arm sequence=%u general-policy=%u (independent)\n"
            "Monotonic milliseconds: arm-request=%llu capture-request=%llu first-packet=%llu "
            "last-packet=%llu; "
            "native stop-reason=%u. These are request/receipt times, not an atomic JS/native "
            "observation.\n"
            "Selected limits (descriptor order):",
            m->vm_epoch, m->arm_generation, m->arm_sequence, m->general_policy,
            (unsigned long long)m->arm_requested_ms, (unsigned long long)m->capture_requested_ms,
            (unsigned long long)report->first_received_ms,
            (unsigned long long)report->last_received_ms, report->stop_reason);
        for (unsigned i = 0; i < TAS_INV_LIMITS; i++)
            ADD("%s%u", i ? "," : " ", m->limits[i]);
        ADD("\nLimit order: "
            "lists,entries,cells,snapshot_ms,js_work_us,callback_work_us,ordinary_rate,"
            "priority_rate,bridge_rate,ordinary_records,priority_records,aliases,alias_bytes,"
            "report_bytes\n");
    } else
        ADD("Capture provenance unavailable (not prepared by admitted host).\n");
    ADD("No contents or raw identities. Labels are ephemeral per arm. Missing observations do not "
        "prove dropped messages.\nKinds: 0 frozen header; 1 ordinary; 2 priority; 3 store; 4 list; "
        "5 coverage; 6 snapshot status; 7 viewport; 8 store member; 9 list member; 10 range "
        "coverage; 11 store traversal; 12 frozen retention loss.\nColumns: "
        "kind,elapsed_ms,family,scope,label,flags,a,b,c. Numeric payloads are bounded signed "
        "integers. Families: 0 translation,1 emission,2 "
        "local_echo,3 reconciliation,4 store,5 IRC_reward,6 reward_store_route,7 reward_render,8 "
        "list,9 "
        "layout.\nUnobserved: per-message filtering/deduplication, server acknowledgments, "
        "confirmed nonce reconciliation, reward renderer/catalog, native row geometry and Fabric "
        "content presentation. "
        "Estimated row sizes unavailable; direct store reward observations do not independently "
        "establish PubSub provenance. Non-atomic JS snapshot; viewport values are donor state. "
        "Coverage flags record installed families during the arm interval; header a/b/c are "
        "ordinary admission skips/priority admission skips/alias evictions. Snapshot flags: 1 store unavailable,2 list "
        "unavailable,4 work budget,8 changed,16 transfer truncated,32 membership sample "
        "truncated.\n"
        "List-member a/b/c: index, measured height in 1/1000 points, position in rounded points. "
        "List flags: 1 unmeasured in current cache,2 measured exactly zero,4 invalid "
        "measurement,1024 measurement "
        "unavailable; "
        "Cache absence does not prove no prior measurement. Heights round to 0.001 points; zero "
        "flag uses the unrounded value. "
        "128 visible,256 margin. Member flags: 8 counterpart present,16 absent after full "
        "comparable scan,"
        "32 membership unknown,64 identity unavailable,512 object-identity only. "
        "Range a/b/c: requested first,last,visible rows sampled; margin is two rows per side. "
        "Range flags: 1 complete including margin,2 partial,4 unavailable,8 margin partial,"
        "16 tail fallback,32 empty list,64 changed,128 budget reached. "
        "Complete range does not imply measured/native pixel geometry. "
        "Normal measured row size cannot prove Fabric text displayed content.\n"
        "Traversal a/b/c: store entries read, lowest read index, highest read index; newest first. "
        "Traversal flags: 1 store available,2 newest entry read,4 all store slots read,8 time "
        "budget,"
        "16 entry limit,32 read failure,64 changed,128 empty store,256 alias continuity limited,"
        "512 comparisons incomplete. Unread entries and unmatched labels remain unknown.\n");
    ADD("Retention kind 12 a/b: ordinary/priority overwrites; separate from header admission "
        "skips. "
        "Saturation flags: 1 ordinary,2 priority,4 admission,8 aliases,16 errors,32 elapsed_ms,64 "
        "labels. "
        "Coverage mask records adapters installed during the arm interval, not uninterrupted "
        "per-scope coverage.\n");
    for (unsigned i = 0; i < count; i++)
        ADD("%d,%d,%d,%d,%d,%d,%d,%d,%d\n", frozen[i][0], frozen[i][1], frozen[i][2], frozen[i][3],
            frozen[i][4], frozen[i][5], frozen[i][6], frozen[i][7], frozen[i][8]);
    /* Export-time derivation only: never spends the capture's 2 ms allowance.
     * At most eight retained lifecycle labels per scope; no raw identifiers. */
    for (unsigned traversal = 0; traversal < count; traversal++) {
        const int32_t *r = frozen[traversal];
        if (r[0] != 11)
            continue;
        int32_t scope = r[3], total = -1, recent[8] = {0}, times[8] = {0};
        unsigned selected = 0, present = 0, absent = 0, unknown = 0;
        for (unsigned i = 0; i < count; i++) {
            const int32_t *v = frozen[i];
            if (v[3] != scope)
                continue;
            if (v[0] == 3)
                total = v[6];
            if (v[0] == 9 && (v[5] & 128)) {
                if (v[5] & 8)
                    present++;
                else if (v[5] & 16)
                    absent++;
                else
                    unknown++;
            }
            if ((v[0] != 1 && v[0] != 2) || v[2] > 2 || v[4] <= 0)
                continue;
            unsigned slot = 0;
            while (slot < selected && recent[slot] != v[4])
                slot++;
            if (slot < selected) {
                if (v[1] > times[slot])
                    times[slot] = v[1];
                continue;
            }
            if (selected < 8)
                slot = selected++;
            else {
                slot = 0;
                for (unsigned k = 1; k < 8; k++)
                    if (times[k] < times[slot])
                        slot = k;
                if (v[1] < times[slot])
                    continue;
            }
            recent[slot] = v[4];
            times[slot] = v[1];
        }
        unsigned store_found = 0, visible_found = 0;
        for (unsigned k = 0; k < selected; k++) {
            bool in_store = false, in_visible = false;
            for (unsigned i = 0; i < count; i++) {
                const int32_t *v = frozen[i];
                if (v[3] != scope || v[4] != recent[k])
                    continue;
                if (v[0] == 8)
                    in_store = true;
                if (v[0] == 9 && (v[5] & 128))
                    in_visible = true;
            }
            store_found += in_store;
            visible_found += in_visible;
        }
        ADD("Store traversal scope=%d available=%u examined=%d/%d read_indices=%d..%d "
            "newest_first=1 "
            "newest_entry_read=%u all_slots_read=%u time_limited=%u entry_limited=%u "
            "read_failure=%u comparisons_incomplete=%u changed=%u empty=%u aliases_limited=%u\n",
            scope, (unsigned)!!(r[5] & 1), r[6], total, r[8], r[7], (unsigned)!!(r[5] & 2),
            (unsigned)!!(r[5] & 4), (unsigned)!!(r[5] & 8), (unsigned)!!(r[5] & 16),
            (unsigned)!!(r[5] & 32), (unsigned)!!(r[5] & 512), (unsigned)!!(r[5] & 64),
            (unsigned)!!(r[5] & 128), (unsigned)!!(r[5] & 256));
        ADD("Viewport store membership scope=%d present=%u absent=%u unknown=%u. "
            "Recent retained lifecycle labels selected=%u store_observed=%u "
            "visible_list_observed=%u; "
            "unmatched remains unknown. Summaries use frozen numeric rows at export time.\n",
            scope, present, absent, unknown, selected, store_found, visible_found);
    }

done:
    return used;
#undef ADD
}

size_t tas_inv_report_format(char *out, size_t cap) {
    if (!tas_inv_report_export_begin())
        return 0;
    size_t n = tas_inv_report_export_format(out, cap);
    tas_inv_report_export_end();
    return n;
}
