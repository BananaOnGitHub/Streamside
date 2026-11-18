# Marked-stream consent inside the video area

Starting state: `527af99` on `feat/native-frontend`. The preceding component/IPA
source is `f6d279ca48790d3960c40dced53360242fd591c0`. The
[device review](SWIFTUI_MARKED_CONTENT_DEVICE_REVIEW_1.json) preserves the supplied
report identity and scoped observations: functional confirmation, ten successful
playback cycles, zero playback failures and all 25 probe counts zero. The report
advertises calibration but no fresh paired baseline accompanies it. The prior
[warning implementation and failures](SWIFTUI_MARKED_CONTENT.md) remain historical
evidence; this successor changes its presentation and media-admission ownership.

## Implementation

The preview and portrait theatre open their existing hierarchy immediately. The
warning, loading/failure states and thumbnail question replace only the 16:9
video slot. Channel identity/details and the separate preview action menu remain
visible. Close dismisses the preview or theatre itself, including from the
thumbnail question. Continue and the independent saved preferences retain their
previous behavior; first-warning Close still discards the checkbox.

The warning's scrollable label area and fixed action area keep actions within
the video frame. Buttons use Apple's iOS 26
[glass](https://developer.apple.com/documentation/swiftui/primitivebuttonstyle/glass)
and [glassProminent](https://developer.apple.com/documentation/swiftui/primitivebuttonstyle/glassprominent)
styles, respecting the existing Liquid Glass preference and Reduce Transparency.
Earlier supported iOS versions and opaque presentation use bordered controls.
No custom motion is added to these controls. The full-window consent controller
and pre-presentation root interception have been removed.

[TheatrePlayback](../../native/swift/TheatrePlayback.swift) is extracted from the
theatre view as the existing shared media facade. It now holds pending consent.
Constructing that facade creates no IVS player, playback request or audio setup;
`start` waits for consent and any thumbnail choice. The native CCL request still
uses the exact previously inspected authenticated Twitch-native query. No new
donor ABI or hooks are added; the exact 32.0 donor and 67 admitted ABI boundaries
remain pinned. Account access restrictions still apply independently.

The same facade and gate survive Watch into theatre. Navigation ownership is
rebound so Close affects the current destination. Before media starts, native
`enterTheatre` changes playback intent only; it performs no audio activation or
IVS initialization. After real preview playback starts, the existing native
promotion retains its established behavior. Cancellation clears consent before
stopping media, so a late label response cannot start playback or close a newer
owner. Theatre background/account loss and preview transaction cancellation
close pending consent and cancel the native label request.

The preview's UIKit video tap button now yields hit testing and accessibility to
consent controls until admission. After admission it resumes its normal Watch
behavior. Outside dismissal, swipe dismissal, source animation and the menu keep
their existing ownership. A pending Watch can navigate to theatre with the warning
still in the video slot; it does not acknowledge the warning or start media.

## Validation

[Linux host validation](SWIFTUI_MARKED_CONTENT_INLINE_HOST_VALIDATION.json) passed
91 native host/donor tests and 12 provider-routing tests. This does not compile
the SwiftUI changes or execute the new Apple-only fixtures.
The Apple path keeps the existing mandatory gates and adds:

- A host fixture executing the production playback/consent state machines with
  only the media boundary stubbed: one label request, no early media start,
  discard-on-Close, same-facade pending Watch, thumbnail choice before start,
  late cancellation and current-owner Close.
- The real Objective-C playback fixture checks pending promotion creates no
  player, request or audio activation and does not change the audio category.
- The coordinate fixture uses the production warning, playback facade, source
  presenter, transaction and menu. It checks 16:9 containment, actual warning
  button touches in preview, both Close paths, pending Watch and exactly one
  media start after the final choice. Existing glass/plain, animation, decoded
  video, source gestures and lifecycle tests remain mandatory.
- Component verification requires the new inline admission, pending Watch and
  native promotion results; missing evidence rejects the component.

The SwiftUI/Objective-C changes still require a successful Apple build. The
fixtures use synthetic labels and media boundaries. They do not establish the
new presentation's device appearance, real Twitch label retrieval, thumbnails,
external-media preservation or RN/Hermes counters. No replacement IPA/device
success is claimed at implementation time.

## Device checks for the replacement

1. Re-enable Show marked stream warnings. Open a marked stream by tap and by
   long press: the existing destination should open with consent inside its
   video rectangle, and Liquid Glass actions should respond without starting audio.
2. Select Don't show again, then Close: the destination should close and warn
   again on the next opening. Continue without remembering should start playback.
3. Continue while remembering: the thumbnail question should remain in the same
   video rectangle. Either thumbnail choice must finish before media begins.
4. From a pending preview, choose Watch: the same warning should move to the
   theatre without media starting. Continue or Close must affect that theatre.
5. Check outside/swipe dismissal, background/account cancellation, first preview
   with external audio, post-consent Watch, both glass settings and Reduce
   Transparency. Export Native diagnostics after exercising these paths.
