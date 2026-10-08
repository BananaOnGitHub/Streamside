#ifndef TAS_IMAGE_TRANSPORT_H
#define TAS_IMAGE_TRANSPORT_H
#include <stddef.h>
/* Aggregate only: no URL, emote identity, headers or body in diagnostics. */
void tas_image_transport_status(char *buffer, size_t capacity);
#endif
