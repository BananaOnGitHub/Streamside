#ifndef TAS_EMOTE_GEOMETRY_H
#define TAS_EMOTE_GEOMETRY_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* Read only dimension headers, never decompress untrusted provider images. */
static inline uint32_t tas_emote_le24(const unsigned char *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16;
}
static inline uint32_t tas_emote_be32(const unsigned char *p) {
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3];
}
static inline double tas_emote_image_aspect(const unsigned char *p, size_t n) {
    if (!p) return 0;
    uint32_t w = 0, h = 0;
    if (n >= 24 && !memcmp(p,"\211PNG\r\n\032\n",8) && !memcmp(p+12,"IHDR",4)) {
        w = tas_emote_be32(p+16); h = tas_emote_be32(p+20);
    } else if (n >= 10 && (!memcmp(p,"GIF87a",6) || !memcmp(p,"GIF89a",6))) {
        w = (uint32_t)p[6] | (uint32_t)p[7] << 8;
        h = (uint32_t)p[8] | (uint32_t)p[9] << 8;
    } else if (n >= 30 && !memcmp(p,"RIFF",4) && !memcmp(p+8,"WEBP",4)) {
        if (!memcmp(p+12,"VP8X",4)) {
            w = 1 + tas_emote_le24(p+24); h = 1 + tas_emote_le24(p+27);
        } else if (!memcmp(p+12,"VP8 ",4) && p[23] == 0x9d && p[24] == 0x01 && p[25] == 0x2a) {
            w = ((uint32_t)p[26] | (uint32_t)p[27] << 8) & 0x3fff;
            h = ((uint32_t)p[28] | (uint32_t)p[29] << 8) & 0x3fff;
        }
    }
    if (!w && n >= 25 && !memcmp(p,"RIFF",4) && !memcmp(p+8,"WEBPVP8L",8) && p[20] == 0x2f) {
        w = 1 + ((uint32_t)p[21] | ((uint32_t)p[22] & 0x3f) << 8);
        h = 1 + ((uint32_t)p[22] >> 6 | (uint32_t)p[23] << 2 | ((uint32_t)p[24] & 0xf) << 10);
    }
    return w && h && w <= 4096 && h <= 4096 ? (double)w / h : 0;
}
/* Idempotent: native attachment setters/getters may call each other. */
static inline void tas_emote_proportions(double *width, double *height, double aspect) {
    if (aspect <= 0 || *height <= 0) return;
    double ratio = *width / *height;
    if (ratio > aspect - 0.000001 && ratio < aspect + 0.000001) return;
    double original_height = *height;
    *width = original_height * aspect;
    if (*width > original_height * 5) {
        *width = original_height * 5; *height = *width / aspect;
    }
}
#endif
