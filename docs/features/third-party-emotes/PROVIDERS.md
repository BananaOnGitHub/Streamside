# Providers, matching, and image identities

The registry in [TASEmotes.c](../../../src/TASEmotes.c) is the authority for provider definitions. UI surfaces receive owned metadata snapshots, not pointers into its mutable room arrays. Twitch's native catalog is a separate authority described in [Emote picker](EMOTE_PICKER.md).

## Catalog ownership and limits

`Room` state separates a global registry from six recently active channel registries. Each room owns its identity/login, sorted entries, provider loaded/pending/failure state, generation, and activity time. The global registry retains at most 2,500 names; each room retains at most 4,000.

Inactive rooms expire after 20 minutes. Eviction/reload can retire image mappings for up to 45 minutes, within a 3,000-entry history, so a visible chat cell can continue resolving its original identity. This is a bounded grace period, not permanent history.

`catalog_changed_locked()` increments the revision used by UI snapshots. A thumbnail completion does not require rebuilding thousands of metadata entries; consumers can update visible images while reusing a catalog revision.

The registry's exact-name ordering supports case-sensitive lookup. Display snapshots are sorted separately using case-insensitive name comparison and an exact-name tie-break. Changing display order does not change chat matching.

## Provider APIs and parsing

The implemented endpoints are:

| Provider | Global | Channel |
| --- | --- | --- |
| 7TV | `https://7tv.io/v3/emote-sets/global` | `https://7tv.io/v3/users/twitch/{room-id}` |
| BTTV | `https://api.betterttv.net/3/cached/emotes/global` | `https://api.betterttv.net/3/cached/users/twitch/{room-id}` |
| FFZ | `https://api.frankerfacez.com/v1/set/global` | `https://api.frankerfacez.com/v1/room/id/{room-id}` |

These are the endpoints used by this source revision, not a promise that provider APIs never change.

[TASEmoteFetch.h](../../../src/TASEmoteFetch.h) admits nonempty HTTP 200 bodies up to 8 MiB before JSON parsing. A channel 404 is an ordinary absent-catalog outcome; a global 404 is a retryable HTTP failure. Transport, empty/oversized body, JSON, schema, and unavailable-session/task failures are distinct.

`parse_provider_locked()` follows each provider's schema:

- 7TV uses the global set or channel `emote_set.emotes`.
- BTTV combines `channelEmotes` and `sharedEmotes`; its global endpoint is an array.
- FFZ uses `default_sets` for globals and the room's returned sets for channel catalogs.

`parse_list_locked()` copies bounded strings while the JSON objects remain alive. Codes are limited to 96 bytes and cannot contain the registry's forbidden whitespace/tag delimiters. URL admission checks provider CDN origin rather than allowing arbitrary JSON-provided endpoints.

7TV asset selection checks advertised files. Animated entries prefer 2x GIF, then WebP/PNG alternatives and 1x variants; still entries prefer WebP/PNG. BTTV uses its 2x CDN route. FFZ prefers its animated 2x URL, then static 2x/1x URLs, normalizing protocol-relative URLs to HTTPS.

Creator credit is copied only when supplied. Dimensions must be positive and bounded to 4,096 in each direction; otherwise the entry begins with a square aspect ratio. Later response-header inspection can learn dimensions without decompressing the image.

## Fetch generations and C-block lifetime

`ensure_loaded()` marks pending work under `g_emote_lock`, captures the room generation, and releases the lock before starting network tasks. Completion rechecks that generation. A successful response from an evicted or reloaded room cannot populate the reused slot.

`fetch_provider()` explicitly retains the room string for its completion block. In this C/Objective-C-runtime build, a plain C block capturing an `id` pointer does not provide the ownership assumptions of ARC Objective-C source. Build 40 exposed an expired room string in a deferred BTTV callback; build 41 added ownership on every completion/unavailable path.

`finish_provider()` clears pending state for accepted, stale, failed, and unavailable results. Failed attempts back off from 60 seconds through 120 and 240 seconds to an eight-minute cap. A reload forces a new generation and fetches; ordinary retry remains demand-driven.

These operations fetch definitions, not a full image library. Images are requested when Twitch or a visible owned surface asks for them.

## Precedence and matching

Exact channel codes take precedence over global codes. Within a scope, the fixed provider rank is 7TV, then BTTV, then FFZ. Arrival order does not decide a same-name collision.

`add_emote_locked()` rejects conflicting identity assignments and keeps registry storage bounded. At capacity, a higher-priority provider can displace a lower-priority entry; the old identity is retired instead of repointed to a new image.

Incoming matching first tries the complete space/tab-delimited word, then a bounded trim of supported boundary punctuation. The code remains case-sensitive. This is different from picker search, which uses a case-insensitive contiguous substring.

Native IRC ranges protect their ownership. Provider matching will not append an overlapping range. The legacy own-message definition adapter has its own narrower literal-space boundary to match Twitch's inspected native definition matcher; do not describe every route as having identical punctuation semantics.

## Deterministic image identity

The original sequential scheme allowed a synthetic CDN URL cached in one launch to mean a different image in another. Stable scope/name/URL identity removes that reassignment.

`image_identity()` uses 64-bit FNV-1a over four zero-separated parts:

1. `Streamside-image-v1`
2. Scope identity
3. Exact code
4. Provider image URL

It maps the result into:

```text
900000000000000 <= ordinary ID < 1000000000000000
```

The 15-digit integer remains exactly representable through JavaScript's number representation. Scope and URL are part of the identity; fetch order and launch order are not.

`identity_available_locked()` checks active and retired entries. A detected collision with different content is refused rather than assigned a replacement route. This is deterministic identity with collision refusal, not a guarantee that a finite hash can never collide.

RN proportional rendering uses a second alias namespace defined in [Chat rendering](CHAT_RENDERING.md). Both identities resolve through the same admitted registry metadata.

## Dimension learning and routing

[TASEmoteGeometry.h](../../../src/TASEmoteGeometry.h) reads bounded PNG/GIF/WebP dimension headers, never decompressing an untrusted image merely to discover its ratio. PNG IHDR, GIF logical screen size, and VP8X/VP8/VP8L headers have distinct checks.

`image_url_copy()` recognizes the synthetic Twitch image route, resolves only known active/retired mappings, and returns the provider URL. It does not synthesize an asset just because the numeric ID falls inside a namespace.

An admitted RN width alias freezes its encoded ratio. Learning a different ratio later does not reinterpret a cached alias already used by a chat cell. The composer uses its own presentation geometry; it is not forced to read RN's four-digit width encoding.

## Snapshot and scope rules

`tas_emotes_picker_copy()`, `tas_emotes_named_copy()`, and `tas_emotes_metadata_copy()` return owned values. Their lifetimes do not depend on the registry lock remaining held.

Combined suggestions suppress a global provider code shadowed by the room. RN bridge operations additionally require exactly one known room matching the explicit ID or login. Unknown/ambiguous rooms do not fall back to the last incoming channel.

Recent names are re-resolved against the active room. A saved name becoming unavailable is omitted; it does not authorize reuse of a stale ID from another room.

Reload retires current definitions, changes generations, and refreshes global/selected room state. Clearing definitions does not erase the shared HTTP cache, Twitch's decoded images, or every composer cache. Those lifetimes are documented in [Image transport](IMAGE_TRANSPORT.md) and [Settings](SETTINGS.md).

## Tests and historical evidence

- [Fetch policy tests](../../../tests/test_emote_fetch.py): status/body-size/schema outcomes and limits.
- [Fetch lifetime tests](../../../tests/test_emote_fetch_lifetime.py): deferred callback ownership and cleanup.
- [Image identity tests](../../../tests/test_emote_images.py): synthetic routing and provider image behavior.
- [Incoming tests](../../../tests/test_rn_incoming.py): ranges, native overlap, shared-room refusal, and fallback.
- [Native picker tests](../../../tests/test_native_picker.py): native catalog authority and collision behavior.

Host tests verify the compiled helpers/adapters and fixture contracts. They do not prove that an arbitrary provider API response, unknown Twitch donor, or visible device render works.

[Native-emote research](../../archive/investigations/NATIVE_EMOTES.md) preserves the catalog and identity discoveries. [History](../../HISTORY.md) separates the large-7TV limit correction, callback crash, and later image-identity fix.

[Emote feature map](README.md) · [Architecture](../../ARCHITECTURE.md)
