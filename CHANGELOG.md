# Changelog

Meaningful changes by public release. Development trials, failed approaches, and build-by-build evidence are in [History](docs/HISTORY.md).

## 3.0.0 - Unreleased

### Added

- Third-party emotes in Twitch 31.5's React Native chat, including incoming and ordinary sent messages, proportional widths, and native animated-image rendering.
- Unified Twitch/provider suggestions with Automatic, Colon, and Off modes.
- Composer image previews, supported GIF animation, and whole-emote deletion.
- Five-row horizontal provider browsing with provider/scope filters, recents, thumbnail names, and provider details.
- Reload Emotes in RN Chat Settings with Twitch's themed touch highlight.

### Improved

- Shared provider-image transport, coalescing, and cache-first delivery.
- Library virtualization and bounded recovery when transfer admission is full.
- Legacy UIKit Recent startup, footer selection, and insertion after keyboard reparenting.
- Handling of provisional iOS keyboard input before emote conversion.

### Changed

- Renamed the project to Streamside and the installed sideload app to Twitch Streamside.
- Replaced the historical donor loader identity with Streamside's own framework/dylib identities.
- Made binary fingerprints, Mach-O layout checks, and packaged-byte verification mandatory throughout package preparation.

Third-party emotes remain opt-in. Jailbreak packages and broader compatibility retain the validation limits documented in [Compatibility](docs/COMPATIBILITY.md).

## 2.3.0

- Added optional 7TV, BTTV, and FFZ global/channel emotes to Twitch 30.4.2 chat.
- Added incoming and own-message rendering, proportional image sizing, animated emotes, and provider detail sheets.
- Added Reload Emotes, Clear Emote Cache, and privacy-safe emote diagnostics.
- Published a separate `2.3.0-jb` prerelease with rootful/rootless packages.

The final IPA packaging later exposed a loader-layout regression despite working development binaries. Its investigation and the source-built correction are recorded in [History](docs/HISTORY.md#the-unpublished-231-transition).

## 2.2.1

- Restricted the settings entry to the main Profile → Settings page.
- Added temporary channel/resource labels and stream-route history to diagnostics.
- Replaced the initial binary-staged assets with source-backed builds sharing the diagnostics implementation across IPA and jailbreak packages.
- Removed the older path-bearing diagnostic log on initialization.

The original candidate and replacement are distinct artifacts. See [release provenance](docs/archive/releases/RELEASE_2.2.1.md). Separate `2.2.1-jb` packages were published as a prerelease and remain untested on a jailbroken device.

## 2.2.0

- Added an in-app settings page, opt-in diagnostic logging, session counters, report copying, and log clearing.
- Bounded logs to 512 KiB and excluded tokens, headers, GraphQL bodies, and manifest contents.
- Restored the historical framework sideload path and normalized its segments to 16 KiB boundaries.
- Retained standalone rootful/rootless packages in the separate `2.2.0-jb` prerelease.

## 2.1.0 - Jailbreak prerelease

- Introduced a standalone TwitchAdBlock dylib identity and rootful/rootless DEBs.
- Added reproducible build, verification, injection, and packaging tools.
- Adopted Apache-2.0 for the native port and added CI artifact builds without automatic publication.

## 2.0.3

- Replaced global playback state with independent per-channel stream contexts.
- Associated rendition URLs with their owning master playlist.
- Fixed PiP/profile-preview stream substitution and black previews caused by shared state.
- Added expiry and cleanup for stream/rendition mappings.

## 2.0.2

- Restored the complete `Assets.car` and fixed signed-in scene-creation crashes.
- Kept the native dylib and VAFT behavior unchanged from 2.0.1.

## 2.0.1

- Normalized playback-token requests at `NSURLSession` task creation.
- Preserved unrelated authenticated startup/account requests.
- Corrected transient playback-header capture and reuse.

## 2.0.0

- Replaced `video-swap-new` with a native VAFT solution-24 adaptation.
- Added VAFT alternate-player selection, playlist handling, and ad-segment fallback.

## 1.0.1

- Expanded replaceable signature space from 16 KiB to 64 KiB.
- Added a reproducible signature-reservation step without changing ad-blocking behavior.

## 1.0.0

- Introduced native `video-swap-new` solution-23 playback-token/HLS interception and alternate-stream handling.
- Retained the donor's original load-command identity.
- Corrected the compiled signing asset with an ad-hoc signature and header padding.

[Published releases](https://github.com/BananaOnGitHub/Streamside/releases) · [Historical evidence](docs/HISTORY.md)
