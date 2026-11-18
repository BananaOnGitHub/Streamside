/* Shared native VAFT solution 24 playlist engine.
 * Extracted without algorithm changes from Streamside.c for both frontends.
 * Requires the transport's fetch_bytes/request_access_token and Foundation
 * value helpers. No constructor, session hooks, auth capture or JS dependencies.
 * Upstream attribution/pin: docs/UPSTREAM.md and docs/licenses/MIT-NOTICES.txt. */
#pragma once
#define TAS_SCHEME "tashttps"
#define TAS_PLAYER_TYPE_COUNT 3
#define TAS_MAX_AD_SEGMENTS 256
#define TAS_MAX_STREAMS 8
#define TAS_MAX_VARIANT_ROUTES 256
#define TAS_RETIRED_ROUTES 64
#define TAS_STREAM_TTL 1800
#define TAS_MANIFEST_CAPACITY 262144
#define TAS_URL_CAPACITY 8192

static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
static const char *g_player_types[TAS_PLAYER_TYPE_COUNT] = {"embed", "popout", "autoplay"};

typedef struct {
    bool active;
    uint64_t generation;
    time_t last_seen;
    time_t master_seen;
    char channel[512];
    char *master_url;
    char *master_manifest;
    char *backup_variant_url;
    char backup_player_type[64];
    time_t backup_created;
    char *backup_masters[TAS_PLAYER_TYPE_COUNT];
    char *backup_master_urls[TAS_PLAYER_TYPE_COUNT];
} TASStreamContext;

typedef struct {
    char url[TAS_URL_CAPACITY];
    size_t stream_index;
    uint64_t generation;
    time_t last_seen;
    time_t registered_at;
} TASVariantRoute;

typedef struct {
    char url[TAS_URL_CAPACITY];
    uint64_t generation;
    time_t retired_at;
    const char *reason;
} TASRetiredRoute;

typedef struct {
    size_t active_streams;
    size_t active_routes;
    bool retired_match;
    const char *retired_reason;
    long long retired_age;
    uint64_t retired_generation;
    long long newest_master_age;
} TASRouteMiss;

typedef struct {
    size_t index;
    uint64_t generation;
    bool valid;
} TASStreamRef;

typedef struct {
    TASStreamRef ref;
    char channel[512];
    char master_url[TAS_URL_CAPACITY];
    char backup_variant_url[TAS_URL_CAPACITY];
    time_t backup_created;
    char *master_manifest;
    long long route_age;
    long long master_age;
} TASStreamSnapshot;

static TASStreamContext g_streams[TAS_MAX_STREAMS];
static TASVariantRoute g_variant_routes[TAS_MAX_VARIANT_ROUTES];
static TASRetiredRoute g_retired_routes[TAS_RETIRED_ROUTES];
static size_t g_next_retired_route;
static uint64_t g_next_stream_generation = 1;

typedef struct {
    char url[4096];
    time_t created;
} TASAdSegment;

static TASAdSegment g_ad_segments[TAS_MAX_AD_SEGMENTS];
static size_t g_next_ad_segment;

static bool fetch_bytes(const char *, id *, id *);
static bool request_access_token(const char *,const char *,char *,size_t,char *,size_t);
static char *absolute_url(const char *,const char *);

static void copy_string(char *destination, size_t capacity, const char *source) {
    if (!destination || capacity == 0) return;
    if (!source) source = "";
    snprintf(destination, capacity, "%s", source);
}

static bool starts_with(const char *value, const char *prefix) {
    return value && prefix && strncmp(value, prefix, strlen(prefix)) == 0;
}

static bool contains(const char *value, const char *needle) {
    return value && needle && strstr(value, needle) != NULL;
}

static void replace_owned_string(char **destination, const char *source) {
    char *replacement = source ? strdup(source) : NULL;
    if (source && !replacement) return;
    free(*destination);
    *destination = replacement;
}

static bool stream_ref_matches_locked(TASStreamRef ref) {
    return ref.valid && ref.index < TAS_MAX_STREAMS &&
           g_streams[ref.index].active &&
           g_streams[ref.index].generation == ref.generation;
}

static void retire_route_locked(TASVariantRoute *route, const char *reason) {
    if (!route->url[0]) return;
    TASRetiredRoute *old = &g_retired_routes[g_next_retired_route++ % TAS_RETIRED_ROUTES];
    copy_string(old->url, sizeof(old->url), route->url);
    old->generation = route->generation;
    old->retired_at = time(NULL);
    old->reason = reason;
    memset(route, 0, sizeof(*route));
}

static size_t active_routes_locked(void) {
    size_t count = 0;
    for (size_t i = 0; i < TAS_MAX_VARIANT_ROUTES; i++) count += g_variant_routes[i].url[0] != '\0';
    return count;
}

static void clear_routes_for_stream_locked(size_t stream_index, const char *reason) {
    for (size_t i = 0; i < TAS_MAX_VARIANT_ROUTES; i++) {
        if (g_variant_routes[i].url[0] && g_variant_routes[i].stream_index == stream_index) {
            retire_route_locked(&g_variant_routes[i], reason);
        }
    }
}

static void clear_active_backup_locked(TASStreamContext *stream) {
    free(stream->backup_variant_url);
    stream->backup_variant_url = NULL;
    stream->backup_player_type[0] = '\0';
    stream->backup_created = 0;
}

static void clear_stream_context_locked(size_t stream_index, const char *reason) {
    TASStreamContext *stream = &g_streams[stream_index];
    clear_routes_for_stream_locked(stream_index, reason);
    free(stream->master_url);
    free(stream->master_manifest);
    free(stream->backup_variant_url);
    for (size_t i = 0; i < TAS_PLAYER_TYPE_COUNT; i++) {
        free(stream->backup_masters[i]);
        free(stream->backup_master_urls[i]);
    }
    memset(stream, 0, sizeof(*stream));
}

static void prune_streams_locked(time_t now) {
    for (size_t i = 0; i < TAS_MAX_STREAMS; i++) {
        if (g_streams[i].active && now - g_streams[i].last_seen > TAS_STREAM_TTL) {
            clear_stream_context_locked(i, "stream_expired");
        }
    }
}

static TASStreamRef update_stream_master_locked(const char *channel, const char *url,
                                                const char *playlist) {
    time_t now = time(NULL);
    prune_streams_locked(now);

    size_t stream_index = TAS_MAX_STREAMS;
    for (size_t i = 0; i < TAS_MAX_STREAMS; i++) {
        if (g_streams[i].active && strcmp(g_streams[i].channel, channel) == 0) {
            stream_index = i;
            break;
        }
    }
    if (stream_index == TAS_MAX_STREAMS) {
        for (size_t i = 0; i < TAS_MAX_STREAMS; i++) {
            if (!g_streams[i].active) {
                stream_index = i;
                break;
            }
        }
    }
    if (stream_index == TAS_MAX_STREAMS) {
        stream_index = 0;
        for (size_t i = 1; i < TAS_MAX_STREAMS; i++) {
            if (g_streams[i].last_seen < g_streams[stream_index].last_seen) stream_index = i;
        }
        clear_stream_context_locked(stream_index, "stream_replaced");
    }

    TASStreamContext *stream = &g_streams[stream_index];
    if (!stream->active) {
        stream->active = true;
        stream->generation = g_next_stream_generation++;
        if (!g_next_stream_generation) g_next_stream_generation = 1;
        copy_string(stream->channel, sizeof(stream->channel), channel);
    }
    replace_owned_string(&stream->master_url, url);
    replace_owned_string(&stream->master_manifest, playlist);
    clear_active_backup_locked(stream);
    stream->last_seen = now;
    stream->master_seen = now;

    TASStreamRef ref = {stream_index, stream->generation, true};
    return ref;
}

static void clear_active_backup(TASStreamRef ref) {
    pthread_mutex_lock(&g_lock);
    if (stream_ref_matches_locked(ref)) clear_active_backup_locked(&g_streams[ref.index]);
    pthread_mutex_unlock(&g_lock);
}

static bool is_twitch_hls_url(const char *url) {
    return url && contains(url, ".m3u8") &&
           (contains(url, "ttvnw.net") || contains(url, "twitch.tv"));
}

static bool is_cached_ad_segment(const char *url) {
    bool found = false;
    time_t now = time(NULL);
    pthread_mutex_lock(&g_lock);
    for (size_t i = 0; i < TAS_MAX_AD_SEGMENTS; i++) {
        if (g_ad_segments[i].created && now - g_ad_segments[i].created > 120) {
            g_ad_segments[i].url[0] = '\0';
            g_ad_segments[i].created = 0;
        }
        if (g_ad_segments[i].url[0] && strcmp(g_ad_segments[i].url, url) == 0) {
            found = true;
        }
    }
    pthread_mutex_unlock(&g_lock);
    return found;
}

static void remember_ad_segment(const char *base_url, const char *segment_url) {
    if (!segment_url || !segment_url[0]) return;
    char cleaned[4096];
    copy_string(cleaned, sizeof(cleaned), segment_url);
    size_t cleaned_length = strlen(cleaned);
    while (cleaned_length && (cleaned[cleaned_length - 1] == '\r' || cleaned[cleaned_length - 1] == '\n')) {
        cleaned[--cleaned_length] = '\0';
    }
    char *absolute = absolute_url(base_url, cleaned);
    if (!absolute || strlen(absolute) >= sizeof(g_ad_segments[0].url)) {
        free(absolute);
        return;
    }
    pthread_mutex_lock(&g_lock);
    size_t index = g_next_ad_segment++ % TAS_MAX_AD_SEGMENTS;
    copy_string(g_ad_segments[index].url, sizeof(g_ad_segments[index].url), absolute);
    g_ad_segments[index].created = time(NULL);
    pthread_mutex_unlock(&g_lock);
    free(absolute);
}

static char *copy_data_text(id data) {
    if (!data) return NULL;
    size_t length = data_length(data);
    char *result = calloc(length + 1, 1);
    if (!result) return NULL;
    memcpy(result, data_bytes(data), length);
    return result;
}

static void append_text(char **buffer, size_t *length, size_t *capacity, const char *text) {
    size_t incoming = strlen(text);
    if (*length + incoming + 1 > *capacity) {
        size_t next = *capacity ? *capacity : 4096;
        while (next < *length + incoming + 1) next *= 2;
        char *grown = realloc(*buffer, next);
        if (!grown) return;
        *buffer = grown;
        *capacity = next;
    }
    memcpy(*buffer + *length, text, incoming);
    *length += incoming;
    (*buffer)[*length] = '\0';
}

static char *absolute_url(const char *base, const char *relative) {
    if (starts_with(relative, "http://") || starts_with(relative, "https://")) return strdup(relative);
    id base_url = nsurl(base);
    id value = msg2((id)objc_getClass("NSURL"), "URLWithString:relativeToURL:", nsstr(relative), base_url);
    return strdup(utf8(msg0(value, "absoluteString")) ?: relative);
}

static char *custom_scheme_url(const char *value) {
    if (starts_with(value, "https://")) {
        size_t length = strlen(value) + strlen(TAS_SCHEME) + 1;
        char *result = malloc(length);
        snprintf(result, length, TAS_SCHEME "://%s", value + strlen("https://"));
        return result;
    }
    return strdup(value);
}

static __attribute__((unused)) char *https_scheme_url(const char *value) {
    if (starts_with(value, TAS_SCHEME "://")) {
        size_t length = strlen(value) + 1;
        char *result = malloc(length);
        snprintf(result, length, "https://%s", value + strlen(TAS_SCHEME "://"));
        return result;
    }
    return strdup(value);
}

static void parse_attribute(const char *line, const char *name, char *output, size_t capacity) {
    output[0] = '\0';
    const char *start = strstr(line, name);
    if (!start) return;
    start += strlen(name);
    if (*start == '"') start++;
    const char *end = start;
    while (*end && *end != ',' && *end != '"' && *end != '\r' && *end != '\n') end++;
    size_t length = (size_t)(end - start);
    if (length >= capacity) length = capacity - 1;
    memcpy(output, start, length);
    output[length] = '\0';
}

static void trim_manifest_line(char *line) {
    size_t length = strlen(line);
    while (length && (line[length - 1] == '\r' || line[length - 1] == '\n')) {
        line[--length] = '\0';
    }
}

static void channel_from_master_url(const char *url, char *output, size_t capacity) {
    output[0] = '\0';
    const char *marker = strstr(url, "/channel/hls/");
    if (!marker) return;
    marker += strlen("/channel/hls/");
    const char *end = strstr(marker, ".m3u8");
    if (!end) return;
    size_t length = (size_t)(end - marker);
    if (length >= capacity) length = capacity - 1;
    memcpy(output, marker, length);
    output[length] = '\0';
}

static void add_variant_route_locked(TASStreamRef ref, const char *url, time_t now) {
    if (!stream_ref_matches_locked(ref) || !url || !url[0] || strlen(url) >= TAS_URL_CAPACITY) return;

    size_t route_index = TAS_MAX_VARIANT_ROUTES;
    for (size_t i = 0; i < TAS_MAX_VARIANT_ROUTES; i++) {
        if (g_variant_routes[i].url[0] && strcmp(g_variant_routes[i].url, url) == 0) {
            route_index = i;
            break;
        }
        if (route_index == TAS_MAX_VARIANT_ROUTES && !g_variant_routes[i].url[0]) route_index = i;
    }
    if (route_index == TAS_MAX_VARIANT_ROUTES) {
        route_index = 0;
        for (size_t i = 1; i < TAS_MAX_VARIANT_ROUTES; i++) {
            if (g_variant_routes[i].last_seen < g_variant_routes[route_index].last_seen) route_index = i;
        }
    }

    TASVariantRoute *route = &g_variant_routes[route_index];
    if (route->url[0] && (strcmp(route->url, url) != 0 || route->generation != ref.generation)) {
        retire_route_locked(route, strcmp(route->url, url) == 0 ? "route_reassigned" : "route_capacity");
    }
    copy_string(route->url, sizeof(route->url), url);
    route->stream_index = ref.index;
    route->generation = ref.generation;
    route->last_seen = now;
    route->registered_at = now;
}

static size_t register_variant_routes_locked(TASStreamRef ref, const char *master_url,
                                              const char *master) {
    if (!stream_ref_matches_locked(ref)) return 0;
    clear_routes_for_stream_locked(ref.index, "master_refresh");

    char *copy = strdup(master);
    if (!copy) return 0;
    time_t now = time(NULL);
    size_t registered = 0;
    char *save = NULL;
    for (char *line = strtok_r(copy, "\n", &save); line; line = strtok_r(NULL, "\n", &save)) {
        trim_manifest_line(line);
        if (line[0] != '#' && contains(line, ".m3u8")) {
            char *absolute = absolute_url(master_url, line);
            add_variant_route_locked(ref, absolute, now);
            registered++;
            free(absolute);
        }
    }
    free(copy);
    return registered;
}

static TASStreamRef stream_for_variant_locked(const char *url, long long *route_age) {
    TASStreamRef invalid = {0, 0, false};
    time_t now = time(NULL);
    for (size_t i = 0; i < TAS_MAX_VARIANT_ROUTES; i++) {
        TASVariantRoute *route = &g_variant_routes[i];
        if (!route->url[0] || strcmp(route->url, url) != 0) continue;
        TASStreamRef ref = {route->stream_index, route->generation, true};
        if (!stream_ref_matches_locked(ref)) {
            retire_route_locked(route, "stale_generation");
            continue;
        }
        *route_age = (long long)(now - route->registered_at);
        route->last_seen = now;
        g_streams[ref.index].last_seen = now;
        return ref;
    }
    return invalid;
}

static void collect_route_miss_locked(const char *url, TASRouteMiss *miss) {
    memset(miss, 0, sizeof(*miss));
    time_t now = time(NULL);
    miss->active_routes = active_routes_locked();
    for (size_t i = 0; i < TAS_MAX_STREAMS; i++) {
        if (!g_streams[i].active) continue;
        miss->active_streams++;
        long long age = (long long)(now - g_streams[i].master_seen);
        if (miss->active_streams == 1 || age < miss->newest_master_age) miss->newest_master_age = age;
    }
    for (size_t i = 0; i < TAS_RETIRED_ROUTES; i++) {
        TASRetiredRoute *old = &g_retired_routes[i];
        if (old->url[0] && strcmp(old->url, url) == 0 &&
            (!miss->retired_match || old->retired_at > now - miss->retired_age)) {
            miss->retired_match = true;
            miss->retired_reason = old->reason;
            miss->retired_age = (long long)(now - old->retired_at);
            miss->retired_generation = old->generation;
        }
    }
}

static bool snapshot_stream_for_variant(const char *url, TASStreamSnapshot *snapshot,
                                         TASRouteMiss *miss) {
    memset(snapshot, 0, sizeof(*snapshot));
    pthread_mutex_lock(&g_lock);
    long long route_age = 0;
    TASStreamRef ref = stream_for_variant_locked(url, &route_age);
    if (!stream_ref_matches_locked(ref)) {
        collect_route_miss_locked(url, miss);
        pthread_mutex_unlock(&g_lock);
        return false;
    }
    TASStreamContext *stream = &g_streams[ref.index];
    snapshot->ref = ref;
    copy_string(snapshot->channel, sizeof(snapshot->channel), stream->channel);
    copy_string(snapshot->master_url, sizeof(snapshot->master_url), stream->master_url);
    copy_string(snapshot->backup_variant_url, sizeof(snapshot->backup_variant_url),
                stream->backup_variant_url);
    snapshot->backup_created = stream->backup_created;
    snapshot->route_age = route_age;
    snapshot->master_age = (long long)(time(NULL) - stream->master_seen);
    snapshot->master_manifest = stream->master_manifest ? strdup(stream->master_manifest) : NULL;
    if (!snapshot->master_manifest) collect_route_miss_locked(url, miss);
    pthread_mutex_unlock(&g_lock);
    return snapshot->master_manifest != NULL;
}

static bool variant_metadata(const char *master, const char *master_url, const char *variant_url,
                             char *resolution, size_t resolution_capacity,
                             char *framerate, size_t framerate_capacity) {
    char *copy = strdup(master);
    char *save = NULL;
    char *previous = NULL;
    bool found = false;
    for (char *line = strtok_r(copy, "\n", &save); line; line = strtok_r(NULL, "\n", &save)) {
        trim_manifest_line(line);
        if (line[0] != '#' && contains(line, ".m3u8")) {
            char *absolute = absolute_url(master_url, line);
            if (strcmp(absolute, variant_url) == 0 && previous && starts_with(previous, "#EXT-X-STREAM-INF")) {
                parse_attribute(previous, "RESOLUTION=", resolution, resolution_capacity);
                parse_attribute(previous, "FRAME-RATE=", framerate, framerate_capacity);
                found = true;
                free(absolute);
                break;
            }
            free(absolute);
        }
        previous = line;
    }
    free(copy);
    return found;
}

static char *variant_for_resolution(const char *master, const char *master_url,
                                    const char *resolution, const char *framerate) {
    char *copy = strdup(master);
    char *save = NULL;
    char *previous = NULL;
    char *closest = NULL;
    long long closest_difference = INT64_MAX;
    char *resolution_match = NULL;
    char *exact = NULL;
    long long target_area = 0;
    if (resolution && resolution[0]) {
        char *separator = strchr(resolution, 'x');
        if (separator) target_area = strtoll(resolution, NULL, 10) * strtoll(separator + 1, NULL, 10);
    }
    for (char *line = strtok_r(copy, "\n", &save); line; line = strtok_r(NULL, "\n", &save)) {
        trim_manifest_line(line);
        if (line[0] != '#' && contains(line, ".m3u8") && previous && starts_with(previous, "#EXT-X-STREAM-INF")) {
            char line_resolution[128];
            char line_framerate[64];
            parse_attribute(previous, "RESOLUTION=", line_resolution, sizeof(line_resolution));
            parse_attribute(previous, "FRAME-RATE=", line_framerate, sizeof(line_framerate));
            char *absolute = absolute_url(master_url, line);
            if (resolution[0] && strcmp(line_resolution, resolution) == 0) {
                if (!resolution_match) resolution_match = strdup(absolute);
                if (!framerate[0] || strcmp(line_framerate, framerate) == 0) {
                    exact = strdup(absolute);
                    free(absolute);
                    break;
                }
            }
            char *separator = strchr(line_resolution, 'x');
            long long area = separator ? strtoll(line_resolution, NULL, 10) * strtoll(separator + 1, NULL, 10) : 0;
            long long difference = target_area && area ? llabs(area - target_area) : 0;
            if (!closest || difference < closest_difference) {
                free(closest);
                closest = strdup(absolute);
                closest_difference = difference;
            }
            free(absolute);
        }
        previous = line;
    }
    char *result = exact ?: resolution_match ?: closest;
    if (result != resolution_match) free(resolution_match);
    if (result != closest) free(closest);
    free(copy);
    return result;
}

static char *url_encode(const char *value) {
    static const char hex[] = "0123456789ABCDEF";
    size_t length = strlen(value);
    char *result = malloc(length * 3 + 1);
    char *out = result;
    for (const unsigned char *in = (const unsigned char *)value; *in; in++) {
        if ((*in >= 'a' && *in <= 'z') || (*in >= 'A' && *in <= 'Z') ||
            (*in >= '0' && *in <= '9') || strchr("-._~", *in)) {
            *out++ = (char)*in;
        } else {
            *out++ = '%';
            *out++ = hex[*in >> 4];
            *out++ = hex[*in & 15];
        }
    }
    *out = '\0';
    return result;
}

static char *usher_with_token(const char *original, const char *signature, const char *token) {
    char *sig = url_encode(signature);
    char *tok = url_encode(token);
    const char *question = strchr(original, '?');
    size_t base_length = question ? (size_t)(question - original) : strlen(original);
    size_t capacity = strlen(original) + strlen(sig) + strlen(tok) + 64;
    char *result = calloc(capacity, 1);
    memcpy(result, original, base_length);
    result[base_length] = '\0';
    strcat(result, "?");
    if (question) {
        char *query = strdup(question + 1);
        char *save = NULL;
        for (char *item = strtok_r(query, "&", &save); item; item = strtok_r(NULL, "&", &save)) {
            if (starts_with(item, "sig=") || starts_with(item, "token=") || starts_with(item, "parent_domains=")) continue;
            strcat(result, item);
            strcat(result, "&");
        }
        free(query);
    }
    strcat(result, "sig=");
    strcat(result, sig);
    strcat(result, "&token=");
    strcat(result, tok);
    free(sig);
    free(tok);
    return result;
}

static bool has_ad_markers(const char *playlist) {
    return contains(playlist, "stitched") ||
           contains(playlist, "\"MIDROLL\"") || contains(playlist, "\"midroll\"");
}

typedef struct {
    size_t extinf;
    size_t live_segments;
    size_t non_live_segments;
    size_t variants;
    size_t dateranges;
    size_t discontinuities;
    size_t prefetches;
    size_t scte_markers;
    bool stitched;
    bool midroll;
    bool twitch_ad_url;
} TASManifestStats;

static TASManifestStats manifest_stats(const char *playlist) {
    TASManifestStats stats = {0};
    if (!playlist) return stats;
    stats.stitched = contains(playlist, "stitched");
    stats.midroll = contains(playlist, "\"MIDROLL\"") || contains(playlist, "\"midroll\"");
    stats.twitch_ad_url = contains(playlist, "X-TV-TWITCH-AD-URL") ||
                          contains(playlist, "X-TV-TWITCH-AD-CLICK-TRACKING-URL");
    char *copy = strdup(playlist);
    if (!copy) return stats;
    char *save = NULL;
    for (char *line = strtok_r(copy, "\n", &save); line; line = strtok_r(NULL, "\n", &save)) {
        trim_manifest_line(line);
        if (starts_with(line, "#EXTINF")) {
            stats.extinf++;
            if (contains(line, ",live")) stats.live_segments++;
            else stats.non_live_segments++;
        } else if (starts_with(line, "#EXT-X-STREAM-INF")) {
            stats.variants++;
        } else if (starts_with(line, "#EXT-X-DATERANGE")) {
            stats.dateranges++;
        } else if (starts_with(line, "#EXT-X-DISCONTINUITY")) {
            stats.discontinuities++;
        } else if (starts_with(line, "#EXT-X-TWITCH-PREFETCH")) {
            stats.prefetches++;
        }
        if (contains(line, "SCTE")) stats.scte_markers++;
    }
    free(copy);
    return stats;
}

static void format_manifest_stats(char *output, size_t capacity, const TASManifestStats *stats,
                                  size_t bytes, bool mapped) {
    snprintf(output, capacity,
             "bytes=%zu mapped=%s variants=%zu extinf=%zu live=%zu non_live=%zu "
             "stitched=%s midroll=%s ad_url_tag=%s daterange=%zu discontinuity=%zu "
             "prefetch=%zu scte=%zu",
             bytes, mapped ? "yes" : "no", stats->variants, stats->extinf,
             stats->live_segments, stats->non_live_segments,
             stats->stitched ? "yes" : "no", stats->midroll ? "yes" : "no",
             stats->twitch_ad_url ? "yes" : "no", stats->dateranges,
             stats->discontinuities, stats->prefetches, stats->scte_markers);
}

static void clear_backup_master(TASStreamRef stream_ref, size_t index) {
    pthread_mutex_lock(&g_lock);
    if (stream_ref_matches_locked(stream_ref)) {
        TASStreamContext *stream = &g_streams[stream_ref.index];
        free(stream->backup_masters[index]);
        free(stream->backup_master_urls[index]);
        stream->backup_masters[index] = NULL;
        stream->backup_master_urls[index] = NULL;
    }
    pthread_mutex_unlock(&g_lock);
}

static char *load_backup_master(const char *original_master, const char *channel,
                                TASStreamRef stream_ref, size_t index,
                                bool *was_cached, char **master_url_out) {
    *was_cached = false;
    *master_url_out = NULL;
    pthread_mutex_lock(&g_lock);
    if (stream_ref_matches_locked(stream_ref) &&
        g_streams[stream_ref.index].backup_masters[index] &&
        g_streams[stream_ref.index].backup_master_urls[index]) {
        *was_cached = true;
        char *master = strdup(g_streams[stream_ref.index].backup_masters[index]);
        *master_url_out = strdup(g_streams[stream_ref.index].backup_master_urls[index]);
        pthread_mutex_unlock(&g_lock);
        if (!master || !*master_url_out) {
            free(master);
            free(*master_url_out);
            *master_url_out = NULL;
            return NULL;
        }
        return master;
    }
    pthread_mutex_unlock(&g_lock);

    char signature[4096];
    char token[16384];
    if (!request_access_token(channel, g_player_types[index], signature, sizeof(signature), token, sizeof(token))) {
        return NULL;
    }
    char *master_url = usher_with_token(original_master, signature, token);
    id master_data = nil;
    id master_response = nil;
    if (!fetch_bytes(master_url, &master_data, &master_response)) {
        if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_SUMMARY)) {
        char detail[192];
        snprintf(detail, sizeof(detail), "player=%s status=%ld",
                 g_player_types[index], master_response ? (long)imsg0(master_response, "statusCode") : 0L);
        tas_diag_log_url("BACKUP_MASTER_FAILURE", master_url, detail);
        }
        free(master_url);
        return NULL;
    }
    char *master = copy_data_text(master_data);
    if (!master) {
        if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_SUMMARY)) {
        char detail[128];
        snprintf(detail, sizeof(detail), "player=%s response copy failed", g_player_types[index]);
        tas_diag_log("BACKUP_MASTER_FAILURE", detail);
        }
        free(master_url);
        return NULL;
    }
    if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_DETAILED)) {
    char detail[192];
    snprintf(detail, sizeof(detail), "player=%s bytes=%zu cached=no",
             g_player_types[index], strlen(master));
    tas_diag_log_url("BACKUP_MASTER", master_url, detail);
    }
    if (strlen(master) < TAS_MANIFEST_CAPACITY && strlen(master_url) < TAS_URL_CAPACITY) {
        pthread_mutex_lock(&g_lock);
        if (stream_ref_matches_locked(stream_ref)) {
            replace_owned_string(&g_streams[stream_ref.index].backup_masters[index], master);
            replace_owned_string(&g_streams[stream_ref.index].backup_master_urls[index], master_url);
        }
        pthread_mutex_unlock(&g_lock);
    }
    *master_url_out = master_url;
    return master;
}

static char *fetch_vaft_variant(const char *original_master, const char *channel,
                                const char *resolution, const char *framerate,
                                TASStreamRef stream_ref,
                                char **selected_base_out) {
    char *fallback = NULL;
    char *fallback_url = NULL;
    const char *fallback_type = NULL;
    *selected_base_out = NULL;

    for (size_t player_index = 0; player_index < TAS_PLAYER_TYPE_COUNT; player_index++) {
        for (size_t attempt = 0; attempt < 2; attempt++) {
            bool was_cached = false;
            char *master_url = NULL;
            char *master = load_backup_master(original_master, channel, stream_ref, player_index,
                                              &was_cached, &master_url);
            if (!master || !master_url) {
                free(master);
                free(master_url);
                break;
            }
            char *variant_url = variant_for_resolution(master, master_url, resolution, framerate);
            free(master);
            free(master_url);

            id variant_data = nil;
            id variant_response = nil;
            bool loaded = variant_url && fetch_bytes(variant_url, &variant_data, &variant_response);
            char *variant = loaded ? copy_data_text(variant_data) : NULL;
            bool has_ads = !variant || has_ad_markers(variant);
            if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_DETAILED)) {
            char candidate_detail[256];
            snprintf(candidate_detail, sizeof(candidate_detail),
                     "player=%s cached_master=%s loaded=%s status=%ld bytes=%zu known_ad=%s",
                     g_player_types[player_index], was_cached ? "yes" : "no",
                     loaded ? "yes" : "no",
                     variant_response ? (long)imsg0(variant_response, "statusCode") : 0L,
                     variant ? strlen(variant) : 0,
                     has_ads ? "yes" : "no");
            tas_diag_log_url("VAFT_CANDIDATE", variant_url, candidate_detail);
            }

            if (variant && player_index == 0) {
                free(fallback);
                free(fallback_url);
                fallback = strdup(variant);
                fallback_url = strdup(variant_url);
                fallback_type = g_player_types[player_index];
            } else if (variant && player_index == TAS_PLAYER_TYPE_COUNT - 1 && !fallback) {
                fallback = strdup(variant);
                fallback_url = strdup(variant_url);
                fallback_type = g_player_types[player_index];
            }

            if (!has_ads) {
                pthread_mutex_lock(&g_lock);
                if (stream_ref_matches_locked(stream_ref)) {
                    TASStreamContext *stream = &g_streams[stream_ref.index];
                    replace_owned_string(&stream->backup_variant_url, variant_url);
                    copy_string(stream->backup_player_type, sizeof(stream->backup_player_type),
                                g_player_types[player_index]);
                    stream->backup_created = time(NULL);
                    stream->last_seen = stream->backup_created;
                }
                pthread_mutex_unlock(&g_lock);
                if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_DETAILED)) fprintf(stderr, "[TAS] VAFT switched to clean %s HLS\n", g_player_types[player_index]);
                tas_diag_metric(TAS_DIAG_CLEAN_ALTERNATE, 1);
                if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_DETAILED)) {
                char detail[128];
                snprintf(detail, sizeof(detail), "player=%s", g_player_types[player_index]);
                tas_diag_log_url("VAFT_CLEAN_SWAP", variant_url, detail);
                }
                free(fallback);
                free(fallback_url);
                *selected_base_out = variant_url;
                return variant;
            }

            free(variant);
            free(variant_url);
            clear_backup_master(stream_ref, player_index);
            if (!was_cached) break;
        }
    }

    if (fallback) {
        if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_DETAILED)) fprintf(stderr, "[TAS] VAFT using %s fallback with stitched segments suppressed\n",
                fallback_type ?: "last-resort");
        if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_DETAILED)) {
        char detail[160];
        snprintf(detail, sizeof(detail), "player=%s known_ad=yes action=strip",
                 fallback_type ?: "last-resort");
        tas_diag_log_url("VAFT_FALLBACK", fallback_url, detail);
        }
        *selected_base_out = fallback_url;
        return fallback;
    }
    free(fallback_url);
    return NULL;
}

static char *strip_ad_segments(const char *playlist, const char *base_url) {
    char *copy = strdup(playlist);
    char *result = NULL;
    size_t length = 0;
    size_t capacity = 0;
    char *save = NULL;
    bool cache_next_uri = false;
    size_t stripped_segments = 0;
    for (char *line = strtok_r(copy, "\n", &save); line; line = strtok_r(NULL, "\n", &save)) {
        trim_manifest_line(line);
        if (cache_next_uri && line[0] != '#') {
            remember_ad_segment(base_url, line);
            stripped_segments++;
            cache_next_uri = false;
        }
        if (starts_with(line, "#EXTINF") && !contains(line, ",live")) {
            cache_next_uri = true;
        }
        if (starts_with(line, "#EXT-X-TWITCH-PREFETCH:")) continue;
        append_text(&result, &length, &capacity, line);
        append_text(&result, &length, &capacity, "\n");
    }
    free(copy);
    if (stripped_segments) {
        tas_diag_metric(TAS_DIAG_STRIPPED_SEGMENT, stripped_segments);
        if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_DETAILED)) {
        char detail[128];
        snprintf(detail, sizeof(detail), "segments=%zu", stripped_segments);
        tas_diag_log_url("SEGMENTS_SUPPRESSED", base_url, detail);
        }
    }
    return result ?: strdup("#EXTM3U\n");
}

static char *playback_url(const char *absolute, bool custom_scheme) {
    return custom_scheme ? custom_scheme_url(absolute) : strdup(absolute);
}

static char *rewrite_manifest_urls(const char *playlist, const char *base_url, bool custom_scheme) {
    char *copy = strdup(playlist);
    char *result = NULL;
    size_t length = 0;
    size_t capacity = 0;
    char *save = NULL;
    for (char *line = strtok_r(copy, "\n", &save); line; line = strtok_r(NULL, "\n", &save)) {
        trim_manifest_line(line);
        if (line[0] != '#' && line[0]) {
            char *absolute = absolute_url(base_url, line);
            char *playable = playback_url(absolute, custom_scheme);
            append_text(&result, &length, &capacity, playable);
            free(playable);
            free(absolute);
        } else if (starts_with(line, "#EXT-X-TWITCH-PREFETCH:")) {
            const char *value = line + strlen("#EXT-X-TWITCH-PREFETCH:");
            char *absolute = absolute_url(base_url, value);
            char *playable = playback_url(absolute, custom_scheme);
            append_text(&result, &length, &capacity, "#EXT-X-TWITCH-PREFETCH:");
            append_text(&result, &length, &capacity, playable);
            free(playable);
            free(absolute);
        } else {
            char *uri = strstr(line, "URI=\"");
            if (uri) {
                const char *value = uri + strlen("URI=\"");
                const char *end = strchr(value, '"');
                if (end) {
                    char relative[8192];
                    size_t size = (size_t)(end - value);
                    if (size >= sizeof(relative)) size = sizeof(relative) - 1;
                    memcpy(relative, value, size);
                    relative[size] = '\0';
                    char *absolute = absolute_url(base_url, relative);
                    char *playable = playback_url(absolute, custom_scheme);
                    char prefix[16384];
                    size_t prefix_length = (size_t)(value - line);
                    if (prefix_length >= sizeof(prefix)) prefix_length = sizeof(prefix) - 1;
                    memcpy(prefix, line, prefix_length);
                    prefix[prefix_length] = '\0';
                    append_text(&result, &length, &capacity, prefix);
                    append_text(&result, &length, &capacity, playable);
                    append_text(&result, &length, &capacity, end);
                    free(playable);
                    free(absolute);
                } else {
                    append_text(&result, &length, &capacity, line);
                }
            } else {
                append_text(&result, &length, &capacity, line);
            }
        }
        append_text(&result, &length, &capacity, "\n");
    }
    free(copy);
    return result ?: strdup(playlist);
}

static char *process_manifest(const char *url, const char *playlist, bool custom_scheme) {
    char channel[512];
    channel_from_master_url(url, channel, sizeof(channel));
    if (channel[0]) {
        tas_diag_metric(TAS_DIAG_MASTER_MANIFEST, 1);
        pthread_mutex_lock(&g_lock);
        size_t previous_routes = active_routes_locked();
        TASStreamRef stream_ref = update_stream_master_locked(channel, url, playlist);
        size_t registered_routes = register_variant_routes_locked(stream_ref, url, playlist);
        size_t active_routes = active_routes_locked();
        pthread_mutex_unlock(&g_lock);
        if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_DETAILED)) {
        TASManifestStats stats = manifest_stats(playlist);
        char detail[768];
        format_manifest_stats(detail, sizeof(detail), &stats, strlen(playlist), true);
        char route_detail[1024];
        snprintf(route_detail, sizeof(route_detail),
                 "%s stream_generation=%llu previous_routes=%zu registered_routes=%zu active_routes=%zu",
                 detail, (unsigned long long)stream_ref.generation, previous_routes,
                 registered_routes, active_routes);
        tas_diag_log_stream("MASTER_MANIFEST", channel, url, route_detail);
        }
        return rewrite_manifest_urls(playlist, url, custom_scheme);
    }

    char resolution[128] = "";
    char framerate[64] = "";
    TASStreamSnapshot stream;
    TASRouteMiss miss;
    if (!snapshot_stream_for_variant(url, &stream, &miss)) {
        tas_diag_metric(TAS_DIAG_VARIANT_MANIFEST, 1);
        tas_diag_metric(TAS_DIAG_UNMAPPED_VARIANT, 1);
        if (has_ad_markers(playlist)) tas_diag_metric(TAS_DIAG_AD_MANIFEST, 1);
        if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_DETAILED)) {
        TASManifestStats stats = manifest_stats(playlist);
        char detail[768];
        format_manifest_stats(detail, sizeof(detail), &stats, strlen(playlist), false);
        char route_detail[1024];
        snprintf(route_detail, sizeof(route_detail),
                 "%s matched_route=no active_streams=%zu active_routes=%zu retired_match=%s "
                 "retired_reason=%s retired_age=%lld retired_generation=%llu newest_master_age=%lld",
                 detail, miss.active_streams, miss.active_routes, miss.retired_match ? "yes" : "no",
                 miss.retired_reason ? miss.retired_reason : "none", miss.retired_age,
                 (unsigned long long)miss.retired_generation, miss.newest_master_age);
        tas_diag_log_url(has_ad_markers(playlist) ? "VARIANT_UNMAPPED_AD" : "VARIANT_UNMAPPED_CLEAN",
                         url, route_detail);
        }
        return rewrite_manifest_urls(playlist, url, custom_scheme);
    }
    tas_diag_metric(TAS_DIAG_VARIANT_MANIFEST, 1);
    if (has_ad_markers(playlist)) tas_diag_metric(TAS_DIAG_AD_MANIFEST, 1);
    if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_DETAILED)) {
    TASManifestStats stats = manifest_stats(playlist);
    char manifest_detail[768];
    format_manifest_stats(manifest_detail, sizeof(manifest_detail), &stats, strlen(playlist), true);
    char route_detail[1024];
    snprintf(route_detail, sizeof(route_detail),
             "%s stream_generation=%llu route_age=%lld master_age=%lld",
             manifest_detail, (unsigned long long)stream.ref.generation,
             stream.route_age, stream.master_age);
    tas_diag_log_stream(has_ad_markers(playlist) ? "VARIANT_AD_MARKED" : "VARIANT_MANIFEST",
                        stream.channel, url, route_detail);
    }
    variant_metadata(stream.master_manifest, stream.master_url, url,
                     resolution, sizeof(resolution), framerate, sizeof(framerate));

    char *selected = NULL;
    char *selected_base = NULL;
    if (has_ad_markers(playlist)) {
        if (stream.backup_variant_url[0] && time(NULL) - stream.backup_created < 600) {
            id backup_data = nil;
            id backup_response = nil;
            if (fetch_bytes(stream.backup_variant_url, &backup_data, &backup_response)) {
                char *candidate = copy_data_text(backup_data);
                if (candidate && !has_ad_markers(candidate)) {
                    selected = candidate;
                    selected_base = strdup(stream.backup_variant_url);
                } else {
                    free(candidate);
                    clear_active_backup(stream.ref);
                }
            }
        }
        if (!selected && stream.master_url[0] && stream.channel[0]) {
            selected = fetch_vaft_variant(stream.master_url, stream.channel, resolution, framerate,
                                          stream.ref, &selected_base);
        }
        if (!selected) {
            selected = strdup(playlist);
            selected_base = strdup(url);
            if(tas_diag_wants(TAS_DIAG_PLAYBACK,TAS_DIAG_SUMMARY)) fprintf(stderr, "[TAS] VAFT alternates unavailable; suppressing stitched segments\n");
            tas_diag_log_url("VAFT_ALTERNATES_UNAVAILABLE", url,
                             "action=use_original_and_suppress_known_ad_segments");
        }
        if (has_ad_markers(selected)) {
            char *stripped = strip_ad_segments(selected, selected_base);
            free(selected);
            selected = stripped;
        }
    } else {
        clear_active_backup(stream.ref);
        selected = strdup(playlist);
        selected_base = strdup(url);
    }
    char *rewritten = rewrite_manifest_urls(selected, selected_base, custom_scheme);
    free(selected);
    free(selected_base);
    free(stream.master_manifest);
    return rewritten;
}
