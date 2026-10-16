#ifndef TAS_ANIMATED_IMAGE_H
#define TAS_ANIMATED_IMAGE_H
#include <objc/objc.h>
#include <stddef.h>
/* Weak declarations isolate subsystem host fixtures. Production always links
 * TASAnimatedImage.c and verifies its definitions in the native artifact. */
/* Retained animated UIImage with ImageIO-backed indexed WebP frames. Nil for
 * static/unsupported/malformed data. Caller clocks remain independent. */
id tas_animated_image_create(id data) __attribute__((weak));
/* Warm and admit a template for the legacy factory. Call only for a successful
 * response from an admitted provider URL; never arbitrary native image data. */
void tas_animated_image_prepare(id data) __attribute__((weak));
void tas_animated_image_retry_hooks(void) __attribute__((weak));
void tas_animated_image_status(char *buffer,size_t capacity) __attribute__((weak));
#endif
