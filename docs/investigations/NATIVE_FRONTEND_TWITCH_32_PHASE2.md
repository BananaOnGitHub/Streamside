# Twitch 32.0 native frontend — Phase 2 candidate

This is an implemented, cross-compiled diagnostic candidate. It has **no physical-device acceptance result**. Existing-session recognition, real followed-channel results, an observed RN baseline, runtime isolation on iOS, signing continuity and measured savings remain unverified. Host emulation and successful ZIP packaging do not establish those results.

## Preserved development state

Work stays on `feat/native-frontend`, following Phase 1 commit `76eb97733fbf11be02dc30d97ef56b4ae6019197` and the recovered development base `f5cacb0e45fb0617b2f44c536cd25f9129763951`. Other development branches and the earlier diagnostic framework are preserved. The old public main was not used as the implementation base. [Phase 1](NATIVE_FRONTEND_TWITCH_32_PHASE1.md) retains the recovery and binary investigation evidence.

The build accepts only the inspected decrypted IPA:

| Identity | Required value |
| --- | --- |
| Application | `tv.twitch`, version `32.0`, build `263110145453907615` |
| Donor IPA bytes | `201278706` |
| Donor IPA SHA-256 | `076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129` |
| Main executable SHA-256 | `f256c2a8576f4bafb26d4bd8f3c36470c0a6fc779e06fd1e254bbefa059875f1` |
| Original Hermes bundle SHA-256 | `1866099398b36a4fc98717dca5715547d6f16785bfa3dc8f74605fe98d1755d8` |
| App iOS floor | `16.4` |

The original JS bundle and all retained donor entries outside the four probe images and app Info.plist are compared byte-for-byte during packaging. Backend frameworks are unchanged. Original signature resources and provisioning profiles are omitted for re-signing. Individual donor image hashes, probe prefixes and ABI entry identities are pinned in [twitch32.json](../../native/twitch32.json). Final package identities and the exact build source revision belong in the companion artifact receipt [artifact receipt](NATIVE_FRONTEND_PHASE2_ARTIFACTS.json).

## Implementation

[SSNIntegration.c](../../native/SSNIntegration.c) contains donor lifecycle and symbol admission. [SSNAccount.c](../../native/SSNAccount.c) contains native service calls. [SSNFrontend.c](../../native/SSNFrontend.c) is a small UIKit table with diagnostics, account identity, up to 50 followed channels, refresh and export. It contains no donor class names, offsets, request operations or credential access. The dedicated `StreamsideNativeProof.framework` links System, Objective-C, Foundation and UIKit; the build rejects other link dependencies.

The frontend is selected by the compiled package mode before app launch. The native package changes the inspected Ultralight/RN eligibility function at `0x1033e5a80` to return false. The baseline retains the original gate. There is no in-app switch that enables RN in the native candidate.

Twitch's application delegate, dependency preparation, native account restoration, GraphQL configuration, notifications and routing entry handlers retain their original bodies. The original scene connection runs before the integration installs the diagnostic controller in Twitch's own window. This conservatively retains the original native root/bootstrap work; it is not a new standalone app process. Subsequent native routing and notification behavior requires device validation. Unsupported routes do not acquire a new frontend in this milestone, and a route that tries to start RN fails the runtime guard.

### Runtime isolation and observation

Twenty-five permanent entry probes cover Twitch's RN holder, warmup, factory accessor and bundle URL; React factory/runtime-factory, host/start, surfaces, instance, script/bundle loading and Hermes instance; Hermes factory variants, RootAPI, implementation and lowest VM constructor plus evaluation variants; and worklet factories/UI-runtime/runtime construction.

The packager writes probes into verified zero padding in each image's executable TEXT mapping. A single non-PC-relative stack instruction at each entry is replaced with a branch. Its trampoline preserves argument registers, all vector registers, LR and flags, calls a numeric observer, executes the original instruction and resumes at entry+4. Observer pointers occupy verified unused writable DATA tail padding. No executable memory is allocated or rewritten at runtime. All four patched images acquire a dependency on the diagnostic framework so its initializer can arm the observers. Loader/Objective-C initialization order on iOS is still an explicit device test.

The observer pointer is published with release/acquire ordering. Missing arming traps before entering donor code. Native-mode attempts to enter guarded RN/runtime paths save a failure report and stop the process with exit code 86; they never return a fabricated Swift/C++ value or silently run RN. `twitch_holder` is a separately reported native owner object, permitted to exist without a React host or VM. Counts are **entry attempts**, not completed allocations. Nested surface/factory counts are not unique runtime totals.

The UI says **UNVERIFIED** until a baseline with the identical source/probe identity has positively observed React factory, host, instance, surface, script loading, Hermes allocation/evaluation and worklet allocation. Arming alone cannot calibrate it. The comparison tool additionally requires reports from two distinct native process launches and the background/foreground sequence. An unobserved worklet baseline remains incomplete. Host-generated synthetic reports cannot qualify as device evidence.

The original React, Hermes and worklet images remain linked and mapped. This trial targets zero runtime creation; it does not demonstrate removal of their image-loading or native initialization overhead.

### Account and followed channels

The bridge reads only the presence of the native PMHTTP manager's authorization object. It does not inspect its fields, retain credentials, access the keychain, set headers, implement login or initiate a renewal scheme. The inspected PMHTTP `HTTP` getter and Objective-C `defaultManager` getter use the same native singleton storage. Twitch continues to own restoration, authorization changes, integrity checks, authentication failure and whatever renewal behavior its implementation provides.

Native `TKGraphQL.sharedInstance.currentUser()` supplies `CurrentUser.user.identity` through exported getters. The interface displays username and display name. Only after that succeeds does it call native `followedUsers(limit: 50, cursor: nil, blockedUserIDs: empty Set<UInt32>)`. This uses Twitch's existing Apollo promise/client/interceptor chain, including its authorization and client-integrity handling. There is no independent HTTP endpoint or JavaScript request/presentation path.

This first-page query returns `User` values without current live/offline state. Rows explicitly say live status is unavailable; they never infer offline status from an old broadcast date. Pagination, playback, chat and emotes are outside this candidate. The explicit empty client-side blocked-ID argument is not an integration with Twitch's native blocked-user provider; server-returned follow data is presented without adding such a local filter.

Native account notifications clear displayed data, cancel the candidate's pending promise and invalidate stale completions. Foreground activation and refresh recheck the native account. New candidate requests pause while the app is inactive. Missing authorization shows signed out. Rejected/timed-out requests clear results and show failure; they do not imply a successful session or successful empty list. Invalid-session handling depends on Twitch's unchanged native interceptor/account behavior and remains a device test. Network and integrity failures are intentionally not distinguished by serializing donor error descriptions.

### ABI admission

[SSNSwiftABI.h](../../native/SSNSwiftABI.h) declares the limited Swift calling conventions. The exact donor exports and instruction prefixes are checked before packaging and again against loaded addresses before native calls. Compiler-generated ARM64 callers are emulated to verify `x8` indirect results, `x20` self/context, direct String results, followed-user arguments and promise map closure/metadata arguments against the inspected donor instructions.

Model storage stays opaque. Complete metadata, value-witness sizes/alignment and getter functions come from the runtime. Value witnesses perform destruction; checked dynamic casts unbox bridged users. Runtime tuple metadata supplies element types/offsets. Native witness operations construct and verify the nil cursor. `Set<UInt32>` is built by a checked cast from an empty NSSet using a runtime-discovered Hashable conformance. The cursor's native witness table at `0x4bd780` records size 17 and stride 24; its single-payload enum operations were inspected and emulated directly from the donor. The tuple has 25 value bytes and 32-byte stride, checked against runtime metadata. No native account protocol witness slots or Swift model field offsets are guessed. Size, completeness, copyability, symbol or mapping mismatches disable service access and remain visible failures.

The bridge follows the documented [Clang Swift calling convention](https://releases.llvm.org/7.0.1/tools/clang/docs/AttributeReference.html), Swift's [runtime metadata declarations](https://github.com/swiftlang/swift/blob/swift-6.0-RELEASE/include/swift/Runtime/Metadata.h), [tuple metadata ABI](https://github.com/swiftlang/swift/blob/swift-6.0-RELEASE/include/swift/ABI/Metadata.h), [value-witness flags](https://github.com/swiftlang/swift/blob/swift-6.0-RELEASE/include/swift/ABI/MetadataValues.h) and [checked casting API](https://github.com/swiftlang/swift/blob/swift-6.0-RELEASE/include/swift/Runtime/Casting.h). The donor's exported Tomorrowland bridge and its closure dispatch were also inspected. These checks establish an admitted call boundary; they do not substitute for executing the service on iOS.

### Diagnostics and privacy

[SSNCore.c](../../native/SSNCore.c) keeps fixed atomic counters and writes at most 16 KiB per report. The app retains latest/previous reports separately for baseline/native, a bounded calibration marker and launch counters. A process restart rotates the prior report rather than treating a fresh counter set as the entire test. Export shares only those report files through the system share sheet.

Reports allow source/donor/mode identities, known numeric failure/state codes, capped channel count, probe counts, launch sequence, transition counts, device model/kernel version and timing/memory measurements. They exclude account names/IDs, channel names, tokens, headers, URLs, bodies, donor error strings and chat content. Account/channel presentation values stay outside the report API. No per-event text log or arbitrary object description is collected.

Memory fields use successful `TASK_VM_INFO` observations, with unavailable observations explicitly marked. Startup timing measures diagnostic-constructor-to-first-active and diagnostic-scaffold readiness. It excludes dyld and work before the diagnostic clock begins; it is not an end-to-end cold-launch measurement. Compare matched foreground conditions and use Instruments or an external launch measurement for a full launch profile. The candidate and baseline both include diagnostic overhead.

## Reproduce

From the `feat/native-frontend` checkout with Zig 0.14.0 and the exact donor:

```sh
python3 tools/native_frontend/build.py \
  --donor /path/to/tv.twitch-32.0.ipa \
  --zig /path/to/zig-0.14.0/zig \
  --mode both
```

Output is under `build/native-frontend/`: two IPAs, the two frameworks, generated admission headers and `artifacts.json`. Packaging verifies input hashes/encryption, all declared Swift exports/prefixes, probe relocation/space, framework identity/dependency closure, ZIP integrity and retained donor entries. It does not claim signing or installation success. Re-sign both IPAs using the same established application/keychain identity. No distribution profile, Apple signing credentials, Xcode or physical iOS device is available in this environment.

Host tests require the exact donor (`SSN_DONOR=/path/to/tv.twitch-32.0.ipa` if it is not in the neighboring donors directory), Python, a C compiler, Zig and `unicorn==2.1.4` on Python's module path:

```sh
python3 -m unittest discover -s tests/native_frontend -v
make test
make docs-check
```

The preserved Hermes regression tests require the donor/toolchain environment recorded in the validation receipt. The Phase 2 build itself uses Python's standard library and Zig, without a Swift compiler or Xcode.

Review device reports with:

```sh
python3 tools/native_frontend/compare_reports.py \
  baseline-latest.json native-latest.json \
  --previous-native native-previous.json
```

The tool fails closed on missing baseline observations, mismatched identities, incomplete arming, runtime attempts, failed account/list states or absent relaunch/transition evidence. Its successful output still requires reviewing actual screen/account/channel observations.

## Validation and blockers

The [validation receipt](NATIVE_FRONTEND_PHASE2_VALIDATION.json) records commands, source revisions, tool/dependency identities, logs and artifact hashes. The existing regression suite passed 218 tests with two Apple-only skips. Documentation checking passed. Both IPA hashes matched a repeated build in the same clean checkout and compiler cache; this is not a separate clean-machine reproducibility test. The completed host run has 23 Phase 2 tests: compiler/ABI emulation, all probe entries at two slides, unarmed/denied paths, evidence rotation/calibration, bounded/private report output and fail-closed comparison. This is host evidence only. Synthetic data exists only in explicitly labeled host test fixtures; the frontend has no sample account or channel data.

The existing regression suite and documentation check are recorded separately. Packaging success establishes the structure and inspected mutations of the unsigned candidate, not iOS compatibility.

| Device criterion | Current result |
| --- | --- |
| Native interface launches | Not tested on iOS |
| Existing session recognized/restored | Not tested on iOS |
| Real followed channels displayed | Not tested on iOS |
| Baseline proves RN/Hermes/worklet probes observe real startup | Not tested on iOS; zero-runtime claims unavailable |
| Zero guarded runtime entries across listing, refresh, transitions and reopening | Not tested on iOS |
| Comparable memory/startup measurements | Collection implemented; no device measurements |
| Signed installation; unauthenticated/invalid sessions; account changes; notifications/routing | Not tested on iOS |

Earlier host build failures are preserved as findings: Clang rejected the initial placement of Swift calling-convention attributes; required main-queue/string symbols were absent from the isolated link stubs; segment normalization required an explicit empty ad-hoc entitlement input; and a merged native display-name getter had an unrelated first symbol label. Final review also caught an initial cursor admission check that confused its 24-byte stride with its 17-byte value size; the check and derived tuple/optional checks were corrected against the actual donor witness table and tested before the final candidate. The declarations, link inputs and export-based admission were corrected before the final candidate was packaged. No failed device run has been replaced with a successful host result.

Physical-device testing and valid signing continuity are the next blockers. Follow [the device instructions](NATIVE_FRONTEND_PHASE2_DEVICE_TEST.md), export the evidence, and retain failures. If the native candidate closes during startup or refresh, recover its numeric report through the baseline installation using the same app container. A stop before observer arming may require an iOS crash report and is a failed/incomplete test, never zero activity. Development stops at this milestone; broader frontend work is not started.
