# VAFT upstream and maintenance

Streamside contains a pinned copy of VAFT and a native iOS adaptation of its playback strategy.

## Pinned source

| Field | Value |
| --- | --- |
| Project | [pixeltris/TwitchAdSolutions](https://github.com/pixeltris/TwitchAdSolutions) |
| Commit | `c51ef2fe8f667f9dc9216eb550924cf0d732ce27` |
| Strategy/distribution | VAFT uBlock Origin script |
| Internal solution version | 24 |
| Local source | [upstream/vaft-ublock-origin.js](../upstream/vaft-ublock-origin.js) |
| Immutable source | [Pinned VAFT file](https://github.com/pixeltris/TwitchAdSolutions/blob/c51ef2fe8f667f9dc9216eb550924cf0d732ce27/vaft/vaft-ublock-origin.js) |
| Recorded retrieval | 2026-08-12 |
| Git blob | `a89a308f87b33f01f3c7d663366e52dc7d6ae020` |
| SHA-256 | `8ba15a99627c3d2a8fab3c3011b43d68ecb89eb40af549b0052d98449f02f591` |

The local copy matches the pinned upstream file. The original moving master URL is retrieval provenance, not the authoritative update pin.

TwitchAdSolutions is archived/read-only at review time. Maintenance therefore means deliberate review of a known upstream revision or another explicitly selected successor, not automatic tracking of a moving branch.

## Preserved strategy

The port retains the alternate player order embed → popout → autoplay, popout playback-token normalization, persisted token query, broad stitched-ad marker, resolution/frame-rate matching, alternate-master caching, and blank-segment fallback.

The browser source's internal solution number is not Streamside's release number. “VAFT solution 24” and “Streamside 3.0.0” identify different version domains.

## Native implementation

The shared native VAFT engine lives in [TASVAFT.h](../native/shared/TASVAFT.h) and is used through the SwiftUI frontend's [native playback adapter](../native/SSNAdBlock.m). Stream ownership, native token requests and playlist decisions are tested through the shared engine and Apple transport fixtures. See the [native VAFT investigation](investigations/SWIFTUI_NATIVE_VAFT.md).

When updating the pin, preserve the upstream revision, hashes, notices and exact strategy changes. Validate the shared engine, native playback transport, local packaging, and actual device playback including ad-bearing streams and cancellation.

## Attribution

VAFT is MIT-licensed. Its notice is retained in [MIT notices](licenses/MIT-NOTICES.txt). Streamside's native implementation remains under the root [Apache-2.0 license](../LICENSE).

[Native investigations](investigations/README.md)
