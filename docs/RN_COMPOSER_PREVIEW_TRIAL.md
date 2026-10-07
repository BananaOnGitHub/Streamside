# Twitch 31.5 text-box previews — builds 61–64

Build 60 is device-confirmed for incoming and own sent-message emote display.
Build 61 preserves both paths and enriches only the composer presentation map.
No catalog/picker integration or send rewriting is introduced.
The build 61 device trial recognizes a provider token but leaves its gray image
placeholder visible. Build 62 adds the missing URL image transport redirect.
The user confirms images render, but with square proportions and no animation.
Build 63 addresses those two native presentation limitations.

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

## Build 63 native presentation

The donor attachment's bounds callback at 0x4274 returns equal width and height.
Its `UIImage.decoded()` implementation at 0x44d8 draws into a static renderer,
flattening the downloaded animation before attachment assignment. These are
separate from the working RN chat image renderer.

Provider-only bounds use the original height and baseline with catalog aspect
ratio. Identity comes from the exact attachment class's `url` Swift String,
bridged through the donor-imported Foundation function (native call at 0x4734).
Runtime ivar spacing, instance bounds, method encodings, synthetic URL and known
registry ID are checked; native/unknown attachments keep original geometry.

The existing mapped URL completion keeps its original task and payload and
also retains validated GIF bytes in a bounded in-memory cache (128 entries,
8 MiB). GIF preflight limits encoded data to 2 MiB, canvas to 524288 pixels,
and frames to 2–300. Each visible provider attachment uses an independent
donor `FLAnimatedImage` decoder with four lazily cached frames. Estimated
decoder/frame/encoded working sets are limited to 16 MiB per editor, with at
most eight tracked editors and 128 attachments each.

A 30 FPS display link updates only attachment images and invalidates display
ranges. It never replaces text storage, selection, marked text, delegates or
send callbacks. Original native layout/change/selection/window/value callbacks
run first. Existing playheads survive layout and reordering; deleted ranges
are checked again at tick time. Hidden/background editors stop and foreground
retries resume without time catch-up. Owner deallocation invalidates the link
and releases decoders. Keyboard composition suspends frame changes. GIF timing,
including long final-frame holds, is preserved; previews loop independently.
Non-GIF bodies keep native decoding and still-image fallback, including animated
WebP if a provider supplies it. No donor framework or JS asset changes on disk.

Build 63 adds four ASAN/UBSAN host tests covering production geometry and
Swift-bridge admission, bounded GIF parsing, independent clocks, timing, IME,
reorder/deletion, window/foreground transitions and deallocation, plus hook ABI
refusal/idempotence. These tests do not establish actual iOS TextKit rendering
or on-device GIF decoding. New sanitized `RN native input previews` counters
report hook/bridge state, proportional sizes, GIF bodies, decoders and advances.

## Build 63 device check

Fully relaunch build 63. Type a known square provider code followed by a space,
then move the caret out of the word or blur if Twitch keeps the active word as
text. Compare a native code, a wide code and an animated code. Verify editing,
backspace, Unicode around a code, and sending preserve literal text and the
working local chat display. Change channel and check room-only codes do not
leak. Inspect RN composer preview counters in the post-test report. Native
input controls when it commits a token. Check width and GIF playback, repeated
instances, deletion, keyboard composition and background/foreground resume.
Inspect the native preview hook/bridge and bounds/sizes/GIF/decoder/advance
counters, plus Image URL completion counters if the placeholder persists.

## Build 64 first-download startup

The user confirms build 63 proportional widths. Animated emotes stay static
on their first load, then animate after deletion and retyping. Its report shows
all native preview hooks and String bridge available, 10 GIF bodies, 11
decoders, 345 ticks, 265 frame advances and zero refusals. Aggregate counters
confirm playback occurred, but cannot identify individual first-load failures.

Production code tracked owners only after a decoder was created. A cold
attachment had no cached GIF bytes, so it created no decoder and was absent
from the weak owner registry. Download completion cached the bytes and scanned
that registry, missing the waiting input. Retyping found the cached bytes and
created a clock. A new production-code regression reproduces this missing
registration before the fix.

Build 64 registers a visible input when a known provider attachment is found,
before requiring cached image bytes. The same bounded weak set (eight owners)
now includes pending inputs; it does not retain them or allocate idle clocks.
Data arrival rescans the current attributed text and creates playback on the
original attachment. Deleted tokens are not rebound, and repeated syncs do not
duplicate owner entries. No extra request, text edit, send change, width change
or decoder/timing change is introduced.

The new ASAN/UBSAN regression covers a token present before its first download,
completion-triggered startup without another edit, a subsequent native still
image assignment, and deletion before completion. The full suite has 80 tests.
On device, fully relaunch build 64 and type an animated provider code that has
not yet been used in the input. It should begin playing after its image loads,
without deletion or retyping. Existing GIF/native/width checks still apply.

```sh
ZIG=/path/to/zig EMOTE_DIAGNOSTIC=0 make verify test
PYTHONPATH=/path/to/hermes-dec ZIG=/path/to/zig \
  python3 tools/verify_rn_width.py /path/to/twitch-31.5.ipa \
  --local --composer --hermesc /path/to/hermes-98/hermesc
```
