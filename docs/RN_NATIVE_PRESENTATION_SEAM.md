# Twitch 31.5: passive native presentation/layout seam

> Archived native-seam analysis on `archive/rn-chat-boundary`. Paragraph attachments were identified as reconstructed inline-child placeholders; no live per-emote mount/image identity join was collected. The original Zig blocker remains recorded. Later width implementation is maintained separately on compat. See [branch closure](BRANCH_ARCHIVE.md).

## Finding and stopping point

The paragraph's observed `NSTextAttachment` objects are **reconstructed inline
child placeholders**, not the native composer's `TwitchEmoteAttachment` objects
and not containers holding the decoded emote bitmap. Any non-text inline child
can produce this placeholder, including non-emote content.

The geometry seam is Fabric's **inline child shadow-node measurement → paragraph
text reservation/measurement → child subtree layout → mounted child view**.
Square and variable-width emotes need the reservation and mounted image subtree
to agree. Image decoding or changing a UIKit image frame alone does not update
the paragraph's reserved width, wrapping or line layout.

This is donor-static evidence, tied to the bundle seen in device reports, plus
interpretation of build-54 A–C. It is not a new live, per-emote correlation test.
No runtime source, catalog, paragraph attachment, request, image or layout was
changed. No synthetic ID or local-echo investigation was performed. Stop here
before implementing provider presentation or choosing a mutation hook.

## Evidence identity and reproduction

Donor IPA SHA256:
`718762b71095c11754b1f58ad01fb580852414e6d7f468fbb2236b7c2419e641`.
Build-54 reports consumed the same embedded Hermes-98 body as earlier reports:
27,786,480 bytes, FNV64 `3c748f1f3e33577c`. This ties the earlier JS analysis to
the observed source body, not proof that every static function executed.

`tools/inspect_rn_presentation.py` reads the donor's arm64 Mach-O function starts,
symbols and Objective-C metadata, then optionally disassembles with Capstone
(tested with 5.0.7). It never executes or modifies the donor. Example:

```sh
python3 tools/inspect_rn_presentation.py /path/to/React.framework/React \
  --class-name RCTParagraphComponentView --selector attributedText
python3 tools/inspect_rn_presentation.py /path/to/React.framework/React \
  --address 0x248c28
```

Addresses below are static virtual addresses in this exact React binary, not
portable runtime hooks or permission to read private storage by guessed offsets.
Annotations are conservative local aids, not a formal dataflow analysis.

## Objects, ownership and identities

| Object | Owner/lifetime | Relationship to native emote presentation |
|---|---|---|
| Fabric attributed-string attachment fragment | Paragraph C++ state/content | Records an inline child shadow view and measured layout metrics; not a decoded image |
| Returned paragraph attributed string | Getter result; ordinary retained/autoreleased lifetime | Fresh conversion on each read, not the persistent mounted view model |
| `NSTextAttachment` in that result | Returned attributed-string run | Fresh placeholder with shared placeholder image and fragment-derived bounds; pointer identity cannot join separate reads |
| Mounted inline child root | Native view hierarchy/Fabric mounting lifecycle | The image-bearing subtree must be found here; it may contain a wrapper before the image component |
| `RCTImageComponentView` | Mounted view hierarchy, potentially recycled | Strongly owns its image content view and shared observer proxy; image state/request changes over its lifetime |
| `RCTUIImageViewAnimated` | Image component's strong `_imageView`/`contentView` | Displays bitmap or animation; separate from the paragraph placeholder |
| Decoded image / animation container | Receive callback, image view and animation storage | Can be shared, transformed or replaced; image identity is not emote/message identity |
| Animation frames | Current-frame/frame-buffer storage | Frame identity can change while the animation container and mounted view remain the same |
| `TwitchEmoteAttachment` | Native composer attributed text | Separate UIKit composer path; observed in C, not in sampled transcript paragraphs |

### Why the paragraph attachment image is not the emote image

`-[RCTParagraphComponentView attributedText]` at `0x201a6c` obtains
`_textView.state` and calls `RCTNSAttributedStringFromAttributedString`
(`0x248c28`). The converter allocates a new attachment for each attachment
fragment, assigns the shared placeholder image and sets bounds from the
fragment's parent shadow-view layout frame. It does not attach the mounted view,
emote ID, CDN URL or decoded emote image to that object.

The placeholder image is created once (`0x2491c8`), rather than obtained from
an emote loader. The corresponding upstream converter uses an empty `[UIImage
new]`. The donor's attachment allocation and image-assignment return addresses
are `0x248cdc` and `0x248ce8`: exactly the first native caller offsets in the
build-54 Foundation hook rows.

The getter therefore creates observable allocations. Build 54 preserves app
state and original results, but its extra getter calls are **not allocation-free**.
Neither its generic allocation counter nor its attachment-run count measures
persistent emote objects. Matching a placeholder image to an image-loading
result by pointer would be the wrong correlation.

## Geometry and update behavior

`ParagraphShadowNode::getContentWithMeasuredAttachments` (`0x268414`) measures
each layoutable inline child and stores its size in the attachment fragment's
layout metrics. This donor adds a small epsilon and rounds sizes upward to the
pixel grid. The attributed-string conversion uses that geometry as the
attachment reservation in the text layout.

`ParagraphShadowNode::layout` (`0x268dc0`) measures text/attachments, clones the
relevant child subtree, applies the measured attachment placement, performs
child layout and sets child layout metrics. It includes a prepared-text-layout
feature-flag branch and handling of clipped attachments; the active flag value
was not measured. UIKit bounds alone do not describe these upstream branches.

The earlier embedded JS trace identifies Twitch's `EmotePart` wrapper **and**
image as 24×24 inline or 56×56 enlarged, with contain-mode presentation. Thus a
wide bitmap inside the unchanged square box remains square in text reservation.
A proportional implementation would need the inline root and image layout
sizes to propagate coherently through this Fabric measurement path. This is a
design constraint, not an implemented fix or verified native-only hook.

Paragraph `updateState:oldState:` (`0x201dc4`) replaces the text-view state and
requests display/layout. `updateLayoutMetrics:oldLayoutMetrics:` (`0x201e80`)
forwards metrics to the text view and requests display/layout. `layoutSubviews`
(`0x201fe0`) sets the text view's frame to the paragraph bounds; it does not
individually resize emote images. `RCTParagraphTextView drawRect:` (`0x20342c`)
uses the text layout manager to draw the attributed content. Paragraph recycling
(`0x201f28`) clears text state and the accessibility provider.

There is no paragraph-specific child-mount override in the donor method list.
Inherited `RCTViewComponentView mountChildComponentView:index:` (`0x215508`)
inserts the native child into the current container, or retains it in the
clipped-child collection. Therefore a raw `subviews` index is not universally
the attachment ordinal, and a child may not currently be visible/mounted.

## Image loading, ownership and animation

Image-component initialization (`0x1e7f48`) creates the animated image view,
stores it strongly, installs it as `contentView`, and creates an observer proxy.
The proxy (`0x229028`) holds a **weak** component delegate. Its image-response
path (`0x229058`) temporarily retains the delegate/image/metadata and schedules
delivery on the main queue. Queued delivery can extend their lifetime beyond
the original request callback.

`_setStateAndResubscribeImageResponseObserver:` (`0x1e87c4`) removes the old
request observer and subscribes to the new state's request. Recycling
(`0x1e892c`) unsubscribes and clears the displayed image. A component pointer
can subsequently represent different content. The inspected receive method
guards state/event-emitter availability but does not compare the supplied
observer pointer; do not assume it provides a request-generation identity check.

`didReceiveImage:metadata:fromObserver:` (`0x1e89dc`) ultimately assigns to the
owned image view (`setImage:` return address `0x1e8bc4`). Tint/cap-inset handling
can change the UIImage identity, and blur takes an asynchronous branch. Actual
image dimensions are reported to the load event; this is not a paragraph/Yoga
layout-width update. Direct pointer equality is useful only for an observed
unchanged-image path, not all image deliveries.

`RCTUIImageViewAnimated setImage:` (`0x2da0a4`) skips reassignment of the same
current image/container pointer. Otherwise it resets the old animation and
tests the `animatedImageFrameAtIndex:` capability and nonzero frame count—not
just the `TwitchAnimatedImage` class name. `setAnimatedImage:` (`0x2db3a4`)
strongly retains the container. Reset (`0x2d9fa8`) clears the container, current
frame and frame buffer and cancels queued frame fetching. Display refresh
(`0x2da8e8`) advances cached frames through the superclass image setter; the
subclass `setImage:` counter is not a frame counter.

## Build-54 A–C interpretation

| Measurement | A | B | C | Interpretation |
|---|---:|---:|---:|---|
| Observer paragraph getter reads | 0 | 282 | 404 | These reads themselves reconstruct placeholder attachments |
| Other paragraph attachment runs | 0 | 468 | 683 | Repeated inline-child reservations; not necessarily emotes or unique objects |
| Native-composer runs in sampled paragraphs | 0 | 0 | 0 | Transcript and composer representations remain separate |
| Global Foundation attachment init / image assignments | 0/0 | 938/938 | 2201/2202 | Includes conversion/observer activity; not decoded-emote allocations |
| Filtered native-composer base init / image assignments | 0/0 | 0/0 | 1/2 | Picker insertion reaches the native composer attachment path |
| Native-composer bounds with UIImage / square source | 0/0 | 0/0 | 6/6 | Repeated square observations; user confirmed the image appeared |
| Twitch-emote loader / HTTP request categories | 0/0 | 206/206 | 293/293 | Loading is active, but not joined to specific mounted children |

No paragraph sampling refusals occurred. The native catalog changed from the
earlier session's 951 to 1,073 entries, without a catalog modification by this
probe. General RN wide/animated counters cannot identify emotes.

## What a further passive correlation would need—and what is not proven

The structural join is the **mounted inline child root → bounded image-component
descendant → owned animated image view → received image/container**, within one
mount/update generation. Placeholder attachment identities are deliberately
excluded. A mount/recycle-aware observer could compare root/image geometry and
same-callback image identity without changing layout or retaining content.

However, build 54 did not collect that join. A chat-scoped image can be a badge
or other inline content. URL-category counts, matching dimensions, mount order
and animation-class counts alone do not prove native-emote provenance. Loading
and display also need not be one-to-one (reuse/caching/coalescing and transforms
are potential gaps, not measured explanations for these counts).

If live confirmation is later required, restrict it to bounded weak object
slots, mount/recycle generations, aggregate rectangle categories and transient
exact identity comparisons. Establish authentic Twitch-emote request/source
provenance separately, count ambiguous/unknown joins, and avoid retaining IDs,
URLs, text, raw pointers, attributes, image bytes or C++ state. Do not call the
paragraph getter merely to manufacture a stable-identity candidate. No such
runtime diagnostic or next test build was added in this investigation.

## Primary implementation references

The donor binary anchors above establish this app's behavior. Upstream files
are explanatory comparisons, not identification of Twitch's exact RN version:

- [RCTAttributedTextUtils.mm](https://github.com/facebook/react-native/blob/v0.79.5/packages/react-native/ReactCommon/react/renderer/textlayoutmanager/platform/ios/react/renderer/textlayoutmanager/RCTAttributedTextUtils.mm)
- [ParagraphShadowNode.cpp](https://github.com/facebook/react-native/blob/v0.79.5/packages/react-native/ReactCommon/react/renderer/components/text/ParagraphShadowNode.cpp)
- [RCTParagraphComponentView.mm](https://github.com/facebook/react-native/blob/v0.80.2/packages/react-native/React/Fabric/Mounting/ComponentViews/Text/RCTParagraphComponentView.mm)
- [RCTImageComponentView.mm](https://github.com/facebook/react-native/blob/v0.79.5/packages/react-native/React/Fabric/Mounting/ComponentViews/Image/RCTImageComponentView.mm)
- [RCTUIImageViewAnimated.mm](https://github.com/facebook/react-native/blob/v0.80.2/packages/react-native/Libraries/Image/RCTUIImageViewAnimated.mm)

## Validation of this investigation

The three new metadata/disassembly-tool tests passed, including independent
absolute/relative method-list fixtures, invalid-list refusal and code/function
bounds. Five existing packaging-tool tests passed; Python compilation and
`git diff --check` passed. Donor ABI verification still matches all 50 existing
donor-defined probe hooks (four Foundation hooks remain runtime-only).

The complete 64-test suite was attempted but could not be validated: the
restored Zig executable crashes even on `zig version`, before harness compilation.
This is a toolchain blocker, not a green full-suite result. No runtime sources,
build/version metadata or IPA were changed, and no new iOS build was attempted.
