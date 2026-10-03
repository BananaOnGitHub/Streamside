#ifndef SS_COMPOSER_MODEL_H
#define SS_COMPOSER_MODEL_H
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

/* Positions are UTF-16 offsets, matching UITextView/NSRange. Spans are sorted,
 * nonoverlapping ranges in the expanded text. Native attachments stay length 1. */
typedef struct { size_t start, length; } SSSpan;
static inline size_t ss_display_position(size_t plain, const SSSpan *spans, size_t n) {
    size_t removed = 0;
    for (size_t i = 0; i < n; i++) {
        if (plain <= spans[i].start) break;
        if (plain < spans[i].start + spans[i].length) return spans[i].start - removed + 1;
        removed += spans[i].length - 1;
    }
    return plain - removed;
}
static inline size_t ss_plain_position(size_t shown, const SSSpan *spans, size_t n) {
    size_t removed = 0;
    for (size_t i = 0; i < n; i++) {
        if (shown <= spans[i].start - removed) break;
        removed += spans[i].length - 1;
    }
    return shown + removed;
}
static inline bool ss_space(uint16_t c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == 0xa0 ||
           (c >= 0x2000 && c <= 0x200a) || c == 0x2028 || c == 0x2029 || c == 0x3000;
}
/* Selection endpoints are expanded UTF-16 offsets. A caret at a word's end
 * still belongs to that word; only moving past it commits its preview. */
static inline bool ss_preview_token_safe(size_t start, size_t end, size_t length,
                                         size_t caret, size_t selected) {
    if (start>=end || end>length || caret>length || selected>length-caret) return false;
    if (!selected) return caret<start || caret>end;
    return caret+selected<=start || caret>=end;
}
/* Verified optional Identity layout: nil uses the name's +16 spare word;
 * no assumptions about padding bytes next to UInt32 or object pointers. */
static inline uint32_t ss_identity_room(const void *bytes, size_t span) {
    if (!bytes || span != 56) return 0;
    uint32_t room; uint64_t presence;
    memcpy(&room,bytes,4); memcpy(&presence,(const unsigned char *)bytes+16,8);
    return presence ? room : 0;
}
/* Completion only at a token's end, never URLs/mentions/inside a word. */
static inline bool ss_completion_span(const uint16_t *text, size_t length, size_t caret,
                                      int mode, SSSpan *span) {
    if (!text || !span || mode < 0 || mode > 1 || caret > length || !caret) return false;
    if (caret < length && !ss_space(text[caret])) return false;
    size_t start = caret;
    while (start && !ss_space(text[start-1]) && text[start-1] != 0xfffc) start--;
    size_t prefix = start;
    if (text[start] == ':') prefix++;
    else if (mode == 1) return false;
    if ((prefix == caret && prefix == start) || caret - prefix > 96) return false;
    for (size_t i = prefix; i < caret; i++)
        if (text[i] == ':' || text[i] == '/' || text[i] == '@' || text[i] == 0xfffc) return false;
    /* Avoid an unhelpful strip on every single normal letter. Colon is explicit. */
    if (prefix == start && caret - prefix < 2) return false;
    *span = (SSSpan){start, caret-start}; return true;
}
static inline bool ss_provider_matches(unsigned char provider, int selected) {
    return selected >= 0 && selected <= 3 && (!selected || provider + 1 == selected);
}
static inline bool ss_ascii_prefix(const char *name, const char *prefix) {
    if (!name || !prefix) return false;
    while (*prefix) {
        unsigned char a = (unsigned char)*name++, b = (unsigned char)*prefix++;
        if (a >= 'A' && a <= 'Z') a += 'a' - 'A';
        if (b >= 'A' && b <= 'Z') b += 'a' - 'A';
        if (!a || a != b) return false;
    }
    return true;
}
/* Suggestions match a contiguous fragment anywhere, as Frosty's contains()
 * does. Preserve exact case-sensitive lookup when inserting/rendering codes. */
static inline bool ss_ascii_contains(const char *name, const char *query) {
    if (!name || !query) return false;
    if (!*query) return true;
    for (; *name; name++) if (ss_ascii_prefix(name,query)) return true;
    return false;
}
#endif
