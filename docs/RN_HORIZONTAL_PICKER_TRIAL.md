# Horizontal RN provider picker — build 67

This trial adds a provider-only horizontal suggestion strip, not a port or
expansion of Twitch's manual emote picker. Native Twitch emote codes keep their
existing catalog/lookup precedence. Incoming chat, sent-message rendering,
composer preview images/clocks, and the device-confirmed build 66 RN info card
retain their working implementations.

## Behavior

- One 60-point row above the composer, horizontally scrollable with 32-point
  proportional image previews and one-line names. No modal or tall provider tray.
- **Automatic:** suggestions after two characters in the current token. An
  explicit colon also opens the strip, including an empty `:` query.
- **Colon:** only colon-prefixed tokens open it.
- **Off:** no provider strip; input previews and chat rendering remain enabled.
- Reads `ss_composer_suggestion_mode()`, the exact preference written by the
  existing settings segmented control. A tiny config/revision snapshot refreshes
  every 250 ms only while the input is focused. Catalog search runs on query or
  revision changes; the timer stops on blur/unmount.
- Contains matching, case-insensitive display ordering, exact-case insertion,
  channel-over-global precedence, 64-row maximum, native-code overlap suppression.
- Tapping replaces only the current completion token (and its opening colon),
  preserves surrounding text, and sets the plain UTF-16 caret after the code.
  Adds a trailing space only when there is no existing whitespace. Drafts remain
  plain text; no synthetic IRC send, attachment send payload, or auto-submit.
- No completion inside words, URLs, mentions, noncollapsed selections, disabled
  send fields, or unknown rooms. Stale row/draft/channel/selection/catalog/mode
  snapshots and character-budget overflows are refused before insertion.

## Exact donor trace and integration

Twitch 31.5's `ChatComposerBar` factory 4869 exports function 22083. It supplies
the controlled draft, channel ID, onDraftChange, input focus, restrictions,
remaining character budget, and native emote map. A factory-local installer
wraps this component in a context provider and adds the strip as a sibling above
it. The original component remains a separate React tree with unchanged props.

Its `AutocompleteTextInput` is module 4619 / function 21415. This renders the
`EmoteTextInput` export through module 3758's live getter, function 19082, which
resolves module 3759. That module's original memoized component (19094) and
lower input wrapper (19088) preserve native event-count handling, ref forwarding,
selection, token maps, native input, font/layout styles, and callbacks. The owned
adapter around its export forwards every callback/ref and observes selection,
change, focus, and blur only when inside the composer context. Unscoped inputs
render the original component with their original props.

Native selection events contain `nativeEvent.selection`; text events become
plain strings before the adapter. To handle either iOS event ordering, text
changes use Twitch's existing `caretFromEdit` export (function 21414). Later
selection events override that estimate. Until a draft snapshot agrees with
the native text, rows cannot insert into it. No composer-text logging is added.

The `buildLocalEcho` native module gains synchronous `getState()` and
`search(channel, query)` exports. Search requires the admitted strip patch,
enabled emotes, mode not Off, a unique explicit room, and bounded strings. It
returns immutable metadata from the existing provider registry. Config contains
only mode, enabled, and catalog revision. Diagnostic counters are aggregate
search/returned-entry/refusal counts, not queries, IDs, URLs, or text.

The owned JS uses verified React CommonJS module 72, RN 5, UI/theme 2118,
NativeModules 16, input 3759, and caret helper 4619. It is compiled with the exact
Hermes-98 compiler, remapped only into existing donor strings, and appended as
new function slots after the info-card graft. No donor function slot is reused.
The 22-register factory retains its frame and every original body byte around
the insertion. Outgoing Call2 staging is above all live low registers. A catch
handler retains the original export if installation throws. Wrong input size,
function count, target header, or digest leaves the preceding working bundle.
The disk bundle is not edited.

## Verification and device checks

Behavior mocks cover all modes, live settings, initial typing/event ordering,
selection/caret/ref forwarding, wide animated asset URLs, native overlap,
Unicode mid-draft insertion, character budgets, stale taps, blur, and unscoped
fallback. Production C fixtures cover bridge registration, metadata, scopes,
mode gates, malformed/oversized strings, disabled preference, and privacy shape.

Exact-donor verification:

```sh
PYTHONPATH=/path/to/hermes-dec ZIG=/path/to/zig \
python3 tools/verify_rn_popup.py /path/to/tv.twitch-31.5.ipa \
  --hermesc /path/to/hermes98/hermesc --strip
```

Checks compiler regeneration, all pre-existing functions/handlers/debug data,
module getter bindings, all imported closure and branch targets, fail-closed
cases, original constants, and independent Hermes-98 disassembly. These checks
do not prove device execution or visual/animated behavior.

Fully close Twitch after installing build 67. In Automatic, type two letters
of a known provider code; scroll and tap it. In Colon, test `:` and `:partial`,
then ordinary text. In Off, verify the strip disappears but previews still work.
Also test a wide/animated result, mid-draft insertion, channel switching,
keyboard dismissal/reopening, and sending the resulting ordinary text. If the
strip never appears, the report's `RN horizontal picker patch` and aggregate
search counters distinguish admission from bridge execution.
