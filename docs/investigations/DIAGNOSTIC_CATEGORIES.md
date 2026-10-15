# Scoped diagnostic collection for 3.1.0

## Baseline and scope

The shared change starts from `dev/3.1.0` at `a785256` (build 6).
The chat integration starts from `fix/rn-chat-gaps` at `a9de281`
(build 9). This changes diagnostic infrastructure, not functional playback,
emote/composer algorithms, message delivery or the unresolved display bug.

The baseline's `TASDiagnosticsEnabled` switch checks only the ordinary disk
writer. Playback prepares manifest statistics and detail strings before that
check, every report formats every subsystem status, and the file can append
512 KiB of HLS traffic. Image-demand, animation, provenance, legacy palette
and rolling chat probes have independent compile-time gates and collectors.
Operational counts and diagnostic-only work must not be treated as equivalent.

## Shared design

`TASDiagnosticPolicy` owns a validated configuration word, six independent
48-entry/384-byte event rings and bounded export. Existing log entry points
classify events before label creation, formatting or storage. Playback's
diagnostic-only detail/manifest-statistics blocks are guarded at their call
sites; interception, route registration, alternate selection, response
delivery and operational counters remain outside those guards.

Preferences use `TASDiagnosticConfigurationV1` in NSUserDefaults. Minimal /
Summary is the default, including migration from the previous master switch.
All changes are launch-applied so diagnostic samplers/bridges can be omitted
without replacing an active React tree or altering its hook ordering. The
status row/report distinguish active versus saved configuration. Native
settings use grouped table rows, category UISwitch controls, preset/verbosity
checkmarks and accessibility labels.

Summary retains essential/failure events and exports up to four per category;
Detailed exports up to twelve. Disabled categories do not call their status
exporters. General supplies a compact version/configuration/privacy header,
compatibility admission and essential failure totals, without playback traces.
Accepted/retained/overwritten/shortened/export-omitted counts distinguish
coverage limits from disabled collection. Clearing ordinary rings preserves
operational counters, feature state and specialized traces.

Obsolete disk logs are removed on startup, not appended to new process-local
evidence. Historical investigation records and candidate hashes remain intact.
The report no longer contains a 512 KiB prior-launch dump.

Experimental collection is owned by exactly one category: library-demand and
palette by Composer; decoder/header comparison by Image Transport; matching
and animation by Rendering; rolling transcript/rewards by Chat. Corresponding
Detailed launch selection is required in addition to the compile flag. The
demand bridge and diagnostic-only native hooks are not installed otherwise.
Disabled collector entry points return before transient request/header/body
inspection or sampling. Basic feature counters may still be updated.

## Validation boundaries

The configuration regressions execute the production policy, actual preference
save/load and actual report assembly with host Foundation adapters. They cover
presets, malformed words, pending versus active settings, module availability,
independent category export, raw-URL/channel label privacy, bounded ring floods,
retention isolation, export limits, truncation and clear semantics. Disabled
collection is tested with intentionally unreadable diagnostic detail/request
pointers to establish early return before inspection.

The existing production URL-protocol lifecycle fixture also runs with the
actual diagnostic query returning Minimal: interception, manifest rewrite
handoff, completion and cancellation still pass. This is not live AVFoundation
or an actual ad-bearing device playback test. Compiled Hermes gates retain the
exact Twitch 31.6 donor and pinned runtime, including 32 accepted snapshots and
7,344 virtualization calculations. Native artifact and final IPA checks remain
separate from device validation.

The cache receipt host fixture uses the already documented Clang 19 alignment
instrumentation workaround from the chat branch. Assertions, other sanitizer
checks and production compilation are not disabled. Apple Foundation/Xcode
integration and the native settings' on-device appearance remain separate
validation requirements.

Use the [diagnostics guide](../features/DIAGNOSTICS.md) and
[troubleshooting instructions](../TROUBLESHOOTING.md) for configuration and
capture. Final branch commits record suite outcomes and candidate identities.

## Validated candidates

The final development candidate runs 179 host tests: 178 pass and the
Apple Foundation/Xcode-only check skips. The integrated chat candidate runs
191: 190 pass and the same Apple-only check skips. Exact donor/runtime inputs
are supplied, so the compiled virtualization check is not skipped. It passes
32 accepted snapshots and 7,344 calculations on each branch. The chat gate
also passes the nine existing observer tests, two new policy/admission tests,
and both compiled installer/factory execution paths with the actual unchanged
reward renderer.

Normal and all-probe native artifact contracts pass on both branches; the
chat-only diagnostic build also passes. Both finished IPAs pass independent
verification against their corresponding final frameworks. The shared policy
and subsystem gates are identical between branches; differences are the chat
module/graft/collector/export integration and branch build identity. The
enabled chat HBC retains build 9's SHA-256
`bc83ad8ebafedb6654d128210f8506628035f4ad105fda53e7c16aa42f4245ce`.

| Branch | Candidate | Compiled flags emote/demand/chat | Bytes |
| --- | --- | --- | --- |
| `dev/3.1.0` | `Twitch_31.6_Streamside_3.1.0-build.10_diagnostic-settings_unsigned.ipa` | `0/0/0` | 194,478,378 |
| `fix/rn-chat-gaps` | `Twitch_31.6_Streamside_3.1.0-build.11_scoped-chat-trace_unsigned.ipa` | `0/0/1` | 194,496,893 |

- Build-10 IPA SHA-256: `84dc1d4ab787a1fdc3be866b87cc8c9d901d6680ecc8a43e2f795eaf7b14320a`.
- Build-11 IPA SHA-256: `c64dab783d9aaff3dca7e66b3b242ff89a463d8aa54b439f29933be82b7b990c`.

These are unsigned test candidates, not a release or device acceptance. In the
chat candidate, keep the existing functional third-party-emote feature enabled,
select Chat / Detailed, and relaunch before capture. UI appearance, real-device
temperature/latency, live ad suppression and the missing-row symptom remain
device validation items, not inferred host-test successes.


## Settings layout follow-up (builds 12 / 13)

The device screenshot of build 11 exposed excessive configuration on the main
Streamside page, repeated relaunch labels, and truncated category details.
Build 12 (development) and build 13 (chat investigation) move configuration and
report actions to a dedicated Diagnostics subpage. Preset and Detail each use
one value row opening a native action sheet; iPad sheets anchor to that row.
Only Custom inserts category switches. A single preset-specific sentence
replaces the all-presets paragraph. A pending restart note appears only when
saved category/detail bits differ from active capture, and disappears on
revert or next launch; the Custom selection marker alone is not a collection
change. Detail changes preserve preset identity instead of exposing Custom
switches automatically. Preset selection still applies its recommended detail.

The selector alert owns its page through an associated object for the lifetime
of its plain-C action blocks, including cancellation. The chat trace collector,
payload, graft and functional hooks are unchanged. Existing build 10/11
artifact hashes above still identify those original candidates.

A production-function host adapter checks preset/detail independence, Custom
section insertion, report section mapping in ordinary and compiled-emote
builds, launch-applied persistence and the pending/revert distinction. Native
build checks cover the Objective-C callbacks; device layout and interaction
remain to be checked on iOS.

Validation of the compact-page source: the development suite ran 180 tests
(179 passed, one Apple-only skip); the investigation suite ran 192 tests
(191 passed, one Apple-only skip). The donor/Hermes settings and virtualization
gates and the compiled rolling chat gate passed. Both ordinary native/DEB
builds and emote+demand probe variants passed artifact verification; the
investigation variant also enabled the compiled chat module. The final
candidates use ordinary flags for build 12 and chat-only flags for build 13.
No playback, emote, or chat functional algorithm was changed in this follow-up.

Both finished unsigned IPAs passed independent verification against their
final framework artifacts. These are test candidates requiring signing and
device UI validation, with the original Twitch 31.6 donor.

| Candidate | Bytes | SHA-256 |
| --- | --- | --- |
| `Twitch_31.6_Streamside_3.1.0-build.12_compact-diagnostics_unsigned.ipa` | 194,479,827 | `479176fc016314e331ccafa3f67895dece9783e5fef448bc2bc9400e52fd91c2` |
| `Twitch_31.6_Streamside_3.1.0-build.13_compact-chat-diagnostics_unsigned.ipa` | 194,498,251 | `920d02270f14c0b58f44c6c065aad90afddcba5f221bfda7e0615dac98cfb884` |
