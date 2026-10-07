# Twitch 31.5 text-box previews — builds 61–62

Build 60 is device-confirmed for incoming and own sent-message emote display.
Build 61 preserves both paths and enriches only the composer presentation map.
No catalog/picker integration or send rewriting is introduced.
The build 61 device trial recognizes a provider token but leaves its gray image
placeholder visible. Build 62 adds the missing URL image transport redirect.

## Exact active seam

The original Hermes-98 function 22083 is a channel-scoped composer component.
At offset 0xa7, its straight-line prefix has loaded draft (r49), channelID
(r75), and native emoteMap (r47). The input's lower wrapper, function 19088,
passes emoteMap and Twitch's existing emoteUrlTemplate to NativeEmoteInputView.
Its native component is TwitchEmoteInputView, supplied by the donor's
twitch_rn_emote_input framework. The native map type is [String:String].
The native framework supplies tokenization, plain-text reconstruction, marked
text/caret protection, selection conversion, deletion and image loading.
No original native framework, embedded JS asset or draft/selection callback
is modified on disk.

The injected synchronous call resolves the already working separate
buildLocalEcho module via NativeModules (Metro module 16), then calls its new
emoteMap export with draft, explicit channelID, and native map. A successful
result replaces only the local r47 presentation value. The input props and TMI
session/catalog maps are never mutated. Its frame stays 97, preserving the
original implicit CallBuiltin staging. The injection's outgoing Call4 slots
r86..96 cannot overwrite any live locals. Missing module, refused input or any
preview lookup/call exception leaves the original map intact; r2's undefined
value is restored on both joins.

## Snapshot rules

- Require one uniquely known room matching the explicit channel identity;
  never use the latest background room, even for global matches.
- Limit draft to 8192 UTF-8 bytes, identities/codes to 96 bytes, native map to
  20000 entries, and added codes to 128. Embedded NUL bodies are refused.
- Match complete, whitespace-delimited, case-sensitive codes in the draft.
  Native entries win collisions; channel definitions win global duplicates.
  Do not turn substrings or punctuation-wrapped codes into input attachments.
- Copy the native map only after a provider match. Preserve its values and
  return nil when nothing changes. IDs use existing provider URL redirection;
  literal draft text remains the send payload.
- Report only aggregate composer preview calls/maps/entries/refusals/scope
  misses and patch state; no draft, identity, code, image URL or tokens are logged.

## Validation and device trial

The exact donor's native `TwitchEmoteInputView.fetchImage(for:)` calls
`NSURLSession.sharedSession.dataTaskWithURL:completionHandler:` (call at
0xb8e4), then resumes the original task. Its completion decodes the returned
data with `UIImage.initWithData:` (0xbb00). The existing provider redirects
covered request selectors, leaving this URL overload uncovered. Build 62
shares the same validated registry URL lookup with a new hook on owned
NSURLSession / __NSURLSessionLocal URL completion methods. It admits only
the expected object-return ABI, retries missing methods, and installs once.
Native/unknown IDs, other hosts, direct provider images, HLS and disabled emotes
pass through unchanged. A mapped task retains its original task and callback
payload; Foundation remains responsible for scheduling, resume and cancellation.
The wrapper captures Twitch's completion as a typed block so Foundation's
copy also copies that nested completion; a plain C id capture cannot ensure it.
Aggregate URL calls/mapped/completed/errors/empty counts distinguish lookup
and transport failures without recording URLs or draft text.

Production C snapshot/gate and emitted-bytecode harnesses run under ASAN/UBSAN.
All 75 tests pass for build 62, including deferred completion invocation after
the URL hook returns and compiler-generated nested-block copy/dispose helpers.
The exact donor validator checks every original instruction and all 254
original composer branch targets, unchanged frame/cache/number metadata,
exception containment, restored undefined and unchanged working patches.
Hermes-98's independent disassembler must recognize the native-map call and
new exception table. The fake host interpreter does not establish live input
behavior, image decode, proportions, animation or IME correctness.

Fully relaunch build 62. Type a known square provider code followed by a space,
then move the caret out of the word or blur if Twitch keeps the active word as
text. Compare a native code, a wide code and an animated code. Verify editing,
backspace, Unicode around a code, and sending preserve literal text and the
working local chat display. Change channel and check room-only codes do not
leak. Inspect RN composer preview counters in the post-test report. Native
input controls whether a preview animates and when it commits a token; this
trial does not add a separate animation layer. Inspect the new Image URL
completion hook and mapping/completion counters if the placeholder persists.

```sh
ZIG=/path/to/zig EMOTE_DIAGNOSTIC=0 make verify test
PYTHONPATH=/path/to/hermes-dec ZIG=/path/to/zig \
  python3 tools/verify_rn_width.py /path/to/twitch-31.5.ipa \
  --local --composer --hermesc /path/to/hermes-98/hermesc
```
