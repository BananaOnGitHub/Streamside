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
