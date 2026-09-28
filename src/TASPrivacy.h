#ifndef TAS_PRIVACY_H
#define TAS_PRIVACY_H

#include <stddef.h>

/* Labels are process-local. Inputs never reach the on-disk diagnostic log. */
void tas_label_channel(const char *channel, char *output, size_t capacity);
void tas_label_url(const char *url, char *output, size_t capacity);

#endif
