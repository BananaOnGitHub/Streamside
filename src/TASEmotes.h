#ifndef TAS_EMOTES_H
#define TAS_EMOTES_H

#include <objc/objc.h>
#include <stdbool.h>
#include <stddef.h>

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
bool tas_emotes_is_provider_image_url(const char *url);
void tas_emotes_image_protocol_request(void);

#endif
