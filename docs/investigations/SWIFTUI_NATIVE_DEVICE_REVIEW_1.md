# SwiftUI device review: account success and logout root takeover

## Candidate and evidence

The tested native report identifies source
`026bf6cbfa9f990dfe0ff2d46df17c63f5bda57c`, proof
`2babc0a0891d8ca8b77cd199f660616d955c25d51bf694f499be6b08041cc9c3`,
Twitch 32.0 build 263110145453907615 and the exact inspected donor. The
[privacy-safe report copies](evidence/swiftui-device-1/) and
[input identities](evidence/swiftui-device-1/inputs.json) preserve four JSON reports
and the original attachment hashes. Original screenshots and the ZIP are retained
outside Git in `artifacts/device-validation/swiftui-device-1/`; AppleDouble ZIP
metadata and screenshots are not copied into the public repository.

The tester confirmed that each IPA replaced the preceding installation; the
baseline and native apps were not installed side by side. The native report was
exported **before logout**, because diagnostics could no longer be reached afterward.
This ordering is essential to interpreting the counters.

## Confirmed observations

The tester reports that SwiftUI launched, displayed the existing account and the
first 50 follows, both refresh actions worked, and navigation was smooth.
The matching native report records account/list state 4, 50 returned channels,
all four images armed (`armed_mask=15`), no failure bits, matching baseline
calibration and zero counts at all 25 runtime probes. It was sampled at 136,385 ms
with four active and two background notifications. This supports the reported
pre-logout account/list/refresh session; notifications alone do not establish all
manual test actions or a complete reopen sequence.

The current baseline report has the same source/proof and a complete positive
control. It observed an RN factory/host/instance, two surfaces, bundle/script
loading, two Hermes engines/runtimes and one worklet runtime. The previous native
and baseline reports belong to `ebbad865` / proof `fd31c494...`; they remain valid
historical records, but cannot supply the previous launch for this new proof.

After the native sign-out action, Twitch replaced the SwiftUI interface with its
normal logged-out welcome. The tester completed the normal login and reached
Twitch's normal main interface. Screenshots establish visible presentation and
user-reported login completion; no report covers either of those stages. They do
not establish that RN started, that RN stayed absent, or that the resulting session
has been restored by Streamside after reopening. There is no evidence that the
compile-time native mode changed to baseline within the process.

## Interpretation and confirmed diagnostic gap

The host only replaces the window root during the initial scene connection. The
validated donor logout adapter preserves Twitch's native account/routing behavior;
that routing can subsequently take presentation away from the Streamside root.
The old window gesture was installed only in baseline mode. The native toolbar's
Diagnostics button therefore disappears with its root. This explains the evidence
gap without assuming a JavaScript runtime.

Static inspection of the exact donor additionally confirms native Objective-C
metadata for `LoggedOutViewController`, `LoggedOutView`, `LoggedOutCategoriesView`,
`TabBarController`, `LoginNetworker` and `LoginVerificationViewController` in Twitch.
These classes make a native legacy route plausible; their presence does not map
the screenshots to those classes or prove the path used. The previously inspected
RN hosted-portal login remains one known route, not proof that every donor login
route must initialize RN.

In native mode the unchanged guarded probe entries stop the process before a
monitored RN/Hermes/worklet entry returns to its donor caller. A stable normal-looking
Twitch screen is therefore worth measuring, not classifying from its appearance.
Coverage remains limited to the validated probes; bypassed or unobserved paths
cannot be ruled out solely by this guard expectation.

Native packaging removes `UIDesignRequiresCompatibility` from the app Info.plist.
That setting affects the donor's system controls as well as the replacement UI.
Apple documents automatic Liquid Glass adoption for standard SwiftUI **and UIKit**
components in [Adopting Liquid Glass](https://developer.apple.com/documentation/technologyoverviews/adopting-liquid-glass).
The pictured tab bar is consistent with UIKit adopting the app's new design mode;
it is not an RN runtime indicator. Baseline packaging retains the original setting.

## Focused diagnostic correction

Both modes now install the existing nonblocking two-finger, one-second hold on
the original app window. It presents diagnostics from the currently presented
controller without restoring the Streamside root, changing the login route or
enabling RN. A missing root or an in-progress presentation leaves the gesture
inactive rather than calling an unknown controller. Replacement of the entire
window, rather than just its root, remains a device-test limitation.

The interface and report separately identify sampled root ownership:
`ui_root_owner=0` unobserved, `1` Streamside, `2` another controller, `3` missing.
This is a bounded numeric presentation field; it does not classify the replacement
as RN. It is refreshed for snapshots and immediately before exports. It is not a
continuous root-transition trace. The Streamside root is held weakly so a replaced
interface can be released; the emergency diagnostics controller is created on use.
No controller names, tokens, account/channel names, web content or credentials are
added to exports. Runtime probes, their guard flags and native auth requests are
unchanged.

## Next device check

Use the new matching baseline/native pair so calibration matches its proof.
In native mode, export once before logout, once at the logged-out welcome, and
once after normal login. On each screen, hold two fingers still for one second to
open Diagnostics, export, then dismiss it to continue. Save each stage's files in
separate folders so `native-latest.json` is not overwritten when collecting them.
Do not enter credentials into diagnostics or share login screenshots containing
credentials/challenges. If a guarded attempt terminates the app, reopen and export
the preserved previous report instead of treating the termination as zero activity.
If the shortcut is absent on a donor screen, record that observation; a new window
or a different process requires further investigation.

The follow-up must establish the runtime counts during logout/login, actual root
ownership, whether Streamside recognizes the resulting session after a full
restart, and whether normal login can become a supported native service path.
Fresh native login and complete RN-free authentication remain unproven. The
original [SwiftUI findings](SWIFTUI_NATIVE_FOUNDATION_TWITCH_32.md) and
[CI validation](SWIFTUI_CI_AND_TOOLING_AUDIT.md) retain their original scopes.
