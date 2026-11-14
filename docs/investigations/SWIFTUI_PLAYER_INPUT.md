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

The first status-fixture attempt, source `b5afdd2423f1d5bd855360292ad0ca2b5ae3f352` in [run 43396617137](https://github.com/BananaOnGitHub/Streamside/actions/runs/43396617137), did not execute UI tests: the pinned compiler rejects deprecated localized Boolean interpolation under warnings-as-errors. The status is now explicitly verbatim debug text. Compiler enforcement remains enabled; its log identity is appended to the visibility failure record.

## Hidden controls remain exposed in accessibility

[Run 43398221004](https://github.com/BananaOnGitHub/Streamside/actions/runs/43398221004), source `f58de1e7a2e5a3e6b2bca586df3e12216b89ea32`, resolved the visibility diagnosis. Glass reported `ticks=897 hold=false popup=false visible=false`; plain reported `ticks=823 hold=false popup=false visible=false`. The timer runs and the popup state clears. The overlay model is hidden, but the faded Group still exposes its buttons in the accessibility hierarchy. Earlier observations did not establish a timer defect; this later state rules out that explanation. The [triage record](SWIFTUI_PLAYER_INPUT_VISIBILITY_TRIAGE.json) preserves the logs.

[PlayerCanvas](../../native/swift/PlayerCanvas.swift) now conditionally mounts the controls subtree. The passive video surface and separate video gesture sibling stay mounted, so hiding does not recreate or stop media. NativeTheatre retains its short opacity transition, disabled with Reduce Motion. Both production and tests use this shared visibility boundary. Hidden controls must actually leave the hierarchy before the test can proceed to video-tap reveal and Close. No assertion or timeout was weakened. The temporary high-frequency fixture counter is removed after diagnosis; bounded state flags remain in failure snapshots. Switch transitions use the same bounded five-second value observation as button-state changes.

An optional x86_64 Mac VM was reachable with Xcode 26.6 (17F113) and Swift 6.3.3. It compiled the seven owned UI/test inputs but failed earlier share-dismissal/switch preconditions, so it provided no passing visibility result. Its log identity is included in the triage record. Only the focused debug inputs were transferred; donor, Git history and credentials stayed in Ubuntu. The owned simulator and temporary VM build tree were removed. Actions remains the required build and validation path.

## Validated build and package

Source `e151b5ff74d45ed3647aa014a1d074bc0d406981` passed [Apple compilation and simulator tests](https://github.com/BananaOnGitHub/Streamside/actions/runs/43400282708). Both owned component modes compiled and linked with the pinned Xcode 26.6 (17F113), Swift 6.3.3 and iPhoneOS SDK 26.5, targeting arm64 iOS 16.4. The native component's two coordinate UI tests passed with glass enabled and disabled. Existing model, UIKit ownership, clock/title, native playback lifecycle and three-process launch-selection fixtures also passed. Mute-readback checks passed against the synthetic native player; no actual donor audio was played in CI. Downstream ABI (17), admission (12), core (10), launch policy (1), probe emulation (6), launch comparison (3), report comparison (5) and Foundation HTTP (1) checks passed.

[Linux build](https://github.com/BananaOnGitHub/Streamside/actions/runs/43400282961) passed 220 of 224 tests with four explicit environment-dependent skips. The native host suite passed all 64 tests. Documentation checks passed. Exact source, proof, toolchain, validation receipts and artifact hashes are in the [build record](SWIFTUI_PLAYER_INPUT_ARTIFACTS.json).

Local packaging re-admitted the exact Twitch 32.0 donor, 51 Swift boundaries, 13 Objective-C methods and 25 runtime probes. The output archive and all retained donor entries were verified, including unchanged HBC/backend content. One Native IPA was created; proprietary donor bytes and signing material stayed outside public Actions. It requires Feather re-signing using the existing application/keychain identity. Physical-device validation remains pending.

Reproduce from this clean source revision, or a compatible documentation-only descendant, using an empty external output directory:

```sh
gh run download 43400282708 \
  --name swiftui-components-e151b5ff74d45ed3647aa014a1d074bc0d406981 \
  --dir ../artifacts/ci/e151b5ff74d45ed3647aa014a1d074bc0d406981
python3 tools/native_frontend/components.py verify \
  --output ../artifacts/ci/e151b5ff74d45ed3647aa014a1d074bc0d406981
python3 tools/native_frontend/build.py \
  --donor ../donors/tv.twitch-32.0.ipa \
  --components ../artifacts/ci/e151b5ff74d45ed3647aa014a1d074bc0d406981 \
  --output ../artifacts/native-frontend/swiftui/player-input-reproduction
```

If CI artifacts expire, rebuild the owned components with the pinned toolchain. Incompatible or incomplete receipts are rejected. After signing/installing, open a live followed channel, try pause/resume, mute/unmute, Share → Copy/Share Link and the down arrow, then repeat with glass disabled. Check normal video and any available ad segment. Export Native diagnostics through a two-finger hold; control counters should advance and SDK mute state should agree, while all monitored RN/Hermes/worklet entries remain zero. Audible mute, device navigation, safe-area layout and real runtime isolation still require that phone check.

## Device confirmation, 2026-11-13

The tester reports that the buttons work well on the packaged `e151b5f` build. Two exports from process launches 31 and 32 match the exact source, donor, proof and probe contract in the build record. Their [device evidence record](SWIFTUI_PLAYER_INPUT_DEVICE.json) retains the archive/report hashes and bounded diagnostic fields. The original archive is preserved outside the checkout under `../artifacts/native-frontend/device/player-input-e151b5f/`. Earlier package-time statements that device testing had not occurred remain accurate for that build step; this section adds the subsequent device result.

Both reports show all 25 monitored RN/Hermes/worklet counters at zero, instrumentation armed mask 15 and no recorded failures. Native root ownership and the navigation guard remain active, with no navigation interventions recorded; each report lists 100 followed channels and background/foreground events. Playback and last-playback error codes are zero. These Native exports do not include a new baseline positive control or independently recalibrate instrumentation.

Close, mute, Share and Settings actions are observed in both exports, with copy-link observed in launch 32. Pause/play has zero action observations in both; the general user confirmation and successful coordinate simulator tests do not create a device counter observation. Both exports were taken without a current player (`player_mute_state[0] = 0`), so zero mismatch samples cannot establish actual audio behavior or SDK getter agreement while playing. Glass/plain, ad/content and audible-mute results were not separately identified. The reported input problem is device-confirmed resolved within that supplied scope; those finer checks remain unrecorded. No further build or monitoring was started for this evidence update.

## Player transition and shared-glass refinement

The next refinement keeps the player overlay layout mounted and inserts/removes concrete control regions inside stable layout slots. This supersedes removing the entire overlay from PlayerCanvas: region transitions now own both appearance and disappearance, while hidden buttons still leave the view tree. The renderer remains passive and mounted. The corner regions use opposing vertical edges by default, or opposing horizontal edges; Fade uses an opacity transition in both directions. Central play/pause always fades. The existing 6% shade also fades. A cubic timing curve with zero endpoint velocity uses 0.38 seconds for flying and 0.22 seconds for Fade, without spring overshoot.

Main Settings → Player → Controls now stores the animation choice. Reduce Motion resolves the effective choice to Fade and disables the selector without erasing the saved preference. The small in-player settings popover retains its existing glass toggle. The four top-right actions share one capsule material when glass is enabled; their individual 44-point hit targets and popover anchors remain separate. Reduced transparency uses an opaque capsule. Existing unavailable actions remain disabled.

Apple references: [Reduce Motion environment](https://developer.apple.com/documentation/swiftui/environmentvalues/accessibilityreducemotion), [custom Liquid Glass](https://developer.apple.com/documentation/SwiftUI/Applying-Liquid-Glass-to-custom-views), and [materialize glass transitions](https://developer.apple.com/documentation/swiftui/glasseffecttransition/materialize). Concrete view transitions animate the control regions; materialize lets the glass material animate in/out without matching unrelated control geometry.

All 64 Linux-compatible native host tests pass. The Apple model fixture additionally checks every saved mode with and without Reduce Motion, plus invalid stored preferences. The existing two coordinate UI cases retain their action/popover/auto-hide checks and add hide/reveal and mute interactions in all three modes with glass on and off. Apple compilation, those simulator checks, and packaging remain pending for this source change. Smoothness, visible fade-out, the grouped material, mid-transition reversal, and the system Reduce Motion setting still require physical-device review; host tests do not establish their appearance. No VM work or continuous Actions monitoring is required for this refinement.

## Animation fixture deadline race

[Run 43539146284](https://github.com/BananaOnGitHub/Streamside/actions/runs/43539146284), source `b2a50ec635595d71a546fd0edaf035baeb74e478`, compiled the native component and executed both coordinate cases. Plain passed the complete sequence. Glass passed its original controls/share/settings/auto-hide assertions and the horizontal mode sequence, then failed the second mute label check in Fade. The first mute touch completed near 147.77 seconds and the second near 151.89 seconds, separated by more than the production four-second deadline. The failure hierarchy shows `hold=false popup=false visible=false`, with the mute button absent. XCTest existence/idle waits outlived the visible window; this result does not establish a mute or transition implementation defect. No components or IPA were admitted. The [failure record](SWIFTUI_PLAYER_ANIMATION_CI_FAILURE.json) preserves the exact logs and timings.

The fixture now enables its explicit visibility hold after the unchanged four-second auto-hide/reveal test, before exercising each mode's action closures. The hold retains already-visible controls, while manual video hide remains hidden until another video tap; enabling the fixture switch explicitly reveals once. This separates deadline validation from slow XCTest touch synthesis. All hide/reveal, mute, Close and popover assertions remain, with unchanged observation timeouts. Production animation, touch routing, visibility policy and playback are unchanged by this correction. Host tests and documentation checks are rerun; replacement Apple validation remains pending.

## Live Actions build progress

The same follow-up exposes the runner's work live instead of buffering the entire Apple worker and each subprocess until completion. Compiler diagnostics, Xcode build tasks, individual XCTest cases and simulator output stream into named expandable log groups. Each command records a start, elapsed completion/failure and, after 30 seconds without output, a truthful still-running message. Major phase results also append to the Actions summary, including an overall component outcome. The workflow gives frontend selection/probe/report tests separate named steps; original-startup components remain independently built, while donor-dependent IPA assembly stays local.

The shared standard-library logger preserves command output in build.log and propagates nonzero exits. A timed-out owned process group is terminated, including its children, with prior output retained. No environment dump, credentials, donor bytes or signing material are added to logging. The source input allowlist includes the helper; component identities continue to admit only source-matched, fully validated builds. Existing validation requirements and per-command test limits remain in effect.

The expanded host suite passes all 68 tests. Four new logger checks verify output arrives before the process finishes, nonzero failures retain diagnostics and fail the summary, timeouts retain partial output and terminate child processes, and missing tools close log groups with a failure. These logger checks also run on the macOS job before compilation. Documentation checks pass. Real Apple compilation and the corrected glass/plain UI cases remain pending until the replacement workflow completes.

## Successful animation build and local package

Source `c1a56aa1686106b1d285aa8c09f445fd60e55478` passed [Apple CI](https://github.com/BananaOnGitHub/Streamside/actions/runs/43541502380), [Linux CI](https://github.com/BananaOnGitHub/Streamside/actions/runs/43541502170) and [documentation CI](https://github.com/BananaOnGitHub/Streamside/actions/runs/43541502371). Both coordinate UI cases passed, retaining the separate real four-second auto-hide check and testing manual hide/reveal and mute in horizontal, Fade and vertical modes. The four live-logger tests passed on macOS, alongside existing model, ownership, clock/title, synthetic playback, launch-selection, ABI and report checks. The published logs now show named streaming phases and individual XCTest activity. This supersedes the preceding pending-validation status without changing the failed run's recorded outcome.

Local packaging validated the exact Twitch 32.0 donor, source-matched component receipts and hashes, 51 Swift boundaries, 13 Objective-C methods and all 25 probe entries. Every retained donor archive entry was verified, including unchanged original HBC. One Native IPA was produced under `../artifacts/`; no donor, signing identity or proprietary output was uploaded to Actions. The [artifact record](SWIFTUI_PLAYER_ANIMATION_ARTIFACTS.json) preserves source/toolchain/test identities, local manifest and workflow-log hashes, and the IPA SHA-256. No VM was used.

Reproduce from this clean revision or a compatible documentation-only descendant:

```sh
gh run download 43541502380 \
  --name swiftui-components-c1a56aa1686106b1d285aa8c09f445fd60e55478 \
  --dir ../artifacts/ci/c1a56aa1686106b1d285aa8c09f445fd60e55478
python3 tools/native_frontend/components.py verify \
  --output ../artifacts/ci/c1a56aa1686106b1d285aa8c09f445fd60e55478
python3 tools/native_frontend/build.py \
  --donor ../donors/tv.twitch-32.0.ipa \
  --components ../artifacts/ci/c1a56aa1686106b1d285aa8c09f445fd60e55478 \
  --output ../artifacts/native-frontend/swiftui/player-animation-reproduction
```

The IPA requires Feather re-signing with the existing application/keychain identity. Device review remains pending: try all three settings under Settings → Player, check entry/exit including actual Fade disappearance, verify the central button stays in place, and check the shared top-right capsule with glass enabled. Enable system Reduce Motion and confirm Fade is selected and the selector disabled, then disable it and verify the saved choice returns. Check controls still work and export Native diagnostics after playback. Simulator control success does not establish physical animation quality, audible mute or a fresh donor runtime positive control.

## Device motion failure and persistent presentation trial

The next device review of source `c1a56aa1686106b1d285aa8c09f445fd60e55478` reports successful fly-in, immediate fly-out, immediate Fade appearance/disappearance, and an immediately visible central play button. This fails the intended visual acceptance despite the successful coordinate suite. The [device failure record](SWIFTUI_PLAYER_MOTION_DEVICE_FAILURE.json) preserves the exact report hash and relevant bounded fields; the original export remains outside the checkout. It matches the packaged source/proof/donor, armed mask 15 and failures zero, with all 25 monitored runtime counters zero. It contains no animation measurements or new positive control. Existing success records remain evidence of compilation, actions and view presence, not successful visual transitions.

The correction trial replaces conditional region insertion/removal and independent glass transitions with persistent controls driven by one explicit animatable scalar. [PlayerControlMotion](../../native/swift/PlayerControlMotion.swift) applies the interpolated opacity and offset to real control content. Edges use the first 0.38 seconds of a 0.56-second fly timeline, followed by a 0.18-second stationary center fade. Reversing the timeline fades the center out first, then flies the edges out. Smoothstep interpolation gives zero velocity at phase endpoints. Fade uses 0.22 seconds for opacity alone, including with Reduce Motion. The shared glass capsule stays mounted. Hidden controls disable input and hide from accessibility on each button; playback and the passive media surface remain unchanged. No conclusion about a particular SwiftUI internal cause is inferred solely from the device export.

The simulator fixture now observes intermediate values from the production AnimatableModifier body, using a bounded test-only collector. Both coordinate cases must additionally observe edge motion/opacity and central opacity at intermediate values in both directions for every mode, central sequencing for flying, and no movement under an injected Reduce Motion environment. Component admission requires the new motion-frame receipt; mere endpoint presence or a passed action test is insufficient. Model checks cover endpoints, stationary center, sequencing and half-opacity Fade. The fixture does not mutate SwiftUI state from interpolation callbacks and does not add device frame logging.

All 69 host tests pass, including rejection of missing motion validation. Apple compilation and actual simulator interpolation checks remain pending for this source change. Modifier-value observations establish an animated render path, not physical display smoothness or pixel-perfect glass compositing. Device confirmation of fly-out, Fade in/out, center sequencing and interruption still remains required after successful packaging. The VM and continuous Actions monitoring remain unused. Apple reference: [Animatable interpolation](https://developer.apple.com/documentation/SwiftUI/Animatable).

## Read-only accessibility fixture correction

[Run 43566492339](https://github.com/BananaOnGitHub/Streamside/actions/runs/43566492339), source `5360e50b3667e3db3d1c9f307b7b44c1799813d1`, compiled and linked the production component and passed its model, ownership, clock/title, synthetic playback and launch fixtures. It failed while compiling the coordinate test app: `accessibilityReduceMotion` is a read-only environment property, so `.environment` cannot accept its key path. Neither coordinate case nor interpolation sampling executed. The downstream ABI job was skipped, and no components or IPA were admitted. The [failure record](SWIFTUI_PLAYER_MOTION_CI_FAILURE.json) preserves the logs and scope.

The fixture now supplies an optional motion-preference input directly to PlayerControls. Normal application callers leave it unset and continue reading the system environment. All eight entry/exit sampling cycles, including the simulated Reduce Motion pair, remain required, with unchanged assertions and limits. The preceding reference to an injected environment described an unsuccessful fixture approach; this replacement tests a supplied preference through the same effective-mode resolver and rendered modifier, not an actual system-setting change. The physical Reduce Motion setting and disabled main-settings selector still require device validation. The animation timeline and playback behavior are unchanged by this compile correction.

## Post-animation control teardown

[Run 43567474931](https://github.com/BananaOnGitHub/Streamside/actions/runs/43567474931), source `a7cb588958a7b6a9697756e4ada9af91ffaeb8b4`, compiled the production component and coordinate fixture, then failed both original auto-hide assertions. Both snapshots show `hold=false popup=false visible=false`, while the player buttons remain exposed to accessibility. The new interpolation check was not reached (`Not checked`); neither successful visual motion nor a visibility-timer defect follows from this hierarchy. The [teardown failure record](SWIFTUI_PLAYER_MOTION_TEARDOWN_FAILURE.json) preserves its log identities. No component distribution or IPA was admitted.

The controls now remain mounted during exit, then unmount after SwiftUI reports the entire animation removed on iOS 17 and later. [Apple's removed completion criterion](https://developer.apple.com/documentation/swiftui/animationcompletioncriteria/removed) is used rather than removing at the visibility request. iOS 16 retains a cancellable duration-plus-final-frame compatibility delay. Each request has a generation guard: a stale exit completion cannot remove a newly revealed overlay. Reopening mounts at the hidden endpoint before a separate render update starts the entry animation. The renderer and media lifecycle remain mounted independently.

The existing interpolation checks now run before auto-hide, so a later accessibility failure still leaves actual motion evidence. A short entry/exit/re-entry sequence also finishes with working mute actions, guarding against stale teardown after reversal. Existing auto-hide/action assertions and their timeouts remain unchanged. Failure snapshots include the latest bounded central modifier value. All 69 host tests pass; Apple compilation, interpolation, completion behavior and device visual confirmation remain pending for this change. The iOS 16 timing fallback is not device-validated.
