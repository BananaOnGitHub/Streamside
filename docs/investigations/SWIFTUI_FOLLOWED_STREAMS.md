# Native followed-stream list trial

This starts from `e6f82a6` on `feat/native-frontend`, following the
[validated account/navigation device trial](SWIFTUI_NATIVE_DEVICE_REVIEW_3.md).
It adds live-stream browsing information only: no playback, chat, or channel
navigation is introduced. Existing window ownership and RN/Hermes/worklet guards
remain in force.

## Native backend admission

The exact Twitch 32.0 donor SHA-256 remains
`076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`.
The new [feed adapter](../../native/SSNFeed.c) uses the existing authenticated
TKGraphQL `personalSections(currentPlayingChannelName:order:blockedUserIDs:)`
operation at TwitchKit `0x2a8958`. Inspection identifies its native
`PersonalSectionsSidebarQuery` constructor at call `0x2a8b48`; the mapper selects
the native `RECS_FOLLOWED_SECTION` at `0x2a8e08`. It does not combine unrelated
recommended/popular sections. Request order tag 0 has the native raw value
`recommended`, verified by emulating the donor's leaf getter. Presentation sorts
returned live channels by viewer count, then channel name for stable ties.
This uses the native response's live/offline sections and does not claim pagination
beyond the records that Twitch's sidebar operation returns.

The first existing native currentUser check still verifies the account. Feed
retrieval then replaces the SwiftUI build's first-50 followedUsers operation.
The preserved UIKit proof uses its earlier request path (`SSN_SWIFTUI=0`).
Account invalidation, native auth/header/integrity infrastructure, request
cancellation/generation checks and the original timeout remain owned by the
existing adapter. No independent HTTP GraphQL endpoint or token access is added.

The [exact donor admission plan](../../native/twitch32.json) now includes
TwitchAnalyticsCore and these inspected boundaries:

- PersonalSectionsResponse is a 16-byte value passed as two direct integer words
  to its live/offline getters; it is not an indirect swiftself getter. Donor leaf
  getter emulation verifies the forwarding. The callback storage remains opaque;
  the complete value is copied for ABI marshalling, without private field access.
- TrackableItem's descriptor at TwitchAnalyticsCore `0x39be4` specifies one type
  parameter, one Equatable requirement and two metadata key arguments. Its actual
  getter at `0x31e18` forwards to the contained type's runtime copy witness.
  Both generic type metadata and Equatable conformances come from Swift's runtime;
  no witness-table slot for an application protocol is guessed.
- LiveStream, User, Game, Thumbnails, Date and Optional/Array values are allocated
  and destroyed using runtime metadata and value witnesses. Concrete getters
  supply stream title, viewers, start date, category, broadcaster/profile image
  and thumbnail URLs. Native Foundation Date/URL values bridge through Foundation;
  no Date, URL or donor struct field layout is synthesized.
- Thumbnails is returned as three direct words. Its indexed URL getter takes the
  size tag before these words and writes an indirect Optional<URL> result. The
  inspected enum descriptor maps tiny/small/medium/large to tags 0/1/2/3.
  Profiles prefer small images and live previews medium images; a missing variant
  falls back to another URL supplied by the native Thumbnails value. No CDN path
  or image size is synthesized from a username.
- Native `currentUserCanWatch` and `thumbnailBlurReason` are preserved. The latter
  enum's actual case order is sexualThemes, adultContent, blurNotRequired, unknown;
  only tag 2 with watch permission supplies a preview URL. Restricted previews
  remain placeholders. Static admission validates these enum descriptors and the
  generic conformance contract as well as symbol addresses/prefixes and full image
  hashes.

Mapped channel details stay in the owned in-memory presentation dictionaries.
Diagnostic exports still contain counts/build identifiers, never channel names,
titles, image URLs, account credentials or request content. No runtime probe or
startup-gate policy was relaxed for the new operation.

## Interface and refresh

The main SwiftUI screen shows compact live rows: 16:9 thumbnail, profile picture
with a small red ring, channel name, title, category, viewers and a small duration
pill at the thumbnail's bottom right. Live rows are sorted by viewers; offline
channels are in a collapsed-by-default DisclosureGroup below. Duplicate channel
records prefer live status. Missing/failed images use stable placeholders, unknown
viewer counts are not converted to zero, and missing categories remain explicit.
Accessibility text sizes switch the row to a stacked layout. Account and diagnostic
controls live behind the gear; signed-out welcome and the window diagnostic gesture
remain available.

Five seconds is interpreted as the minimum interval between accepted manual
refresh starts. Concurrent pulls are coalesced by rejection while a refresh is in
flight; an early repeat shows a short wait message. Metadata and image generation
advance together only for an accepted refresh. Pull-to-refresh waits for the native
account/feed operation to settle, using its existing 30-second service timeout.
This local throttle reduces repeated requests; it does not establish Twitch's
server rate-limit policy or guarantee that a server never throttles.

The image loader uses an isolated, credential/cookie-free URLSession. HTTPS
jtvnw.net URLs (including redirects) are permitted; other hosts, credentials,
non-HTTPS schemes and nonstandard ports are rejected. Visible row tasks initiate
image loads and cancel when their views disappear. There is no polling, timestamp
cache-busting, automatic retry or per-follow stream-query fan-out. A session limits
connections per host to three, applies five-second image request/resource timeouts,
revalidates HTTP cache entries, limits decoded image count/cost and downsamples
previews to at most 480 pixels (avatars 80). Responses over 2 MiB are rejected before
decoding. The size check follows data download; it is not a streaming transfer cap.
The URL cache has a 12 MiB memory allowance, no disk allowance; decoded image cache
is limited to 24 MiB / 96 entries. CDN cache/server behavior can still limit how
recent a returned preview is.

## Timer material, animation and accessibility

Apple documents [Liquid Glass for custom views](https://developer.apple.com/documentation/swiftui/applying-liquid-glass-to-custom-views),
[numeric text transitions](https://developer.apple.com/documentation/swiftui/contenttransition/numerictext(countsdown:)),
[Reduce Motion](https://developer.apple.com/documentation/swiftui/environmentvalues/accessibilityreducemotion),
and the [pausable timeline schedule](https://developer.apple.com/documentation/swiftui/animationtimelineschedule/init(minimuminterval:paused:)).
The pill uses a native capsule glass effect on iOS 26+, with material fallback on
older supported systems. It does not use private Liquid Glass APIs. Its clock is
derived from the native stream start date and current time, rather than incrementing
a drifting counter. A one-second minimum schedule pauses outside the active scene.
Digit transitions explicitly become identity/no animation when Reduce Motion is
on. Reduce Transparency selects an opaque capsule. There are no decorative pulses,
interactive glass effects or large morphing animations over the thumbnail.

## Validation status

Host validation passes **46 native tests**, including 12 Swift calling-convention
fixtures, actual donor getter emulation and enum/generic contract admission. The
three-word-result test initially failed because its outer C fixture lacked C ABI
result storage; the fixture was corrected to provide storage and check all three
returned words. New C feed/account objects compile for arm64 iOS with the pinned
Zig compiler and warnings-as-errors. A syntax-only invocation was unsupported by
that driver; object compilation is the recorded successful C check.

Pure Swift model tests now cover refresh exclusion/cooldown, live-first grouping,
viewer sorting/deduplication, missing/invalid fields, restricted thumbnails,
elapsed formatting and the image URL policy. Apple CI compilation and these model
tests, final linking/packaging, and actual device feed/image/accessibility behavior
are pending at the initial implementation commit. Synthetic fixtures are confined
to tests and are not successful authenticated device results.


### Sparse-thumbnail follow-up

The initial source is `439440c129848dffcdf30b0ae77f668e847c9b2a`.
Before packaging, image selection was hardened for sidebar responses containing
only some native size variants. Missing preferred small/medium URLs now use another
supplied native variant. Pure Swift tests also exercise optional struct, nil, URL
and Date Foundation bridging used by the mapper. No interface or runtime guard
policy changed. This supersedes the initial in-progress component build for
packaging; final CI and artifact identities are recorded below when available.
