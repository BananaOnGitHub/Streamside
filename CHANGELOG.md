# Changelog

## 2.3.0-dev.3 (development; image/menu diagnosis)

- The dev.2 report confirmed provider fetches, incoming IRC rewrites, and
  synthetic image redirects, while the previous chat-menu hooks saw no sheet.
- Added aggregate image response status/MIME counters and a targeted chat
  settings button and presentation probe. No chat text, room IDs, or image URLs
  are recorded.

## 2.3.0-dev.2 (development; device retest pending)

- Added privacy-safe emote and chat-menu counters to the diagnostic report.
- Hooked inherited WebSocket receive implementations and recognized sheets
  presented by Twitch's ChatSettingsController without an exact title match.
- Kept the emote switch off by default and the published 2.2.1 assets unchanged.

## 2.3.0-dev.1 (development; device validation pending)

- Added optional 7TV, BTTV, and FFZ global and channel emotes to incoming chat.
- Added a relaunch-gated emote switch and Clear Emote Cache to Ad Block, plus
  Reload Emotes in the stream Chat Settings action sheet.
- Bounded per-room maps and image-ID history, with idle expiry and API retry
  backoff. No separate emote image files are stored by the module.
- Built the same source for the IPA framework and rootful/rootless jailbreak
  packages. The emote hooks and menu placement still need on-device testing.

## 2.2.1 source-backed replacement (IPA and jailbreak prerelease)

- Reconstructed the R5 diagnostics in checked-in source. Both package formats
  now use the same implementation of temporary channel and resource labels,
  route registration history, and retired-route reasons for unmapped variants.
- Logging remains off by default. The older 2.2.0 diagnostic log containing
  request paths is removed on first initialization of this build.
- Retains the device-confirmed main Settings button scope fix. These new
  replacement binaries have not yet been tested on a device.

## 2.2.1 original IPA (superseded)

- Added opt-in diagnostics with temporary channel and playlist labels that
  reset when Twitch restarts, plus route history for investigating playback.
- Clarified in the app that diagnostic logging starts off and explained the
  lifetime of those labels.
- Limited the Ad Block button to the main Settings screen; fixed its absence
  in the R6 candidate and its appearance on Chat Identity in the R5 build.
- Published the device-confirmed R7 behavior with a 2.2.1 build label.
- The separately versioned 2.2.1-jb source build has the Settings entry fix,
  but lacks the IPA's newer R5 privacy and route diagnostics.

## 2.2.1-jb original packages (superseded)

- Built the standalone rootful and rootless packages from the checked-in
  source with the main Settings button fix.
- Kept the original 2.2.0 diagnostics implementation; R5's newer privacy
  labels and route history are not present in these packages.

## 2.2.0

- Added an Ad Block entry to Twitch's profile settings screen.
- Added persistent, opt-in diagnostic logging with a 512 KiB cap.
- Added an in-app diagnostic report with session counters, viewing, copying,
  and clearing controls.
- Sanitized all logged URLs and excluded query strings, fragments, headers,
  access tokens, and manifest contents.
- Logged HLS interception, manifest classification, VAFT candidate selection,
  access-token failures, clean swaps, unmapped variants, and suppressed
  segments.
- Restored the proven `Tweach.framework/Tweach` physical path for sideload
  compatibility while retaining `TwitchAdBlock.dylib` for jailbreak packages.
- Normalized the sideload framework's Mach-O segments to 16 KiB boundaries so
  ESign and LiveContainer/ZSign can replace its signature successfully.
- Updated the build, verification, patching, tests, and release tooling for the
  framework-based sideload layout.

## 2.1.0

- Renamed the native library and load command to `TwitchAdBlock.dylib`.
- Added standalone rootful and rootless jailbreak DEB packages scoped to the
  Twitch bundle.
- Added DEBs to automated builds, release archives, and checksums.
- The clean dylib identity remains the jailbreak packaging path; sideload
  builds subsequently returned to the compatibility path in 2.2.0.

## 2.0.3

- Replaced the single global stream slot with per-channel VAFT contexts.
- Mapped each media-playlist URL to the master playlist that produced it.
- Scoped clean variants and alternate-player caches to their owning stream.
- Fixed profile previews that could clone the active PiP stream or turn black.
- Added a local IPA patcher, Mach-O verification, tests, and reproducible
  GitHub Actions builds.
