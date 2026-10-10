# Archived branch: archive/rn-chat-boundary

Closed at the user's request on 2026-10-10. Active Twitch 31.5 implementation
continues on `compat/twitch-31.5` at build 87. This archive preserves
`diagnostic/rn-chat-boundary` and its complete ancestry with documentation-only closure.

- Last implementation/probe head: `82c3251ffc895ecb3d4f769b61ac13d322895afc`.
- Retained report build: `3.0.0-build.65`; bundle build: `3.0.0.65`.
- Source, probe code, tests, build metadata and historical findings are unchanged.
- No new IPA, playback fix, release or device validation is claimed by closure.

## Purpose

Identify Twitch 31.5's active React Native ingress, catalog/metadata, native composer, Fabric presentation and emote-info paths while legacy hooks remained idle.

## Work retained

Builds 51–54 added passive ABI-gated ingress, source/surface, catalog-shape, input, image and paragraph observations, donor analysis tools and bounded host fixtures. Device reports established SRWebSocket → RCTWebSocketModule → websocketMessage delivery toward JS, a code-to-ID native composer map and the observed embedded Hermes source. Static analysis found paragraph attachments are reconstructed inline-child placeholders; emote width belongs at coordinated Fabric inline measurement/subtree layout, not placeholder-image mutation. The branch later merged compat through build 64, retaining both histories, and build 65 added guarded tap/host/sheet/content trace prefixes.

## Outcome and limits

Later compat build-66 notes record that provider taps reach the RN sheet while its query-backed native card content does not execute. Compat implemented the provider card at that boundary. Incoming rendering, widths, local echo, input previews, suggestions, the library and later transport corrections live on compat. This archive preserves the extra passive probes, tools and findings; they are not merged into current compat. The static native-seam investigation did not collect a live per-emote mount/image identity join, and its recorded Zig blocker is retained rather than rewritten as a passing full suite.

## Evidence and validation records

- [RN_CHAT_BOUNDARY_PROBE.md](RN_CHAT_BOUNDARY_PROBE.md)
- [RN_BUILD53_FINDINGS.md](RN_BUILD53_FINDINGS.md)
- [RN_EMOTE_REPRESENTATION.md](RN_EMOTE_REPRESENTATION.md)
- [RN_NATIVE_PRESENTATION_SEAM.md](RN_NATIVE_PRESENTATION_SEAM.md)
- [RN_EMOTE_INFO_TRACE.md](RN_EMOTE_INFO_TRACE.md)

These notes preserve the original host/donor checks, device observations and
coverage limits. Their historical test procedures and open-stage statements
are not requests to repeat the old diagnostic pass. The archive's normal build
keeps its original compile-time diagnostic defaults; explicit probe flags
remain necessary to reproduce a diagnostic artifact.

## Successor

Use [compat/twitch-31.5](https://github.com/BananaOnGitHub/Streamside/tree/compat/twitch-31.5)
for current implementation. The [archive index](https://github.com/BananaOnGitHub/Streamside/blob/compat/twitch-31.5/docs/DIAGNOSTIC_BRANCH_ARCHIVE.md)
records all four closed branches and what was incorporated. Existing main and
older archive histories are left intact.

