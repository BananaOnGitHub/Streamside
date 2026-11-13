#pragma once
#include <stdbool.h>
#ifndef SSN_DEV_LAUNCH_SELECTOR
#define SSN_DEV_LAUNCH_SELECTOR 0
#endif
/* Selected once by the diagnostic constructor, before gates/observers publish.
 * Scheduling never changes this process's selection. */
void ssn_launch_select(void);
bool ssn_native_mode(void);
/* 0 independent original control, 1 native default, 2 original one-shot. */
unsigned ssn_launch_origin(void);
unsigned ssn_launch_error(void);
bool ssn_launch_selector_enabled(void);
bool ssn_launch_pending(void);
bool ssn_launch_schedule_original(bool requested);
