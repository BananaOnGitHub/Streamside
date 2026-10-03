#ifndef TAS_EMOTE_UI_H
#define TAS_EMOTE_UI_H
#include <stddef.h>
#include <objc/objc.h>
/* Shared provider-details sheet. Metadata is borrowed and retained by the sheet. */
BOOL tas_emote_ui_present_details(id view, id metadata);
void tas_emote_ui_retry_hooks(void);
void tas_emote_ui_status(char *buffer, size_t capacity);
#endif
