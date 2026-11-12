# Silent account updates and compact title popover

Starts at clean `feat/native-frontend` commit `c9846ae`, with compiled source
`cad1e034dcca4f6efb076214527656e635b7a5b9`. The
[previous continuity trial](SWIFTUI_FEED_CONTINUITY.md) and its failed first CI
attempt remain preserved. This follow-up does not change playback or chat scope.

## Device results and remaining failure

[Reports and validation receipt](evidence/swiftui-device-5/validation.json) preserve
all four supplied JSON files and the original ZIP hash. Matching cad1 baseline
launch 11 supplies a positive RN/Hermes/worklet control. Its calibrated field is
false because it reads the previously saved proof on process start; its positive
control writes the new proof, and native launch 17 subsequently reports calibrated
true. The native report arms all four images (15), has zero failures and all 25
entry counts zero, root ownership 1, navigation guard 1 and account/list ready 4
with 100 records. It records four foregrounds and three backgrounds at 203925 ms.
Footprint is 98716112 bytes, peak 104335800; these are uncontrolled snapshots.
Both previous reports belong to d534 and are excluded from cad1 restart evidence.

The user confirms live timer animation now works. Background continuity still
fails: the feed disappears and reloads. The full-title bottom sheet is also the
wrong presentation. The supplied Frosty screenshot is a desired compact-popover
reference, not a Streamside test result, and remains in external artifacts only.

## Notification boundary correction

The previous fix removed unconditional clearing from routine refresh, but left
all five TwitchIdentity notifications routed through ssn_account_changed(). That
includes UserUpdated and UserIsAvailable from the already-inspected native
account-information publication region (`0x10075c788`, posts at `0x10075e3ec`).
Code inspection establishes this remaining clearing path. The supplied reports
lack per-notification observations, so they cannot prove which signal caused the
observed background disappearance. The next build records bounded numeric evidence.

The adapter now retains the opaque PMHTTP defaultAuth object used by its successful
native currentUser request. It never reads, copies or exports credentials. Only
UserUpdated/UserIsAvailable under that exact same verified authorization object
retain the existing in-memory account and feed. A missing/replaced authorization
object, login, logout, token-change or unknown event invalidates immediately.
Token-change behavior remains conservative even if the object identity is the
same; no renewal semantics are inferred. Twitch's own observers and lifecycle
handlers continue running. Fresh sign-in still requires a successful currentUser
request; an information notification alone cannot establish authentication.

The same opaque authorization must remain in effect through both request stages;
a result from a replaced authorization is discarded. Request-generation checks
still reject cancelled work. Refresh also checks for a replaced authorization
before presenting retained data. Same-context information events schedule silent
refresh instead of clearing, and automatic restoration callbacks coalesce while
a request is already active. Failed currentUser verification, missing authorization
and ABI/monitor failure remain fail-closed. Feed-only request failure retains the
previous list with its explicit retry message, as in the earlier trial.

New bounded report fields are account_events (five counts in updated, available,
login, logout, token order), account_updates_retained, and account_data_clears.
The summary includes retained/clear totals. They record no object addresses,
notification payloads, account names, tokens, titles or request content. Counts
are observations, not guesses that an unobserved path had no activity. Runtime
probes, guard policy and positive-control requirements remain unchanged.

The finite notification policy lives in the dedicated native integration header
[SSNSessionPolicy.h](../../native/SSNSessionPolicy.h). Native host tests exercise
same-context information refresh versus replaced/missing context and every hard
boundary, reject unknown events and check the bounded report counters. This is
synthetic policy/reporting evidence, not execution of Twitch's account manager.

## Presentation correction

Duration pills retain the confirmed native clock and animation, but use the default
system font design at 10 points, medium weight, with stable-width numeric digits.
The full title uses a native anchored popover above the row, regular material,
body text and compact padding, with no navigation bar or bottom-sheet detents.
Short titles size to their text; taller content can scroll within a 220-point
content bound. Tap outside to dismiss. The one-second hold, VoiceOver action and
saved two-line option remain unchanged. Near screen edges the system may adjust
popover placement to fit.

Apple's [popover API](https://developer.apple.com/documentation/swiftui/view/popover(ispresented:attachmentanchor:arrowedge:content:))
and [compact presentation adaptation](https://developer.apple.com/documentation/swiftui/view/presentationcompactadaptation(_:))
specify the public presentation boundary. Explicit .popover adaptation keeps it
compact on iPhone; it is not allowed to fall back to the default sheet adaptation.
The minimum deployment remains iOS 16.4.

## Initial validation

Local native checks pass 47/47, including the new policy/reporting regression.
Both changed native integration/account C objects compile for arm64 iOS with
warnings as errors. The exact Twitch 32.0 donor SHA-256 was rechecked before
inspection: `076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`.
No private Swift service/signature, protocol witness or model layout was added.
Apple compilation, final package identities and replacement device results are
pending at this implementation checkpoint.


## Successful Apple build and local packaging

Compiled/packaged source: `48fe69640ad202a8de2abcb82c998c300d68d7c2`.
Proof: `99d7d0fc40608aed43ea46efccd823d05f1e951b949674f38022ac287e44b898`.
[Artifact and validation receipts](SWIFTUI_SILENT_REFRESH_ARTIFACTS.json) preserve
exact IPA/framework/modified-image/manifest hashes, source/toolchain identities
and test scopes. Both final IPAs were independently rehashed after assembly.

[Apple Actions 43274509020](https://github.com/BananaOnGitHub/Streamside/actions/runs/43274509020)
succeeded using pinned Xcode 26.6 / 17F113, Swift 6.3.3 and iPhoneOS SDK 26.5.
Both baseline/native frameworks compiled, linked and passed ad-hoc signature
verification. Both pure Swift model programs, real UIKit window-ownership fixtures
and production-clock lifecycle simulator fixtures passed. Apple-compiled ABI 12,
component admission 9, core/policy reporting 8, Foundation HTTP 1 and synthetic
report comparison 5 tests passed. Local native checks passed 47/47, and the changed
native C objects compiled for arm64 iOS with warnings as errors. These tests do not
execute Twitch account notifications or inspect the popover on a physical device.

[Linux Actions 43274509197](https://github.com/BananaOnGitHub/Streamside/actions/runs/43274509197)
succeeded: 224 tests, 220 passed, four skipped (Apple Foundation/ImageIO and missing
legacy exact donor/Hermes runner). Documentation checks pass. Local packaging again
re-admitted the exact donor and 40 ABI entries, installed the unchanged 25 probes,
verified retained donor content and unchanged HBC, and checked output ZIP/images.
The donor, IPA and signing material were not uploaded to public CI. Final sizes
and hashes are in the linked receipts. Feather signing with the established app/
keychain identity is still required.

Reproduction (source/proof-compatible checkout, external empty output):

```sh
gh run download 43274509020 --name swiftui-components-48fe69640ad202a8de2abcb82c998c300d68d7c2 --dir ../artifacts/ci/48fe69640ad202a8de2abcb82c998c300d68d7c2
python3 tools/native_frontend/components.py verify --output ../artifacts/ci/48fe69640ad202a8de2abcb82c998c300d68d7c2
python3 tools/native_frontend/build.py --donor ../donors/tv.twitch-32.0.ipa --frontend swiftui --components ../artifacts/ci/48fe69640ad202a8de2abcb82c998c300d68d7c2 --mode both --output ../artifacts/native-frontend/swiftui/silent-refresh-rebuild
```

Rebuild the pinned source workflow when Actions artifacts expire. Reassembled
artifacts receive their own hashes; previous package identities are not rewritten.

## Device check

1. Sign/install the matching baseline with Feather using the established identity.
   Open Twitch and export reports using the two-finger hold. The replacement proof
   requires its own positive control.
2. Replace it with the native IPA using that same identity. Verify the timer's new
   system typography and continuing animation. Hold a long title for one second:
   expect a small frosted popover, normally above the row, with the full title and
   no bottom sheet. Tap outside to dismiss. Try a row near the top and bottom.
3. Scroll down and expand Offline. Export once, then background for ten seconds
   and return. The current feed/images/expanded section should stay present while
   metadata refreshes silently. Export again. During a same-authorization return,
   account_data_clears should not increase. Retained notification counts may rise
   if native information notifications fire; zero such events is not proof they
   were tested. If it still blanks, preserve both reports rather than treating a
   final ready snapshot as successful continuity.
4. Pull to refresh and check content remains visible. Sign out once and verify
   account/feed data clears, then sign in through Twitch and confirm SwiftUI
   returns. Actual logout legitimately increments clear counts. Export after the
   sequence and after a separate full close/reopen; keep latest and previous files.
   Require complete/calibrated monitoring, root ownership 1, zero failures and zero
   guarded RN/Hermes/worklet entry counts throughout.

Physical-device confirmation of this replacement is pending. The previous cad1
reports establish timer animation and runtime isolation for that source only;
they explicitly fail background continuity. This source corrects the remaining
information-notification invalidation path and adds evidence to diagnose other
causes. It does not claim that those causes have all been exercised or resolved,
nor that invalid-session/account-switch behavior has received new device coverage.
