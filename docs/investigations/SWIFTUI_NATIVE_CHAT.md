# Native read-only stream chat

The portrait theatre shows public live chat beneath the player. Messages appear as they arrive and the transcript scrolls to the newest row without animation. Twitch's RGB tag colors the author label. A display name that differs from the login beyond capitalization appears as Display Name (login). An unset name or color uses the login or the system foreground. The panel renders plain text and has no composer.

## Transport and lifecycle

The verified Twitch 32.0 donor (SHA-256 `076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`) contains `KMPMobileChat` with exported WebSocket setup and channel-join selectors. Static names establish the presence of native chat infrastructure. They leave the factory dependencies, account ownership and callback lifetime unverified. The [older chat investigation](../archive/investigations/RN_CHAT_BOUNDARY_PROBE.md) documents a different donor's IRC ingress and RN presentation.

The new listener uses Foundation's WebSocket and Twitch's public guest IRC login. The standard tagged message fields are documented in [Twitch IRC](https://dev.twitch.tv/docs/chat/irc/). Guest access was verified separately and can change at the service. The socket uses TLS and an ephemeral session without account credentials or cookies. The client negotiates tags, joins the selected room and replies to keepalives. It has no chat-send command. The last 200 messages live only in memory and Twitch's delete and clear events remove affected rows. Diagnostics record no transcript or user names.

The theatre opens chat after native stream access and content consent, while the same account owns the active theatre. Closing the theatre, moving to another screen, backgrounding the app or losing the account ends the connection. A new eligible foreground session reconnects. The local test stream and the thumbnail and profile previews have no chat connection.

## Validation

An Ubuntu probe against Twitch returned a guest welcome, tag capability acknowledgement, seven public room-state responses, and two tagged messages with Twitch colors. The probe retained counts only. Apple model fixtures cover tagged frames, Unicode names, color parsing, wrong rooms, deletes, duplicate IDs, and the bounded transcript. Device testing still needs to cover live message rendering, scrolling, and rejoining after backgrounding in the signed theatre.

### Initial Swift compiler failure

[GitHub run 45328037839](https://github.com/BananaOnGitHub/Streamside/actions/runs/45328037839) for `5aedc14d9e823bc29a60a172785ad36861c49d08` failed in the iPhone SwiftUI build. The compiler rejected direct comparisons of a parsed optional `Substring` with the expected room's `String`. The parser now compares two `Substring` values and treats a missing destination as an empty token. The model fixtures check a missing room and both IRC keepalive forms. The failed job log is retained beside the local build ticket. Linking, model execution and simulator validation were not reached.

### Verified chat test package

Source `9f2505e1b284054894cf0b18d20137fdc8a620d2` passed the Apple and ABI jobs in [GitHub run 45329795140](https://github.com/BananaOnGitHub/Streamside/actions/runs/45329795140). The Swift chat parser fixtures, seven existing simulator coordinate tests and all 78 local component checks passed. The simulator profile gate checked that the back button was absent while both artwork viewers were open and that Done returned to the same profile. The verified Xcode 26.6 component archive has SHA-256 `6f5b24c9f771bc1a1a7cd8e601a1c016a4267ef7a7dc1072ba1632014300e9b7`.

Local assembly from the pinned Twitch 32.0 donor produced `artifacts/native-frontend/native-chat-9f2505e/StreamsideNativeProof-Twitch32-native.ipa`, 197,437,463 bytes, SHA-256 `a5d3f293aa21e9e8b9ddff51da8dc9c6a634fae6639141826841f583b4bc9b44`. Archive integrity passed. Live theatre chat, scroll behavior, and the Liquid Glass response still need iPhone confirmation.

## Reading older messages and catching up

Device testing confirmed live chat delivery. With the first transcript, each arrival scrolled the reader to the newest row. User-driven scrolling now holds the visible transcript and keeps processing live messages and moderation in memory. The animated catch-up pill appears on the first unread arrival and counts the retained unread rows. Tapping it or scrolling back to the bottom resumes following. The divider before the first retained unread row stays visible in the transcript. A long pause can exceed the existing 200-message live history. Older arrivals then age out while the reading viewport remains fixed.

The portrait stream info pane now receives the same linear progress transaction as the controls, including their deferred reveal after being remounted. Both use the cubic fly curve or the smooth fade curve with the configured duration. The panel clips upward into the bottom of the video and gives the space to chat. Reduce Motion uses the fade curve. Content consent, local tests, and playback errors keep their info accessible.

The Apple model fixtures cover paused retention, duplicate and deleted unread messages, capacity and marker placement. A separate simulator fixture checks the reading position, count and marker, returning to live chat, and the viewport growing and shrinking with the control animation. The live-device animation timing, glass and chat scrolling remain device checks.

### Align live chat to the visible bottom edge

[GitHub run 45359907026](https://github.com/BananaOnGitHub/Streamside/actions/runs/45359907026) for `a145ee1520775d295a14cbe1b888e3c2ca604a4f` passed compilation, the Swift chat model checks and the seven existing simulator cases. The new catch-up simulator case failed at its first live-follow assertion. The screenshot showed rows through 57 of 60, and the accessibility tree placed row 59 outside the visible content area while the scroll bar reported 92%. The job log and screenshot remain beside the local build ticket. The screenshot SHA-256 is `ae86143e2b76e739fdc1d510fe8b840eafed9fb733c2efa8a54a6f3154c440c8`.

On iOS 18 and later, live follow and catch-up now target SwiftUI's scroll bottom edge instead of aligning the last row while the viewport resizes. The scroll phase uses bottom content insets when deciding whether a manual scroll has returned to live. iOS 16 and 17 use a tail anchor. The simulator gate still requires the latest row to be physically hittable at launch, after catch-up and after more live messages arrive.

[GitHub run 45365619369](https://github.com/BananaOnGitHub/Streamside/actions/runs/45365619369) for `8900bba584116e80631de5edcbb31c0011278e0e` compiled and passed the seven existing coordinate gates. The edge anchor alone still left the latest row below the visible area after the stream info panel expanded. The failure archive is retained with the build ticket. The screenshot SHA-256 is `1ae8100c9722439f24f7ec3bf22a8f52b1317c23d9c33d64f2b097ae88b400ff`.

The transcript now measures all retained rows and computes its live scroll offset from the observed content height, viewport height and insets. Viewport changes update the live position without animating the scroll or moving a paused reader. The catch-up case runs first so a regression is reported before the longer independent tests. All eight tests and the existing build and component checks remain mandatory.

### Native worker deadline on the eight-case simulator run

[GitHub run 45464271393](https://github.com/BananaOnGitHub/Streamside/actions/runs/45464271393) for `b6b6109c9b993099d303345e8c365c65b2eb668e` passed the complete chat catch-up case, including unread counts, the marker, live follow and the moving viewport. Six more coordinate cases passed. The 2,250-second native worker deadline then stopped the final profile preview case as it was tapping Done in the avatar viewer. No assertion failed in the captured output. Baseline validation and artifact admission were not reached. The job log and failure archive remain beside the local build ticket.

The native worker now allows 45 minutes. The shared component stage derives its deadline from both worker limits plus two minutes, which leaves 57 minutes for the component stage. The GitHub job allows 65 minutes so the remaining stages and artifact uploads have room to finish. The individual simulator deadlines and all mandatory assertions are unchanged. Codemagic's job limit and dispatcher quota policy are unchanged.

### Verified chat catch-up package

Source `9bbbe826656fa194ac31c42bb31b8e47102b9cd1` passed the Apple and ABI jobs in [GitHub run 45480946438](https://github.com/BananaOnGitHub/Streamside/actions/runs/45480946438). The Swift chat model tests, all eight simulator coordinate cases and all 78 local component checks passed. The catch-up case verified that messages do not move the paused reader, the pill shows the unread count, the divider marks the new messages, new arrivals keep following after catch-up, and the info panel changes the chat viewport. The verified Xcode 26.6 component archive has SHA-256 `6221e1f9811c8d7e5896dddf925c673943aaeff47b6ceca5ea60703c9c32111a`.

Local assembly from the pinned Twitch 32.0 donor produced `artifacts/native-frontend/chat-catch-up-9bbbe82/StreamsideNativeProof-Twitch32-native.ipa`, 197,484,435 bytes, SHA-256 `9c6c748e3e5c6f58d5d54d2256219ec7fcae5f038678255a13aae2af50942053`. Archive integrity passed. Live chat behavior and the visual timing of the pill and panel remain iPhone checks.

## Unread pill hit target and sender avatars

The unread pill now uses its full capsule as the interaction shape, with a minimum height of 44 points. The existing simulator catch-up case taps near the left edge of the capsule and checks that live follow and the unread divider still work.

Chat takes the sender ID from Twitch IRC's `user-id` tag. Twitch 32.0 exports `TKGraphQL.fetchSmallProfileImageURL(forUserWithID:)` at TwitchKit address `0x2c78c4`. Inspection found the client in `x20` and the `UInt32` ID read from `w0`, with the indirect result pointer saved from `x8` and forwarded to the promise constructor. Packaging checks the export and instruction prefix on the pinned donor, and the host ABI fixture checks those registers at the adapter call. The result uses the existing native Promise bridge with the system Swift metadata for `Optional<URL>`. The request owner cancels on session replacement and returns only the image URL.

The 18-point circle reserves room for every sender and uses a placeholder while loading or when an image is unavailable. iOS 18 and later request images for visible rows. iOS 16 and 17 prioritize the newest rows while following live chat. The chat queue retains at most 24 distinct senders, runs one lookup and download at a time, spaces attempts by at least 650 ms, and suppresses failed lookups for 90 seconds while their cache entries remain. The image cache decodes chat avatars to at most 54 pixels per side. Chat retains up to 96 sender entries per theatre, cancels pending work when chat becomes inactive, and uses the existing diskless Twitch image session. Reports omit chat sender IDs and artwork URLs.

All 127 host tests passed, including exact donor admission and the new adapter calling-convention test. The Apple fixtures cover IRC user IDs, request authorization and account replacement, and the edge tap. Live avatar loading, visual fit and hit behavior still require an iPhone check.

[GitHub run 45516895210](https://github.com/BananaOnGitHub/Streamside/actions/runs/45516895210) compiled the native component and stopped before simulator validation when the Objective-C account-lifetime fixture exited with SIGSEGV. The fixture released its fake default auth object after the account-loss test but left the shared pointer set. The next test, the signed-out avatar lookup, tried to retain that stale pointer. The fixture now clears the fake default auth before polling the account-loss request and checks that a signed-out avatar request submits no network work and returns no data. The production bridge and all existing gates are unchanged.

### Verified avatar and pill test package

Source `8912dadb5c2d0307587b15d17253add0f38d3f50` passed the Apple and ABI jobs in [GitHub run 45519019091](https://github.com/BananaOnGitHub/Streamside/actions/runs/45519019091). The account fixture and all eight simulator coordinate cases passed, including the tap near the edge of the glass unread pill. Local retrieval passed all 79 component checks. The verified Xcode 26.6 component archive has SHA-256 `774ff8b1ee7d8df2d9ce13fb31f087c4cc3da60e758082f998d156b97f6e50d5`.

Local assembly from the pinned Twitch 32.0 donor produced `artifacts/native-frontend/chat-avatars-8912dad/StreamsideNativeProof-Twitch32-native.ipa`, 197,512,331 bytes, SHA-256 `2c80bf3df099d5d64753b0aa47ea860faa6538ba354f4522f284416c09d779d2`. Archive integrity passed. The live native avatar response and image loading, including on chat scrollback, still need physical-device testing.

## Native chat composer

The iPhone theatre keeps a single-line composer below the transcript, above the keyboard when focused. As the composer gains or clears text, its right-hand Send button slides in or out. Reduce Motion uses opacity. iOS 26 uses Liquid Glass, older versions use system material, and Reduce Transparency uses a solid surface. Sending is explicit from the button or the keyboard. The composer allows one submission at a time and clears the submitted draft after confirmation. An edited draft is preserved. Rejected and unconfirmed sends keep the draft and show feedback. The app does not automatically resubmit. The guest reader shows Twitch's own broadcast of the message when the room receives it.

Twitch 32.0 exports `SendChatMessageInput` and `SendChatMessageMutation` in TwitchGraphQLAPI. The input at `0x76d070` takes the channel ID, body, nullable nonce and nullable reply ID as eight direct words in `x0` through `x7`. The adapter checks the nullable value width at runtime and uses Apollo's native nil initializer for the two optional arguments. The mutation allocator at `0x22f1d0` consumes the input in `x0` and the class metadata in `x20`. The existing authenticated Apollo path performs the write to the current theatre's numeric channel ID. Native session changes cancel pending observation. Only the confirmation flag crosses the bridge. Chat drafts, message IDs and drop details stay out of diagnostics.

The host ABI fixture checks the eight input words and exact donor admission. Apple fixtures cover write authorization, invalid channels, rejected results and explicit confirmation. The simulator catch-up case also types and sends a fixture message, then checks the button leaves the hierarchy. Live send and its appearance with the keyboard still require a physical-device check.
