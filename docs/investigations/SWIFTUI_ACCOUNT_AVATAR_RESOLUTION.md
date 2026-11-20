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

## First Apple build failure and menu correction

Source `0fe2c11adc0decd4439c6973a4d55ff1447e9e07` compiled and linked successfully on [Codemagic build 6aff38b78f52ca275128fc9d](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6aff38b78f52ca275128fc9d). Native model/admission, quality lifecycle, audio, ownership and launch fixtures passed. The marked-content coordinate gate also passed. The build then failed in `testGlassControls`: the nested SwiftUI resolution menu exposed its 480p option, but XCTest could not obtain a hittable point and repeatedly waited for animation completion until the unchanged 300-second deadline. The remaining coordinate gates and complete baseline component validation did not run. No successful components or IPA were produced.

[Preserved failure evidence](SWIFTUI_ACCOUNT_AVATAR_RESOLUTION_BUILD_FAILURE_1.json) records the owned logs/archive hashes and limits. Screenshot export failed because the timed-out result bundle was incomplete; the logs do not establish the framework's internal cause.

The correction replaces only the nested SwiftUI picker with a persistent UIKit menu button. UIKit owns the dropdown/action lifecycle, with menu identity retained across player/clock updates unless choices or selection change. Auto, saved-unavailable fallback and SDK-bound selection remain unchanged. Tests still require a real visible/hittable option tap and changed selection in glass/plain modes; explicit guards now fail immediately if a queried option is not hittable. No gates, receipts or deadlines were relaxed. All 96 Ubuntu checks passed after the change. Corrected Apple execution and physical-device results remain pending.

## Second Apple run: native menu passed, clipboard fixture stalled

[GitHub run 44588164746](https://github.com/BananaOnGitHub/Streamside/actions/runs/44588164746), source `c775729acdab35e63ccca3142bebe5235ea1d493`, passed compilation, native playback/quality/lifecycle fixtures, marked-content UI and the complete glass-controls gate (186.501 seconds), including actual UIKit Resolution selection. The plain-controls gate stalled at its first Read clipboard action following Copy Link, before its Resolution interaction. The app event loop and subsequent accessibility requests stopped responding. The unchanged 300-second worker limit ended the test; the incomplete result bundle again prevented screenshot export. No successful components or IPA were produced. [Scoped evidence](SWIFTUI_ACCOUNT_AVATAR_RESOLUTION_BUILD_FAILURE_2.json) preserves logs, hashes and the reported failure boundary.

The next correction is limited to the Apple test environment. A scoped helper saves Simulator's `PasteboardAutomaticSync` setting, disables and verifies host synchronization before creating the simulator, then restores the prior value or absent key in `finally`. All real simulator-local Copy Link and system-share clipboard assertions remain enabled. The five UI gates, native quality selection, component requirements and deadlines are unchanged; no retry or skip was added.

[WebKit's primary investigation](https://bugs.webkit.org/show_bug.cgi?id=237372) documents historical simulator clipboard timeouts and disabling this synchronization as a mitigation. That supports trying this environment isolation; it does not prove the exact cause on the current Xcode runner. No process stack or successful replacement run is available yet. Five host tests cover preference/default restoration, error cleanup, value rejection and verification; all 101 Ubuntu tests pass. Actual environment isolation, the remaining plain/preview/thumbnail gates, full component validation and physical-device testing remain pending.

## Successful Apple run and local package

Source `533e3f0e587a5d9336a7944c3c5868fdab2d6fbb` passed [GitHub run 44600451526](https://github.com/BananaOnGitHub/Streamside/actions/runs/44600451526). All six Apple stages and all five coordinate gates passed. Glass/plain tests both selected a real UIKit menu option and verified its changed selection, while retaining clipboard, rendered-motion and opacity checks. Native fixtures passed quality selection without another request/player, missing-rendition fallback/restoration, background restoration and teardown. Model tests passed per-channel persistence, Auto, bounds/isolation and avatar identity. Existing decoded-video, preview, account/audio/VAFT and local-test gates passed.

The build log confirms simulator host clipboard synchronization was disabled/verified and its original absent preference restored after testing. This successful run supports the scoped environment mitigation; it does not independently prove the cause of the preceding clipboard stall. Both failure records remain preserved.

Verified retrieval, all 67 post-download checks, exact-donor admission and local package verification passed. [Validation receipts and identities](SWIFTUI_ACCOUNT_AVATAR_RESOLUTION_VALIDATION.json) retain exact source/toolchain/archive/framework/IPA hashes. The package uses Twitch 32.0 build 263110145453907615, with 67 admitted Swift ABI entries, 25 probes, four newly pinned Objective-C quality selectors, retained donor contents verified and original HBC unchanged. Only the native IPA was assembled; donor/signing inputs remained local.

Candidate: `artifacts/native-frontend/account-avatar-resolution-533e3f0/StreamsideNativeProof-Twitch32-native.ipa` (relative to the Streamside workspace). Sign with Feather using the existing app identity; adjacent `TESTING.txt` covers avatar/heading review, real quality selection, per-channel persistence, Auto and lifecycle regression checks. Physical-device validation remains pending.

## Physical-device follow-up

The user confirmed successful resolution switching, the authenticated account avatar in Settings, saved resolution restoration after reopening, and independent preferences on other channels for source `533e3f0`. [Scoped device record](SWIFTUI_ACCOUNT_AVATAR_RESOLUTION_DEVICE.json) associates those observations with the previously packaged IPA. No diagnostic export accompanied this report; it does not add a new runtime-count observation.

The subsequent [channel profile trial](SWIFTUI_CHANNEL_PROFILE.md) removes audio-only quality choices following intermittent device behavior. The earlier successful build and its hashes above are unchanged.
