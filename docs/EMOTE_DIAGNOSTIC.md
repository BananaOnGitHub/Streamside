# Temporary missing-emote diagnostics (builds 39–45)

Build with `EMOTE_DIAGNOSTIC=1 ZIG=/path/to/zig make verify test` and use the
normal IPA patching/verification tools. The switch defaults to `0`. Probe code,
retained state and the Inspect Emote settings row are absent from normal builds.
Build 39 only observes the matching/rendering path. Build 40 also separates image
and HLS transport queues, and observes canceled requests and URL-less failures.
Build 41 retains channel identifiers until catalog requests finish, fixing the
expired-string callback crash while preserving build 40's transport separation.
Build 42 adds read-only native playback observations for the selected code.
Build 43 records recent provider playback before a code is selected.
Build 44 also retains request mapping, transport outcomes and native assignment
inputs/results before selection, corrects child roles and exposes tracking gaps.
Build 45 observes GIF/UIImage decode results, weak result identities, and native
chat handoff branches. The uncommitted build 45 source was lost in a workspace
restore; this implementation reconstructs that diagnostic stage from its retained
design and tested IPA/report. It is not a byte-identical source recovery.

## Build 45 provenance

Read-only hooks forward the original decoder once and return its unchanged
result. GIF initialization, UIImage data initialization (including scale), and
the cached GIF poster getter are observed. Private full-body fingerprints match
response bytes to decodes; neither fingerprint nor bytes are exported or retained.
The budget is 256 weak result identities, 256 attempts and 64 response keys with
32 numeric emote IDs each. All expire after 600 monotonic seconds; inputs over
8 MiB are not fingerprinted. Separate 16-row decode and handoff rings survive
layer cleanup traffic. Normal builds compile out every provenance hook.

`mode=0` selects the donor's animated child; `wants-animation` reads image-data
intent and `animated-url` only records URL presence. Native static/animated and
async-task result branches are labeled only after checking the donor Mach-O UUID
and exact setter return offset. Other callers remain `unknown`.

`source=observed-object` establishes a weak identity match to an observed decode.
`reuse=reused` means another observed assignment of that same live result, not a
proven cache hit. A preceding GIF attempt matched to a still image's response
body is context, not proof that the GIF object was flattened. Unknown origins
include older cached objects, unobserved constructors, expired or evicted records.
The recorder never invokes lazy frame decoding or changes result selection.

## Device procedure

1. Visit the affected channel so its emote catalog can load.
2. After noticing a failure, open **Diagnostics → Inspect Emote**. Enter the exact
   failing or frozen code, including capitalization, and select **Start Trace**.
3. You do not need to predict which emote will break or reproduce it again.
   Selection filters retained playback; it does not clear or restart recording.
   Incoming-message and lookup stages still begin at selection, so additional
   chat/composer activity can add that evidence if needed.
4. Copy **Diagnostic Report → Copy Diagnostic Report** and include a screenshot
   of the missing or frozen emote. The normal Diagnostic Logging toggle is not
   required for the memory trace. Existing fetch/image counters remain included.

Selecting a new code resets only its matching/rendering trace (48 observations
plus stage totals), not the playback recorder. Relaunching clears both. Only the
explicitly entered code is printed. Playback stores numeric synthetic IDs and
copied state, not chat, senders, channel identifiers, asset URLs or object addresses.

The recorder reads up to 64 weakly held provider image layers once a second
while any are tracked, independently of the recovery timer. Empty weak tables
stop its timer; the next provider layout/assignment restarts it. History is capped
at 32 emote IDs, each with 16 visible samples, 16 transitions, four last-visible
layer snapshots, 16 image-loading events, 16 assignments and four last-progress
layer snapshots. Entries expire after 600 monotonic seconds; capacity pressure
can evict them sooner. Nothing promises ten minutes of uninterrupted samples.
Reports include at most four matching IDs, oldest-first within each sample/event
ring, with last-visible snapshots separately labeled. `age` gives observation age.
No chat row, decoded animation or image is kept alive for history. Chat pruning
therefore cannot delete a retained snapshot. Expired/evicted history cannot be
recovered, nor can an ID be matched to a newly entered code after its catalog
mapping has disappeared (an already-selected retired ID remains matchable).

At capacity a newly visible layer can replace a hidden/offscreen observer;
`tracking-evicted` reports this with `weak-layer=live`. A denied admission reports
`tracking-limited`, `layer=untracked` and `reason=capacity`. Such a layer does not
receive an ordinal or cumulative counters; its setter input/results are still
copied with `layer=0 tracking=untracked`. Only an admitted layer disappearing
from the weak set produces `layer-released weak-layer=gone`. No event establishes
that the owning chat row was deallocated. Global denial/eviction counts count
events, not unique layers. Timer state, live count, poll count and last-poll age
make missing periodic observation explicit.

## Reading the report

| Observation | What it establishes |
| --- | --- |
| Exact catalog hit channel/global | The selected code exists in the currently observed scope. |
| Case variants, other cached rooms, loaded/pending/failures | Case mismatch, scope mismatch, or incomplete provider loading can be distinguished. |
| incoming catalog-miss / native-overlap / tag-capacity | Why Streamside left an incoming code unchanged. |
| incoming-gate | The selected code arrived in an IRC body, but its tags or room identity failed the existing parsing gate. |
| incoming tag-appended | A synthetic emote tag was actually added to the IRC line. |
| native-delivery emote-token / literal-text-token | The native delivery callback saw the selected code as an emote or ordinary text, where this callback is used. |
| named-lookup, local-match, composer | Exact lookup, own-message matching and composer preview decisions. |
| image-request-mapped, image-response | Target request mapping and observed HTTP/error/byte/image type result. |
| image-protocol-start / image-protocol-cancel | The selected asset reached transport, or its client canceled before transport completion. Cancellation can be normal when a chat row leaves the screen. |
| chat-token-sizing, chat-image-layer-frame/layout | Native chat created/accessed the emote token and its image layer. |
| chat-animation-decoded, chat-layer-has-image | The native animation setter received a decoded object, or the static attachment layer had image contents. |

Playback rows include elapsed monotonic seconds (`t`), a layer ordinal, native
refresh-hook availability, cumulative refresh `ticks` and frame `advances`, the
current frame `index` and total `frames`, animation/current-frame/child-layer
`contents` presence, display-link state, `shouldAnimate`/`needsDisplayUpdate`
flags (`should`/`dirty`, -1 means unavailable), `loops`, visibility and the existing
recovery gate. `gate=resume-eligible` reports the existing condition; sampling
does not invoke recovery. `gate=no-link` exposes the missing-link case.

Increasing ticks without advances identifies callbacks without an observed frame
change; it does not by itself prove a decoder failure (consider frame count and
delays). Flat ticks with a visible running link suggests a clock/callback issue,
provided `refresh=hooked`. Comparing cumulative advances avoids mistaking a
complete animation loop between samples for a freeze. Check successive rows
for the same layer ordinal; counters and ordinals survive animation clearing or
replacement, and selection never resets them. `role=animated` or `role=static`
comes from comparing the object to the attachment's actual child fields;
`role=unknown` means neither field identifies it. A detached admitted layer keeps
its last known role. Both `animated-child` and `static-child` report each child's
visibility where available,
not an unverified interpretation of Twitch's private display-mode enum. An invisible
animated child is not proof that the whole emote is invisible or broken.
Transitions include animation assignment/clearing, static-image replacement,
stopping, removal, tracking eviction/denial and genuine weak-layer release. Identical hidden polls add no rows;
cleanup events cannot overwrite the separate last-visible snapshots. Flat clock
counts are evidence to interpret, not an automatic declaration of a freeze.
For a visible multi-frame image with a running link, three seconds without an
observed advance records `no-refresh-3s` or `no-frame-change-3s`, together with
`last-frame-progress` if available in its own retained category. This category
keeps the latest observed visible advance for up to four layers even after a
static assignment or lifecycle traffic. Long intentional frame holds can trigger this
too. These events are diagnostic only and do not resume playback. A copied
progress snapshot's `t` and `age` describe the observation when progress was
recorded, not when a later quiet-clock event was generated.
Sampling never calls the lazy
frame decoder, resets the playhead, creates a display link or resumes playback.

An absent image request does not itself prove a failure: Twitch can use its
existing decoded/disk cache. Image history retains mapped synthetic request kind
(static/animated/default/unknown), provider format (GIF/WebP/PNG/other), transport
start/cancellation and HTTP/error/byte/MIME classification. Active and retained
catalog identities are resolved without retaining URLs in history. Assignment
history keeps before/after role, visibility, input presence/frame count and
resident animation/frame/contents facts separately, so repeated static setters
cannot erase transport evidence. A nonnil native animation input establishes
that a decoded object reached the setter; a missing input/request does not prove
a decoding failure. This probe does not intercept cache hits or decoder internals
and never calls a frame-at-index method. Build 40 attributes protocol results using the
original request, including errors with no response URL. A layer-layout event establishes layout, not a successful
paint on the device. No selected-code event is also useful when compared with
the existing WebSocket/native-delivery counters and the screenshot: the affected
message may have taken another path, such as history, or never passed these hooks.
