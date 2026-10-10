# Twitch 31.5 compatibility experiment — build 48

## Current branch status — build 87

`compat/twitch-31.5` is the active implementation branch. It advances directly
from build 72 (`645d34f2a3617f73072fa7d7d635af5ffa28b2f9`) through build 87
(`7f48f67ea9ee3273f6c312587fafac6e077b10ec`), followed by documentation-only
archive closure. The report version is `3.0.0-build.87` and framework bundle
version is `3.0.0.87`; documentation does not add another build number.

This includes the RN fractional-column correction, cache-first transport,
conservative network-proven receipts, bounded overflow recovery, and the
user-confirmed native Recent and footer fixes. Both RN and legacy UIKit paths
remain supported. The user observed the legacy path on vertical-enabled
broadcasts; its continued presence is intentional.

The four diagnostic branches are retained as documented `archive/` branches.
Their independent forensic probes are not merged into compat. See
[Diagnostic branch archive](DIAGNOSTIC_BRANCH_ARCHIVE.md) for each branch's
purpose, outcome, preserved source head and outstanding evidence limits.

The remaining sections are the original build-48 packaging record, not current
version restrictions or instructions to repeat the historical device trial.

This is the historical build-48 packaging report. Subsequent device results,
build-49 constraint cleanup and the sent-emote investigation are documented in
[Twitch 31.5 sent emotes](TWITCH_31_5_SENT_EMOTES.md). Version restrictions below
describe build 48, not the current compatibility-branch source.

## Scope and baseline

- Branch: `compat/twitch-31.5`.
- Parent: canonical `main`, `5a0cda0a05c9aa2be51e78fcb756eb1bbdf6b1d3` (build 45).
- No commits from `diagnostic/build46-image-result` or
  `diagnostic/build47-request-decision` were incorporated. Those branches and
  every archive branch remain unchanged.
- Normal Streamside feature set, built with `EMOTE_DIAGNOSTIC=0`. Existing
  operational counters/settings remain; temporary emote inspection, rolling
  playback and decoder provenance instrumentation are compiled out.
- No TwitchPlusK transplant, hook port, feature refactor or patcher changes.
  The only application-source change is the build label, now
  `3.0.0-build.48`; framework metadata is synchronized at `3.0.0.48`.

## Donor

| Field | Value |
| --- | --- |
| Bundle ID | `tv.twitch` |
| Twitch version | `31.5` |
| Twitch build | `262752111271985979` |
| Minimum iOS | `16.4` |
| Main Mach-O UUID | `6A2F9D5F-C563-3B41-9EDE-0CE9D0A0EFF5` |
| Main encryption ID | `0` (already decrypted) |

Donor SHA-256:
`718762b71095c11754b1f58ad01fb580852414e6d7f468fbb2236b7c2419e641`.

The supplied IPA is not overwritten or committed to this repository.

## Build and packaging

Linux cross-build using Zig **0.14.0**, repository stubs and the unchanged IPA
patcher/verification tools:

```sh
EMOTE_DIAGNOSTIC=0 ZIG=/path/to/zig-0.14.0/zig make ipa \
  INPUT_IPA=/path/to/tv.twitch-31.5.ipa \
  OUTPUT_IPA=/path/to/Twitch-31.5-Streamside-build48-test-unsigned.ipa
```

The first test run rejected a descriptive suffix added to the report build
label, because its metadata contract expects exactly `3.0.0-build.48`. The
suffix was removed, rather than weakening that test. The complete target was
then rebuilt and rerun successfully. There were no compiler, donor-header
injection, patcher or output-verification errors on the successful run.

## Verification results

- All **57 tests** passed, with Zig available; no tests were skipped.
- Both framework and dylib Mach-O layout/signature contracts passed.
- Patcher output ZIP CRC and duplicate-entry checks passed.
- Exactly one required `LC_LOAD_DYLIB` was added for
  `@rpath/Streamside.framework/Streamside`.
- Main executable has the same size and unchanged original load commands,
  instructions and file data. Only its command-count/size header fields and
  previously empty load-command padding changed.
- **4,251 donor ZIP entries are byte-identical.** No entries were removed.
  Only `Payload/Twitch.app/Twitch` and the app `Info.plist` changed. Exactly
  two entries were added: the Streamside framework binary and its `Info.plist`.
- In the app plist, only `CFBundleDisplayName` and `CFBundleName` changed, to
  `Twitch Streamside`. Twitch version, bundle ID and minimum iOS are unchanged.
- Packaged framework is byte-identical to the verified build artifact.
- All **67 thin arm64 Mach-O executable entries** inspected in the donor had
  no nonzero encryption ID. This is a static check, not a signing guarantee.
- `Assets.car` is unchanged, SHA-256
  `903ef7e19e7b553d60b252695b75888b173b019522e0f5a9c9de9a8eb6e4af96`.
- Normal framework contains no `Inspect Emote`, temporary rendering probe,
  rolling playback, decoder handoff or request-decision markers. Probe
  function/state names were also absent from its bytes.

## Known compatibility limits and device testing

Successful packaging is **not** proof of successful device launch or private
hook compatibility. No iOS device was available for this build.

1. `native_bridge_ready()` in `SSComposer.c` deliberately permits only Twitch
   `30.4.2`. The unified native Twitch-catalog adapter will therefore remain
   disabled on `31.5`. Its guard was preserved; native autocomplete/picker
   behavior must not be replaced by an unverified Swift layout adapter.
2. A static name scan found 27 of 28 inspected chat/composer target names in
   the donor. `TKIdentity` was absent, including from the main app and
   TwitchKit Objective-C class-name sections. The local-delivery enrichment
   hook checks this class before installation and is expected to remain
   unavailable unless the runtime supplies it elsewhere. WebSocket emote
   rewriting is a separate path. Name presence does not establish method ABI,
   ivar layout, hook installation or correct rendering.
3. Temporary diagnostic instrumentation is disabled; this experiment does not
   fix or prove resolution of the earlier animated/static-image investigation.

Sign the IPA with the tester's usual sideloading tool before installation.
Re-signing must cover the app, extensions and embedded frameworks. The output
is not installation-signed and the donor's old signature is invalid after
load-command injection. The existing bundle ID is retained, so it can replace
the current Twitch install depending on the signing tool's bundle-ID choice.

Suggested device checks: launch and Streamside settings; stream playback;
incoming third-party emotes; own sent messages; static/animated emotes;
composer insertion and native keyboard behavior. Note crashes, missing hooks
or absent features separately from successful package preparation.

## Delivered artifact

- File: `Twitch-31.5-Streamside-build48-test-unsigned.ipa`.
- Size: **191,809,952 bytes**.
- IPA SHA-256:
  `252cf68ab140756dabc194e1e8a45db6fa9b33ed59dee5ae5d293912c5dc4406`.
- Framework size: **408,128 bytes**.
- Framework SHA-256:
  `94e902f5025b2d3684f60ba24ccaa19dff8d736c62147ac8364a31cf978e2435`.

IPA/package hashes identify this particular locally verified build, not every
possible rebuild or a subsequently re-signed IPA.
