# Account avatar and per-channel stream resolution

Implemented on `feat/native-frontend`, based on `8301c9f`. This record accompanies the implementation commit. Apple compilation, simulator execution, local packaging and device results remain pending at submission.

## Settings presentation

General and Followed streams retain their navigation titles without repeating the same label above their first section. Settings' authenticated account row displays a circular profile image, using the current-user native model's supplied profile images and the existing bounded, credential-free Twitch CDN image cache. Missing/unsupported images retain the person placeholder. Refreshing an avatar does not count as an account transition or close the player; username/display-name identity comparisons remain intact.

The avatar adapter uses the already-admitted `User.profileImages`, `Thumbnails` metadata and thumbnail URL getter. It obtains value witnesses/Optional URL storage from the Swift runtime, tries the small size then supplied alternatives, and copies only the resulting URL into the owned presentation snapshot. It adds no login flow, authorization access or GraphQL request. Account validity and token ownership are unchanged. No avatar or quality details were added to diagnostic exports.

## Player resolution

The theatre gear popover now includes a native Resolution menu. It lists Auto and names from the active IVS player's available quality objects. Manual switching passes the selected object from the current player to `setQuality:adaptive:` on the main thread. Auto uses `setQuality:nil`. It does not replace the player or issue another playback authorization request. The preview's saved choice carries into the same-player theatre handoff without changing mute/audio policy.

[StreamQualityPreferences](../../native/swift/StreamQualityPreferences.swift) stores an explicit choice per channel, case-insensitively, with bounded keys/values and a maximum of 256 channel records. Auto removes the stored override. Selection uses the SDK-provided rendition name, not an array index, signed URL or SDK object. Background/retry media recreation retains desired quality and applies it after the new player's qualities become available. If the saved name is absent, playback uses Auto and the popover explains the fallback; the saved preference remains so that a future broadcast can restore it. Before qualities are available, the menu is disabled. The local synthetic stream creates no player or resolution options.

## Inspected boundary and validation

The exact Twitch 32.0 donor embeds AmazonIVSPlayer 1.58.0. Four Objective-C entries were inspected and added to the donor admission plan: `IVSPlayer.qualities`, `setQuality:`, `setQuality:adaptive:` and `IVSQuality.name`. Each has an exact class, encoding, address and prefix; runtime method encodings are also checked before quality calls. Mismatch disables resolution access while retaining existing playback behavior. Existing Swift call-lowering signatures suffice for avatar retrieval; no Swift field layout or protocol witness slot was introduced.

The public [IVS player reference](https://aws.github.io/amazon-ivs-player-docs/1.32.0/ios/Classes/IVSPlayer.html) describes qualities becoming available after Ready, nil quality selecting Auto and adaptive manual switching. The [quality reference](https://aws.github.io/amazon-ivs-player-docs/1.32.0/ios/Classes/IVSQuality.html) defines the display name. Those reference pages describe SDK 1.32; the implementation boundary was independently verified in the bundled 1.58.0 donor. The version-specific hosted 1.58.0 reference was inaccessible during investigation.

[Host evidence](SWIFTUI_ACCOUNT_AVATAR_RESOLUTION_HOST_VALIDATION.json): 96 Ubuntu tests passed, including exact-donor admission and rejection of changed quality signatures/prefixes. This does not execute the new Swift or UIKit tests.

Apple CI now requires per-channel persistence/Auto/isolation/bounds and avatar identity model checks; actual Resolution menu interaction in both glass/plain coordinate fixtures; and native facade fixtures for quality listing/switching, fallback/restoration, unchanged request/player counts, background recreation and teardown. Component receipts require the additional resolution and quality lifecycle checks. The existing five UI gates, real decoded-video clipping, native audio/session/VAFT and local-test isolation checks remain mandatory.

After successful Apple compilation, retrieve through `make native-ci-fetch` and package locally with the pinned donor as usual. Device checks: Settings avatar/placeholder; cleaned General/Followed headings; select a real available resolution, close/reopen the same channel, compare another channel, background/foreground and relaunch; Auto clears only that channel's override; temporary missing rendition falls back without losing the choice; preview remains muted and promotes without a second player; diagnostics retain guarded RN/Hermes behavior. Device appearance, actual rendition changes and runtime counts remain unverified until reported.
