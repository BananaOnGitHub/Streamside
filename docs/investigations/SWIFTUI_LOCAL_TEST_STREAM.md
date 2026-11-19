# Development-only local test stream

Implemented on `feat/native-frontend`, based on `63f927b40c239dd4c1b46fd9ed701f1b40a6f5f9`. This record accompanies the implementation commit. Apple compilation, simulator execution, packaging and physical-device results remain pending at submission.

## Use

Open Settings → Diagnostics → Development testing → Local test stream. Enable Show local test stream, edit the metadata and save. The authenticated followed list shows a separate Local test stream section above the real follows. Tap its thumbnail for the player or hold for the preview. Remove it through the same editor, or turn off its visibility.

The editor supports channel name/username, title, category, comma-separated tags, live/offline, verified badge, viewer count, marked-content labels and simulated Ready/Loading/Buffering status. Its draft persists in app-local preferences across refresh and relaunch. Local artwork is generated in code. The entry has an explicit local identity and display-name prefix; it cannot be confused with a successful Twitch follow or playback request.

For warning tests, enable Show marked stream warnings in Player settings. Mark the entry and enter any content labels. The production warning, Continue/Close, remembered consent and thumbnail-choice preferences apply. Remembered Continue changes the real preferences, so re-enable warnings between repeated tests. An already-enabled marked-thumbnail preference skips the redundant thumbnail question. Simulated Buffering plus a long title/tags can exercise the preview status footer without an external stream.

## Isolation and ownership

[LocalTestStream](../../native/swift/LocalTestStream.swift) holds bounded, normalized local data. [The editor](../../native/swift/LocalTestStreamViews.swift) is available only when compiled with `SSN_DEVELOPMENT`, in native mode with the existing development launch selector enabled. The original-startup control is compiled without this flag and cannot save or materialize the entry. The one-shot original launch does not expose the tool.

NativeServices projects the entry separately from `state.channels`; native account/follow results and diagnostic counts remain genuine. Native snapshots cannot set the typed local origin. Synthetic metadata is not sent to the native diagnostic exporter.

[TheatrePlayback](../../native/swift/TheatrePlayback.swift) never instantiates `SSNPlayback` for a typed local entry, including in disabled builds and when its username matches a real channel. Consent uses local labels. After admission, preview/theatre show a labeled local placeholder and selected status, without IVS, authorization/token requests or an audio session. Thumbnail/avatar URLs and native channel ID stay absent. Local theatre polling is disabled. Normal account/navigation validity, cancellation and preview-to-theatre ownership still apply. No donor hooks or runtime-probe changes were added.

This fixture validates presentation and consent behavior. It does not establish real restricted-stream authorization, decoded video, ad suppression or zero-runtime device acceptance. Existing real-video and playback gates remain mandatory.

## Validation

[Host evidence](SWIFTUI_LOCAL_TEST_STREAM_HOST_VALIDATION.json): 95 Ubuntu tests passed. These cover build orchestration, component receipt enforcement and the existing Linux-compatible native checks; they do not execute SwiftUI or the new Swift fixtures.

The Apple build now requires the production editor create/remove interaction within the existing marked-content coordinate test. Model fixtures test metadata normalization, persistence/removal, typed origin and disabled-build isolation. Admission fixtures verify that every simulated status passes through consent without creating the native playback facade, remains muted through handoff and cannot restart after cancellation. Existing five coordinate tests, real decoded-video clipping, native playback/account/audio lifecycle, ABI and component verification gates remain enabled. Compiler receipts record the development flag and component verification rejects missing or wrong-mode flags.

Reproducible submission: commit/push this branch, then run `make native-ci` from Ubuntu. It selects Codemagic when quota permits, otherwise GitHub Actions. No donor IPA or signing material is transferred. After a successful Apple build, `make native-ci-fetch` verifies the components; use the existing local donor packaging path and Feather for installation. Build submission is separate from successful compilation and device validation.

Device checks: create/edit/remove; refresh/background/relaunch persistence; tap and hold entry; Close without preference changes; Continue with/without remembering; marked thumbnails already enabled; long title/tags with Buffering; preview Watch handoff; account loss and no other-audio interruption. Export runtime diagnostics as usual, but local test metadata is deliberately absent and these results must not be reported as real Twitch playback.

## Successful Apple build and local package

Source `714c61c0d75e7ae6cc61132d5993cfe45784d343` passed [Codemagic build 6afe9b58d133a39c4a13054f](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afe9b58d133a39c4a13054f). All six validation stages and all five coordinate tests passed, including production editor create/remove and retained real decoded-video/clipping checks. Model/admission tests passed for native and disabled control components. Development tools were enabled only in the native component. Xcode 26.6 (17F113), Swift 6.3.3, SDK 26.5 and the arm64 iOS 16.4 target match the pinned toolchain.

Verified retrieval and 67 post-download tests passed. Exact Twitch 32.0 donor admission and local IPA assembly passed with 67 ABI boundaries, 25 runtime probes, retained donor entries verified and the original HBC unchanged. Only a native IPA was assembled; donor and signing inputs stayed local. [Validation identities and receipts](SWIFTUI_LOCAL_TEST_STREAM_VALIDATION.json) preserve source, toolchain, archive, framework and package hashes.

Candidate: `artifacts/native-frontend/local-test-stream-714c61c/StreamsideNativeProof-Twitch32-native.ipa` (relative to the Streamside workspace), requiring local Feather signing. The adjacent `TESTING.txt` describes creation, warning/thumbnail cases, preview/player, persistence and removal. Device validation remains pending; this build does not establish real marked-stream playback or device runtime absence.
