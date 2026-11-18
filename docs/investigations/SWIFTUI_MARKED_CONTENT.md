# Native marked-stream consent trial

Development base: `7bb4492` on `feat/native-frontend`, following device-confirmed
native VAFT playback. This record describes an implementation awaiting Apple CI
and physical-device validation; it does not establish successful restricted playback.

## Native boundary

The exact Twitch 32.0 donor (build 263110145453907615) was identity-checked before
inspection. SHA-256:
`076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`.
The admission plan now contains 67 exact native entry points, up from 55.

`LiveStream.thumbnailBlurReason` is separate from `currentUserCanWatch`.
The feed now exports both decisions independently and supplies the native User
identifier for a content-classification query. Acknowledgement never changes the
donor's account entitlement. Missing watch permission fails closed.

[SSNContentLabels.c](../../native/SSNContentLabels.c) calls the donor's generated
`ContentClassificationLabelStreamMetadataQuery(channelId:)` using the existing
TKGraphQL/TWApolloClient authenticated, integrity-aware Promise path and native
cache-policy tag 1. It maps enabled labels' localized names, not freeform stream
tags. Constructor String words use X0/X1 and class metadata uses Swiftself X20;
generated Data/User/Stream/Label getters take direct values. Runtime metadata
checks, optional value witnesses, bridging and dynamic casts own all value and
array handling. No Swift field, array-storage, or protocol-witness layout is invented.

[SSNContentLabels.m](../../native/SSNContentLabels.m) retains the request and native
account identity, polls on main, cancels on invalid account or a 15-second deadline,
and returns presentation strings only. Native errors, request credentials and
content labels are not added to diagnostic exports. No additional donor hooks,
RN entry points, or login path changes are introduced.

## Consent and presentation

[MarkedContentGate](../../native/swift/MarkedContentGate.swift) owns no media.
The centered material warning uses `eye.slash`, the actual returned labels,
Continue/Close and a checkbox. Missing labels show Retry/Close and never start
playback. Closing ignores checkbox changes. Continue alone approves this opening.
Continue with Don't show again persists warnings off, asks whether to enable marked
thumbnails, saves that choice, and only then admits media creation.

Both thumbnail long press and ordinary tap pass through the same gate. Pending
preview approval creates no preview session or player, suppresses duplicate holds,
and discards stale approvals after source cancellation. Authentication loss and
backgrounding cancel the gate. The overlay dismisses before preview or theatre
creation. Preview-to-theatre still uses the existing single-player handoff and
mute-before-load policy.

Defaults are warnings on, marked thumbnails off. Independent controls exist in
Followed streams (Load marked stream thumbnails) and Player (Show marked stream
warnings). The warning control is also in the player's settings popover. Hidden
thumbnails have no image request, even though a native URL can be retained in the
presentation snapshot. Changing the thumbnail setting invalidates the image task;
hidden cached/in-flight imagery cannot be displayed by the restricted row.

## Validation scope

[Host validation record](SWIFTUI_MARKED_CONTENT_HOST_VALIDATION.json): 90 native frontend
tests and 12 provider-routing tests passed; documentation check passed with no
errors. These checks do not execute SwiftUI or real native GraphQL.

Local Linux validation covers donor identity/ABI admission, actual ARM64 query
constructor and localized-name/enabled getter execution, C caller lowering, C/ARC
ownership declarations, component verification and existing native/VAFT gates.
An initial emulator test failed because the larger GraphQL image overlapped the
feed fixture's scratch memory. The new fixture maps only inspected functions and
separate scratch regions; this was a test-harness failure, not an executed device
request. No unsuccessful device result has been discarded.

Apple CI additionally compiles the full frontend and interoperability layer;
executes the production consent model's Close/Continue/preferences/cancellation/
retry states; tests the real Objective-C request owner against a synthetic native
promise and account changes; tests delayed thumbnail approval before any media
allocation; and runs a fifth coordinate test using the production warning view.
The new model/native-request receipt, preview consent receipt and warning UI receipt
are required during downloaded-component verification. All existing gates remain.
Simulator data is explicitly synthetic and cannot establish Twitch account access,
actual CCL availability, thumbnails, IVS behavior, or device runtime counts.

## Device checklist after a successful Apple build

1. With warnings on and marked thumbnails off, check the crossed-out eye placeholder.
2. Tap a marked stream: confirm actual Twitch content labels, then Close with the
   checkbox selected. Confirm no playback/audio and that the next attempt warns again.
3. Continue without the checkbox: check real playback, then leave and long press the
   marked thumbnail. Confirm the same gate precedes the muted preview.
4. Continue with the checkbox: choose Keep hidden or Show thumbnails. Verify playback
   starts only after that choice and both independent settings reflect the choices.
5. Re-enable warnings in Player; change thumbnail visibility independently in Followed
   streams. Repeat through preview and Watch; check that preview audio still mixes
   with other media and Watch keeps its existing single-player behavior.
6. Background or sign out while loading labels: returning must not start stale media.
   Also check a genuinely unavailable/subscriber-only stream remains denied by Twitch.
7. Export diagnostics after theatre/preview/background/reopen. Compare source/proof
   identities and all RN/Hermes probes. Zero counts without positive baseline calibration
   remain observations, not independently calibrated absence proof.

Apple build identity, packaging hashes, actual-label and device outcomes belong in
successor validation records once available. Donors and signing material stay local.
