#pragma once
#include <stdbool.h>
#include <stdint.h>
#define SSN_ADBLOCK_KEY "dev.streamside.player.adblock"
/* No donor objects or credentials cross this owned boundary. Install only after
 * launch selection; baseline/original startup must remain untouched. */
void ssn_adblock_install(void);
bool ssn_adblock_enabled(void);
bool ssn_adblock_active(void);
void ssn_adblock_set_enabled(bool enabled);
uint64_t ssn_adblock_begin(void);
void ssn_adblock_end(uint64_t lease);
