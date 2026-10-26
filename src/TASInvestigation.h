#ifndef TAS_INVESTIGATION_H
#define TAS_INVESTIGATION_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define TAS_INV_ABI 1U
#define TAS_INV_MANIFEST_BYTES 16384U
#define TAS_INV_EVENT_FAMILIES 10U
#define TAS_INV_CAPABILITIES 3U
enum { TAS_INV_UNSUPPORTED, TAS_INV_DORMANT, TAS_INV_ARMED, TAS_INV_CAPTURING, TAS_INV_STOPPING };
enum { TAS_INV_ARM = 1, TAS_INV_CAPTURE, TAS_INV_STOP };
enum {
    TAS_INV_OK,
    TAS_INV_BAD_MANIFEST,
    TAS_INV_BAD_INTEGRITY,
    TAS_INV_BAD_DONOR,
    TAS_INV_NO_RUNTIME,
    TAS_INV_BUSY,
    TAS_INV_BAD_STATE,
    TAS_INV_TIMEOUT,
    TAS_INV_THERMAL,
    TAS_INV_MEMORY,
    TAS_INV_BACKGROUND
};
enum { TAS_INV_BUNDLED, TAS_INV_PINNED_CACHE, TAS_INV_CACHE_REJECTED };
enum { TAS_INV_SNAPSHOT = 1, TAS_INV_LIFECYCLE = 2, TAS_INV_REWARDS = 4 };
enum {
    TAS_INV_TRANSLATION,
    TAS_INV_EMISSION,
    TAS_INV_LOCAL_ECHO,
    TAS_INV_RECONCILIATION,
    TAS_INV_STORE,
    TAS_INV_IRC_REWARD,
    TAS_INV_PUBSUB_REWARD,
    TAS_INV_REWARD_RENDER,
    TAS_INV_LIST,
    TAS_INV_LAYOUT
};
enum {
    TAS_INV_MAX_LISTS,
    TAS_INV_MAX_ENTRIES,
    TAS_INV_MAX_CELLS,
    TAS_INV_SNAPSHOT_MS,
    TAS_INV_JS_WORK_US,
    TAS_INV_CALLBACK_WORK_US,
    TAS_INV_EVENTS_PER_SECOND,
    TAS_INV_PRIORITY_PER_SECOND,
    TAS_INV_BRIDGE_BATCHES_PER_SECOND,
    TAS_INV_ORDINARY_EVENTS,
    TAS_INV_PRIORITY_EVENTS,
    TAS_INV_IDENTITY_ALIASES,
    TAS_INV_ALIAS_BYTES,
    TAS_INV_REPORT_BYTES,
    TAS_INV_LIMITS
};
/* The platform implementation uses the system SHA-256 primitive. No trust
 * anchor, URL, selector, field path or executable payload comes from JSON. */
typedef bool (*TASInvSHA256)(const void *, size_t, unsigned char[32]);
typedef struct {
    uint32_t version, capabilities, events, limits[TAS_INV_LIMITS];
    bool return_armed;
    char title[65], description[257];
} TASInvManifest;
typedef struct {
    const char *id;
    uint32_t version, mask, events;
    bool startup_required;
} TASInvCapability;
typedef struct {
    const char *version, *build, *main_uuid, *main_text_sha256;
    const char *hermes_uuid, *hermes_text_sha256, *hbc_sha256;
    uint32_t hbc_version, hbc_bytes;
} TASInvDonor;
typedef struct {
    uint32_t operation, generation, sequence;
    TASInvManifest manifest;
} TASInvCommand;
typedef struct {
    uint32_t state, reason, generation, sequence, pending, registry_source;
    uint32_t ready_capabilities;
    uint64_t deadline_ms;
} TASInvStatus;
extern const uint32_t tas_inv_ceilings[TAS_INV_LIMITS];
const TASInvCapability *tas_inv_capability(unsigned index);
bool tas_inv_parse(const void *, size_t, TASInvManifest *);
/* Cache accepts only the exact compiled immutable bytes; invalid cache uses
 * the independently verified bundle, without changing activation state. */
bool tas_inv_registry(const void *, size_t, TASInvSHA256, TASInvManifest *, unsigned *source);
bool tas_inv_donor_matches(const TASInvDonor *);
bool tas_inv_initialize(TASInvSHA256);
/* Read-only selection snapshot. Trust admission and configuration replacement
 * remain separate from parsing; v1 exposes no downloaded-configuration setter. */
bool tas_inv_configuration(TASInvManifest *, char digest[65], unsigned *source);
void tas_inv_set_safety(unsigned reason);
/* Called only by the compiled host after its ABI/bootstrap/command checks.
 * ready_capabilities describes actually installed adapters, not manifest wishes. */
bool tas_inv_admit(const TASInvDonor *, uint32_t ready_capabilities, uint32_t vm_generation);
bool tas_inv_begin(unsigned operation, uint64_t now_ms, TASInvCommand *);
bool tas_inv_ack(uint32_t generation, uint32_t sequence, unsigned operation, bool success);
bool tas_inv_expire(uint64_t now_ms);
void tas_inv_invalidate(unsigned reason);
TASInvStatus tas_inv_status(void);
const char *tas_inv_state_name(unsigned);
const char *tas_inv_reason_name(unsigned);
#endif
