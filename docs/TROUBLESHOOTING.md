# Troubleshooting

Start with the affected surface. Keep the report and visible result from the same launch whenever possible; clearing the event log does not reset launch counters.

## The Streamside page or emotes are missing

Open the main **Profile → Settings** page, not Chat Identity or a nested preferences page. The settings entry is scoped to the main native settings screen.

Enable third-party emotes there and fully quit/reopen Twitch. They are off by default and launch-gated. If the page itself is missing, include the app version and installation route; the injected binary may not have loaded or the native screen may have changed.

If a code remains text, first check that the channel's provider definitions loaded. Loading is asynchronous and old messages are not replayed. Use Reload Emotes, then try a new message. Correct capitalization matters for exact matching.

## Incoming works but sent emotes do not

Incoming and own-message display are different adapters. State whether the message was ordinary chat or `/me`, whether the stream used RN/legacy, and whether ordinary text still appears.

RN's separate `/me` handler is unchanged. Missing registration/export/callback counts and a displayed plain code have different meanings. A rewrite counter alone does not prove visible rendering.

## Emote images are square, wrong, or static

Proportional layout depends on the renderer. RN must admit the exact Hermes width patch; legacy needs both reservation and image-layer geometry. A native composer attachment uses another seam.

Specify chat versus composer versus library and include a crop showing the result. Unknown dimensions can begin square, and an already admitted RN width alias does not change its encoded ratio later.

For a wrong image, compare the name/scope/provider and whether the problem follows a channel switch or restart. Current identities bind scope/name/URL; do not diagnose every wrong bitmap as insufficient width.

GIF composer support is bounded; non-GIF or oversized/unsupported GIF previews can remain still. Native RN transcript animation is Twitch's path. Report which surface stops and whether scrolling, deleting/retyping, or foregrounding changes it.

## Suggestions or the provider library are absent

Automatic completion needs two characters at a token end; Colon mode needs `:`. URLs, mentions, mid-word carets, selections, and marked input can intentionally suppress owned completion.

Off disables the owned strip but leaves manual library browsing available. Open Twitch's emote keyboard and look for **Third-party emotes** and its footer shortcut.

A missing provider section with native UI intact can mean source/bridge admission failed. Include the hook/patch portion of the report. Do not assume every stream uses RN because the donor contains RN code.

## A recent emote is not listed or does not move immediately

Recent history saves up to 40 names, resolved against the current room. Unavailable names are omitted. The row is frozen while the menu is open; close/reopen to see a new order. Twitch's own Recent list remains separate.

## Keyboard predictions convert too early

Unconfirmed marked input should remain under UIKit's control until committed. Record the keyboard/language, whether it was an inline prediction or IME composition, and the exact sequence of typing/accepting/cancelling without sharing private text.

The guard covers native change/selection and value/map setters. A reproducible failure on another keyboard is useful evidence, not a reason to add a global typing delay.

## Reload Emotes is absent

On RN, it belongs directly beneath the Chat Settings title, before Identity. On legacy, it uses the native chat-menu integration.

It requires the launch-enabled feature and an admitted explicit channel. An unknown/ambiguous room can refuse reload. Include the screen and report; the main-page/module admission matters more than searching another preferences subsection.

## Slow images or blank tiles

Capture whether the issue is first loading, reopening, rapid scrolling, or repeated warm use. Cache hits, queued flights, mounted JS instances, unique assets, and Foundation tasks are not interchangeable counts.

Current RN geometry avoids full-catalog startup mounting; the transport retains bounded flights, direct cache delivery, and overflow recovery. A new slow report should identify the boundary before changing capacities.

## Playback ads, black previews, or PiP interference

Include Twitch/iOS versions, installation method, account sign-in state, and preroll/midroll/PiP/profile-preview scope. Enable logging, reproduce, and copy the report.

Unknown media routes preserve native playback rather than borrowing another stream's backup. Zero ad-marked counters do not establish successful suppression. Historical single-global-state builds before 2.0.3 had PiP/profile-preview cross-talk.

## Signing or packaging failures

Use the verified framework for sideloading, not the jailbreak dylib. Keep the adjacent build fingerprint with it. Rebuild from intended source when integrity checks fail; do not regenerate a receipt over an arbitrary replacement or bypass the normalizer.

The current build requires 16 KiB segment geometry and exact loader/signature metadata. A signer failure can be a binary-layout issue, not proof that the filename itself is forbidden.

If Twitch launches logged out but crashes after login, verify the complete donor `Assets.car`. Historical truncated assets survived login but failed during signed-in scene construction. Current packaging requires and verifies that catalog.

See [Packaging](development/PACKAGING.md) for developer checks and [README installation](../README.md#installation) for setup.

## Useful reports

Use [Contributing](../CONTRIBUTING.md) for the report checklist and [Security](../SECURITY.md) for redaction. Do not post tokens, signing material, provisioning profiles, raw authenticated requests, or unrelated private chat.
