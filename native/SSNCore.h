#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
typedef struct { const char *name,*image; uintptr_t offset; uint32_t opcode; bool guard; } SSNProbeSpec;
typedef struct { const char *name; uintptr_t cave,slot; } SSNImageSpec;
#include "SSNBuild.h"
enum { SSN_RESTORING, SSN_SIGNED_OUT, SSN_LOADING_ACCOUNT, SSN_LOADING_FOLLOWS,
       SSN_READY, SSN_EMPTY, SSN_REQUEST_FAILED, SSN_ABI_FAILED, SSN_SESSION_CHANGED, SSN_MONITOR_FAILED };
void ssn_core_start(const char *directory);
void ssn_probe_hit(unsigned index);
void ssn_arm_image(unsigned index, bool valid);
void ssn_failure(unsigned code);
void ssn_service(unsigned state, unsigned count);
void ssn_transition(bool foreground);
void ssn_scaffold_ready(void);
bool ssn_calibrated(void);
bool ssn_armed(void);
bool ssn_failed(void);
unsigned ssn_state(void);
uint64_t ssn_count(unsigned index);
const char *ssn_state_text(void);
const char *ssn_report_path(void);
void ssn_report(void);
void ssn_summary(char *buffer,size_t size);
