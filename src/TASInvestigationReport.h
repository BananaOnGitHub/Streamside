#ifndef TAS_INVESTIGATION_REPORT_H
#define TAS_INVESTIGATION_REPORT_H
#include "TASInvestigation.h"
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
/* Fixed native provenance is pinned before the first packet. No remote JSON,
 * object, address, or arbitrary text enters this record. These fields describe
 * existing admission/configuration facts, not new observation probes. */
typedef struct {
    uint32_t manifest_version, registry_source, capabilities, vm_epoch;
    uint32_t arm_generation, arm_sequence, general_policy, limits[TAS_INV_LIMITS];
    uint64_t arm_requested_ms, capture_requested_ms;
    char manifest_sha256[65], original_hbc[65], patched_hbc[65];
    char native_profile[65], main_uuid[33], react_uuid[33], hermes_uuid[33];
    char main_text[65], react_text[65], hermes_text[65];
    bool available;
} TASInvReportMetadata;
void tas_inv_report_prepare(uint32_t, uint32_t, const TASInvReportMetadata *);
void tas_inv_report_stop(unsigned reason);
/* One immutable export copy. begin is short/locked; format performs no live
 * access and holds no report lock. UI invokes it on one worker, finish on main. */
bool tas_inv_report_export_begin(void);
size_t tas_inv_report_export_format(char *, size_t);
void tas_inv_report_export_end(void);
void tas_inv_report_export_cancel(void);
bool tas_inv_report_export_cancelled(void);
size_t tas_inv_report_owned_bytes(void);
/* Numeric-only, bounded wire. Never retain input text. One frozen capture. */
bool tas_inv_report_accept(uint32_t generation, uint32_t sequence, const void *, size_t,
                           uint64_t now_ms);
bool tas_inv_report_complete(uint32_t generation, uint32_t sequence);
void tas_inv_report_interrupt(void);
bool tas_inv_report_available(void);
bool tas_inv_report_started(uint32_t, uint32_t);
size_t tas_inv_report_format(char *, size_t);
#endif
