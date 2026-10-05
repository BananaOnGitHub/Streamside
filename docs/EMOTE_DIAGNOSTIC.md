# Temporary missing-emote diagnostics (builds 39–43)

Build with `EMOTE_DIAGNOSTIC=1 ZIG=/path/to/zig make verify test` and use the
normal IPA patching/verification tools. The switch defaults to `0`. Probe code,
retained state and the Inspect Emote settings row are absent from normal builds.
Build 39 only observes the matching/rendering path. Build 40 also separates image
and HLS transport queues, and observes canceled requests and URL-less failures.
Build 41 retains channel identifiers until catalog requests finish, fixing the
expired-string callback crash while preserving build 40's transport separation.
Build 42 adds read-only native playback observations for the selected code.
Build 43 records recent provider playback before a code is selected.

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

The recorder reads up to 64 weakly held provider animation layers once a second
while any are tracked, independently of the recovery timer. Empty weak tables
stop its timer; the next provider layout/assignment restarts it. History is capped
at 32 emote IDs, each with 16 visible samples, 16 transitions and four last-visible
layer snapshots. Entries expire after 600 monotonic seconds; capacity pressure
can evict them sooner. Nothing promises ten minutes of uninterrupted samples.
Reports include at most four matching IDs, oldest-first within each sample/event
ring, with last-visible snapshots separately labeled. `age` gives observation age.
No chat row, decoded animation or image is kept alive for history. Chat pruning
therefore cannot delete a retained snapshot. Expired/evicted history cannot be
recovered, nor can an ID be matched to a newly entered code after its catalog
mapping has disappeared (an already-selected retired ID remains matchable).

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
replacement, and selection never resets them. `role=animated` identifies the
observed child; `static-child` reports a static sibling's visibility where available,
not an unverified interpretation of Twitch's private display-mode enum. An invisible
animated child is not proof that the whole emote is invisible or broken.
Transitions include animation assignment/clearing, static-image replacement,
stopping, removal, and weak row release. Identical hidden polls add no rows;
cleanup events cannot overwrite the separate last-visible snapshots. Flat clock
counts are evidence to interpret, not an automatic declaration of a freeze.
For a visible multi-frame image with a running link, three seconds without an
observed advance records `no-refresh-3s` or `no-frame-change-3s`, together with
`last-frame-progress` if available. Long intentional frame holds can trigger this
too. These events are diagnostic only and do not resume playback. A copied
progress snapshot's `t` is its original observation time; its `age` is the time
since that snapshot was added to the transition ring.
Sampling never calls the lazy
frame decoder, resets the playhead, creates a display link or resumes playback.

An absent image request does not itself prove a failure: Twitch can use its
existing decoded/disk cache. Build 40 attributes protocol results using the
original request, including errors with no response URL. A layer-layout event establishes layout, not a successful
paint on the device. No selected-code event is also useful when compared with
the existing WebSocket/native-delivery counters and the screenshot: the affected
message may have taken another path, such as history, or never passed these hooks.
