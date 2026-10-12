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

## Native differences

| Browser mechanism | Native implementation |
| --- | --- |
| Worker/fetch interception | Foundation session/task adapters and URL protocol |
| Browser player/DOM actions | Not ported as DOM operations; Twitch's native player remains responsible for UI |
| Browser stream maps | Bounded generation-bearing `TASStreamContext` and exact URL route tables |
| Browser blank-media fetch | Native synthetic response for remembered ad-segment requests |
| Browser visibility/player reload logic | Not equivalent to native lifecycle; no claim of a complete browser-player port |
| Browser headers/state | Transient observed Twitch headers; sanitized diagnostics exclude them |

AVFoundation retains a custom-scheme resource-loader path. Amazon IVS uses the Foundation interception route. Native multi-player ownership is a significant correction: a global slot was insufficient for PiP and profile previews.

The provider-emote system, composer, Hermes grafts, shared image cache, and native settings are Streamside features, not VAFT script behavior.

## Updating the pin

1. Select an explicit upstream commit and inspect its diff from the current pin.
2. Record the immutable URL, solution version, retrieval provenance, Git blob, SHA-256, and license/copyright notices.
3. Review each strategy change against [Streamside.c](../src/Streamside.c): token variables/query, markers, alternate order, matching, fallback, and manifest URL handling.
4. Port relevant behavior rather than executing browser script in Twitch's native process.
5. Run host protocol/privacy tests, native build/package guards, and focused device playback checks.
6. Exercise main playback, PiP, profile previews, unknown routes, alternate failure, cancellation, and an actual ad-bearing case.
7. Update this document, [Adblock](features/ADBLOCK.md), [Changelog](../CHANGELOG.md), and [third-party notices](THIRD_PARTY_NOTICES.md) together.

Do not treat an upstream bump as proof of iOS compatibility. The exact RN donor admission is an independent emote concern.

## Attribution

VAFT is MIT-licensed. Its notice is retained in [MIT notices](licenses/MIT-NOTICES.txt). Streamside's native implementation remains under the root [Apache-2.0 license](../LICENSE).

[Architecture](ARCHITECTURE.md) · [Adblock](features/ADBLOCK.md) · [History](HISTORY.md)
