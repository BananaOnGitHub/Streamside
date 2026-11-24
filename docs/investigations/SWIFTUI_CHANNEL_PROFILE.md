# Native channel profile prototype

Work on `feat/native-frontend` starts at `b3f43bf390192c508015023fc99b42e60e3d5dd7`, after the user accepted the resolution/avatar build `533e3f0`. This record accompanies the implementation commit. Apple compilation, simulator execution, local packaging and profile device acceptance are pending at submission.

## Presentation and ownership

Channel identity buttons in the live/offline feed, Quick Look details and theatre open an owned SwiftUI profile. Quick Look's View profile action is enabled. Its existing transaction first finishes dismissal, stops the preview and releases navigation, then opens the profile. The Watch transaction still transfers its original player. Opening a profile from theatre retires and dismisses theatre first; closing the profile returns to the feed rather than maintaining a hidden audible theatre.

The banner extends behind the status area while the back control stays within the safe area. Identity, verified badge, live category/viewers, biography, follower count and social links precede Liquid Glass follow/notification controls and disabled Subscribe. Home contains the existing muted native live surface, full title and tags. About shows standard text/image/link panels. Interactive extension panels are identified as unavailable. Panel text is plain text in this prototype; no HTML/JavaScript, recaps, subscription or other profile pages are implemented. Reduce Transparency uses a solid control background and pre-iOS-26 devices use material. The profile uses the system cross-dissolve; it adds no custom motion or colour configuration.

The inline player uses `TheatrePlayback(preview:true)`, setting mute before any load and retaining existing content-consent and ambient/mixing audio policies. Home/About and background transitions stop/recreate the inline facade. Watch dismisses the profile and passes the same facade to the existing theatre; only the theatre's successful presentation promotes audio. Account/session change closes the profile and cancels requests. Existing root ownership, launch selection and RN/Hermes instrumentation remain unchanged. This implementation adds no donor hooks.

## Exact Twitch 32 services

The inspected donor is Twitch 32.0 build `263110145453907615`, IPA SHA-256 `076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`. Existing image hashes and new export/selector admission live in [twitch32.json](../../native/twitch32.json).

Twitch's `ProfileViewController`, `ProfileHomeViewController`, `ProfilePanelsViewController`, `ChannelNotificationSettingsManager` and notification button model expose no usable Objective-C designated constructor for the required private Swift dependencies. The original About implementation has web-view navigation. Calling inherited `NSObject.init` or reading their Swift fields would not establish a valid service boundary. The prototype therefore owns its view/menu and reuses the generated native operations and existing authenticated Apollo client. The notification menu is recreated using the donor's four backend choices; it does not claim to embed Twitch's controller.

[SSNProfileRequest.c](../../native/SSNProfileRequest.c) confines the donor-specific Swift ABI. It uses:

- `ProfileInfoFromChannelIDQuery` for native profile metadata and its shared profile fragment, including standard panels and social links.
- `UserFollowingStateQuery` for the viewer/channel relationship, follow permission and current notification choice.
- `UnfollowUserMutation`, `FollowUserMutation` and `SetLiveNotificationsEnrollmentMutation` for explicit user actions only.
- `TKGraphQL.apolloClient`, native `fetchAsPromise` and `performAsPromise`; existing authorization, client-integrity and account handling remain in the donor. No independent endpoint, token extraction or login/renewal logic is added.

Inspected boundaries include the profile constructor at `TwitchGraphQLAPI+0x54bd94`, notification input at `+0x776de4`, native mutation overload at `TwitchKit+0x24d8ec`, mutation result `unwrapped` at `TwitchApollo+0x93f0`, and nullable nil-literal initializer at `ApolloAPI+0xcb88`. The query's concrete nullable arguments use native constructors and runtime metadata. Mutation-result metadata has two generic parameters, two requirements and four packed key arguments; conformance comes from `swift_conformsToProtocol`, without protocol witness-slot indexing. The native `unwrapped` getter copies through the runtime value witness rather than decoding a Swift Result layout.

Each operation uses its own generated `Data.__data` getter. Native `DataDict._data` and standard dictionary bridging copy the response; nested native values are unboxed through `swift_dynamicCast` and their actual runtime metadata. No donor object-field offsets are read. Only whitelisted, depth/count/length-bounded profile/follow fields pass into presentation models. Request/error content and account/channel metadata are not added to diagnostic exports. The existing credential-free image cache accepts Twitch image hosts and the exact `panels-images.twitch.tv` host; it retains timeouts, response bounds and redirect checks.

Notification values are `PERSONALIZED`, `ALWAYS`, `LIVE_UP_ONLY` and `NEVER`; the UI labels are Personalized, Always, Go Live Only and Off. Unfollow uses a compact popover with the question and sole destructive action; outside tap dismisses without writing. A confirmed mutation is followed by a fresh relationship query before the UI reports the new state. Failure or unconfirmed state remains an explicit error; no mutation is retried automatically. Confirmed changes request a guarded feed refresh.

## Video-only resolutions

The source request sets `allow_audio_only=false`. Available qualities are filtered to positive video width/height through inspected `IVSQuality` Objective-C getters, with runtime encoding checks. Old saved `audio_only` preferences resolve to Auto. Other per-channel preferences and quality-selection behavior are retained. The existing synthetic native quality fixture now supplies an audio-only object and requires it to be absent from the visible list.

## Validation and reproducibility

[Host record](SWIFTUI_CHANNEL_PROFILE_HOST.json): all 113 native-frontend Ubuntu checks and 12 provider-routing checks pass. The new C adapter also compiles for the iOS ARM64 ABI with Zig/Clang warnings treated as errors. Host checks include exact donor identity/export/selector admission, caller-register emulation, execution of the inspected query constructor and nullable initializer against synthetic runtime callbacks, descriptor rejection and component-receipt requirements. These checks do not run a Twitch account or Apple UI.

Apple CI compiles all production profile source and requires new Foundation normalization/lifetime and Swift model tests for account cancellation, field bounds, safe links, follow/notification writes and post-write verification. A sixth coordinate gate exercises the production Home/About profile, disabled Subscribe, outside-dismiss confirmation, four notification choices, confirmed unfollow and close with synthetic backend data. Existing five coordinate gates, decoded-video clipping, audio/VAFT/lifecycle/quality tests and source/toolchain-matched component verification remain mandatory. The production preview transaction gains a profile-route ordering test. No tests are skipped or deadlines relaxed.

Submit through `make native-ci`; this selects one provider using account balance/history and falls back to GitHub Actions. The pinned Apple toolchain is unchanged. After a successful build, `make native-ci-fetch` verifies exact-source components and receipts before the usual local donor packaging. Donor IPA and signing inputs remain local. Submission is not a successful compilation, and no new installable IPA is claimed here.

Device checks after packaging:

1. Open a channel by its feed avatar/name and by Quick Look → View profile. Check banner/notch, live/offline identity, biography, links and Home/About panels.
2. On Home, confirm muted video leaves other media playing; About, background, account loss and close stop the inline player. Watch should continue into theatre without duplicate playback or early audio.
3. Open/dismiss Unfollow outside the popover without changing follow state. If desired, explicitly confirm a real unfollow and verify it persists; this changes the actual account. Verify notification choice restoration and errors while offline. Subscribe stays unavailable.
4. Confirm no audio-only resolution, saved video preferences remain per channel, and diagnostics still show the expected guarded native runtime counts. Export a report after profile/preview/theatre/background/reopen checks. Visual success alone is not evidence of zero RN/Hermes creation.

Real authenticated profile queries, mutations, actual IVS profile playback and physical-device runtime counts remain unvalidated until device results are supplied.

## First Apple build failure: error-state qualification

[GitHub run 44649618815](https://github.com/BananaOnGitHub/Streamside/actions/runs/44649618815), source `eb280a53864d6fe8be132e1f7bd4f46d432e2277`, failed during the initial iPhone SwiftUI compilation. In `ChannelProfileModel.change`, the catch handler assigned a message to the implicit immutable `Error` binding named `error`, rather than the model's string property. The compiler reported both the immutable assignment and incompatible String/Error types. Build-logging and shared VAFT stages passed; linking, new profile model/native tests, simulator gates, component verification and packaging were not reached.

The correction is limited to `self.error` in that handler. The existing model test that checks an unconfirmed mutation's failure state remains mandatory. All 113 Ubuntu native-frontend checks pass after the correction; Ubuntu does not compile this SwiftUI code. Apple revalidation remains pending at resubmission. No gate or deadline changed. [Failure record](SWIFTUI_CHANNEL_PROFILE_BUILD_FAILURE_1.json) retains the run identity and hashes for the bounded diagnostics archive and job log, stored outside the source checkout.

## Second Apple build failure: fixture assertion macro

[GitHub run 44662345316](https://github.com/BananaOnGitHub/Streamside/actions/runs/44662345316), source `a7c8e4a42476b96a401dfc8029e07f21f2d36033`, passed production SwiftUI and native interoperability compilation, framework linking and signature verification. Existing account/feed/presentation models, VAFT transport, content-label lifetime and inline-consent admission tests also passed. It failed while compiling `profile_test.m`: the inline expected dictionary inside `NSCAssert` contained commas that the preprocessor treated as macro argument separators. The first syntax error was at line 33; subsequent errors were a cascade from the malformed expansion.

The correction moves the identical expected dictionary into a named variable before the unchanged equality assertion. Production source is untouched in this correction. All 113 Ubuntu native-frontend checks pass; these do not execute the Foundation fixture. Profile fixture execution, new profile model tests, simulator gates and complete component validation remain pending. No mandatory test or deadline was removed or relaxed. [Second failure record](SWIFTUI_CHANNEL_PROFILE_BUILD_FAILURE_2.json) preserves exact run/artifact identities, passed boundaries and evidence hashes outside the source tree.

## Successful Apple run and local package

Source `d3c96a775b0fb0935ca0395180d01edf6dec02f6` passed [GitHub run 44663919920](https://github.com/BananaOnGitHub/Streamside/actions/runs/44663919920). All six Apple stages and all six coordinate gates passed, including the new production Home/About profile interaction gate. Native normalization/account-lifetime and Swift profile model tests passed. Existing glass/plain controls, consent, preview gestures, changing decoded-video clipping, single-player handoff, audio/session/VAFT and quality checks remain required and passed. Xcode 26.6 (`17F113`), Swift 6.3.3 and iPhoneOS SDK 26.5 match the pinned toolchain.

Ubuntu retrieved the exact source-matched components and verified the archive hash, source/proof/toolchain identities, required receipts and post-download suites against the Apple-produced ARM64 caller object. Local assembly verified the exact donor identity and all admitted boundaries, preserved original HBC/backend bytes and checked every retained ZIP entry. Only the native IPA was assembled; donor bytes and signing material were not uploaded to Actions. [Successful validation/package record](SWIFTUI_CHANNEL_PROFILE_VALIDATION.json) retains the complete required receipts, source revision, artifact hashes and reproducible command.

The Feather-signable package is `artifacts/native-frontend/channel-profile-d3c96a7/StreamsideNativeProof-Twitch32-native.ipa`, 197,207,757 bytes, SHA-256 `210c898fa81a8ff8efa5da18e5b0b787315b5551bbc6feb1c5f59d6745edc5ba`. It still requires local signing with the same application/keychain identity. Physical-device validation of authenticated profile/panel data, follow/notification changes, inline profile playback and runtime counts remains pending; synthetic backend and UIKit results are not device acceptance.

## Device profile-data failure and relocation-safe metadata

The user reported that the profile opens but cannot retrieve details on source `d3c96a7`. [Scoped device/correction evidence](SWIFTUI_CHANNEL_PROFILE_DEVICE_FAILURE_1.json) preserves the report identity and relevant observations. SwiftUI still owns the root, the account/feed state is ready with 100 returned channels, all four probe images are armed, the global failure mask is zero, and all 25 runtime-entry counters are zero. The export has no matching baseline calibration and no profile-specific stages; it does not establish which profile request or decode step ran. The earlier synthetic CI success and package hashes remain valid within their original scope and did not establish authenticated profile loading.

Exact-donor analysis found a definite early initialization failure. `TwitchApollo+0x14a20` exports `TwitchGraphQLError` value metadata. Its second word at `+0x14a28` is a `DYLD_CHAINED_PTR_64_OFFSET` rebase, encoded on disk as `0x0030000000010df0`. dyld replaces it with the loaded address of `+0x10df0`. The runtime resolver's 16-byte file-prefix comparison therefore rejects this data symbol after loading. `initialize()` cannot obtain the error metadata and returns false before the new native profile request begins. The correction calls the inspected metadata accessor at `+0xcc68`, whose instruction bytes remain stable under image relocation. Metadata data-export bytes remain inspection evidence, outside the runtime prefix table. Native request authorization, integrity, renewal and account state are unchanged.

Donor admission now walks the supported pointer chains and rejects a runtime prefix entry overlapping a dyld fixup. Regressions verify the actual metadata slot is a fixup, reject reintroduction of the old entry, and execute the real accessor at different image bases. This checks runtime relocation behavior that the original on-disk export-prefix tests missed; it does not claim to execute an authenticated service request on Ubuntu.

A review of the same bridge also corrected callback ownership: per-operation static C records must not be passed as Swift-managed thick-closure contexts. Five capture-free value/error mapping entry points now use NULL contexts. Mutation map callbacks were already capture-free. The native normalization path remains whitelisted and bounded.

Diagnostic exports add `profile_events`, a fixed 5 × 12 numeric table. Rows are profile, relationship, unfollow, follow and notifications. Columns are started, ABI ready, submitted, mapped, normalization failed, native error, completed, cancelled, session changed, timed out, unavailable and response rejected. The last stage includes Swift presentation rejection of a malformed/unconfirmed response. Original-startup mode leaves these counters zero. They do not set global runtime failure bits or alter any RN/Hermes probe counts, and contain no identity, token, request/response, URL or error-text values.

All 116 Ubuntu native-frontend tests and 12 provider-routing tests pass. The production C adapter compiles for the iOS ARM64 ABI with warnings as errors. Existing Foundation tests additionally assert native completion/cancellation/account-change stage observations, and Swift model tests assert numeric rejection callbacks. Existing Apple/component gates are retained. Corrected Apple compilation and real-device profile retrieval remain pending at submission. After installation, open a profile, allow loading to finish (or retry), then export native diagnostics; the new table distinguishes initialization, transport, normalization and presentation rejection if data still cannot load.

## Third Apple failure: simulator clipboard-read stall

[GitHub run 44680012229](https://github.com/BananaOnGitHub/Streamside/actions/runs/44680012229), source `952cf7ba9d15b6c893cdf048ca69051c99279ff2`, passed production compilation/linking, native profile normalization/lifetime and Swift profile models, existing owned simulator lifecycle fixtures, marked-content UI and the full glass-controls gate. The plain-controls test stalled on its first Read clipboard action after production Copy Link. The app stopped responding to idle and accessibility requests; the copied-link equality check failed, and failure collection then reached the unchanged 300-second gate deadline. The incomplete result bundle prevented screenshot export. [Third failure evidence](SWIFTUI_CHANNEL_PROFILE_BUILD_FAILURE_3.json) preserves logs, diagnostics hashes and exact passed/not-reached boundaries. No replacement components or IPA were produced.

Simulator host pasteboard synchronization was already disabled and verified. Its earlier successful mitigation did not prevent this recurrence. The log identifies a synchronous general-pasteboard read as the boundary, but no process stack establishes the underlying service or permission cause. The correction replaces the test-only read button with [SwiftUI's system PasteButton](https://developer.apple.com/documentation/swiftui/pastebutton/init(payloadtype:onpaste:)), accepting a real URL. Production Copy Link and UIKit Share Copy still write the real general pasteboard; the tests tap the actual system Paste control and require the same exact URL. Each round trip first clears both clipboard and displayed result, preventing stale success. Both glass/plain clipboard pass markers are required by the worker. Production UI, six coordinate gates, test deadlines, donor admission and component requirements remain intact. Apple execution of the changed fixture and authenticated profile-device retesting remain pending.

All 117 Ubuntu native-frontend tests and 12 provider-routing tests pass after the fixture change. The full native suite used the explicit pinned Zig compiler; an initial invocation without that environment failed and was rerun without skips. Documentation validation passes. These host checks do not execute the changed system Paste control; Apple simulator validation remains pending.

## Corrected profile build and local IPA

Source `5e355f90b06aa7a5cefd206788a53e9b45f2c05f` passed the Apple and ABI jobs in [GitHub run 44684010749](https://github.com/BananaOnGitHub/Streamside/actions/runs/44684010749). All six Apple stages and six coordinate gates passed. Both player-control styles verified fresh Copy Link and system-share Copy through the system Paste control. Profile normalization and model fixtures passed, along with the Home/About interaction test. The verified component download passed 77 local checks across seven suites.

Local assembly used the pinned Twitch 32.0 donor and produced `artifacts/native-frontend/channel-profile-5e355f9/StreamsideNativeProof-Twitch32-native.ipa`. The IPA includes the relocation-safe profile bridge and the numeric `profile_events` diagnostics. Sign it with Feather using the existing application and keychain identity, then open a channel profile and check its details and About panels. Export native diagnostics after the attempt so that the request stages can be compared with the result. [Build and package evidence](SWIFTUI_CHANNEL_PROFILE_CORRECTION_VALIDATION.json) records the exact toolchain, hashes and test scope. Authenticated profile loading on a physical device remains pending.

## Profile viewport and relationship decoding

On `5e355f9`, the device showed real profile details and live video, but the live status, action bar, tabs and preview extended beyond the trailing screen edge. The generic profile error also appeared. [Device evidence](SWIFTUI_CHANNEL_PROFILE_DEVICE_2.json) shows seven completed profile metadata requests and seven relationship responses that reached the mapping callback and failed normalization. No mutations ran. These results confirm real profile metadata retrieval on this device and isolate the remaining load error to the relationship response.

The profile now sizes its banner and content from the viewport. The banner and panel artwork crop inside bounded overlays, and the live status can wrap. The banner uses a bottom gradient and a light material blur behind the identity. Reduce Transparency uses the color gradient alone.

Twitch 32.0's generated `UserFollowingStateQuery` returns `followsSettingState` as `GraphQLEnum<FollowsChannelNotificationSettingState>`. That value can be boxed inside the bridged Apollo dictionary. For this field, the native normalizer now accepts the exact enum through a metadata-checked cast and calls ApolloAPI's pinned `rawValue` accessor. Emulation covers the accessor's known and unknown cases against synthetic metadata callbacks. The device counters do not identify the individual rejected field. The replacement build must confirm the fix against a real response. The model now reports a separate follow/notification error when profile metadata has loaded and only the relationship read fails. About remains available and follow writes stay disabled until the relationship loads.

The existing profile coordinate gate now checks the full-width tab, action and 16:9 preview frames with a long live status. It also checks that a failed relationship read leaves About available. The Foundation fixture exercises a boxed notification value and retains the privacy whitelist. Apple and physical-device validation remain pending for this change.

## Fourth Apple failure during Xcode result finalization

[GitHub run 44698730424](https://github.com/BananaOnGitHub/Streamside/actions/runs/44698730424), source `8bacfc8`, passed production compilation and the native and Swift profile fixtures. `testMarkedContentConsent` finished in 208.647 seconds with one executed test and zero failures. Startup and test execution consumed about 255 of the command's 300 seconds. Xcode did not return before the deadline, and the partial result bundle had no `Info.plist`. Later coordinate gates did not run. [Failure evidence](SWIFTUI_CHANNEL_PROFILE_BUILD_FAILURE_4.json) identifies the run, preserves hashes and distinguishes the passed XCTest case from the failed command.

The coordinate runner retains its existing execution deadlines. A successful selected-suite footer provides up to 120 seconds for Xcode to finish writing results and exit when the original deadline would allow less. This allowance starts once. Xcode must still exit successfully and the worker must verify every expected test and receipt. Local regressions cover a split footer, delayed successful exit, nonzero exit after the footer, an incomplete footer and stalled finalization. The overall CI workflow deadline is unchanged. The replacement Apple run and the corrected profile IPA are pending.

## Validated profile viewport and relationship build

Source `ea8b0d9` passed both jobs in [GitHub run 44701442860](https://github.com/BananaOnGitHub/Streamside/actions/runs/44701442860). All six Apple stages and six coordinate gates completed, including the expanded profile fixture that checks viewport bounds, the 16:9 preview and About access during a relationship failure. Every `xcodebuild` test command exited within its previous deadline in this run. The local runner regressions exercise the added allowance beyond the original deadline. The exact downloaded components passed 77 checks across seven suites.

Local assembly produced `artifacts/native-frontend/channel-profile-ea8b0d9/StreamsideNativeProof-Twitch32-native.ipa`. [Build and package evidence](SWIFTUI_CHANNEL_PROFILE_VIEWPORT_VALIDATION.json) records the source, toolchain, test timings, hashes and device scope. Physical-device validation remains pending for crop-to-fill banner artwork, the banner fade and real authenticated follow and notification state.

## Compact profile actions, branded links and About decoding

On `ea8b0d9`, the device screenshot shows the bounded profile and banner gradient. It also shows both relationship controls active while live video plays. No corresponding numeric export or About payload accompanied the panel loading report. The missing field, an empty list and unreadable records were previously indistinguishable in About.

The profile now keeps only the Live or Offline label next to the avatar. Live category and viewer count appear below the stream title above its tags. The follower count anchors the left side of the compact actions row. Follow, notifications and the star sit on its right. The star uses a solid capsule and opens a small link to [Twitch's web subscription manager](https://www.twitch.tv/subscriptions). The existing authenticated profile fragment supplies `currentUser: self { subscriptionBenefit { id } }`. A present benefit fills the star, an explicit null leaves it outlined, and missing status is represented separately for accessibility. The app makes no subscription writes and does not pass credentials to the web link.

Recognized social domains use bundled [Simple Icons artwork](https://github.com/simple-icons/simple-icons/tree/10.0.0) with platform-specific tints. Twitter and X hosts both use the bird unless the link title explicitly names X. Other URLs keep the chain glyph. [Artwork provenance](../../native/assets/profile-social.json) pins the source and generated PNG hashes. Components verify the artwork against the repository before local assembly.

The same native `ProfileInfoFragment` selects the nullable panel records and the standard panel title, description, image and link. The profile bridge now recognizes Foundation arrays and boxed Swift arrays, resolves the pinned generated panel type and projects its data using its own donor getter. The restricted panel decoder skips null elements and isolates unreadable items while retaining other usable panels. A missing or unreadable list gives About a retry and a link to the channel's Twitch About page. An explicit empty array has a separate empty state and the same web link. Interactive extensions remain identified as unavailable. The diagnostics append four fixed columns to `profile_events`: panel field missing, empty, available and unreadable. These counters contain no panel contents, URLs or channel names.

Apple simulator coverage includes the compact header, subscription popover and About flow. Host emulation checks the exact donor metadata and getter path. A fresh device test is required to confirm that the reported channel's panels now appear, because the earlier export does not identify its response shape.

Ubuntu passed all 124 native frontend tests, including the donor panel boundary and bundled artwork checks. The C profile adapter also passed ARM64 iOS compilation with warnings as errors. The revised SwiftUI and Foundation fixtures await Apple execution.

## Fifth Apple failure: stale consent accessibility value

[GitHub run 44723220754](https://github.com/BananaOnGitHub/Streamside/actions/runs/44723220754), source `319d477`, compiled and linked the profile changes and passed the native and Swift profile fixtures. The marked-content coordinate case failed an immediate accessibility read after tapping “Don’t show again” in theatre. The first snapshot reported “Not selected” and the captured failure hierarchy showed “Selected” about 1.6 seconds later. XCTest reported one failed test. Xcode then reached the 300-second command deadline with an unfinished result bundle. [Failure evidence](SWIFTUI_CHANNEL_PROFILE_BUILD_FAILURE_5.json) preserves both the assertion and the later state.

The test now waits for “Selected” after the single tap using the existing five-second value predicate. The remaining consent assertions are identical. Xcode startup took about 109 seconds in this run. The runner now budgets up to 150 seconds for setup, the same 300 or 600 seconds for the selected XCTest case and 120 seconds for result writing after a complete pass or failure summary. A pass still requires a successful Xcode exit, the named case, one executed test with zero failures and all six coordinate receipts. The overall workflow limit and the failed-build artifact scope stay in place. Apple revalidation and the updated IPA are pending.

## Validated profile actions and panel package

Source `bfdabb8` passed both jobs in [GitHub run 44758634903](https://github.com/BananaOnGitHub/Streamside/actions/runs/44758634903). The marked-content consent test and all five remaining coordinate gates passed. The profile gate covered the compact action row, subscription popover, stream detail placement and About with fixture panel data. Native and Swift profile fixtures passed, and the verified component download passed 78 checks in seven suites.

Local assembly produced `artifacts/native-frontend/channel-profile-bfdabb8/StreamsideNativeProof-Twitch32-native.ipa`. All eight social images were verified inside the IPA. [Build and package evidence](SWIFTUI_CHANNEL_PROFILE_PANELS_VALIDATION.json) includes the artifact identities and timing receipts. The affected channel's live About response and the authenticated subscription state still need physical-device testing. If About continues to show no panels, the four appended `profile_events` counters distinguish a missing list, an empty list, a decoded list and an unreadable list.

## Device panel artwork and Twitch CDN migration

The `bfdabb8` device report recorded three successful profile and follow-state requests. All three profiles had nonempty decoded panel lists, and About displayed cards or image placeholders. [Device and CDN evidence](SWIFTUI_CHANNEL_PROFILE_DEVICE_PANELS.json) records the report hash, scoped observations and validation limits.

A public Twitch channel About page displayed five panel images from `panels.twitch.tv`. The image policy previously rejected that host and allowed `panels-images.twitch.tv`, which returned no A, AAAA or CNAME answer in the live DNS check. The current host returned `200 image/png` for two visible panel images and a verified older panel path. This reproduces the policy mismatch without logging authenticated GraphQL payloads.

The image policy adds the exact current host and rewrites HTTPS legacy panel artwork URLs to it. The credential-free session still checks HTTPS, ports, redirects, HTTP status, image MIME type, byte count and ImageIO decoding. About displays panel artwork at its natural aspect ratio and distinguishes loading from a failed image request. The existing simulator profile gate uses a local response for a tall PNG at the current host, reached from a legacy panel URL. The real-device artwork check remains pending.

## Sixth Apple failure: native worker total deadline

[GitHub run 44785194285](https://github.com/BananaOnGitHub/Streamside/actions/runs/44785194285), source `c93ae13`, compiled and linked the artwork fix and passed both profile fixtures. Marked content, glass controls, plain controls and Quick Look completed. XCTest passed the thumbnail case with zero failures in 109.202 seconds. Its result was still finalizing when the 1800-second native worker deadline ended the process. The new profile artwork coordinate case never started. [Failure evidence](SWIFTUI_CHANNEL_PROFILE_BUILD_FAILURE_6.json) preserves the distinction between the passed XCTest case and the incomplete command.

The native worker now has 2250 seconds. The baseline has 600 seconds, informed by the prior successful baseline of 333.9 seconds. Both fit inside the existing 3000-second component stage. The GitHub Apple job has 55 minutes so the other checks and artifact upload can finish after the component stage. Codemagic's 40-minute budget still applies on that provider. Individual simulator limits and required receipts are unchanged. The replacement Apple validation and artwork device test are pending.

## Seventh Apple failure: Quick Look menu tap after scrolling

[GitHub run 44791085804](https://github.com/BananaOnGitHub/Streamside/actions/runs/44791085804), source `2bbd3e8`, compiled the artwork change and passed the profile fixtures, marked content and both player control styles. The short Quick Look menu and video taps each transferred the same, still-decoding player. In the long case, the last detail was visible after scrolling, but a tap on Watch left the preview on screen. XCTest reported a failed handoff assertion and Xcode returned exit 65 with a completed result bundle. [Failure evidence](SWIFTUI_CHANNEL_PROFILE_BUILD_FAILURE_7.json) preserves the fixture screenshot and accessibility log. The thumbnail and profile artwork gates had not run.

The menu now assigns the full extent of each action row to a UIKit button. The SwiftUI title, icon and glass background remain the presentation layer. The existing coordinate gate taps the trailing padding once, including after the long details scroll, and still requires the single-player handoff and decoded theatre frames. The fixture shows that Watch did not activate, without identifying the internal touch failure. All 126 host checks passed. The new hit targets await Apple validation.

## Eighth Apple failure: unavailable preview action state

[GitHub run 44801411797](https://github.com/BananaOnGitHub/Streamside/actions/runs/44801411797), source `3fca3b9`, built the SwiftUI component and passed the marked-content and both player control gates. XCTest stopped at the first Quick Look opening because it reported the View profile row as enabled. The fixture supplies no profile callback. The test stopped before any Watch tap and before the thumbnail and artwork gates. [Failure evidence](SWIFTUI_CHANNEL_PROFILE_BUILD_FAILURE_8.json) records the assertion and fixture screenshot.

The unavailable row again uses a disabled SwiftUI button, as in the last passing version of this test. Active actions retain the full-width native touch targets. The coordinate gate requires the unavailable row to be present and disabled by its accessibility identifier. The single-tap Watch, player reuse and artwork checks remain required.

## Ninth Apple failure: cancellation assertion raced the preview return

[GitHub run 44808271626](https://github.com/BananaOnGitHub/Streamside/actions/runs/44808271626), source `0d31552`, passed the full Quick Look panel gate. The unavailable profile row was disabled and one tap after scrolling transferred the same player with decoded video still advancing. The thumbnail gate later asserted that Watch had disappeared immediately after the account-loss stop count reached one. Its teardown snapshot showed the thumbnail restored, the menu absent and zero Watch actions. The profile artwork coordinate case had yet to start. [Failure evidence](SWIFTUI_CHANNEL_PROFILE_BUILD_FAILURE_9.json) includes both the test log and the fixture screenshot.

The simulator test separately requires one media stop and bounded disappearance of the Watch row. After account loss it also checks that the source is hittable and rechecks the stop and Watch counts. The same disappearance check covers backgrounding and swipes, which use the same cancellation path. Production teardown and all required gates are unchanged.

## Verified artwork and Quick Look test package

Source `d50c38e` passed the Apple and ABI jobs in [GitHub run 44821693367](https://github.com/BananaOnGitHub/Streamside/actions/runs/44821693367). All six coordinate gates passed, including the disabled Quick Look profile row, the scrolled Watch handoff, thumbnail cancellation and decoded tall About panel artwork. The simulator supplied fixture image bytes only after the production image policy rewrote the legacy URL to Twitch's current panel host. The downloaded components also passed all 78 local verification tests.

Local packaging produced one native IPA at `artifacts/native-frontend/channel-profile-d50c38e/StreamsideNativeProof-Twitch32-native.ipa` from the exact Twitch 32.0 donor, keeping the donor and assembled IPA local. [Build and package evidence](SWIFTUI_CHANNEL_PROFILE_ARTWORK_VALIDATION.json) records the revisions, timings, toolchain, validation scopes and artifact hashes. Real panel artwork on the affected channel and the updated Quick Look handoff still need physical-device confirmation.

## Device artwork and About panel links

An iPhone check of source `d50c38e` confirmed that artwork loaded in About. A text panel displayed raw Markdown link syntax. The screenshot captured the rendering issue. The image-link destination still needed testing.

The About panel model now parses inline Markdown while preserving the original spacing and line breaks. Only existing HTTP and HTTPS destination policy matches retain clickable link attributes. A linked image is the tap target, and the separate text link remains available when the panel has no image or its artwork fails to load. A long press presents a native SwiftUI context menu with a transient WebKit preview and an Open link action. The preview uses a nonpersistent website data store, disables content JavaScript and stops loading when dismissed. Some destinations need the full browser to render. [SwiftUI context menu API](https://developer.apple.com/documentation/swiftui/view/contextmenu%28menuitems%3Apreview%3A%29)

Apple fixtures cover inline link markup, whitespace and rejected destinations. The profile coordinate test opens the artwork directly, long-presses for the context action, and taps the rendered Markdown link, checking the destination for each. The fixture does not depend on a live destination. The WebKit page content and gesture on the real profile need device testing.

## Markdown blocks, larger link previews and profile navigation

Device testing of the panel-links package confirmed link activation. Feedback identified unstyled block markup, a compact webpage preview and an uneven profile transition. The screenshots and identifying profile details remain local.

About now renders Foundation's Markdown block structure in SwiftUI, including headings, nested quotes and lists, code, separators and tables. Inline styling and the existing HTTP/HTTPS link policy still apply. Inline-only descriptions keep their original line breaks. The existing system context menu requests a preview with 16-point side margins on iPhone and a taller webpage area, bounded by the available height and the action menu.

The window owner now uses a UIKit navigation stack to push the SwiftUI profile. Its built-in transition and leading-edge swipe work with the existing banner and back control. The profile retains media ownership through a Watch handoff until the stack has returned to the feed. The profile simulator fixture exercises that navigation controller with button and edge-swipe returns. Apple validation and device measurements of the context preview are pending.

## Tenth Apple failure: Fade frame sampling

[GitHub run 44852174365](https://github.com/BananaOnGitHub/Streamside/actions/runs/44852174365), source `007d108`, compiled the profile changes, passed the Markdown block and link tests, and completed the marked-content coordinate gate. The glass control fixture observed synchronized Fade entry frames across a progress range of 0.018–0.766. Its endpoint waiter returned before the sample collector recorded progress above the required 0.8. The profile navigation and preview coordinate checks had yet to run. [Failure evidence](SWIFTUI_CHANNEL_PROFILE_BUILD_FAILURE_10.json) records the exact run, sample range and diagnostic artifact hashes.

The measured stages now wait for both the rendered endpoint and the existing sample range before evaluating the results. If either is missing at the existing deadline, the failure includes the observed range and details from completed stages. The production animation and all frame, pixel and interaction requirements are unchanged.

## Verified profile navigation and Markdown package

Source `156eb857fc87ed382367294b6522a3585bf3ce0e` passed both jobs in [GitHub run 44854539551](https://github.com/BananaOnGitHub/Streamside/actions/runs/44854539551). All six coordinate gates passed. The profile fixture verified Markdown headings and links, the image context menu, the back button and the leading-edge swipe. Both player styles met the existing motion and pixel requirements. Local component verification passed 78 checks.

Xcode 26.6 (17F113) compiled the SwiftUI component. The verified component archive SHA-256 is `3a5f78f8e4a183817f17d40d0d9172ac8612866b62335e0ad9995cc1779d7265`. Local assembly from the pinned Twitch 32.0 donor produced one native IPA at `artifacts/native-frontend/channel-profile-156eb85/StreamsideNativeProof-Twitch32-native.ipa`, 197,291,232 bytes, SHA-256 `0e9bfd7c0aa0d720607d7557eead0169cbc0d84f0dc5db26bd55dd22624cfc0e`. The actual webpage preview size and appearance on an iPhone remain to be checked.

## Profile link menus, swipes and accent color

Device feedback confirmed the larger preview and the standard profile push. On iOS 17 and later, link-bearing Markdown blocks use TextKit to open the native link menu on the actual link range. The preview uses the same nonpersistent WebKit configuration and size as linked artwork. Earlier iOS versions retain inline link taps. A profile-only swipe selects Home or About and yields at the screen edges, inside horizontal scroll views and over the segmented control.

The anchored stream preview keeps its shared-player lifecycle and separate action plate. The full-width rows use native button presentation and pressed feedback. Player quick settings no longer include the marked-content warning switch. The existing switch remains in Settings → Player. Settings → General adds a system color picker and reset for the profile accent. The preference applies within profiles, including Markdown links, while live indicators and brand artwork keep their semantic colors.

The simulator fixture checks both tab swipe directions, Markdown link tap and long-press actions, the General color picker, and the quick-settings contents. Apple validation and an iPhone visual check are pending.

## Eleventh Apple failure: Markdown link compilation

[GitHub run 44888747898](https://github.com/BananaOnGitHub/Streamside/actions/runs/44888747898), source `66b4fd5`, stopped before linking. Xcode rejected a redundant discarded result from the Void-returning `OpenURLAction` and the inline-code intent name in the TextKit view. The view now calls the URL action directly and uses [Foundation’s Swift inline-code intent](https://developer.apple.com/documentation/foundation/inlinepresentationintent). [Failure evidence](SWIFTUI_CHANNEL_PROFILE_BUILD_FAILURE_11.json) records the source, compiler phase and artifact hashes. The new interactions still require Apple simulator validation.

## Verified profile accent and link preview package

Source `6116a79d81bc908daf5add49db791118958b0141` passed both jobs in [GitHub run 44917030520](https://github.com/BananaOnGitHub/Streamside/actions/runs/44917030520). All six coordinate cases passed. The simulator verified both tab swipe directions, Markdown and image link actions, the preview menu handoff, General color picker presence and the updated player quick settings. All 78 local component checks passed.

The verified Xcode 26.6 component archive has SHA-256 `46e16c084534e38950b50de9b99c87c155323f49546493e7116310e84b70198c`. Local assembly from the pinned Twitch 32.0 donor produced `artifacts/native-frontend/channel-profile-6116a79/StreamsideNativeProof-Twitch32-native.ipa`, 197,313,598 bytes, SHA-256 `42387b4b4243a80ec96c18f5d560a18adc6ad9f091db878ece4dd2affe3dfd50`. Live webpage rendering, the accent's appearance and saved color behavior need an iPhone check.

## Artwork accents and interactive tab paging

Device feedback confirmed the profile swipes, link interactions and picker from the previous package. This revision replaces the picker with a bounded dominant-color sample of the decoded banner, falling back to the avatar and then to the system foreground. The sampler uses the cached image, groups opaque pixels by quantized color and adjusts brightness for the light or dark surface. The subscription star keeps its centered hit area and subscription action with a glyph-only presentation.

Home and About now follow the horizontal pan within the profile. Short pulls return to the selected page; committed swipes update the same selection used by the segmented control. Only the active page sets the vertical scroll extent and participates in accessibility. The navigation edge gesture and independently scrolling content retain priority. Both About link types now use the same sized WebKit preview content and the same Open link action. The originating text and image retain their platform context-menu anchors.

The simulator checks a short cancelled swipe, full swipes in both directions, edge navigation, both link menus and the star's alignment. App appearance, live webpage rendering and artwork color matching still need an iPhone check.

## Twelfth Apple failure: profile gesture override

[GitHub run 44955554283](https://github.com/BananaOnGitHub/Streamside/actions/runs/44955554283), source `6268c7f`, stopped during Swift compilation. The tab pan's gesture start method overrides a UIKit view method and required an explicit `override`. The method now overrides UIKit's implementation, applies the directional filter only to the profile pan and defers to the inherited method for other gestures. The run did not reach linking or simulator tests. [Failure evidence](SWIFTUI_CHANNEL_PROFILE_BUILD_FAILURE_12.json)

## Verified artwork accent and paging package

Source `d73e602ee1d7f3ceeb626f42df13cf2044cfc003` passed both jobs in [GitHub run 44974608274](https://github.com/BananaOnGitHub/Streamside/actions/runs/44974608274). All six coordinate cases passed. Profile checks covered a short swipe that returned to Home, committed swipes in both directions, the navigation edge swipe, the subscription star’s alignment and both link menus. All 78 local component checks passed.

The verified Xcode 26.6 component archive has SHA-256 `9dfbc00e45d4a2cbaeaf7d1ea8bc4bc77521545b9b77a371aeaeb0245132d4c5`. Local assembly from the pinned Twitch 32.0 donor produced `artifacts/native-frontend/channel-profile-d73e602/StreamsideNativeProof-Twitch32-native.ipa`, 197,322,374 bytes, SHA-256 `bde5c849377caa30bffa5e7a9ff5d5ea247702f796d5cf6867f7e58c26039c87`. Artwork color matching, how the pages track the finger, and the look of live webpage previews still need iPhone review.

## Profile playback after paging and preview commits

An iPhone report described a stall when swiping from Home to About. The profile started native retirement as soon as tab selection changed, and the first drag could mount the entire About pane. The native stop path already retires final disposal off the main queue, but its pause and view detachment still run on the main thread. Tab selection now updates independently of the media operation. Animation completion schedules the tab-specific start or stop, and a new gesture invalidates an older completion. Leaving the profile, losing the account and backgrounding still stop immediately. About text is present for the first drag and artwork starts after the first settled visit.

Settings → Profile offers Banner, Profile picture and Manual. Banner falls back to the avatar and then the system foreground. Profile picture falls back to the system foreground. Manual uses one saved color for all channels and reuses the previous manual color preference when available.

Image and Markdown links share the UIKit preview commit action. A tap on the WebKit preview and the Open link menu row both open the original link. Inline text still uses TextKit to identify links and dispatch short taps. Simulator fixtures exercise the preview's actual tap location for both link types. Responsiveness with the live native player and live webpage rendering require iPhone validation.

## Verified profile playback and preview commit package

Source `9b8e5ebfc414f40876b8a6df66b63ccf2fed7ef1` passed both jobs in [GitHub run 45002682355](https://github.com/BananaOnGitHub/Streamside/actions/runs/45002682355). All six coordinate cases passed, including the tab swipes and tapping the WebKit preview to open both image and Markdown links. All 78 local component checks passed.

The verified Xcode 26.6 component archive has SHA-256 `eebd8ac2a2f6592d0e3bb1ca4e4dce29c0e1dfe542338bbdf67f8ebabdfe256d`. Local assembly from the pinned Twitch 32.0 donor produced `artifacts/native-frontend/channel-profile-9b8e5eb/StreamsideNativeProof-Twitch32-native.ipa`, 197,334,876 bytes, SHA-256 `1918bcc208b6e45da3eac5b490530b8757f92b974327ac6c8706664f612a5f56`. The fixture uses a synthetic profile video surface, so the live playback swipe and the three accent modes still need an iPhone check.

## Social rail and Markdown gesture isolation

Device feedback confirmed the live-player tab transition and artwork accent modes. A horizontal drag on the social links could still move the page underneath. The tab recognizer previously relied on finding a horizontally scrollable UIKit ancestor of the touched view. The social rail now supplies its own visible bounds for touch admission so the profile pan yields throughout the rail.

Markdown link holds could produce two haptics and only intermittently show a preview. Previously the UITextView had its built-in text interactions and the added panel context-menu interaction on the same hit view. A transparent sibling now admits only touches inside the intended link's TextKit line rectangles. It owns short taps and the shared context menu, while the text view retains text rendering, selection outside links and accessible link activation. The context preview still opens the original URL on tap.

The profile coordinate fixture scrolls the rail through its final link and requires the Home page to stay in place. It also opens the same Markdown preview from two distinct positions and checks both committed destinations. Apple validation and an iPhone haptic check are pending.

Source `3adb20dd1ecf59ace6262a94522db45d0ecbaf71` passed both jobs in [GitHub run 45107061678](https://github.com/BananaOnGitHub/Streamside/actions/runs/45107061678), including the profile gesture checks in the iOS Simulator. Local component verification also passed. The Xcode 26.6 component archive has SHA-256 `de7f733bd888036c8a40c33500500619c15f6b8aadbb6fad052fcdc185a5d2e5`.

Local assembly from the pinned Twitch 32.0 donor produced `artifacts/native-frontend/channel-profile-3adb20d/StreamsideNativeProof-Twitch32-native.ipa`, 197,340,563 bytes, SHA-256 `e94732c515936a73d327a16ac372e814418a56f620cada4337240d2b122841d5`. Archive integrity passed. The swipe and link preview behavior still need confirmation on an iPhone, including haptics and live webpage loading.

## Profile link and artwork previews

Device testing confirmed that swiping the social rail leaves the rest of the profile still. Markdown link holds could open the right preview without a visible lift. The single touch owner now draws a pressed highlight around the hit link's TextKit line rectangles. UIKit animates those rectangles from the actual text view when opening and closing the menu. Social buttons reuse the panel WebKit menu and its tap-to-open behavior, with the existing rail swipe exclusion.

Banner and profile picture holds use SwiftUI context previews with the entire image fitted into the card. Open image presents the local file in system Quick Look for zoom and sharing. A publicly documented CDN sample served 300×300 and 600×600 avatars, and returned 404 for 1200×1200 and an unsized URL. The image loader tries 600×600 only for matching Twitch avatar URLs and falls back to the supplied URL. Banners use the supplied URL at its delivered resolution. The existing credential-free image session and host policy apply. Quick Look receives the original response bytes, and the temporary file is released with the owning artwork view.

A separate simulator gate covers social link tap and preview commit, both artwork menu sources, native viewer presentation and the Share control. It leaves the existing profile and playback gates in place. The CDN resolution with real profile responses and the hold animation still need physical-device validation.

### Quick Look toolbar in the profile viewer

Source `e8bbd47123d40ee426032ecd3f3a85b14b0d970f` compiled and passed the six existing coordinate gates in [GitHub run 45118125553](https://github.com/BananaOnGitHub/Streamside/actions/runs/45118125553). The seventh gate passed the social link's tap and WebKit preview commit. Opening the banner displayed the complete 32×48 fixture in Quick Look, visible in the screenshot and as Image canvas in the accessibility tree. The screenshot had no toolbar, and the test failed waiting for a dismissal control. It did not reach the avatar check or component verification. The failure log and screenshot are stored beside the local build ticket. The screenshot SHA-256 is `9b6878e2832f4a5fad436cfebb86c3be28a63c2bd94e520a17ae15dba8a40620`.

The full-screen image viewer now hosts the system Quick Look controller beneath its own visible toolbar. Done dismisses the image and Share uses the native share sheet with the original image file. The simulator gate requires Quick Look's rendered image and both hittable controls on each artwork path, then verifies dismissal. The context menus and image-fetching policy are unchanged.

Source `009e16ff8951e95ac2539cc20237d7ed4760188e` passed the Apple and ABI jobs in [GitHub run 45126479528](https://github.com/BananaOnGitHub/Streamside/actions/runs/45126479528). All seven coordinate gates passed, including the social link preview commit and banner and avatar rendering, visible Share and Done controls, and dismissal. All 78 local component checks passed. The verified Xcode 26.6 component archive has SHA-256 `040731fc064597cdd1491206ab174448c0c126ad37f5c1f80c63cc62745f337b`.

Local assembly from the pinned Twitch 32.0 donor produced `artifacts/native-frontend/channel-profile-009e16f/StreamsideNativeProof-Twitch32-native.ipa`, 197,392,536 bytes, SHA-256 `ee7f0e81ef40e43a64f93f43441878696a3c63192a8c1087293ffab592c1e742`. Archive integrity passed. Hold feedback, live webpage and artwork loading, and image sharing with a real profile remain physical-device checks.

### Preserve the Markdown source and profile during previews

On device, a link hold in a multi-line Markdown block showed the selected rectangle while clipping the surrounding lines. The prior targeted preview used the live text view with a path restricted to the link. The context menu now lifts a separately rendered copy of the selected line rectangles. The original text view stays in place, and link hit testing and the rounded press highlight continue to use the same TextKit geometry.

Device testing also found that tapping Done could affect the profile back control behind the artwork viewer. The profile now owns a single artwork cover and keeps the back action inactive from presentation through the end of dismissal. The simulator fixture still checks real Quick Look image rendering and Share, then verifies that Done leaves the profile open for both artwork sources and that a separate back tap closes it. The live Markdown lift and iPhone dismissal behavior still need confirmation on device.

Source `69dedc8426128fb9ac97827250df66ae5e08a683` passed the Apple and ABI jobs in [GitHub run 45138480837](https://github.com/BananaOnGitHub/Streamside/actions/runs/45138480837). All seven simulator coordinate tests passed, including the Markdown preview commits and the check that Done returns to the same profile from both image viewers. All 78 local component checks passed. The Xcode 26.6 component archive has SHA-256 `5666c786fe4180e27e346d2621f8d63ae51236d999c99a41c170a623a846b2fe`.

Local assembly from the pinned Twitch 32.0 donor produced `artifacts/native-frontend/channel-profile-69dedc8/StreamsideNativeProof-Twitch32-native.ipa`, 197,393,660 bytes, SHA-256 `3a374cb688199214d09a63a72856c2962e76a786f47657f8b3768c7e24d6ff41`. Archive integrity passed. Physical-device validation remains open for surrounding text visibility during the lift and tapping Done over the profile back button.

Device testing confirmed surrounding Markdown stays visible and Done returns to the profile with source `69dedc8`. The covered back button's Liquid Glass still visibly responded to a Done tap. The profile now removes the glass view itself until the artwork cover has finished dismissing. The simulator checks that the back control is absent while the artwork viewer is up, then checks that it can be tapped after dismissal. The glass response still needs an iPhone check.
