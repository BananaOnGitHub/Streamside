#ifndef TAS_RN_PROBE_H
#define TAS_RN_PROBE_H
#include <stddef.h>
void tas_rn_probe_retry_hooks(void);
void tas_rn_probe_status(char *buffer, size_t capacity);
#endif
