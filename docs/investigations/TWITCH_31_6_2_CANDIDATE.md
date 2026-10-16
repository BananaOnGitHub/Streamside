# Twitch 31.6.2 candidate — Streamside 3.1.0 build 18

Prepared on `dev/3.1.0` from `0bf7a61`, following the
[read-only hotfix comparison](TWITCH_31_6_HOTFIX_COMPARISON.md).
This is a test candidate, not on-device acceptance or a published release.
Report identity is `3.1.0-build.18`; framework bundle build is `3.1.0.18`.

## Scope and input

The supplied Twitch 31.6.2 donor identifies build `262872150334984303`.
Its 197,132,394-byte IPA has SHA-256
`8cf72803d0e0b1aeb7c062af2d0cbac1e20f78e9f3c73fc590ac5ae9d1d29186`.
The input archive remains unchanged.

Its original 28,682,408-byte Hermes-98 bundle is identical to the verified
31.6 body: SHA-256
`20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458`.
The existing exact-body admission and all five patch stages remain unchanged.
No donor lengths, checksums, function IDs, offsets, module bindings, register
operands or exception ranges were replaced to admit the new app version.

Only Streamside's report/framework build labels change from build 17. The
device-accepted legacy library-selection transition and WebP timing/read-ahead
remain intact. Playback, emote behavior and diagnostic policy are unchanged.
The paused `fix/rn-chat-gaps` branch and its specialized rolling trace are
untouched. This candidate does not address the unresolved RN gaps or redemption
behavior described in the comparison.

## Validation

- The suite ran 193 tests: 191 passed; the two Apple Foundation/ImageIO
  integration checks skipped on Linux. No failures.
- Full five-stage structural verification passed against this exact 31.6.2
  IPA: deterministic owned-payload regeneration, Metro/export bindings,
  preserved predecessor functions, constants, handlers and debug data,
  imported closure/branch bounds, and independent Hermes-98 disassembly.
- The pinned Hermes gate passed with the 31.6.2 original bundle: 32 accepted
  snapshots and 7,344 emote-library window calculations, including the actual
  donor settings factory/component. This does not test the transcript's
  LegendList or live Fabric layout.
- Emote+demand diagnostic native artifacts passed their build gate, defined
  WebP symbol checks and Mach-O artifact contracts. The subsequent ordinary
  artifacts passed the same artifact verification; both DEBs built.
- The finished ordinary IPA passed `tools/verify_ipa.py` independently of
  packaging. Additional direct comparisons confirmed unchanged original
  Hermes bytes, main executable `__text`, `Assets.car`, and Twitch version/
  build metadata. Its injected framework identifies build `3.1.0.18`.
- Documentation validation passed. Original donor hashes were rechecked
  after packaging.

The normal candidate uses `EMOTE_DIAGNOSTIC=0`,
`IMAGE_DEMAND_DIAGNOSTIC=0`, and no compiled experimental chat trace.
Runtime diagnostic category settings retain their existing defaults and
launch-applied behavior.

## Artifact and device boundary

- Filename: `Twitch_31.6.2_Streamside_3.1.0-build.18_unsigned.ipa`.
- Bytes: 194,489,275.
- SHA-256: `c9e59ec67fffdc765cdc6d0926ba138b35a46701a2aaa0e0d0bdc5e0111b9b32`.

The IPA requires signing through the usual sideloading route. Launch, RN and
legacy chat, own messages, emote surfaces, library/input transitions, stream
reopen/PiP, token renewal, HLS playback and an ad-bearing case still require
device validation for this package. Successful host checks and packaging do
not establish those outcomes or extend the released compatibility matrix.
