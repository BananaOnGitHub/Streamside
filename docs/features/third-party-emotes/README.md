# Third-party emotes

Streamside makes provider emotes usable inside Twitch's existing chat surfaces. One registry supplies definitions and image identities; each integration keeps Twitch's own message, editor, catalog, and rendering responsibilities intact.

## Read by subsystem

| Guide | Main question |
| --- | --- |
| [Providers](PROVIDERS.md) | How are catalogs fetched, matched, scoped, and assigned stable identities? |
| [Chat rendering](CHAT_RENDERING.md) | How do incoming and sent messages become native images in RN and UIKit? |
| [Composer](COMPOSER.md) | How do previews coexist with literal drafts, selection, undo, and provisional input? |
| [Emote picker](EMOTE_PICKER.md) | How do suggestions, native autocomplete, five-row browsing, and recents work? |
| [Emote details](EMOTE_DETAILS.md) | How are provider metadata, native-card fallback, holds, and dismissal handled? |
| [Image transport](IMAGE_TRANSPORT.md) | How do cache lookup, coalescing, scheduling, cancellation, and overflow interact? |
| [Settings](SETTINGS.md) | Which changes require relaunch, and what do reload and clear actually do? |

## Common boundaries

A **provider definition** identifies an exact code, provider image URL, scope, and available metadata. A **synthetic identity** lets Twitch's ordinary image request refer to that definition. An RN **width alias** additionally carries an admitted aspect ratio; it is not a different downloaded asset.

A **native catalog snapshot** comes from Twitch's current account/chat autocomplete authority. It is separate from provider definitions. Native codes win collisions in suggestions and composer previews.

A **consumer** is one request/delivery owner. A **flight** is a shared transfer for an identical request variant. Several visible images can consume one flight; one image can also be recreated without starting a different transfer.

A **Recent snapshot** is the list frozen for an open menu. Persistent history stores names, not a reusable collection of room-specific IDs.

## Architecture-specific behavior

RN uses IRC metadata, a display-line range adapter, guarded Hermes component changes, and Twitch's native RN text input. Legacy chat uses UIKit/Swift presentation definitions, TextKit geometry, per-input expanded-text snapshots, and copied collection-layout attributes.

These paths share registries and transport but are not interchangeable. An RN paragraph placeholder is not a composer attachment; a legacy animation timer is not the RN chat decoder. Keep those distinctions when debugging.

The feature is disabled by default and launch-gated. With it disabled at startup, the provider module installs no emote hooks and makes no provider API requests. Turning suggestion mode Off is a smaller change: rendering and manual browsing remain enabled.

[Architecture](../../ARCHITECTURE.md) · [Compatibility](../../COMPATIBILITY.md) · [Diagnostics](../DIAGNOSTICS.md) · [Historical investigations](../../archive/README.md)
