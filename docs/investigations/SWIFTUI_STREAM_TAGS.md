# Native followed-stream tags

## Implementation trial — 2026-11-15

Starts from `a2275ed` on `feat/native-frontend`. Live followed-channel rows gain
one compact line of Liquid Glass tag pills immediately below the category.
Playback, routing, account lifecycle and runtime guards retain their existing
paths. No tag search/filter or independent network request is introduced.

## Donor findings and native boundary

Exact Twitch 32.0 donor SHA-256:
`076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`.
The existing donor validator passed all 12 pinned images and every ABI entry,
including these newly admitted TwitchCore exports:

- `LiveStream.tags` at `0x3d014`: Swift self in X20, retained array result in X0.
  Its getter obtains field placement from runtime metadata. The adapter never
  reads that placement or Swift array internals.
- `Tag` metadata accessor at `0x53a8c`: complete runtime metadata supplies value
  witnesses for allocation, casting and destruction; enum payload layout is not
  synthesized.
- `Tag.displayName` at `0x544a0`: Swift self in X20, owned String in X0/X1.
  Inspected return paths preserve the localized/native freeform display name.

The existing TwitchKit StreamFragment mapper at `0x2d2618` reads `streamTags`
at call `0x2d2df0`, localized tag fragment names at `0x2d2e78`, `freeformTags` at
`0x2d3068`, and freeform names at `0x2d30d4`. The adapter consumes the tags already
present on the native LiveStream returned by the authenticated personal-sections
feed. It does not fabricate tags when the response has none or fan out extra
per-channel requests. Real device response completeness remains to be checked.

The inspected native `_TtC6Twitch7TagView` has `buttons`, `totalWidth` and
`containerScrollView` fields. Its layout helper calls each button's
`sizeThatFits:` at `0x10398e488` and updates scroll content size at `0x10398e834`.
`TagPriorityController` additionally has commerce/watch-streak priority state.
These observations support measuring actual labels rather than assuming a fixed
pill count; they do not establish the exact ranking/packing algorithm used by
every Twitch list screen. No original UI controller is instantiated to obtain
this behavior.

Swift Array<Tag> values bridge through the existing runtime Objective-C bridge;
each boxed Tag is cast using its actual metadata and read through displayName.
Native bounds admit at most 100 source tags and 256 UTF-16 units per name, and
retain at most 32 display names. The owned presentation snapshot now permits a
structured string array, preserving account/channel field type checks. Swift
removes empty/control-containing names and case-insensitive duplicates, while
offline rows receive no stale tags. Names stay in memory; diagnostic reports do
not gain tag names or request content.

## Presentation policy

Scaled semibold system text is measured with UIFont using the same point size
and weight as the SwiftUI label. The width includes capsule padding and a
rounding allowance. The selected set maximizes the number of complete pills
that fit the available line, then prefers earlier native tags among equally
large fitting sets. Selected tags retain native order. A long early tag cannot
block multiple shorter ones. Pills do not wrap, truncate or add a hidden-count
badge, and only the selected pills are rendered. The existing five-second feed
refresh gate supplies updated metadata as usual; tags have no separate poller.

On iOS 26, pills use `glassEffect` inside a GlassEffectContainer. Reduce
Transparency uses a solid system background; older supported systems use thin
material. System text-size changes and the existing accessible stacked-row
layout change fitting width/font size naturally. Tag touches pass through to the
row's existing stream-open action. The player-specific Liquid Glass preference
does not control feed pills.

## Validation

Host regression: **71 tests passed**, including a new ARM64 call-lowering check
for Tag-array retrieval. The mandatory Swift model suite now checks structured
snapshot parsing, offline/malformed input, Unicode/deduplication, oversized tags,
exact-width cases and an independent exhaustive subset oracle for 261 widths.
Those Swift model checks require the hosted Apple build; Linux test results do
not claim Swift compilation. Donor inspection is static and does not prove that
live tags are present on a signed-in device.

Apple compilation, component download/admission and local packaging results are
recorded below when complete. Device review must check real live-channel tags,
refresh/background continuity, one/two-line titles, larger text, Reduce
Transparency, row taps and unchanged RN/Hermes counters.
