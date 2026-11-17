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
