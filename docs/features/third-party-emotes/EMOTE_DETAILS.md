# Provider emote details

Provider details show the registry's metadata without asking Twitch's GraphQL service to recognize a synthetic ID. Native Twitch IDs retain Twitch's original card.

The shared metadata includes exact name, provider, Channel/Global scope, available creator credit, asset URL, and aspect ratio. It is an owned snapshot; presentation does not retain a mutable registry entry.

## RN card boundary

Build 65 tracing showed a provider tap reached Twitch's RN bottom sheet, but its query-backed native content did not produce a provider card. The current [ProviderEmoteInfo.js](../../../src/rn/ProviderEmoteInfo.js) graft routes at that content boundary.

`getMetadata` resolves an exact active/retired synthetic identity, including width aliases. Missing metadata returns the original component. Provider/native trees are separate, so provider rendering does not conditionally add hook slots inside Twitch's native component.

The provider component uses Twitch's theme, BottomSheet, and `useSheetHandoff`. Preview width is proportional within the supported display box. It supplies accessible title/action labels and creator credit only when known.

The library's hold card uses the same metadata/action bridge in [ProviderEmoteStrip.js](../../../src/rn/ProviderEmoteStrip.js).

## Actions and lifecycle

Copy name, Copy image URL, and Open in browser record an action and close the sheet. The bridge is invoked from `onClosed`, after the handoff reports completed dismissal. Close without an action does not invoke the bridge.

`rn_popup_action()` accepts only the bounded action enum and synthetic identifier. It re-resolves metadata; JS cannot submit arbitrary clipboard text or a URL. UIKit work is dispatched to main with an explicitly owned metadata snapshot.

Browser handoff opens the provider **asset URL** and requires the application to remain active. It does not invent a creator/profile destination. No sheet/controller is retained across Safari.

## Legacy UIKit presentation

[TASEmoteUI.c](../../../src/TASEmoteUI.c) presents an owned provider sheet for provider chat taps. [SSComposer.c](../../../src/SSComposer.c) supplies tile and editor holds.

The editor hold hit-tests TextKit glyph bounds and private attachment identity. It ignores whitespace, ordinary/native text, foreign attachments, and marked composition. The recognizer is installed once per exact editor and detached on rebinding/teardown.

Both tile/editor holds use 0.5 seconds. Only Began queues presentation; early native text-item menu callbacks do not open the sheet. Owned provider hits suppress the generic image menu, and recognizer failure priority prevents duplicate native context-menu haptics.

Tile holds cancel touch-up insertion. Short taps or movement fail the hold normally, retaining native editing or scroll cancellation. Editor touches are not globally cancelled.

Successful composer presentation emits one light impact. Stale, duplicate, cancelled, or failed requests do not. The pending request rechecks weak ownership and the live attachment before presentation.

## Dismissal scope and layering

The UIKit presenter dismisses only its currently owned navigation wrapper, not Twitch's stream controller or an ancestor. Repeated actions coalesce while dismissal is pending.

Browser launch runs from dismissal completion. The C block explicitly retains the URL, releases it afterward, and does not capture a composer/stream controller. If Twitch has become inactive, it skips launch. Copy/Done preserve their immediate-dismiss semantics.

Before presentation, the legacy window-level suggestion strip is hidden. Image, selection, and timer updates cannot raise it over a pending sheet or parent modal. After dismissal, placement restores it only when the original input is still focused with matches.

## Refusal and tests

Unknown IDs, stale owners, unsupported native ABI, failed presentation, or missing metadata preserve the native fallback rather than constructing a partial card.

[RN popup tests](../../../tests/test_rn_popup.py), [Presentation-route tests](../../../tests/test_provider_presentation_route.py), and [Composer details tests](../../../tests/test_composer_details.py) cover card routing, action ordering, attachment identity, gesture priority, wrapper scope, and lifecycle interruption.

The [RN provider-info trial](../../archive/experiments/RN_PROVIDER_INFO_TRIAL.md) and [info trace](../../archive/investigations/RN_EMOTE_INFO_TRACE.md) preserve the query-content discovery. The early hold/browser corrections are recorded in [History](../../HISTORY.md).

[Feature map](README.md) · [Composer](COMPOSER.md) · [Picker](EMOTE_PICKER.md)
