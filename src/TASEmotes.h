#ifndef TAS_EMOTES_H
#define TAS_EMOTES_H

#include <objc/objc.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* The preference is read once at launch. A relaunch installs/removes the hooks. */
bool tas_emotes_enabled_this_launch(void);
void tas_emotes_initialize(void);
void tas_emotes_retry_hooks(void);
void tas_emotes_reload(void);
void tas_emotes_clear_cache(void);
id tas_emotes_rewrite_request_copy(id request);
void tas_emotes_status(char *buffer, size_t capacity);
void tas_emotes_image_request(bool has_completion);
void tas_emotes_image_result(id data, id response, id error);
void tas_emotes_image_result_for_url(const char *url, id data, id response, id error);
bool tas_emotes_is_provider_image_url(const char *url);
/* Transient marker on the URL object produced by our synthetic-ID redirect.
 * Not a wire header, persistent identity, or fallback to another chat room. */
bool tas_emotes_is_redirected_image_url(id url);
void tas_emotes_image_protocol_request(const char *url);
void tas_emotes_image_protocol_cancel(const char *url);
/* Retained snapshots; callers release them. No chat text is retained. */
id tas_emotes_metadata_copy(uint64_t synthetic_id);
id tas_emotes_local_matches_copy(id channel, id content);
/* Provider: 0 All, 1 7TV, 2 BTTV, 3 FFZ. Scope: -1 suggestions, 0 channel, 1 global.
 * Channel must be the composer's identity; no background-chat fallback.
 * Queries match case-insensitive fragments anywhere in a name. Display snapshots
 * sort by name ignoring case, then apply the result limit. */
id tas_emotes_picker_copy(id channel, int provider, int scope, id query, size_t limit);
/* Cheap invalidation token. Image arrivals do not change the catalog. */
uint64_t tas_emotes_catalog_revision(void);
id tas_emotes_named_copy(id channel, id name);
double tas_emotes_aspect(uint64_t synthetic_id);

#endif
