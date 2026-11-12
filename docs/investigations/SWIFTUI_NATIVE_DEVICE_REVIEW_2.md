# SwiftUI device review: donor-native logout and login

The restart report was subsequently supplied and validated; see
[restart validation](#restart-validation-report-5) for the resolved persistence check.
The initial review and its originally pending status remain preserved below.

## Build and preserved evidence

The tested pair identifies compiled source
`a454012f11c9bf47e2eea272eec8dacfc54412ca`, proof
`c9d05e19ae05c8e63627e12221afc4c3187a4151e35b5de80df8b2223c9db808`,
Twitch 32.0 build 263110145453907615 and the exact inspected donor. The
[package receipt](SWIFTUI_NATIVE_LOGOUT_DIAGNOSTICS_ARTIFACTS.json) identifies its
Actions build and local assembly. [The supplied report copies](evidence/swiftui-device-2/)
retain six original JSON files, including the superseded baseline report.
[Validation and input hashes](evidence/swiftui-device-2/validation.json) preserve
archive/file identities, stage mapping and the checks performed. The original ZIP
remains outside Git at `artifacts/device-validation/swiftui-device-2/nativetesting.zip`;
AppleDouble metadata is not copied into the repository.

The tester maps native reports 1–3 to before logout, the logged-out welcome and
after completing Twitch login. Report 4 was an extra observation after entering
a stream with chat. This review does not implement or accept Streamside playback
or chat; that final sample exercises Twitch's existing interface only.

## Measured sequence

All four native reports have launch sequence 7, first-active time 808 ms,
scaffold-ready time 585 ms, matching device/build/proof, increasing uptime and
nondecreasing cumulative probe counts. They describe one recorded native launch,
not four restarts. All four images remain armed, all failure bits remain clear,
and all reports confirm matching baseline calibration.

| Report and user-described stage | Uptime | Root owner | Native account/list result | Holder entries | Guarded entries |
| --- | --- | --- | --- | --- | --- |
| 1: before logout | 18.425 s | Streamside (`1`) | Ready, 50 channels | 0 | All 24 zero |
| 2: logged-out welcome | 67.683 s | Another controller (`2`) | Signed out, zero channels | 0 | All 24 zero |
| 3: after Twitch login | 130.700 s | Another controller (`2`) | Ready, 50 channels | 0 | All 24 zero |
| 4: after stream/chat visit | 329.862 s | Another controller (`2`) | Ready, 50 channels | 1 | All 24 zero |

The matching baseline is a genuine positive control: RN factory, host and instance
entries are present, two surface entries, bundle/script loading, two Hermes
runtime/implementation/engine entries, evaluation counts of 11 and one worklet
runtime. Its source/proof/device match this native sequence. The previous baseline
belongs to the older `026bf6c` build and is retained as history, not calibration
for the new sequence.

## What this establishes

The prior uncertainty about presentation takeover is narrowed: sampled root
ownership changes from Streamside to another controller in the same recorded
native launch. Diagnostics remain usable after that change. Together with the
user's described screens, this supports Twitch taking over the original window's
root with its legacy native route. The reports do not expose controller classes
or reconstruct every intermediate navigation step.

More significantly, the native account adapter observes signed-out state with old
results cleared, then successfully retrieves the account and 50 follows after
Twitch login. In [the preserved account bridge](../../native/SSNAccount.c), an
account change clears saved presentation results and cancels pending work; state
4 is produced after successful native current-user and followed-users requests.
The post-login result therefore provides evidence that this tested first-party
login produces a session usable by the existing native GraphQL path. It is not a
third-party OAuth-token substitution or a fabricated saved list. Account identity
is intentionally absent from the diagnostic files.

All monitored RN host/factory, surface, bundle/evaluation, Hermes and worklet
entries remain zero through the tested logout/login sequence. Counters are
cumulative and native guards are active, rather than probes being installed only
at export time. This supports an RN/Hermes-free **observed donor-native login
route**, within the inspected instrumentation coverage. It does not prove every
possible login method, recovery/challenge flow or uninspected runtime entry.
This does not classify any web content displayed inside the login UI; the
instrumented boundary is the app's RN/Hermes/worklet entry paths.
The tester subsequently confirmed Twitch username/password login. The reports
themselves intentionally omit login method and credential data. Social providers
and additional verification/recovery challenges were not established by this test.

## Why `twitch_holder=1` is distinct

The original probe plan identifies `twitch_holder` at Twitch `0x1033acce0`, the
native `TwitchRNHost` holder initialization entry. It was explicitly non-guarding
before these results: [Phase 2's probe design](NATIVE_FRONTEND_TWITCH_32_PHASE2.md)
permits this native owner object without a React host or VM. The actual lazy
React factory accessor is a different, guarded entry at `0x1033bf864`.

Report 4 records one holder entry attempt, while `twitch_factory`, `rn_factory`,
`rn_host`, every surface/bundle probe, Hermes constructors/evaluation and worklet
constructors all remain zero. A holder entry is not proof of a completed
allocation, a unique runtime count or RN startup. Its appearance somewhere
between reports 3 and 4 cannot be attributed specifically to chat rather than
stream presentation, navigation or another dependency without further tracing.
No guard was relaxed to accommodate this result. The existing comparison tool
already checks only guarded entries for runtime attempts; it does not reject an
allowed holder count.

## Remaining boundary and next work

The outcome resolves the earlier question of whether the observed native-mode
logout/login route starts a monitored RN runtime: no such entry is recorded,
and authenticated native requests work afterward. It also changes the next
investigation priority. A usable first-party donor-native login route now has
device evidence; an RN hosted portal is not the only known possibility.

SwiftUI still loses ownership of the main interface after logout. A controlled
SwiftUI login entry, validated native presentation/completion boundary and return
to the SwiftUI shell remain implementation work. Do not bypass native account
management, guess a private Swift ABI, or add a custom credential form. The
existing [authentication investigation](SWIFTUI_NATIVE_FOUNDATION_TWITCH_32.md)
continues to describe the inspected RN route and unproven provider/challenge
coverage; this device result supplements that historical scope.

The tester subsequently reported that fully closing and reopening the native app
returns to SwiftUI, and offered a report from that restart. That additional report
has not yet been supplied; its new launch sequence, restored account/list state
and runtime counts remain to be checked. The unchanged full-sequence comparison rejects using these
same-launch snapshots as separate launches, reporting missing distinct process
launches and an incomplete foreground/background/reopen sequence. That expected
failure is preserved in the validation JSON; the test was not weakened.
The next evidence step is to review the already captured restart report, rather
than ask for an unchanged test to be repeated. It can verify the distinct launch,
restored native account/list result and zero guarded runtime counts. No new build
is needed.

No source code, runtime gate, authentication request, CI toolchain or package
bytes are changed by this evidence review. Documentation validation is recorded
with the review commit. Performance is not inferred from these different UI
states or the tester's exploratory stream/chat visit.

## Restart validation: report 5

The subsequently supplied [report 5](<evidence/swiftui-device-2/native-latest 5.json>)
identifies the same donor, compiled source, proof and device as reports 1–4.
Its SHA-256 is `45973a12ff4ec81a342d6daa88db3b0edb3f9aa15ee99f0a4ea15738b70d9079`.
[The restart validation receipt](evidence/swiftui-device-2/restart-validation.json)
records its original bytes/hash and the full comparison outcome.

The recorded native launch sequence advances from 7 to 8. At 9.096 seconds of
uptime, the window root belongs to Streamside again (`ui_root_owner=1`), the native
account/list state is ready (`4`), and 50 followed channels have been retrieved.
All four instrumented images are armed, no failure bits are set, matching baseline
calibration is present and **all 25 probe counts are zero**, including the optional
holder count. The previous launch's holder entry is still preserved in report 4;
counters begin anew for the restarted process.

The unchanged strict comparison passes using the matching baseline, report 4 as
the prior native launch and report 5 as the current launch, with no consistency
failures. This supplements the tester's reported full close/reopen and return to
SwiftUI with instrumented evidence of session restoration and authenticated native
account/followed-channel requests in a distinct launch. The earlier same-launch
comparison failure remains in `validation.json` as historical evidence; it was not
rewritten into a pass.

For the observed Twitch username/password route, the evidence now covers logout,
native first-party login, usable native GraphQL access and restoration after a
full restart without monitored RN/Hermes/worklet entry attempts. The remaining
frontend boundary is controlled SwiftUI login presentation and an in-process
return to the SwiftUI shell after authentication. Startup remounting alone does
not implement that handoff. Other providers/challenges and untested routes remain
outside this result; no new performance or playback/chat acceptance is inferred.
No code, compiled candidate or validation requirement changed for this follow-up.
