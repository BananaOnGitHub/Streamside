#ifndef TAS_INVESTIGATION_REPORT_H
#define TAS_INVESTIGATION_REPORT_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
/* Numeric-only, bounded wire. Never retain input text. One frozen capture. */
bool tas_inv_report_accept(uint32_t generation, uint32_t sequence, const void *, size_t,
                           uint64_t now_ms);
bool tas_inv_report_complete(uint32_t generation, uint32_t sequence);
void tas_inv_report_interrupt(void);
size_t tas_inv_report_format(char *, size_t);
#endif
