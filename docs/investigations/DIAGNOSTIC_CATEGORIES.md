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
