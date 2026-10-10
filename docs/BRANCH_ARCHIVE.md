# Archived branch: archive/build46-image-result

Closed at the user's request on 2026-10-10. Active Twitch 31.5 implementation
continues on `compat/twitch-31.5` at build 87. This archive preserves
`diagnostic/build46-image-result` and its complete ancestry with documentation-only closure.

- Last implementation/probe head: `b074e6f0c6e17771a64783deb70eb8baebe38c27`.
- Retained report build: `3.0.0-build.46`; bundle build: `3.0.0.46`.
- Source, probe code, tests, build metadata and historical findings are unchanged.
- No new IPA, playback fix, release or device validation is claimed by closure.

## Purpose

Explain animated provider emotes being handed to legacy chat as still images after a multi-frame GIF decode.

## Work retained

Added guarded UIImage/CGImage constructors and getter observations, native response-wrapper entry points, donor-specific static ImageIO call-site labels, bounded weak image/raster identities, cached poster relationships and a separate result-origin ring. Original request selection, decoder results and animation playback are preserved.

## Outcome and limits

The later build-47 record reports repeated handoff of the same observed static UIImage. A later WebP download was not linked to that older image. This is observed object reuse, not proof of a cache hit, animation flattening or a completed playback fix. Unobserved/direct Swift paths and expired identities remain coverage gaps.

## Evidence and validation records

- [EMOTE_DIAGNOSTIC.md](EMOTE_DIAGNOSTIC.md)

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

