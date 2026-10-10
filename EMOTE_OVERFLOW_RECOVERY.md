# Build 83: isolated overflow recovery

> Included in active `compat/twitch-31.5` build 87; the investigation is preserved
> at `archive/rn-image-demand`. Production host and real Apple Foundation
> recovery gates passed. The user accepted the overflow change; the later
> supplied low-pressure device report did not exercise saturation. The freeze
> and evidence limits below remain current. See [branch closure](docs/DIAGNOSTIC_BRANCH_ARCHIVE.md).

Performance architecture is frozen: 512 ordinary flights, 64 consumers per
flight, eight active transfers (six background), foreground-first/FIFO ordering,
existing shared session, cache freshness rules, lookup budgets and RN windows.
No downloader, prefetcher, polling retry loop or throughput tuning is added.

## Recovery contract

Only an ordinary admission refusal enters a separate fixed registry: 64 groups,
64 consumers per group, 4096 consumers total. Coalescing uses the same URL,
exact headers and cache-policy identity. Foreground promotion is preserved.
The first admission starts a 30-second monotonic deadline; joining or promotion
does not reset it. One shared GCD deadline timer expires pending groups, without
starting or retrying transfers.

When ordinary capacity is released, pending ownership moves to free ordinary
slots, foreground-first then FIFO. The existing scheduler alone starts tasks.
Original queue timestamps survive recovery. Once moved, ordinary lifecycle rules
apply. Expired pending entries are never recovered and receive a stop-aware
NSURLErrorTimedOut completion outside registry locks.

Cancellation removes only that consumer, frees empty groups, and suppresses
callbacks even if timeout extraction or ordinary recovery raced with stopLoading.
Session initialization on lookup workers also supplies pending groups admitted
before initialization. Fresh direct-cache delivery bypasses both registries,
including when both are full. If both admission registries are exhausted, the
existing terminal failure path completes once.

Diagnostics expose aggregate waiting/joined/recovered/cancelled/expired/rejected
counts and current/peak/limit occupancy, without asset values. Ordinary budget
refusals still count unsuccessful ordinary admission attempts, including those
subsequently recovered. Pending expiry has no Foundation task, so is separate
from Foundation transport timeout metrics.

## Regression gates

Host production-lifecycle fixtures cover recovery order, coalescing and identity,
foreground promotion, unchanged deadlines, repeat cancellation, stop/recovery and
stop/timeout races, immediate completion, bootstrap spills, exact bounds, full
registry cache bypass, expiry and no resurrection, with diagnostics on and off.
The real Apple Foundation HTTP fixture holds eight transfers until explicitly
released, saturates the ordinary registry, recovers one coalesced survivor,
cancels its peer and all queued placeholders, and verifies exactly one HTTP
request for the survivor and none for cancelled queued URLs.

Existing receipt-time tests retain persisted network provenance, Age plus elapsed
time, reopening without resetting freshness, expiry requiring Foundation
validation, and fallback for missing/untrustworthy metadata. Apple CI additionally
tests real HTTP receipt storage and conditional validation. Full host regression,
compiled Hermes snapshot validation, iOS cross-build and Mach-O checks are required
before acceptance; Apple-only tests are explicitly skipped on Linux.

## Device evidence and freeze

Build 82 reports E to F added 215 cache checks: 197 direct hits, 18 Foundation
local-cache fetches, zero additional network fetches and zero new receipt stamps.
Direct delivered consumers increased by 198 (coalescing differs from hit groups).
All direct hits were delivered within 250 ms; 260 additional library onLoad
callbacks also fell within 250 ms. Accidental close/reopen makes F a mixed test,
not an uninterrupted scroll-back test, but does not invalidate cache evidence.

The 313 earlier cumulative 1–5-second queue waits remain real observations. They
are not proven harmless, all cold, or a visible device bottleneck. E/F show zero
budget refusals, lookup spills and transport errors; peak ordinary occupancy was
73/512, queued 67, consumers 77. Cache lookup groups peaked at 32/512 with two
workers; all lookup operations/lane waits were within 250 ms. One detached task
completed within five seconds with no accumulation. Library live views peaked
at 130, mask 26; F ended at 60 live library views.

Earlier A/B used only old Foundation-local entries and correctly stored no new
receipt stamps. C then recorded 64 network arrivals and 64 stamps; D recorded
74 direct hits (77 delivered consumers). These short reports do not prove exact
expiry or persistent-clock correctness; controlled regression fixtures do.
Overflow recovery addresses a latent correctness contract independently of this
device evidence. Revisit throughput only if subsequent device behavior demonstrates
an actual remaining bottleneck.
