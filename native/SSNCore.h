#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "SSNLaunch.h"
typedef struct { const char *name,*image; uintptr_t offset; uint32_t opcode; bool guard; } SSNProbeSpec;
typedef struct { const char *name; uintptr_t cave,slot; } SSNImageSpec;
#include "SSNBuild.h"
enum { SSN_RESTORING, SSN_SIGNED_OUT, SSN_LOADING_ACCOUNT, SSN_LOADING_FOLLOWS,
       SSN_READY, SSN_EMPTY, SSN_REQUEST_FAILED, SSN_ABI_FAILED, SSN_SESSION_CHANGED, SSN_MONITOR_FAILED, SSN_FEED_FAILED };
void ssn_core_start(const char *directory);
void ssn_probe_hit(unsigned index);
void ssn_arm_image(unsigned index, bool valid);
void ssn_failure(unsigned code);
void ssn_service(unsigned state, unsigned count);
void ssn_transition(bool foreground);
void ssn_scaffold_ready(void);
/* 0 unobserved, 1 Streamside root, 2 another root, 3 missing root. Not RN classification. */
void ssn_presentation(unsigned owner);
/* Bounded numeric navigation evidence: suppressed roots, auth opens, verified returns, failures, closes. */
void ssn_navigation_armed(void);
bool ssn_navigation_guarded(void);
void ssn_navigation_event(unsigned event);
void ssn_account_observed(unsigned event,bool preserved);
void ssn_account_data_cleared(void);
bool ssn_calibrated(void);
bool ssn_armed(void);
bool ssn_failed(void);
unsigned ssn_state(void);
uint64_t ssn_count(unsigned index);
const char *ssn_state_text(void);
const char *ssn_report_path(void);
void ssn_report(void);
void ssn_summary(char *buffer,size_t size);

/* Bounded playback evidence, independent of all runtime entry probes. */
void ssn_playback_status(unsigned phase,unsigned error);
void ssn_playback_event(unsigned event);

/* Native-only installation/request observations. Original mode leaves all zero. */
void ssn_frontend_event(unsigned event);

/* Bounded taps: video, close, pause, mute, share, settings, copy. No content. */
void ssn_player_control_event(unsigned event);

/* SDK-reported mute state is unknown without a current player. No audio data. */
void ssn_playback_mute(bool known,bool requested,bool reported);
