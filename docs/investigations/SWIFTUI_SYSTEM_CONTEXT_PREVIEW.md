# System context preview trial

2026-11-16. Branch: `feat/native-frontend`. Starting revision:
`b5a197600ed212d5ce7df78fcf7b3ed513951227`. The implementation revision is the
commit introducing this record; the build dispatcher and compiler receipts bind
submitted builds to its full Git revision and transferred-input hashes.

This trial replaces the owned Quick Look modal with a genuine UIKit context
preview. It is an implementation candidate, **not an Apple or device acceptance
result**. Apple compilation and simulator execution are pending at submission.
The prior [styling results](SWIFTUI_QUICK_LOOK_STYLE.md) and their artifact hashes
continue to describe their original candidate, not this one.

## Apple mechanism evaluation

The following primary documentation was inspected before choosing the path:

| Mechanism | Finding and decision |
| --- | --- |
| [SwiftUI contextMenu(menuItems:preview:)](https://developer.apple.com/documentation/swiftui/view/contextmenu%28menuitems%3Apreview%3A%29) | Supplies a system preview and menu. Its public SwiftUI modifier does not expose UIKit's display/end animator and targeted-preview delegate callbacks. Those boundaries are needed to guard the existing UIKit media ownership transfer; use the UIKit interaction directly. |
| [UIContextMenuInteraction](https://developer.apple.com/documentation/uikit/adding-context-menus-in-your-app) | Accepts an owned preview-provider controller and real UIMenu actions. UIKit manages recognition, lift, placement, backdrop, menu styling and outside dismissal. Chosen prototype. |
| [UIContextMenuInteractionDelegate](https://developer.apple.com/documentation/uikit/uicontextmenuinteractiondelegate) and [current highlight delegate](https://developer.apple.com/documentation/uikit/uicontextmenuinteractiondelegate/contextmenuinteraction%28_%3Aconfiguration%3Ahighlightpreviewforitemwithidentifier%3A%29) | Current per-item highlight/dismissal methods are available from iOS 16, below the component's iOS 16.4 floor. Return UITargetedPreview for the actual thumbnail UIImageView, with a source-local UIPreviewParameters visible path. Do not use the deprecated single-configuration preview callbacks. |
| [Context-menu animator](https://developer.apple.com/documentation/uikit/uicontextmenuinteractionanimating) | Its completion callback orders removal of the system presentation before the guarded root presents the theatre. Preview commits use the system dismiss style. |
| [SwiftUI zoom navigation transition](https://developer.apple.com/documentation/swiftui/zoomnavigationtransition) | Available from iOS 18 and designed for navigation. It does not supply this context-menu lifecycle or separate native action menu, so it is not the preview presentation. |
| [SwiftUI glassEffect](https://developer.apple.com/documentation/swiftui/view/glasseffect%28_%3Ain%3A%29) | Applied only to the information area on iOS 26+, with regular material on older supported versions and an opaque Reduce Transparency fallback. The video has no glass/blur modifier. UIKit owns the action menu's system appearance. |

QLPreviewController is a document/file preview facility and is not used as a live
stream host. No private context-menu presentation API or donor hook was added.
Apple's APIs permit the proposed controller/ownership arrangement; documentation
alone does **not** establish that the system keeps IVS moving or allows the long
details area to scroll. Those are explicit prototype gates, not assumptions.

## Implementation boundaries

- `ThumbnailActions.swift` now hosts the actual cached thumbnail UIImageView,
  rather than a clear gesture overlay. Native context recognition and an ordinary
  tap recognizer coexist on that source. Timer artwork does not intercept touches.
  Current UIKit highlight/dismissal callbacks target that same view and its
  current window geometry, including after scrolling.
- `QuickLookController.swift` is a preview-provider controller. Streamside never
  presents it using `present`, a SwiftUI sheet, or a fullscreen preview overlay.
  UIKit provides shadows, lift/return animation, backdrop and outside dismissal.
  There is no X button or custom close control.
- `QuickLookPanel.swift` contains a 16:9 passive video surface and a bounded,
  scrollable information area. Full title, identity, category, all tags and the
  existing live ring remain. Continuous 24-point corners and a UIKit layer mask
  clip the actual media subtree; only the upper video corners are rounded.
  The mute symbol is a small passive badge in the video's bottom-right corner.
- The separate action menu is an actual UIMenu: **Watch stream** and disabled
  **View profile**. UIKit owns its size, placement and accessibility behavior.
  Tapping the preview also uses the native preview-commit delegate to Watch.
- `ContextPreviewSession.swift` owns one media transaction. Preparation sets mute
  intent before authorization/load. Display claims the guarded root and starts
  playback once. Watch only records intent. After UIKit's dismissal animator
  completes, one queued main-thread decision validates account/activity and
  transfers the existing TheatrePlayback to the existing theatre controller.
  The theatre cross-dissolves and unmutes only after its presentation completes.
  This is an ordered system dismissal followed by a theatre cross-dissolve,
  rather than the previous simultaneous fade between two owned controllers.
  Physical review must establish whether the resulting motion meets the target.
- Outside dismissal, source removal, inactive-app notification, account change,
  rejected ownership or a rejected handoff stop/release once. Cancellation wins
  over pending Watch. Deinitialization also releases an abandoned root claim.
  Once transferred, the theatre owns teardown and `startIfNeeded` preserves the
  running request/player. No extra preview request is made for Watch.
- Existing native authorization, IVS facade, audio intent, account/session/root
  guards and RN/Hermes probes remain. No Swift donor ABI, token path, unrelated
  player control, chat, PiP or profile implementation changed.

UIKit owns Reduce Motion behavior for its lift/menu animations; Streamside adds
no competing custom preview animation. The shared live ring and tag views retain
their existing accessibility behavior. OS-level Reduce Motion/Transparency,
VoiceOver and older supported iOS behavior still need device review.

## Focused validation and evidence

Host execution completed before submission:

- **74 native frontend Python/C/ARM64-emulation tests passed**, with the existing
  pinned Linux test toolchain. Two additional host tests bound public failure
  stills and verify their hashes; component admission also rejects missing
  system-preview, source-animation or decoded-video validation fields.
- The exact local donor was rehashed, unchanged: Twitch **32.0**, build
  **263110145453907615**, SHA-256
  `076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`.
  It is not an Apple build input. No donor packaging or device execution occurred.

The Apple path retains the mandatory arm64 SwiftUI/Objective-C compilation,
linking, ABI fixture, UIKit ownership, three-process launch selection, clock,
full-title/haptic, native playback/mute, model and component admission gates.
Existing glass/plain player-control, opacity-pixel and motion checks remain.
The pin is Xcode **26.6 (17F113)**, iPhoneOS SDK **26.5**, Swift language mode 5,
component deployment target **iOS 16.4**. The hosted compiler reports its actual
Swift compiler version; no compiler result is inferred from the pin.

New Apple checks are part of those mandatory gates:

1. The UIKit transaction executable checks start-once, completion-before-handoff,
   duplicate/late actions, failed claims/handoffs, cancellation during dismissal,
   background/account invalidation, wrapping of all tags and targeted geometry in
   a real scrolled source container.
2. The coordinate fixture opens the actual native context menu by long-pressing
   the production thumbnail bridge. Release must leave it open. Outside tap must
   dismiss toward the same source, preserve source geometry and stop once.
   A bounded display-link probe must observe intermediate presentation geometry
   or opacity in the actual UIKit tree. Tap and scroll must retain their distinct
   behavior; background and account-loss paths must cancel without Watch.
3. A small, locally encoded, alternating red/blue H.264 movie plays through a real
   AVPlayerLayer in the **production PassivePlayerSurface, QuickLookPanel and
   QuickLookController**. Actual screen pixels must change after finger release,
   remain 16:9, and exclude video color at both rounded upper corners. Static
   artwork or a player-ready callback cannot satisfy this gate.
4. Short/long details and all tags must remain reachable; the native menu is
   separate and compact, Profile disabled, X absent. Watch must reparent the same
   fixture video/player into theatre, continue decoding and tear down once.

This donor-free AVPlayerLayer test is a focused system-presentation prototype,
**not a substitute for IVS device validation**. If UIKit freezes video, blocks
required details interaction, or the source/gesture/handoff tests fail, the build
must fail. Preserve that result before considering an owned source-anchored
alternative; no speculative fallback is silently enabled.

Failure logs remain available. UI-test failure screenshots are exported from the
result bundle into a separate `player-input-failure.zip` (up to eight PNGs, 2 MiB
each, 16 MiB total, with hashes). Both hosted providers retain that bounded,
owned-fixture-only archive. Recordings, the complete result bundle, account data,
donor images, credentials and signing material are not exported. Admitted
components continue to require their complete exact receipts and input hashes.

## Pending acceptance

One quota-selected Apple build is submitted for this commit. No agent monitoring,
status polling, artifact download or IPA assembly follows submission. Until its
results are reviewed, Apple compilation, all new simulator checks and component
validation remain **pending**, even though host tests passed.

After Apple acceptance, package locally with the exact donor and retained Feather
signing path. On a physical iPhone, verify real IVS video clipping/advancement,
preview silence, lift/return motion, release-and-inspect, full details/tags,
outside dismissal, preview-tap and Watch handoffs, repeated cancellation,
background/foreground, account loss, tap/scroll and accessibility settings. Export
native diagnostics and confirm the existing RN/Hermes counters stay zero. The
previous runtime report is historical evidence and does not validate this change.

## First Apple build failure

The [first build](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afad00790e83b09c4faec35), source `5afb9f968a32ee5a739a0c8daff4f94f8d0ba493`, failed during iPhone Swift compilation with Xcode 26.6 / Swift 6.3.3. The compiler rejected access to the main-actor `phase` property inside the autoclosure created by `&&` in `ContextPreviewSession.deinit`. No simulator checks ran. The follow-up evaluates that state separately before the Boolean combination, preserving the same cleanup decision. The original provider log and downloaded failure archive remain associated with the failed revision. The archive SHA-256 is `5ced3a624028d6997bee4b6a83d77c87313be84edc42864a41e15f876e2cd6a0`.

## Second Apple build: simulator fixture findings

The [second build](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afad35590e83b09c4faed77), source `c94867e2824b9c419b9c36ea212d6f3560e9522c`, compiled the iPhone frontend and passed the source-target and media-transaction simulator executable. Both existing player-control UI tests passed. Two new UI tests failed. The native menu opened, release preserved it, and outside dismissal returned to the source and stopped once. UIKit exposed the preview and its contents under system accessibility labels rather than the identifiers used by the first fixture. Its separately managed presentation also produced no intermediate samples on the supplied controller layer. The failure screenshot shows a decoded video frame and the native menu; it does not establish that video advances or that IVS works.

The follow-up queries the actual observed system labels and checks scene presentation layers for an animated intermediate rectangle containing the source center. The video must still visibly change and remain clipped; the source animation, action, lifecycle and full-details gates remain required. The test timeout is extended to allow the unchanged lengthy control tests plus the added preview scenarios. The retained provider log archive SHA-256 is `6c0bb6ff7c8c9fdbbcb4c12ae9e66a38c8d353d372b74777add18336cd584419`; the bounded screenshot archive SHA-256 is `adffecb0ef26c62808453f4d77dffe6996572ca4e5a5fc9ebe4ea79179495d8e`.

## Third Apple build: native preview scrolling limitation

The [third build](https://codemagic.io/app/6af941a4db82100031adf1d4/build/6afad8c990e83b09c4faef78), source `13ecef3ffb853cd13308ca60e11ae6089e852ef2`, compiled the frontend and fixture. Both existing control tests and the thumbnail hold/tap/scroll, native source animation, outside dismissal and cancellation test passed. The short-details scenarios observed changing decoded video, clipped upper corners and a shared-player transfer through both the Watch action and preview tap.

The long-details scenario failed: eight upward drags within the system preview did not expose the final detail, and the accessibility hierarchy continued to show the long title extending beyond the preview bounds. Consequently, full title and tag access is not established for the system context-preview path. This focused prototype demonstrates a practical incompatibility with the required interactive details on the tested iOS 26.5 simulator; it does not establish behavior on a physical device or other OS versions. The correct next step is an owned, source-anchored interactive presentation with the same player-ownership and gesture checks, followed by a new Apple and device validation. Do not remove the long-details gate or treat the successful short preview as complete acceptance.

The retained log archive SHA-256 is `d67ee85954b8b3db7ba41b7ce9f0534e6885ef3722a460640adf8af3c4c98f70`; the screenshot archive SHA-256 is `d1707f60a59ad18b7947b07bbc362be88b16d5479160593521fdb3e719df28f0`. No new IPA was assembled for this failed candidate.
