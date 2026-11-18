# Preview swipes and channel verification

2026-11-17. Branch `feat/native-frontend`, starting from device-accepted preview
record `6e69e97`. This extends the accepted centered hold/scroll-return behavior;
its [implementation and device evidence](SWIFTUI_ANCHORED_PREVIEW.md#centered-hold-device-acceptance)
remain preserved. Apple compilation and physical-device acceptance for this
extension are pending.

## Preview dismissal and channel identity

A pan on the floating preview tracks the finger in any direction. The card and
small action menu move together with a restrained backdrop change. A sufficient
distance (55 points), or a short fast swipe, enters the same source-return and
single media teardown transaction as outside dismissal. A small/cancelled drag
settles back into place. Video-button touches are cancelled by an admitted pan,
and late Watch actions cannot transfer an ending/cancelled session. Reduce Motion
retains the established fade dismissal. App/account cancellation, mute-before-load,
external-audio mixing, shared-player Watch handoff and native root ownership are
unchanged.

The presenter arbitrates with the information ScrollView: vertical drags that
can scroll content stay with it; at an outward edge they can dismiss. Horizontal
drags and drags on video work in all directions. No donor navigation or RN hook
was added. The existing full-details scrolling, outside return and live-video
clipping checks remain mandatory.

The portrait stream page now displays the native feed's profile image in a
32-point circular view to the left of the channel name. It reuses the existing
bounded native image cache. Live/offline followed rows, preview details and the
stream page share VerifiedChannelName, with the verification image immediately
after the name.

## Eligibility and ABI evidence

Verification presentation uses the native User.isPartner value supplied in the
existing authenticated personalSections results. Twitch documents the verified
user badge as a [Partner benefit](https://www.twitch.tv/p/partners).
Names, viewer counts, thumbnails and the selected artwork never imply eligibility.
Unverified channels receive no badge, and a missing/malformed snapshot flag is
false. Offline User results are handled through the same getter. No new API
request, public account lookup or credential path was introduced.

The exact Twitch 32.0 donor remains build 263110145453907615, IPA SHA-256
`076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`.
The pinned TwitchCore image exports
`_$s10TwitchCore4UserV9isPartnerSbvg` at unslid `0x683ac`;
its checked 16-byte prefix is `fd7bbfa9fd030091000080d2d8fdff97`.
Disassembly shows Swift self in X20, an internal User metadata accessor at
`0x67b18`, the runtime field offset loaded from metadata + `0x3c`, and the partner
bit returned in W0. The adapter calls the exported getter using an inspected
swiftcall UInt8 result; it never reads the User/roles layout itself. The getter
is a new donor-admission entry (55 total); instrumentation remains 25 probes.

Host emulation executes the actual getter while substituting only metadata
access, checking two synthetic field offsets and partner, affiliate, staff,
combined and monetized role values. The C caller fixture independently checks
X20 self and the low-byte return with Zig, and is also compiled with Apple Clang
as part of the existing downloaded-component gate. This establishes static/ABI
behavior, not live account output on an iPhone.

## General settings and artwork

Settings retains Account at the top. A General navigation entry with a cog now
appears above Followed streams and Player. Its native menu picker contains the
actual artwork beside Twitch (default), VERIFIEDBTW and Off; Off uses a system
hidden-eye glyph. The preference persists through AppStorage and applies to all
three presentation locations. Invalid stored values resolve to Twitch. The
replacement icon changes appearance only for eligible channels.

The official Twitch badge was fetched from its [official CDN](https://static-cdn.jtvnw.net/badges/v1/d12a2e27-16f6-41d0-ab77-b780518f00a3/3)
as a 72-pixel PNG. The requested [7TV emote](https://7tv.app/emotes/01GCR0DKM00006PE9P72Y03BED)
was accessible through 7TV's public v3 API. Its upstream name is Verified,
creator CrxstalStar; the preference label remains VERIFIEDBTW. The 64-pixel 2x
PNG supplies enough detail for the 16-point badge and 18-point menu image at 3x.
Both originals and URL/creator/dimension/SHA-256 provenance are in
[native/assets/verification.json](../../native/assets/verification.json).

The public PNGs are reproducible source assets, not extracted donor resources.
They are included in source identity, the Apple input allowlist, the fixture app's
resources and the distributable framework's exact file manifest. Component
admission compares their bytes to source even if an artifact manifest is changed.
Artwork is decoded/resized once locally and has no per-row or runtime download.
Donor IPAs and signing material remain local.

## Validation and remaining device review

All 80 native frontend host tests and 12 provider-routing tests passed. Coverage
includes exact-donor getter semantics, Swift caller ABI, strict snapshot eligibility,
asset provenance/dimensions, resource tamper rejection and mandatory new receipt
fields. Host logs are retained outside the repository under the validation artifact
directory. Documentation and whitespace validation are required before commit.

The four mandatory Apple UI cases retain all previous motion/video/ownership
gates. Preview tests additionally swipe left/right/up/down from the video,
require one stop and zero Watch transfers, and retain long-detail scrolling.
The General picker test switches custom artwork, Off and Twitch, requires decoded
artwork to appear, and checks that an ordinary channel has no image. These new
UI markers are required by the component receipt; missing observations fail.
The Apple model fixture checks default/fallback options and malformed eligibility.

Apple compilation/simulator results, real followed-channel verification flags,
menu artwork on device and the new avatar have not yet been validated on iOS.
After successful Apple compilation, package locally through the existing admitted
component path. Device review should exercise directional swipes, details scrolling,
short drag cancellation, Watch/video tap, all General options across feed/preview/
theatre, an ordinary channel, audio preservation, background/account transitions
and Native diagnostic export. No replacement IPA or expanded device-runtime claim
is made at implementation time. Submit once through quota-aware Apple routing;
monitoring stays off.

## First Apple run and simulator-input correction

[Codemagic build 6afcc54ad133a39c4a126307](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afcc54ad133a39c4a126307)
used source `4fb27e83589b6903155ad83ec4fc14d469da6588` and failed its mandatory
UI gate. Compilation/linking succeeded. Both player-control cases and the
thumbnail/General-settings case passed. The preview case passed its three
short/long-details, changing decoded-video, clipped-corners and shared-player
Watch scenarios, then failed opening the first fresh swipe scenario. No swipe
was executed. The failure hierarchy showed Watches: 1, Previews: 0, Stops: 0:
the synthetic 0.7-second hold had become a tap. This is not evidence of successful
swipe handling or a completed simulator validation.

The fixture's hold observer performs up to three synchronous pixel captures on
the main thread, competing with the native 0.45-second long-press timer. The
correction confines those captures to the dedicated hold-animation case and
increases synthetic holds to 1.2 seconds for simulator scheduling headroom.
The production hold duration/animation and all input handlers remain unchanged.
The log does not establish exactly why that particular timer missed; the next
Apple run must still pass the actual holds, all four swipes and every previous
gate. There are no retries or accessibility activation substitutes. Direction
markers now identify each fresh swipe scenario before opening its preview.

Failure artifacts are preserved outside the repository under
`artifacts/ci/4fb27e83589b6903155ad83ec4fc14d469da6588/failure/`:

- `player-input-failure.zip`: 97,048 bytes, SHA-256
  `6e356052ef26163c0ffc6407b6efa69f57e26b20e5d34ebcd75d399825b72b71`.
- `Streamside_14_artifacts.zip`: 45,052 bytes, SHA-256
  `833f66bbec1918a6a4eef01039fadf89df1a1798e55af35349212554416eedbf`.

All 80 native frontend host tests passed again after this correction (9.431s).
Documentation validation checked 119 Markdown files and 1,158 references with zero
errors; whitespace validation passed. A replacement Apple run is required;
physical-device acceptance remains pending.

## Successful replacement and local test package

[Codemagic build 6afccb7fd133a39c4a126579](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afccb7fd133a39c4a126579)
passed using exact source `c03d67de6aed0d81b89d601b2db3671261c92333`.
Xcode 26.6 (17F113), Swift 6.3.3 and iPhoneOS SDK 26.5 compiled and linked both
instrumented component modes for arm64 iOS 16.4. No donor was uploaded.
All mandatory Apple stages passed, including the four UI cases, left/right/up/down
swipe cancellation, General artwork/Off selection, ordinary-channel suppression,
long-details scrolling, source hold/return animation, real changing decoded-video
clipping and the shared-player Watch transition. Existing playback/audio,
account/background cancellation, launch-selection, ownership, networking and
control-motion gates also passed. These are donor-free simulator observations.

Ubuntu downloaded and admitted the exact source/toolchain-matched components;
58 ABI/component/core/launch/probe/comparison checks passed. Local packaging then
validated the original donor and all 55 ABI entries and 25 probes. Every retained
donor entry was checked, including the unchanged original HBC. Only the native IPA
was assembled; the last device-accepted centered-hold build remains a rollback.

The test IPA is 196,921,256 bytes, SHA-256
`60f24c3f22dfdac3fb9f977e12abdb508ac02b184461f72ea99efde44e26a134`.
The framework SHA-256 is
`3a53cf2a0b5e5bede9df3cff698c44c41a2e2cb4da640a4495047d3fc9bf7f04`.
The [compact validation record](SWIFTUI_PREVIEW_SWIPES_VERIFICATION_VALIDATION.json)
contains exact build, proof, donor, artwork, component and package identities and
all Apple stage/receipt results. IPA/components remain outside the repository.
Physical-device acceptance is still pending; simulator results do not establish
real Twitch playback, session behavior or RN/Hermes runtime absence on device.

Install with Feather using the existing application/keychain identity. Hold a live
thumbnail and swipe the preview in each direction; also try a small drag that
returns, scrolling long details, outside dismissal and Watch. In Settings →
General, try Twitch, VERIFIEDBTW and Off, checking a verified and an ordinary
channel in the feed, preview and stream page. Confirm the stream-page avatar and
existing audio/lifecycle behavior, then export Native diagnostics after review.

## Device review and unblocked preview return

The c03d67d package was device-reviewed: badge changes, preview swipes in all
directions and channel avatars were reported functional. The
[bounded review record](SWIFTUI_PREVIEW_SWIPES_VERIFICATION_DEVICE_REVIEW.json)
checks the supplied export against source/proof/donor/package identities and
preserves its raw hash. The raw export remains private in the local artifact
folder. It reports zero failures, playback errors, mute mismatches or hits across
all 25 runtime probes, with ten balanced playback loads/playing/decoded/releases/
stops and 100 channels. Baseline calibration is false and background count zero;
no independent calibrated runtime or new background acceptance is inferred.

The next correction removes the input block during cancellation's visual return.
The presenter immediately restores the source, releases touch/accessibility
ownership and becomes a passive overlay. Cancellation stops/releases preview
media and clears that row's coordinator immediately, allowing a new feed action
without waiting for the old visual cleanup. A passive composed-view snapshot
preserves the preview during user dismissal after its player stops. It receives
no touches, owns no media and is removed with the closing card. Watch retains its existing ordered
single-player handoff and audio promotion.

The accepted critically damped 0.52-second return is retained. A display link in
the common run-loop mode translates the return's coordinate space toward the
thumbnail's current position as the feed scrolls. It adjusts only the target
position's contribution to the existing trajectory; it never restarts the spring
or changes its completion deadline. Disappearing/recycled sources keep the last
available target. Closing snapshots cannot intercept input, and an old completion
cannot unhide a thumbnail or clear a session now owned by a newer preview.
Reduce Motion and Watch retain their existing 0.18-second fade, and inactive
cancellation retains immediate cleanup. No donor hooks or playback requests were
added. UIKit's [interaction control](https://developer.apple.com/documentation/uikit/uiview/isuserinteractionenabled)
and [display link](https://developer.apple.com/documentation/quartzcore/cadisplaylink)
provide the input release and bounded visual tracking.

The mandatory owned UIKit fixture now checks actual root hit testing during
return, a scrolled target's translated snapshot, completion within the existing
animation budget under additional scrolling, immediate media/row release,
overlapping previews and stale completion isolation. Component admission requires
its new unblocked_return receipt; a missing receipt is rejected. All existing
coordinate/decoded-video/clipping and lifecycle gates remain required. Apple and
physical-device validation of this correction are pending at implementation time.

Host validation after the correction: 81 native frontend tests passed (8.971s),
including rejection of a component missing unblocked-return evidence; all 12
provider-routing tests passed. Updated Python tooling compiled successfully.
Host logs remain outside the repository in the validation artifact folder.
Apple-specific assertions and composed-video snapshot appearance still require
the submitted Apple run and device review; host results do not establish them.

## Unblocked-return Apple failure and observation correction

[Codemagic build 6afceb3ed133a39c4a126fb9](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afceb3ed133a39c4a126fb9)
failed from source `c4ec52c4df9a85a25fdf92be7caef49587b77a75`.
Compilation/linking and the owned Quick Look receipt passed, including immediate
feed hit testing, moving-source tracking, fixed return duration, early media
release and overlapping-preview isolation. The full preview UI case also passed
all four swipes, long details, decoded-video clipping and Watch handoff. The
plain player case passed. Two other mandatory observations failed, so no IPA was
packaged and the Apple result remains failed.

First, the thumbnail fixture computed its return-animation result in stop(),
which now runs before visual dismissal starts. That also stopped the presentation
layer probe before any return frames. It showed Stops: 1 and Returned to source,
but No observed animation. The correction adds an optional fixture-only callback
at actual cancellation-return completion, and leaves the layer probe running
until then. Immediate playback teardown stays independent of visual sampling.
Production callers leave the callback nil. The requirement to observe actual
intermediate source geometry during both entry and return remains unchanged.

Second, the glass-control case passed all eight modifier-motion stages but failed
the existing actual Fade-pixel gate. Entry region ratios were 0.086–0.090 and exit
ratios 0.999–1.000, outside the required 0.15–0.85 interval. The prior snapshot
schedule slept half a duration from a SwiftUI state assignment without observing
when the renderer began that transition. No rendered-phase evidence was available
for these two captures, so the log alone does not establish a production Fade
regression or its precise scheduling cause.

The corrected pixel observer waits for a fresh actual production modifier sample,
Fade style, correct direction and progress between 0.4 and 0.6, then yields one
compositor interval before a single snapshot. The wait is bounded to three seconds;
a missing intermediate frame fails. It records observed/captured progress for
future triage. The existing pixel contrast/count and 0.15–0.85 requirements for
center, actions and audio in both material modes are retained. There are no
snapshot retries or changes to theatre animations, durations, or buttons.

Failure evidence remains outside the repository in the source's CI failure folder:

- `player-input-failure.zip`: 365,189 bytes, SHA-256
  `e48ad882d54c58c8c729de25e6836292636f5d1cab3a7de7a9589b0236bc7b9c`.
- `Streamside_16_artifacts.zip`: 49,455 bytes, SHA-256
  `4fab6d5530f92c61f8c09acbfaec447dfdb938fe69ea4257d0e44c19910f38f3`.

All 81 native frontend host tests passed after this correction (9.155s).
A replacement Apple run is required to establish the corrected observations;
physical-device validation of unblocked closing remains pending.

## Successful unblocked-return build and local package

[Codemagic build 6afcf115d133a39c4a12716d](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afcf115d133a39c4a12716d)
passed using exact source `5ada9ea64f1e3a777f71bab68a83018ce9b4ca40`.
Xcode 26.6 (17F113), Swift 6.3.3 and iPhoneOS SDK 26.5 compiled/linked the
arm64 iOS 16.4 components. All mandatory stages passed, including the new
unblocked-return receipt, all four UI cases and the unchanged native ownership,
playback/audio, lifecycle, launch-selection and networking gates. The thumbnail
case now observed both entry and actual completed return motion after immediate
media teardown. All directional swipes, clipping and shared-player handoff passed.

Both actual Fade-pixel checks passed with rendered-phase evidence. Glass entry
was observed at progress 0.406 and captured at 0.427; exit was observed at 0.594
and captured at 0.551. Corresponding region pixel ratios were 0.418–0.429 and
0.587–0.588. Plain entry/exit ratios were 0.363–0.368 and 0.622–0.631. Every region
satisfied the retained contrast/count and 0.15–0.85 thresholds. These are owned
simulator observations; the fixed-duration moving-source and overlap tests also
passed there, without establishing phone visual acceptance.

Ubuntu component/ABI admission and all 59 post-download regression checks passed.
Local packaging revalidated the exact donor, 55 ABI entries and 25 runtime probes,
and every retained donor archive entry including unchanged HBC. The single native
IPA is 196,923,072 bytes, SHA-256
`3ef6f357f07c79c9742345498e572c9924677f0affd3b6b34be23c2eb50c98c8`.
Framework SHA-256 is
`03d23684e86db37e51aa4d473ccac85d8c748e4492bb20ecd3a3036a68022c6c`.
The [validation record](SWIFTUI_PREVIEW_UNBLOCKED_RETURN_VALIDATION.json) preserves
exact source/proof/donor/toolchain/build identities, receipts, pixel observations
and artifact hashes. Outputs remain outside the source tree. No donor/signing
material was uploaded; no VM or extra baseline IPA was used. The c03d67d
badge/avatar/swipe build remains the device-reviewed rollback.

Install with Feather using the existing identity. Close a preview with an outside
tap or swipe, then immediately scroll or tap another stream. The returning image
should follow its thumbnail and finish in the original half-second even while
scrolling. Also repeat close/reopen and verify Watch still transfers normally.
Review the return's static preview appearance and export Native diagnostics.
Physical-device acceptance and new runtime observations remain pending.
