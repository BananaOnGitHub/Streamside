# SwiftUI account transitions and navigation ownership trial

Investigation started from `93e4510868f8ecbfa63edef1b623db974a095b55` on
`feat/native-frontend`. This follows the [device review](SWIFTUI_NATIVE_DEVICE_REVIEW_2.md):
password login restored the account without monitored RN/Hermes activity, but the
legacy native router owned the window until the next process launch.

## Exact donor and observed routing

Inspection and local packaging require Twitch 32.0, build 263110145453907615,
IPA SHA-256 `076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`.
The inspected main image is admitted through the existing `native/twitch32.json`.
Addresses below are unslid main-image addresses, obtained from Objective-C class
metadata, LC_FUNCTION_STARTS, and bounded ARM64 branch inspection. They describe
static relationships, not an exhaustive executed authentication call graph.

- `StandardAccountManager` has no Objective-C methods. Its fields include native
  authentication state, authenticator/failure subscriptions, an authentication
  action queue, and the native router. Account processing near `0x10075b384`
  references UserDidLogIn (`0x10075be98`), posts a native notification
  (`0x10075bfa0`), and references logout/token-change notifications. The next
  processing region, `0x10075c788`, references UserUpdated (`0x10075cf80`) and
  UserIsAvailable (`0x10075df8c`), with a notification post at `0x10075e3ec`.
  Existing verified TwitchIdentity name getters observe all five signals without
  reading notification payloads. No new private account-manager call is needed.
- `AppRouter` registers native account observers in `0x10399b1e4`. Its Objective-C
  `userUpdated:` thunk at `0x1039aa77c` selects worker `0x1039aa788`; that worker
  calls routing function `0x10399bb40` at `0x1039aa900`. This routing function has
  three direct calls to root installer `0x1039adb28`. Other installer callers are
  `0x10399b644`, `0x10399cf7c`, and `0x1039adc48`.
- The installer at `0x1039adb28` updates the child of an existing native
  `RootViewController`, or builds that wrapper, attaches its child through UIKit,
  and calls `UIWindow.setRootViewController:` at `0x1039adc2c`. After the setter it
  only releases objects and returns; it does not require a read-back of the root.
  When Streamside owns the root, the existing-wrapper branch does not apply.
- `SceneDelegate.sceneDidBecomeActive:` (`0x1030b1904`) enters worker
  `0x1030b64c8`; `sceneWillEnterForeground:` (`0x1030b1954`) enters native
  AppDelegate work at `0x1030af20c`. These inspected bodies have no direct window
  root setter. This does not exclude indirect/deferred routing. Streamside leaves
  scene callbacks and router observers running and controls subsequent writes at
  the public UIKit setter boundary instead of replacing account handlers.

Full temporary disassemblies remain outside the source tree. This record retains
selected relationships; no donor binary or disassembly is a public CI input.

## Implementation boundary

`SSNWindowOwnership.m` is the dedicated window integration layer. It validates
UIKit's public setter argument/return types and rejects a window subclass override.
It chains the original setter for every other window. In native mode, the original
scene bootstrap completes before ownership is installed. SwiftUI then remains the
strongly held root, and subsequent donor root requests on that window are refused.
Baseline mode does not install the interception. Private Swift routing functions,
field layouts and protocol witnesses are neither invoked nor modified.

The Swift host classifies a requested controller through bounded public UIKit
containment (at most 64 visited controllers), without loading donor views. It keeps
one existing hierarchy containing Twitch's native LoggedOutViewController. Signed
out users can present that hierarchy using **Sign in**. Streamside adds a close
button through an owned navigation controller; closing dismisses the UI, without
claiming to cancel provider work or change Twitch's session. Donor login,
verification, integrity and account handlers remain responsible for authentication.
No credentials or notification payloads cross the owned presentation boundary.

The existing native currentUser request must produce an authenticated presentation
state before the modal is dismissed. A notification or saved-auth presence alone
cannot complete sign-in. Follows loading is not required for this return: verified
account state is already available in phase 3. Account-change invalidation and
request generation checks continue to remove stale results.

The existing two-finger diagnostic gesture remains available over authentication.
Reports add `navigation_guard_armed` and five numeric `navigation_events`, ordered:
blocked root requests, sign-in presentations, verified returns, navigation failures,
manual closes. Failure sets bit 11 and disables sign-in. Runtime probes, guard
flags, startup eligibility patch and positive-control requirements are unchanged.

## Validation and limits

Initial host run: 29 tests ran, with the ABI setup failing because the required Zig
compiler was not configured. Re-running with the existing pinned compiler passed
all 35 tests. After adding numeric navigation evidence coverage, **36 host tests
passed**. No failed run is counted as success.

Apple build validation includes pure Swift account-return tests and a real UIKit
simulator fixture exercising the production window setter implementation: baseline
pass-through, other-window isolation, owned-root rejection of donor/nil writes,
subclass-override refusal and repeat-install refusal. This fixture uses synthetic
owned controllers and no donor/session. Component admission requires its successful
receipt; simulator results do not establish donor login correctness.

Physical device acceptance remains pending for this trial. In particular, reuse of
Twitch's constructed login hierarchy, its provider/verification presentations,
account notification ordering, and navigation side effects require device evidence.
The hook controls the original scene window; replacement of the entire window or
a new scene is not claimed as supported. The emergency gesture also belongs to that
window. Missing native sign-in hierarchy is reported as unavailable; there is no
legacy-home or RN fallback.

## Device check

1. Install the matching baseline with Feather, open Twitch, exercise its normal
   interface, and export diagnostics with two fingers held still for one second.
2. Replace it with the matching native IPA, preserving its app data. Open it;
   confirm the account and follows, then export a report.
3. Sign out. Streamside should remain visible and offer Sign in. Export a report.
4. Open Sign in; check Close sign-in returns to Streamside. Open it again and use
   Twitch username/password. Successful account verification should return to
   SwiftUI automatically, with real follows. Export a report.
5. Refresh, background/reopen, then fully close/reopen; export another report.
   If any step fails, export from the current screen using the two-finger gesture.

Expected: window root remains Streamside, navigation guard is 1, navigation
failures are zero, runtime monitoring is complete and calibrated, and all guarded
RN/Hermes/worklet entries remain zero. The allowed native `twitch_holder` remains
reported separately. Social sign-in, verification challenges, invalid sessions and
other provider routes require separate testing; password success does not cover them.

## Apple validation attempts

[Run 43156050297](https://github.com/BananaOnGitHub/Streamside/actions/runs/43156050297)
at `9cd05478e8d30a7597119ef7f6d1ca5717a04df1` compiled and linked the baseline
framework and passed pure Swift model tests. It failed while compiling the new
simulator fixture: its other-window variable was unused in baseline mode under
warnings-as-errors. No components or IPA were distributed from this failed run.
The fixture now exercises baseline other-window routing as well. Failure logs were
retained outside the repository; this record preserves the meaningful outcome.
