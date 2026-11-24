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
