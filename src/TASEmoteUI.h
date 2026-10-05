#ifndef TAS_EMOTE_UI_H
#define TAS_EMOTE_UI_H
#include <stddef.h>
#include <objc/objc.h>
/* Shared provider-details sheet. Metadata is borrowed and retained by the sheet. */
BOOL tas_emote_ui_present_details(id view, id metadata);
/* Window-level composer suggestions must yield to the owning chat's modals. */
BOOL tas_emote_ui_modal_visible(id view);
void tas_emote_ui_retry_hooks(void);
void tas_emote_ui_status(char *buffer, size_t capacity);
#if TAS_EMOTE_DIAGNOSTIC
void tas_emote_ui_probe_start(void); /* Main thread; idempotent, does not reset history. */
#endif
#endif
