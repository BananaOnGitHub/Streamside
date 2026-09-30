#ifndef TAS_EMOTE_FETCH_H
#define TAS_EMOTE_FETCH_H

#include <stdbool.h>
#include <stddef.h>

/* Real 7TV channel sets can exceed 5 MiB and 2,000 entries. Keep both
 * response parsing and the retained registry bounded without discarding them. */
#define TAS_EMOTE_MAX_API_BYTES (8 * 1024 * 1024)
#define TAS_EMOTE_MAX_ROOM 4000

typedef enum {
    TAS_FETCH_READY, TAS_FETCH_ABSENT, TAS_FETCH_HTTP, TAS_FETCH_TRANSPORT,
    TAS_FETCH_EMPTY, TAS_FETCH_OVERSIZED, TAS_FETCH_JSON, TAS_FETCH_SCHEMA,
    TAS_FETCH_UNAVAILABLE
} TASEmoteFetchResult;

static inline TASEmoteFetchResult tas_emote_fetch_result(long status, size_t bytes,
                                                        bool transport_error, bool global) {
    if (transport_error) return TAS_FETCH_TRANSPORT;
    /* A missing channel is normal; a missing global endpoint must be retried. */
    if (status == 404 && !global) return TAS_FETCH_ABSENT;
    if (status != 200) return TAS_FETCH_HTTP;
    if (!bytes) return TAS_FETCH_EMPTY;
    if (bytes > TAS_EMOTE_MAX_API_BYTES) return TAS_FETCH_OVERSIZED;
    return TAS_FETCH_READY;
}

static inline const char *tas_emote_fetch_result_name(TASEmoteFetchResult result) {
    switch (result) {
        case TAS_FETCH_READY: return "loaded";
        case TAS_FETCH_ABSENT: return "absent";
        case TAS_FETCH_HTTP: return "http";
        case TAS_FETCH_TRANSPORT: return "transport";
        case TAS_FETCH_EMPTY: return "empty";
        case TAS_FETCH_OVERSIZED: return "oversized";
        case TAS_FETCH_JSON: return "json";
        case TAS_FETCH_SCHEMA: return "schema";
        case TAS_FETCH_UNAVAILABLE: return "unavailable";
    }
    return "unknown";
}
#endif
