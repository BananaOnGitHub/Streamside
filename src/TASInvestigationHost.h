#ifndef TAS_INVESTIGATION_HOST_H
#define TAS_INVESTIGATION_HOST_H
#include "TASInvestigation.h"
/* Weak declarations keep isolated pre-existing subsystem fixtures independent.
 * Both production binaries always link TASInvestigationHost.c. */
void tas_inv_host_initialize(void) __attribute__((weak));
bool tas_inv_host_supported(void) __attribute__((weak));
bool tas_inv_host_sha256(const void *, size_t, unsigned char[32]) __attribute__((weak));
void tas_inv_host_source_admitted(void) __attribute__((weak));
bool tas_inv_host_request(unsigned operation) __attribute__((weak));
void tas_inv_host_status(char *, size_t) __attribute__((weak));
void tas_inv_host_explanation(char *, size_t) __attribute__((weak));
void tas_inv_host_source_checked(unsigned) __attribute__((weak));
void tas_emotes_install_investigation_bootstrap(void);
#endif
