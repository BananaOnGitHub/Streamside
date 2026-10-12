# Architecture

Streamside runs inside Twitch's application process. A native playback core observes Foundation and AVFoundation requests; a provider registry supplies emote definitions and stable image identities; separate adapters integrate those definitions with Twitch's RN and legacy UIKit chat paths.

Twitch remains responsible for playback, account state, message models, native emote availability, and most rendering. Streamside adds information at admitted boundaries instead of replacing the chat client or theatre UI.

## System map

| Subsystem | Owner and responsibility | Main implementation |
| --- | --- | --- |
| Playback core | Stream contexts, exact rendition routes, alternate manifests, synthetic ad responses | [Streamside.c](../src/Streamside.c) |
| Provider registry | Global/channel catalogs, exact matching, persistent image identities, retired mappings | [TASEmotes.c](../src/TASEmotes.c) |
| Shared image transport | HTTP cache lookup, coalesced transfers, consumer cancellation, overflow recovery | [Streamside.c](../src/Streamside.c), cache/overflow headers |
| RN integration | Source-owned Hermes patch chain, native bridge exports, scoped React components | [RN patch headers](../src/TASRNWidthPatch.h), [ProviderEmoteStrip.js](../src/rn/ProviderEmoteStrip.js) |
| Legacy presentation | Native per-message emote definitions, TextKit/image-layer sizing, provider animation recovery | [TASEmotePresentation.c](../src/TASEmotePresentation.c), [TASEmoteUI.c](../src/TASEmoteUI.c) |
| Composer and native catalogs | Per-input editor state, suggestions, UIKit picker integration, native catalog snapshots | [SSComposer.c](../src/SSComposer.c), [TASRNComposerUI.c](../src/TASRNComposerUI.c) |
| Settings and diagnostics | Preferences, runtime-created settings/report controllers, sanitized observation | [TASDiagnostics.c](../src/TASDiagnostics.c), [TASPrivacy.c](../src/TASPrivacy.c) |
| Artifact tooling | Loader identity, segment/signature geometry, build receipts, package readback | [artifact_guard.py](../tools/artifact_guard.py), [Packaging](development/PACKAGING.md) |

The native files are C compiled with Objective-C runtime calls and blocks. Integration with Swift values is explicit and guarded; the project does not construct arbitrary Swift model storage.

## Two live-chat architectures

The inspected Twitch 31.5 donor contains two active integrations:

| Responsibility | React Native / Hermes / Fabric | Legacy UIKit / Swift |
| --- | --- | --- |
| Incoming messages | Enrich IRC metadata before `RCTWebSocketModule` delivers it to JS | Reuse the native WebSocket receive integration and synthetic-ID image route |
| Own-message display | Append provider ranges to the completed `LibraryTmiClient` ordinary-chat line | Enrich the renderer's per-message emote-definition response for admitted own messages |
| Proportional layout | Set both wrapper/image width before Fabric measures the inline child | Coordinate TextKit reservation and provider image-layer geometry |
| Composer | Extend the native input's recognition map; preserve Twitch's draft/tokenizer | Own provider previews and supply scoped expanded-text snapshots to native validation |
| Native catalog | Use the current RN input's code-to-ID map | Snapshot the exact autocomplete manager on its serial queue using verified Swift bridges |
| Picker | Adapt the native tray, section list, navigation, and scoped leaf exports | Insert owned content using copied layout coordinates and guarded footer integration |
| Details | Provider component within Twitch's bottom-sheet system | Owned UIKit provider sheet with scoped presentation/dismissal |

On the tested distribution, horizontal-only broadcasts used RN; broadcasts exposing horizontal and vertical presentation used legacy chat. Rotation alone does not select the renderer. A future Twitch release needs its own observation and admission checks.

RN paragraph `NSTextAttachment` objects are reconstructed placeholders for inline children. They are not the decoded emote objects used by the composer. Mutating them after measurement is not the current proportional-width mechanism.

The ordinary sent-message handler and the separate `/me` action handler are different paths. RN provider adaptation patches the former, not the latter.

## Playback integration

The constructor installs request/session and asset-loader adapters, initializes diagnostics, and then initializes enabled emote integrations. Playback does not depend on a private Twitch player class.

`NSURLSession` task-creation hooks observe `gql.twitch.tv` requests and normalize recognized playback-token bodies. Account/startup responses are not proxied. A runtime-created `NSURLProtocol` handles known Twitch HLS, remembered synthetic ad-segment responses, and enabled provider-image URLs. The AVFoundation compatibility path uses `tashttps` and `AVAssetResourceLoader`.

A master playlist establishes a `TASStreamContext` and registers the exact rendition URLs it contains. Subsequent media playlists select that owner before alternate-player logic runs. Eight bounded stream slots and generation-bearing references prevent one player's delayed completion from writing into another player's reused slot.

Main playback, PiP, and profile previews can overlap. Their clean variants and alternate masters remain scoped to their owning context. Unmapped variants do not borrow “the last stream.”

See [Adblock](features/ADBLOCK.md) for the request/manifest algorithm and fallback semantics.

## Emote data flow

An admitted room observation initiates global/channel provider fetches. The registry publishes bounded definitions and immutable metadata snapshots. It resolves channel names before global names and uses fixed provider precedence to handle exact-code collisions.

Incoming frames gain synthetic emote ranges without changing their message bodies. RN ordinary own-message display gains provider-only ranges after Twitch has completed its display line. Legacy presentation gains native-compatible emote definitions while retaining the original message and token objects.

Twitch then asks for an image using its ordinary synthetic CDN route. The registry redirects that identity to the provider asset; the image transport does not decide which emote a name means. Keeping registry identity separate from transport identity prevents unrelated rooms, URLs, or request variants from being conflated.

Native Twitch catalogs remain authoritative for Twitch/subscriber suggestions. Streamside does not fetch subscription tiers itself or turn locked native palette entries into owned emotes.

## State ownership

| State | Lifetime and authority |
| --- | --- |
| Playback context | One observed channel/master generation; expires or is replaced in a bounded table |
| Rendition route | Exact URL plus stream slot/generation; retired records explain misses |
| Provider room | Explicit room identity; provider fetch generations reject obsolete callbacks |
| Image identity | Scope + exact code + provider URL; no launch-order reassignment |
| RN patched source | Associated with the exact `RCTSource`; donor file on disk is unchanged |
| Composer state | Exact input/editor, selection, recognition map, visible previews, and weak owners |
| Recent history | Up to 40 saved names; resolved against current definitions |
| Open picker | Its first admitted Recent snapshot; stable until reopening |
| Image flight | One request variant; consumers own cancellation independently |
| Cache annotation | Foundation-owned cached response, verified timing/variant metadata, boot-scoped epoch |
| Diagnostic label | Process-local bounded label, not a persistent channel/resource identity |

These boundaries prevent a background room, recycled image view, delayed callback, or reopened menu from silently taking ownership of another surface.

## Concurrency and lifecycle

Playback tables and provider catalogs use separate locks. Provider fetches set pending state under the registry lock and start network work after releasing it. Each C-block callback explicitly owns the room string until completion, including stale and failed responses.

Image transport has a separate provider session and concurrent completion queue. HLS completion processing can synchronously fetch alternate tokens/manifests; it cannot hold provider delivery behind that queue. Two cache-lookup workers deliver eligible fresh hits without transfer admission. Misses enter the bounded shared scheduler.

Transport callbacks and cancellation messages run outside the shared transport lock. Cache-to-transfer handoff follows the defined cache → transport lock order and admits the whole consumer group before starting a task. Protocol stop state is checked during delivery, including reentrant stops.

UIKit work runs on the main thread. Legacy native catalog bridging runs on the exact manager's serial queue and publishes owned snapshots back to the UI. RN wrappers keep draft/selection state in input-scoped contexts rather than global variables. Timers and weak membership are detached or stopped when their surfaces disappear.

Chat animation and composer animation are separate. RN transcript images retain Twitch's decoder/rendering path. Composer GIF previews use independent bounded decoders and per-input display links. Legacy provider-layer recovery reuses Twitch's existing animation state and playhead.

## Hermes integration and compatibility

The RN source adapter first calls the original `RCTSource.data` getter. Admission checks the complete donor body, Hermes version, original function metadata, and checksum before producing an owned patched `NSData`.

The patch chain installs width handling, ordinary own-message adaptation, composer maps, provider cards, and the scoped composer/library/settings component graft. Later stages have their own structural checks and fallback. A source instance remembers its admission result and owns any resulting buffer.

The JS adapters replace verified writable leaf exports and preserve native props/callbacks. Installer failure restores the original exports. Adding React hooks to a donor body that already rendered would alter hook ordering; the autocomplete adapter specifically avoids that.

Runtime class names, Objective-C encodings, ivar spans/alignment, Swift value-witness sizes, and live ownership checks guard native adapters. A marketing version string is not sufficient to admit an unknown ABI. The exact RN donor requirement is stronger than the runtime admission used by legacy adapters.

See [Twitch internals](development/TWITCH_INTERNALS.md) for porting and [Compatibility](COMPATIBILITY.md) for supported claims.

## Failure handling

Missing definitions leave codes as text. Invalid/shared-room frames retain the original receive value. Missing or unsafe provider details retain Twitch's card. Preview exceptions resume original own-message emission. Unknown source bodies retain the original bundle.

Cache uncertainty returns to Foundation's normal validation path; it is not permission to serve stale data. Cancelling one image consumer does not cancel another consumer's delivery. Overflow recovery is bounded and expires rather than becoming an unbounded downloader.

Packaging uses a different boundary: changed binary bytes, invalid signature/layout metadata, or a missing fingerprint stop the operation. Runtime fallback preserves app behavior where possible; package integrity fails closed.

## Settings and observation

Third-party emotes are launch-gated and disabled by default. When disabled at launch, their hooks and provider requests are not installed. Suggestion modes are immediately effective and are independent of manual library browsing.

Counters describe activity even when event logging is off. Opt-in logs contain classified events and temporary labels, not raw chat, room IDs, URLs, headers, tokens, or manifests. Foundation's provider-image cache can persist HTTP data/metadata; that is separate from diagnostic logging and registry clearing.

See [Settings](features/third-party-emotes/SETTINGS.md) and [Diagnostics](features/DIAGNOSTICS.md).

## Continue reading

[Emote subsystem map](features/third-party-emotes/README.md) · [Testing](development/TESTING.md) · [Packaging](development/PACKAGING.md) · [History](HISTORY.md) · [Research archive](archive/README.md)
