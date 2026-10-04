#ifndef TAS_EMOTE_PROBE_H
#define TAS_EMOTE_PROBE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Temporary, opt-in build instrumentation. Normal builds compile it out. */
#ifndef TAS_EMOTE_DIAGNOSTIC
#define TAS_EMOTE_DIAGNOSTIC 0
#endif
#if TAS_EMOTE_DIAGNOSTIC
bool tas_emote_probe_set(const char *code);
void tas_emote_probe_status(char *buffer, size_t capacity);
void tas_emote_probe_stage(uint64_t number, const char *stage);
void tas_emote_probe_observe(const char *stage, const char *code,
                            const char *channel, const char *outcome);
void tas_emote_probe_text(const char *stage, const char *body,
                         const char *channel, const char *outcome);
#else
static inline void tas_emote_probe_stage(uint64_t number, const char *stage) {
    (void)number; (void)stage;
}
#endif
#endif
