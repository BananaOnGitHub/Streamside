# Archived branch: archive/build47-request-decision

Closed at the user's request on 2026-10-10. Active Twitch 31.5 implementation
continues on `compat/twitch-31.5` at build 87. This archive preserves
`diagnostic/build47-request-decision` and its complete ancestry with documentation-only closure.

- Last implementation/probe head: `1f58c73fd36a28e72e71994e184eb495d8a05c67`.
- Retained report build: `3.0.0-build.47`; bundle build: `3.0.0.47`.
- Source, probe code, tests, build metadata and historical findings are unchanged.
- No new IPA, playback fix, release or device validation is claimed by closure.

## Purpose

Determine which native static/animated requester and cache paths are observed, rather than infer cache selection from reuse of a still UIImage.

## Work retained

Retained build 46 and added six native requester wrappers, donor-UUID/return-site-gated NSCache observations, bounded weak cache and result identities, payload-to-handoff correlation, launch-local private request keys and GIF/WebP container animation metadata. It does not replace cache values, change requests, decode pixels or mutate playback.

## Outcome and limits

The instrumentation separates request entry, empty/nonempty lookup, observed payload identity and later assignment. It deliberately leaves native type/expiry acceptance unknown. Direct Swift bypasses, unknown slots and unlinked downloads remain gaps. No device finding retained on this branch establishes that build 47 itself fixed the original freeze.

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

