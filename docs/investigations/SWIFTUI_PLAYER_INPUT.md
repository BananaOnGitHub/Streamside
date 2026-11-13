# Native player input correction

## Device failure and scope

The player-controls source `f7366b217e82955e1cbeb9aabcc3d2fe894f1b51`, recorded by `ba48755894be12e1141ae2830d2b69963d103cb3`, played media but failed its device control check: Close, Pause/Play and Share did not respond reliably, and mute did not change its icon during normal video. Settings consistently opened its popover; mute appeared to work during ads. This does not establish an ad-specific audio defect. No post-failure device report is available for this correction.

Unchanged mute icon and multiple unrelated failed actions point to input delivery. Earlier playback fixtures called setters directly and therefore did not validate touches on the SwiftUI overlay. The existing successful playback evidence and earlier artifact hashes retain their original scope; they do not establish working controls.

## Implementation

[PlayerCanvas](../../native/swift/PlayerCanvas.swift) constrains the media surface to a 16:9 display-only UIKit container. UIKit interaction is disabled on that container, including its renderer descendants; SwiftUI hit testing is disabled on the representable. The reveal/hide gesture occupies a separate sibling behind the controls instead of an ancestor of the overlay. Each control has an explicit 44-point hit region. Interactive glass applies to the entire button, inside a shared glass container on iOS 26; plain buttons retain the same hit regions.

The existing native login ownership, player lifecycle, playback authorization, runtime guards and disabled feature boundaries remain unchanged. This correction does not alter device volume or ad handling.

Bounded, content-free diagnostic additions:

- `player_control_events`: seven counters in order: video visibility toggle, close, pause/play, mute, share, settings, copy link. A counter advances when the action closure executes; it is not proof of a successful media operation.
- `player_mute_state`: `[known, requested, reported]`, sampled from the native IVS player. Unknown means no current player, rather than successful unmuting.
- `player_mute_mismatched_samples`: cumulative samples where the known SDK getter differs from the requested state. It is a sample count, not a count of distinct failures.

The exact Twitch 32.0 donor remains SHA-256 `076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`. Its `IVSPlayer.muted` getter is admitted with Objective-C encoding `B16@0:8`, address `0x619f0` and inspected instruction prefix in the donor contract. Both getter and existing setter forward to the native internal player. Runtime ABI validation also requires that getter before calls. There are now 13 admitted Objective-C methods; Swift ABI targets and all 25 runtime probes are unchanged. Getter agreement alone cannot prove audible muting.

## Validation design

Linux host suite: 64 tests passed after the changes, including counter bounds, mute readback and strict component receipt admission.

New donor-free XCUITest fixtures compile the production canvas, controls, popovers, share actions and visibility model. Coordinate taps within the padded hit region check repeated mute/pause label changes, copy-link and system share, settings, auto-hide/reveal and close with glass both enabled and disabled. A hostile synthetic renderer changes intrinsic dimensions and fails if it receives a touch. The real UIKit/SwiftUI test therefore covers input routing while the existing playback fixture covers native service calls. Neither substitutes for donor playback or audible device validation.

The macOS workflow runs these tests once per component build, reusing its simulator. Its job limit increases from 15 to 25 minutes to include the additional Xcode build and UI test launch. Generated projects and derived data remain outside the checkout. A component without a successful two-style coordinate-test receipt is rejected by local packaging.

Apple CI, final packaging identities and physical-device results will be appended separately. The current change is not yet device-confirmed. Required phone check: open a live stream, use Close/Pause/Mute/Share during normal video and an available ad segment, check both glass settings, then export Native diagnostics. Verify audible stream-only mute, navigation/teardown, and unchanged RN/Hermes/worklet counters.

## Initial Apple run failure

[Run 43384386580](https://github.com/BananaOnGitHub/Streamside/actions/runs/43384386580), source `7a14eafe442000437ad6b252dae30082e3e20ae2`, compiled both components and the XCUITest fixture, then failed when `test-without-building` exceeded the worker's 240-second command limit. It did not establish passing UI tests and produced no admitted components or IPA. The original timeout path discarded partial subprocess stdout; that limits diagnosis and must not be interpreted as zero observed activity. The [failure record](SWIFTUI_PLAYER_INPUT_CI_FAILURE.json) preserves exact log hashes; full generated logs remain outside the active source tree.

The follow-up retains partial command output on timeout and gives the two actual UI tests a bounded 600-second command allowance. The same assertions remain required; timeout, failure or missing test observations still reject packaging. The overall job limit remains 25 minutes.

## System share triage

[Run 43386513540](https://github.com/BananaOnGitHub/Streamside/actions/runs/43386513540), source `314c6cbe5f9cb1209fbaf1e862bf06a9ee77acb6`, finished both UI tests with assertion failures rather than timing out. Both styles passed three repeated mute/unmute, pause/resume, Share-popover and copy-link cycles across synthetic renderer changes. Both failed because the test could not find the system activity's `Copy` button after tapping Share Link. This observation does not yet distinguish a changed system label from presentation/input failure. Later settings, visibility and Close checks were not reached. No IPA was packaged. The [retained failure record](SWIFTUI_PLAYER_INPUT_SHARE_FAILURE.json) identifies the logs.

The next triage preserves the synthetic UI accessibility hierarchy at failure and compares a center tap solely for diagnosis; a retry cannot pass the failed initial edge-tap assertion. Native component validation now runs before the independent control component, shortening feedback for native failures while keeping both components and their admission rules required.

## Share test selector correction

[Run 43388153616](https://github.com/BananaOnGitHub/Streamside/actions/runs/43388153616), source `9dd59482a530ba63ba6e186bc5b31f7c96e7308c`, captured both edge-tap accessibility hierarchies. Both contain `ShareSheet.RemoteContainerView` and an `actionGroupCell` labeled `Copy`: Share Link had presented the system share sheet successfully. The test's `app.buttons["Copy"]` query was wrong for the pinned iOS 26 simulator. The diagnostic center tap dismissed the sheet, and did not count as a pass. The [triage record](SWIFTUI_PLAYER_INPUT_SHARE_TRIAGE.json) preserves the exact logs and outcome.

The corrected query selects the observed Copy cell, requires it to be hittable, invokes the real action and requires the sheet to dismiss. It also clears the clipboard before system sharing and verifies that the action copies the exact synthetic public channel URL. No production share implementation changes were needed for this selector correction. All later settings, visibility and Close assertions remain required.

## Popover dismissal precondition

[Run 43389961724](https://github.com/BananaOnGitHub/Streamside/actions/runs/43389961724), source `0715cf6117d2ba684ffa4ba5118520b1fdec0df2`, exercised real system Copy, observed activity dismissal, verified the public channel URL and opened Settings in both styles. It then failed auto-hide. XCTest logged a computed hit point of `{-1,-1}` when the fixture tried to dismiss its popover by tapping the obscured underlying Harness label. It did not verify that the next tap actually switched off the fixture's explicit hold. That sequence does not establish a production visibility-model defect. Close/reveal remained unvalidated and no IPA was admitted. The [failure record](SWIFTUI_PLAYER_INPUT_POPOVER_FAILURE.json) preserves the logs.

The fixture now taps a real coordinate in empty space below the player, requires the popover content to disappear and checks that the hold switch changes from 1 to 0 before the same seven-second auto-hide check. The test retains every control assertion and emits its synthetic UI hierarchy on any later failure.

## Explicit fixture switch hit target

[Run 43392132610](https://github.com/BananaOnGitHub/Streamside/actions/runs/43392132610), source `3bb9dd263dcf310cfcdffad8a877ed105ce60901`, dismissed both popovers and verified system Copy in both styles. It failed the newly explicit hold-off precondition. The retained hierarchy shows the merged switch row spans x=0...402, while its interactive child occupies x=341...404. The automatic center tap missed that thumb; both values stayed 1. This narrows the earlier auto-hide failure to a fixture that had never released its hold. The [failure record](SWIFTUI_PLAYER_INPUT_HOLD_FAILURE.json) preserves that observation.

The test now taps the actual trailing switch thumb by coordinate. It still requires value 0 before the unchanged seven-second auto-hide limit, value 1 after reveal, and successful Close. Production controls and the visibility model are unchanged by this fixture correction.

## Confirmed visibility failure with released hold

[Run 43394297510](https://github.com/BananaOnGitHub/Streamside/actions/runs/43394297510), source `9b4b9c3dbd528abc5ebea620b15dc1b2a0a3d1cd`, passed the hold-off precondition with value 0 in both styles, dismissed menu contents, and still failed auto-hide. The hierarchy contains controls and no presented menu. This later evidence cannot be explained by the earlier invalid switch tap. No Close/reveal pass or IPA was admitted. The [failure record](SWIFTUI_PLAYER_INPUT_VISIBILITY_FAILURE.json) preserves the logs.

The synthetic fixture now exposes its loop tick count, hold flag, presentation callback flag and visibility state to failure snapshots. This distinguishes loop cancellation from stale presentation state before a production correction is selected. No device content or credentials enter that status.
