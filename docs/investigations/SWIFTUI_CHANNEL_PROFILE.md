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
