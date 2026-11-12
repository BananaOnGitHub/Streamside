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
