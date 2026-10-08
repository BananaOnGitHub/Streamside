# Provider info in React Native — build 66

## Device evidence and implementation

Build 64's first-download composer animation is user-confirmed. Build 65 on
`diagnostic/rn-chat-boundary` traced the active RN info route on Twitch 31.5:

| Seam | Native | Provider resolved | Provider missing | No ID |
| --- | ---: | ---: | ---: | ---: |
| EmotePart | 22 | 41 | 0 | 0 |
| Tap | 1 | 2 | 0 | 0 |
| ChatCardHost | 1 | 2 | 0 | 14 |
| Emote sheet | 3 | 6 | 0 | 0 |
| EmoteCard content | 2 | 0 | 0 | 0 |

Render counts are repeated observations, not distinct taps/messages. The two
provider taps reach the sheet but fail to reach successful content. Static
inspection explains this: function 19172 queries Twitch metadata for emoteID
before creating EmoteCard content. Provider synthetic IDs have no corresponding
Twitch query record. No further runtime logging is needed before this trial.

ChatCardHost factory 3801 stores the emote sheet closure 19172 in environment
slot 13. Build 66 wraps that component at factory offset 0x5e. The wrapper has
no hooks. An immutable registry snapshot for the exact synthetic ID selects
the separate provider component; native/unknown IDs or lookup exceptions return
an element of the original component with its original props. Width aliases and
recently retired visible emotes use the same registry lookup as image delivery.
It does not infer a channel or substitute a GraphQL response.

The provider component uses React (Metro 72, CommonJS with optional default
interop), RN (5), and Twitch useTheme/BottomSheet/useSheetHandoff (2118).
Metro 245 is JSX runtime, not a theme-hook export. Its content is an RN Image, proportional
bounded preview, name, provider/global/channel/creator subtitle, Copy name,
Copy image URL, Open in browser, and Close. Preview animation relies on the
donor RN image decoder, already working in chat; popup animation awaits device
confirmation. No Twitch subscription/follow/report actions are shown for
provider IDs. Native emotes retain Twitch's original card and actions.

Row actions first invoke handoff.onClose. Once the existing sheet calls
onClosed, its original handoff is completed and the selected action is sent to
the separate native module. Native code re-resolves the exact ID and accepts
only three enumerated actions. It queues UIKit work on main with an owned
snapshot, without holding a presenter during browser opening. JS cannot supply
clipboard text or an arbitrary URL. The normal sheet close performs no action.

## Owned bytecode and validation

`src/rn/ProviderEmoteInfo.js` is compiled by the exact Hermes-98 compiler.
`tools/rn_graft.py` imports only owned functions, remaps property string IDs to
the admitted donor pool, widens operands/branches, and relocates handler ranges.
Literal buffers, switches, unsupported indexed operands and debug data are
refused. `TASRNPopupPayload.h` contains owned code and numeric pool references,
not copied donor function bodies.

The in-memory patch extends the function table by 11 entries (132 bytes).
Donor sections shift together; absolute code/full-header/debug-section offsets
are adjusted. It appends the owned code and a clone of factory 3801 with one
21-byte insertion. The factory stays frame 32: injected Call2 staging is above
all live registers. A bounded Catch preserves slot 13's original component if
installation throws. All original factory branches are after the insertion.
The complete working width/local/composer chain must already be admitted.
Unexpected length, header, footer or target metadata leaves that chain intact.

Validation commands:

```sh
ZIG=/path/to/zig EMOTE_DIAGNOSTIC=0 make verify test
PYTHONPATH=/path/to/hermes-dec ZIG=/path/to/zig \
  python3 tools/verify_rn_popup.py /path/to/twitch-31.5.ipa \
  --hermesc /path/to/hermes98/hermesc
```

The exact-donor check verifies all 47,311 previous functions, constants, handler
and debug metadata; imported closure IDs and branch/handler boundaries; compiler
regeneration; original immutability; changed-target/footer/repeated-admission
refusal; and an independent Hermes disassembly. Node mocks test native fallback,
hook separation, proportional image source and actions after dismissal. These
checks do not execute Twitch on a device. The embedded bundle and native RN
framework stay byte-identical in the packaged IPA.

## Device trial

Fully close Twitch and launch build 66. Tap a static provider emote, a wide
provider emote, and an animated provider emote in chat. Check preview, name,
subtitle, close/backdrop, copy actions and browser handoff. Then tap a native
Twitch emote and confirm its normal card. Repeat after reopening and switching
channels. Composer holds and picker integration are later milestones.

The report adds `RN provider info patch` and aggregate lookup/resolved/missing/
actions/refused counts. No emote code, sender/channel identity, URLs, chat text,
headers or image bodies are logged. Build 66 returns to the compat branch;
build 65 and the extra passive boundary probes remain on the diagnostic branch.
No main update, release, tag or workflow dispatch is involved.
