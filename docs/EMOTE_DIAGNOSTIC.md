# Temporary missing-emote diagnostic build (39)

Build with `EMOTE_DIAGNOSTIC=1 ZIG=/path/to/zig make verify test` and use the
normal IPA patching/verification tools. The switch defaults to `0`. Probe code,
retained state and the Inspect Emote settings row are absent from normal builds.
This build observes the existing matching/rendering path; it does not fix it.

## Device procedure

1. Visit the affected channel so its emote catalog can load.
2. In Streamside settings, open **Diagnostics → Inspect Emote**. Enter the exact
   failing code, including capitalization, and select **Start Trace**.
3. Return to that channel. Reproduce the problem with new chat messages. Type
   the code into the composer too, so its lookup is recorded. Historical messages
   already on screen may not revisit the incoming WebSocket path.
4. Copy **Diagnostic Report → Copy Diagnostic Report** and include a screenshot
   of the code remaining text. The normal Diagnostic Logging toggle is not
   required for the memory trace. Existing fetch/image counters remain included.

Selecting a new code clears the previous target's trace. Relaunching clears it
too. Only the explicitly entered code is included; no surrounding message,
sender, channel identifier or URL is stored in the trace. There are 48 bounded
observations plus stage totals; consecutive identical observations coalesce.

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
| chat-token-sizing, chat-image-layer-frame/layout | Native chat created/accessed the emote token and its image layer. |
| chat-animation-decoded, chat-layer-has-image | The native animation setter received a decoded object, or the static attachment layer had image contents. |

An absent image request does not itself prove a failure: Twitch can use its
existing decoded/disk cache. Image responses without a URL cannot be attributed
to the selected code. A layer-layout event establishes layout, not a successful
paint on the device. No selected-code event is also useful when compared with
the existing WebSocket/native-delivery counters and the screenshot: the affected
message may have taken another path, such as history, or never passed these hooks.
