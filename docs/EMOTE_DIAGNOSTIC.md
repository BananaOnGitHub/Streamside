# Temporary missing-emote diagnostics (builds 39–42)

Build with `EMOTE_DIAGNOSTIC=1 ZIG=/path/to/zig make verify test` and use the
normal IPA patching/verification tools. The switch defaults to `0`. Probe code,
retained state and the Inspect Emote settings row are absent from normal builds.
Build 39 only observes the matching/rendering path. Build 40 also separates image
and HLS transport queues, and observes canceled requests and URL-less failures.
Build 41 retains channel identifiers until catalog requests finish, fixing the
expired-string callback crash while preserving build 40's transport separation.
Build 42 adds read-only native playback observations for the selected code.

## Device procedure

1. Visit the affected channel so its emote catalog can load.
2. In Streamside settings, open **Diagnostics → Inspect Emote**. Enter the exact
   failing or frozen code, including capitalization, and select **Start Trace**.
3. Return to that channel. Reproduce the problem with new chat messages. Type
   the code into the composer too, so its lookup is recorded. Historical messages
   already on screen may not revisit the incoming WebSocket path.
4. Copy **Diagnostic Report → Copy Diagnostic Report** and include a screenshot
   of the missing or frozen emote. The normal Diagnostic Logging toggle is not
   required for the memory trace. Existing fetch/image counters remain included.

Selecting a new code clears the previous target's trace. Relaunching clears it
too. Only the explicitly entered code is included; no surrounding message,
sender, channel identifier or URL is stored in the trace. There are 48 bounded
rendering observations plus stage totals; consecutive identical observations coalesce.
Build 42 also retains 32 independent playback samples. A main-thread observer
reads weakly held layers once a second for ten minutes after Start Trace, including
animations already cached before tracing. Select Start Trace again to renew the
window. Layer ordinals distinguish concurrent copies; they are reset on a new
trace. No object addresses are printed and no layer/image is retained.

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
for the same layer ordinal; resetting/replacing an animation assigns a new ordinal.
Static emotes can report `no-animation-layer`. Invisible/detached rows are still
sampled even when the recovery timer has stopped. Sampling never calls the lazy
frame decoder, resets the playhead, creates a display link or resumes playback.

An absent image request does not itself prove a failure: Twitch can use its
existing decoded/disk cache. Build 40 attributes protocol results using the
original request, including errors with no response URL. A layer-layout event establishes layout, not a successful
paint on the device. No selected-code event is also useful when compared with
the existing WebSocket/native-delivery counters and the screenshot: the affected
message may have taken another path, such as history, or never passed these hooks.
