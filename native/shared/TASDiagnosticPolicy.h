#ifndef TAS_DIAGNOSTIC_POLICY_H
#define TAS_DIAGNOSTIC_POLICY_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
enum { TAS_DIAG_GENERAL, TAS_DIAG_PLAYBACK, TAS_DIAG_RENDERING,
       TAS_DIAG_IMAGES, TAS_DIAG_COMPOSER, TAS_DIAG_CHAT, TAS_DIAG_CATEGORIES };
enum { TAS_DIAG_SUMMARY, TAS_DIAG_DETAILED };
enum { TAS_DIAG_MINIMAL, TAS_DIAG_ADS, TAS_DIAG_EMOTES, TAS_DIAG_CHAT_PRESET, TAS_DIAG_CUSTOM };
#define TAS_DIAG_DETAIL_BIT 256U
#define TAS_DIAG_CUSTOM_BIT 512U
#define TAS_DIAG_CONFIG_KEY "TASDiagnosticConfigurationV1"
/* Weak only to keep isolated subsystem host fixtures independent of the app's
 * policy engine. Both production binaries always link TASDiagnosticPolicy.c. */
unsigned tas_diag_policy_word(void) __attribute__((weak));
static inline bool tas_diag_wants(unsigned category, unsigned level) {
    unsigned w=tas_diag_policy_word ? tas_diag_policy_word() : 319U;
    return category<TAS_DIAG_CATEGORIES && (w&(1U<<category)) &&
           (level==TAS_DIAG_SUMMARY || (w&TAS_DIAG_DETAIL_BIT));
}
unsigned tas_diag_config_normalize(unsigned word);
unsigned tas_diag_preset_word(unsigned preset);
unsigned tas_diag_preset_for(unsigned word);
const char *tas_diag_category_name(unsigned category);
const char *tas_diag_preset_name(unsigned preset);
void tas_diag_policy_initialize(unsigned saved);
void tas_diag_events_clear(void);
void tas_diag_event_store(unsigned category,unsigned level,const char *event,const char *detail);
void tas_diag_events_report(unsigned category,char *buffer,size_t capacity);
void tas_diag_configuration_report(unsigned saved,char *buffer,size_t capacity);
void tas_diag_classify(const char *event,unsigned *category,unsigned *level);
#endif
