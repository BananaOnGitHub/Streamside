# SwiftUI device review: persistent ownership during authentication

The later [background/foreground follow-up](#backgroundforeground-follow-up-report-6)
resolves the missing event observation. The initial review and its original strict
comparison outcome are preserved below.

This reviews the [authentication ownership trial](SWIFTUI_AUTHENTICATION_OWNERSHIP.md),
compiled and packaged at `1c059c1fb8ffb0fb8e76621f7e12c4bb6bf57035`, proof
`f072ea03b43c891af10727131e4f8f024ec5917efc44cebf07719940ebc73ce6`.
The [package receipt](SWIFTUI_AUTHENTICATION_OWNERSHIP_ARTIFACTS.json) retains donor,
toolchain, CI and IPA hashes. The tester reports successful logout, Twitch sign-in
presentation, return to SwiftUI, refresh, background/reopen and full close/reopen.

## Evidence identity and review

[Original JSON copies](evidence/swiftui-device-3/) retain seven files from the supplied
archive. [Validation and hashes](evidence/swiftui-device-3/validation.json) record
archive/member identities, stage mapping, consistency checks and the unchanged
strict comparison outcome. Archive SHA-256:
`b4aa8e8e6369c573b7e40dcb0715eba832742492bc3983654c5cd589dbfec135`.
The original ZIP is preserved outside Git at
`../artifacts/device-validation/swiftui-device-3/nativetesting.zip`; AppleDouble
metadata is not copied into the source tree. The reports contain numeric diagnostic
state and build/platform identifiers, without account/channel names, credentials or
request content.

Matching files identify Twitch 32.0 build 263110145453907615, exact donor SHA-256
`076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`, device
`iPhone17,1`, kernel `27.0.0`, and the source/proof above. `baseline-previous.json`
belongs to older source `a454012` / proof `c9d05e19`; it is preserved but excluded
from the current positive control and comparison.

## Observed sequence

Every native report has all four instrumented images armed (`15`), failure bits
clear, matching baseline calibration, navigation guard armed (`1`), Streamside root
ownership (`1`), and **all 25 monitored entry counts zero**. This includes the
optional native holder as well as the 24 guarded runtime entries.

| Report | Stage | Launch | Uptime | Account/list | Blocked roots / sign-in opens / verified returns |
| --- | --- | --- | --- | --- | --- |
| native-latest.json | Initial authenticated SwiftUI | 13 | 8.023 s | Ready, 50 follows | 0 / 0 / 0 |
| native-latest 2.json | Signed out | 13 | 27.824 s | Signed out, zero follows | 1 / 0 / 0 |
| native-latest 3.json | After native sign-in | 13 | 72.635 s | Ready, 50 follows | 2 / 1 / 1 |
| native-latest 4.json | Refresh/list interaction | 13 | 109.787 s | Ready, 50 follows | 2 / 1 / 1 |
| native-latest 5.json | Full close/reopen | 14 | 8.657 s | Ready, 50 follows | 0 / 0 / 0 |

Within launch 13, uptime and cumulative counters are consistent. Navigation
failures and manual-close counters are zero throughout. The two blocked root
requests and the presentation/verified-return counters support the intended
navigation boundary actually being exercised, rather than SwiftUI only appearing
again at process startup. The first logged-out snapshot clears the account/list
presentation; subsequent native requests reach ready state with 50 results. The
tester confirms the corresponding native login and SwiftUI screens.

Launch 14 independently records the account and 50 follows restored in SwiftUI.
The launch sequence advances, constructor-to-active/scaffold timings reset, and
navigation counters start at zero in the new process. This establishes a distinct
recorded launch, consistent with the tester's full close/reopen.

The matching baseline records genuine positive-control activity: RN factory, host
and instance each 1; surface/root-surface entries 3; bundle/script entries present;
Hermes runtime/implementation/engine entries each 2 and evaluation counts 11;
worklet runtime 1. Baseline navigation guard is correctly zero. Thus the native
zeros are backed by actual observations of the instrumented runtime paths in the
matching baseline, rather than missing instrumentation being treated as success.
These are entry counts, not unique completed runtime allocations.

## Remaining lifecycle evidence gap

All supplied native snapshots have `backgrounds=0`. Launch 13's foreground count
advances from 1 to 2, but that alone does not establish a recorded background
transition. The tester reports that background/reopen worked; the snapshot after
refresh contains no recorded background event, and the reopened process starts
fresh counters. The archive contains no `native-previous.json` from the final
export that could preserve the prior process's later cumulative counters.

The existing comparison was run without changes using matching baseline,
`native-latest 4.json` as prior launch and `native-latest 5.json` as current launch.
It returns `evidence_incomplete_or_failed`, with exactly one failure:
`Foreground/background/reopen sequence incomplete`. Source/proof, donor, device,
probe coverage, counts, account/list success and distinct launches pass its checks.
The result is retained verbatim in the validation receipt. No counter is edited,
missing event inferred, or acceptance check relaxed.

If retained, `native-previous.json` from the final export is the next evidence to
inspect. It may cover the background/foreground interval without repeating login
or generating a new build. Until then, the full instrumented lifecycle acceptance
remains incomplete despite the tester's successful observed behavior.

## Measurements and scope

Snapshot physical footprints are 68.81 MiB initially, 71.80 MiB signed out,
87.99 MiB after sign-in, 87.11 MiB after refresh and 66.63 MiB after restart.
Launch 13's peak observed footprint is 129.28 MiB; the baseline snapshot is
346.53 MiB at 52.805 seconds. Constructor-to-first-active is 1186 ms baseline,
672 ms native launch 13 and 780 ms native launch 14. These are comparable recorded
fields, with different screens/uptimes and one observed sequence. They are not a
controlled performance benchmark, a cold-start distribution or total process
startup: the clock starts at the diagnostic constructor and excludes earlier work.

The in-process SwiftUI ownership and native sign-in return now have device evidence,
resolving that pending boundary in the earlier trial. The verified account/list
state, session restoration and matching positive control support this tested native
path without monitored RN/Hermes/worklet entry attempts. Coverage does not extend
to every donor route, whole-window replacement, other scenes, or arbitrary embedded
web content. Login provider was not specified for this run; prior password-specific
evidence belongs to the previous build. Manual close/retry, social providers,
verification/recovery challenges, invalid sessions and account switching are not
established here. No Streamside playback/chat feature is implemented or accepted.

This review changes evidence only. It preserves the source, probe guard policy,
packaged IPA identities and strict comparison requirements; no new build is needed.


## Background/foreground follow-up: report 6

The supplied [report 6](<evidence/swiftui-device-3/native-latest 6.json>) records
launch 15 at 68.279 seconds, with **3 foreground activations and 2 background
transitions in that process**. Its SHA-256 is
`982be9174c32f0dc170f5834d4ecc169c64d103701d1038ee087b4ecec2cd2cc`.
The [follow-up validation receipt](evidence/swiftui-device-3/background-validation.json)
preserves its identity, exact assertions and the relationship to earlier evidence.

The report matches the source, proof, donor, device and OS of the positive-control
baseline and reports 1–5. All four probe images are armed (`15`), baseline calibration
is confirmed, failure bits are zero and **all 25 monitored entry counts are zero**.
SwiftUI remains the root (`1`), the navigation guard remains armed (`1`), and the
native account/list state is ready (`4`) with 50 followed channels. Its five
navigation event counts are zero: this process records restored-account use and
lifecycle transitions; it does not repeat the earlier login presentation. The
physical footprint snapshot is 79087984 bytes, approximately 75.42 MiB, without a
new performance claim.

This resolves the missing instrumented background/foreground observation. Taken
together, the matching-build reports cover the observed logout/login/refresh in
launch 13, account/follows restoration after full close/reopen in launch 14, and
background/foreground use with restored account/follows in launch 15. The monitored
runtime guards and zero entry counts remain intact in each supplied native sample.
No new package or repeat login is needed for this follow-up check.

The original strict single-sequence comparison remains unchanged: its launch 13
input still lacks a background count and its exact incomplete result remains in
`validation.json`. This review does not change counters, reverse process order,
weaken that checker, or describe the separate scenarios as one continuous launch.
No later restart after launch 15 is supplied. The background gap is resolved by a
separate matching-build device observation, alongside the already retained restart
evidence, rather than by claiming the old comparison has become a pass.

The broader limits above still apply: other providers, verification/recovery,
manual cancellation/retry, invalid-session behavior, account switching and other
scenes or whole-window replacement are not established. This follow-up changes
only investigation records and preserves the original source and IPA identities.
