# Streamside Native: SwiftUI foundation and authentication boundaries

The build procedure below records the original VM-built candidate. Routine
compilation now uses [the donor-free Actions pipeline](../development/NATIVE_SWIFTUI_CI.md);
no VM or SSH setup is assumed available. Original source/proof/package identities
remain unchanged. [The tooling audit](SWIFTUI_CI_AND_TOOLING_AUDIT.md) records the migration.

## Scope and checkpoint

Continue `feat/native-frontend` from `59c1936c1e0a69f20b4b7ba9ac2d6330c4ca2940`. Annotated local tag `native-phase2-uikit-verified` preserves the working Phase 2 source and the signed-in/signed-out device evidence at that revision. `native/SSNFrontend.c` is unchanged and remains buildable with `--frontend uikit`; the original Phase 2 packages and their receipts are preserved. The tag can be inspected/recovered without modifying other development branches. Ubuntu owns the authoritative repository and Git history; no repository or donor is copied to macOS.

The new default frontend is SwiftUI. Twitch's original application/scene delegates, native initialization, window, account authority, authorization/integrity pipeline and lifecycle observers remain. A `UIHostingController` replaces the native window's root after the original scene connection, as in the Phase 2 substitution. There is no second `UIApplication` or competing SwiftUI `@main` app. SwiftUI owns the replacement shell's navigation and presentation. Existing donor URL/notification routes remain forwarded; their behavior and potential RN demand still require device testing.

No playback, chat, emotes, credential fields, custom credential submission or RN login fallback is added. Fresh sign-in is explicitly unavailable in this candidate. This stage provides a compiled foundation with existing-session access and a validated native logout entry point; it does not claim an RN-free complete fresh-authentication lifecycle.

## Presentation and service architecture

- [SwiftUI host](../../native/swift/SwiftUIHost.swift): mounts the shell in the original window. The baseline retains Twitch's original root, with a two-finger one-second hold opening SwiftUI diagnostics; no overlay blocks Settings.
- [SwiftUI shell](../../native/swift/StreamsideShell.swift): standard `NavigationStack`, `List`, account/followed sections, refresh controls, progress, errors, signed-out welcome, sign-out confirmation, accessible Diagnostics and a system report share sheet.
- [Swift service facade](../../native/swift/NativeServices.swift) and [value models](../../native/swift/NativeModels.swift): main-thread observable state, presentation values and an account-service interface. Identity and channel data are cleared at signed-out/account-change/failure/logout boundaries. UI values never enter report generation.
- [Owned Objective-C facade](../../native/SSNNativeBridge.m): main-thread snapshots/actions, mode-specific report URLs and bounded sign-out observation. It calls the preserved C/native integration rather than exposing donor Swift values or credentials to SwiftUI.
- [Account bridge](../../native/SSNAccount.c): unchanged native current-user/followed-users requests and opaque Swift ABI handling. Existing native PMHTTP authorization, GraphQL/Apollo interceptors and integrity handling remain authoritative.

Only the first 50 followed channels are requested. Live/offline status is not supplied by the native model used here, so the UI states that live status is unavailable. No fixture, public endpoint, inferred offline status, profile-image request or channel playback action is introduced.

Native standard controls use dynamic text, system colors and accessibility labels. Target deployment remains iOS 16.4; no iOS 26-only SwiftUI API is required. The donor's main executable already declares SDK 26.5 and minimum 16.4 but its Info.plist opts into `UIDesignRequiresCompatibility`. The SwiftUI native package removes that opt-out; the baseline preserves it. Standard controls can therefore adopt the newer system design where available, without custom glass rendering. Actual appearance/accessibility remains a device check. Apple's [UIKit integration guidance](https://developer.apple.com/documentation/swiftui/uikit-integration) supports hosting SwiftUI content inside an existing UIKit app; Apple's [WWDC25 platform guidance](https://developer.apple.com/videos/play/wwdc2025/102/) describes newer system rendering for standard controls built with the modern SDK.

## Authentication investigation: exact Twitch 32.0

Input: donor SHA256 `076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`, Twitch 32.0 build `263110145453907615`. The [static inventory](TWITCH_32_AUTHENTICATION_INVESTIGATION.json) records exact main/HBC/compiler hashes, 17 selected bytecode functions, eight native classes, relevant property references and function hashes. Regenerate it with [the inspector](../../tools/inspect_native_auth.py):

```sh
PYTHONPATH=/home/bananas/Agent-Stuff/streamside/toolchains/python python3 tools/inspect_native_auth.py --donor /home/bananas/Agent-Stuff/streamside/donors/tv.twitch-32.0.ipa --hermesc /home/bananas/Agent-Stuff/streamside/toolchains/hermes-build/bin/hermesc --output /tmp/twitch32-auth.json
```

This command only disassembles verified bytecode and reads native metadata. It never executes the donor app, Hermes JavaScript, login or a network request. It retains bounded relationships/hashes, not full proprietary disassembly or credentials.

| Boundary | Established static evidence | Still unestablished |
| --- | --- | --- |
| Current RN login presentation | `LoginScreen` uses `useAuth.completeLogin`, `LOGIN_URL`/`SIGNUP_URL`, and `PortalWebView`. The bundle contains `https://m.twitch.tv/wv/auth/login` and its signup counterpart. | Which feature-gated/region-specific login variant is chosen on every device, and the remote portal's current behavior. |
| Hosted portal completion | `parseLoginMessage` parses JSON event names including login/signup success and extracts accessToken/token plus auxiliary login fields. `parseLoginPortalMessage` turns accepted outcomes into an access-token result for `completeLogin`. | A complete, validated origin/navigation/message-trust contract for a new WKWebView host, cancellation and all challenge outcomes. No credential-bearing portal messages were received or logged. |
| JS session management | `AuthProvider` receives session/clientId/fetchImpl, creates callbacks around `setToken`/`logout`, and `AuthSession` stores a token, calls persistence.save and notifies listeners. | Complete binding of the current app's supplied session/persistence implementation back into the first-party account manager. A standalone JS Keychain persistence implementation is present; its presence does not prove it is the native app's selected account path. |
| Native account establishment/restoration | Phase 1 inspected StandardAccountManager login-with-access-token, Keychain restoration, HTTP auth installation and identity notifications. Phase 2 reports exercised existing-session native account/list access without observed runtime creation. | A safely callable fresh-login ingress from hosted completion to that manager, including token provenance, verification, persistence and all authorization changes. An account-manager symbol alone is insufficient. |
| Native credential/challenge support | LoginNetworker metadata has account-manager, GraphQL, HTTP/cookie storage and MobileShield dependencies. Native LoginVerificationViewController has verification/passport error and account-manager fields. | Whether the currently selected RN/portal login route uses these legacy/native components, their complete safe service ABI, and challenge coverage. No password/2FA/CAPTCHA requests were reproduced. |
| Social authentication | SocialAuthSession stores a system session, completion, auth URL and presentation anchor and implements the ASWebAuthenticationSession presentation callback. SocialAuthEventHandler and a native Amazon authorization SDK/ASWebAuthenticationSession strategy exist. Native code includes system web-session construction and authorization-request calls in the social-auth region. | End-to-end Apple/Google/Amazon mapping, provider code/token exchange, recovery and native-session establishment. GoogleCast is not Google Sign-In; SDK/class presence does not prove usable provider authentication. |
| Public hosted OAuth | Twitch documents registered-client OAuth/OIDC flows, registered redirect URLs and scoped app/user tokens. | Compatibility of credentials issued to a separate Streamside registration with this first-party client's native GraphQL/integrity/account lifecycle. No such substitution is made. |

The portal finding narrows the investigation: the inspected RN screen wraps hosted authentication rather than proving username/password submission is implemented by the native account manager. A future WebKit-owned hosted flow could avoid Hermes, but that remains a candidate, not implemented login. A safe next authentication milestone needs the exact trusted portal bridge and a validated first-party native completion/persistence adapter. Reproducing portal callbacks by string name or passing a public OAuth token to a private native function would not establish that contract.

Twitch's [OAuth flow documentation](https://dev.twitch.tv/docs/authentication/getting-tokens-oauth/) and [app registration documentation](https://dev.twitch.tv/docs/authentication/register-app/) describe per-application client IDs, redirect registration and scopes. They provide a supported third-party API login option; they do not document conversion into Twitch's first-party session infrastructure. No independent registration, embedded client secret, token extraction, credential collection or renewal policy is added here.

### Implemented native logout

Twitch's existing Objective-C app-delegate selector `logoutUserWithUserInitiated:` is at unslid `0x103d078c0`, with encoding `v20@0:8B16`. The adapter forwards the boolean to the existing native account-manager service; its original Swift code owns witness dispatch. [Admission](../../tools/native_frontend/validate.py) checks the exact donor method/class/encoding/address/16-byte prefix, and [integration](../../native/SSNIntegration.c) rechecks the live class, method encoding, loaded implementation address and prefix before returning a target. Unknown or hooked adapters are rejected. The frontend contains no donor offsets or protocol-witness accesses.

After explicit native UI confirmation, the facade clears presentation/pending requests, invokes that validated adapter with `userInitiated=YES`, and checks only presence/absence of native HTTP authorization at 250 ms intervals for at most 120 observations. It does not read a token or erase Keychain/cookies independently. Completion is reported only after native authorization disappears, followed by the normal account refresh. Timeout/failure shows an understandable error and hides stale account data. Logout itself is not cancellable once submitted. Original account-change notifications remain active.

This path is ABI-validated and compiled, but not device-executed in this stage. Native logout can trigger donor routing or other side effects. An unexpected RN demand remains a guarded process failure with evidence, never a fallback. Do not mark logout/persistence success until the device test confirms it.

### State support

| State | Candidate behavior |
| --- | --- |
| Existing account checking/restoration | Progress, then native account/list data or a failure/signed-out state. |
| Authenticated | Current account, real first-page follows, refresh and validated sign-out action. |
| Unauthenticated | Functional SwiftUI welcome, check-existing-account action and diagnostics; explicit notice that fresh login is unavailable. |
| Signing out | Progress; account/list masked immediately. Failure to confirm logout produces an error and retry through an account check. |
| Request/compatibility failure | Generic error/retry or diagnostics; no raw donor error payload shown/exported. |
| Fresh authentication in progress/cancel/failure | Not claimed: there is no implemented login operation or nonfunctional login button. |

## Runtime isolation and data handling

The 25 probe definitions, ARM64 trampolines, warmup/eligibility gate, guarded failure behavior, baseline positive-control requirements, report schema/caps and account-request implementation are unchanged. New logout metadata admission does not add or bypass a runtime entry point. SwiftUI, Foundation, UIKit, Combine and system Swift libraries are the new module's dependencies; it links no React/Hermes/worklet dependency. The donor executable still maps its original frameworks, as before.

Ordinary UI changes consume main-thread snapshots. No JS evaluator, RN factory call, RN screen or hidden authentication runtime is added. The baseline deliberately runs RN and must observe its positive control again because the source/proof changes. Phase 2 device zeros remain historical evidence for their original packages, not automatic proof for this SwiftUI build.

Reports contain numeric diagnostics/build identities; account/channel presentation data stay in memory. Native exports attach only native latest/previous files; baseline exports attach only baseline latest/previous files. Retained prior-build reports keep their own proof identities. If an RN guard fires before an observer can arm, preserve crash evidence and treat the run as incomplete, not zero.

## Build ownership and available validation

The user-provided SSH alias `tahoe` was verified using `xcodebuild -version` and `swift --version`: Xcode 26.6 build 17F113; Apple Swift 6.3.3. The VM reports macOS 26.7.1 and iPhoneOS SDK 26.5. Its system clock is not used to infer user-facing test dates.

[The Ubuntu build orchestrator](../../tools/native_frontend/build.py) validates the exact donor locally, generates proof/admission data, and transfers an explicit source/test/header allowlist to an isolated `/tmp/streamside-native.*` directory on the VM. [The worker](../../tools/native_frontend/apple_worker.py) verifies those input hashes and uses the Apple SDK for arm64 iOS 16.4 compilation/linking and ad-hoc signature verification. Swift is compiled in Swift 5 language mode by Swift 6.3.3; concurrency-sensitive service/UI work is main-actor/main-thread owned. It returns the binary, generated Objective-C interface, ABI caller object and build/compiler records. Temporary successful remote build directories are removed; failed attempts are retained for investigation. SSH configuration and key files are never opened, displayed, copied or modified by these scripts. No donor or Git history is transferred.

Run from Ubuntu on `feat/native-frontend`:

```sh
python3 tools/native_frontend/build.py --donor /home/bananas/Agent-Stuff/streamside/donors/tv.twitch-32.0.ipa --frontend swiftui --apple-build-host tahoe --mode both --output build/native-swiftui
```

The IPAs still require the usual device-authorized re-signing with the existing app/keychain identity. Packaging and retained-entry verification occur on Ubuntu. This is a reproducible build path, not a claim of byte-identical output across random macOS workspaces or toolchains. Apple linker UUID/debug paths/ad-hoc signatures can affect exact bytes; each supplied build gets exact hashes.

Host validation so far: 25 native frontend tests passed with no skips (the preserved 23 plus two logout admission tests); the six Swift ABI caller/register tests also passed against Apple-compiled caller code. A macOS executable built from the pure Swift presentation models passed synthetic state-boundary checks, including removal of stale data on sign-out/account change/failure. These do not execute Twitch services or SwiftUI on iOS. The first exploratory build required the imported notification-name correction, then the Clang `-Os` flag correction; failure logs are preserved under `build/native-swiftui-trial/` and `build/native-swiftui-trial2/`. A subsequent dirty-checkout candidate compiled/linked and packaged successfully in `build/native-swiftui-trial3/`; it is not the delivered clean-source identity.

Physical-device validation remains necessary for SwiftUI hosting/navigation, signed-in restoration/list/refresh, signed-out state, native logout, account changes, the new baseline positive control, zero runtime counts and stability across transitions/restarts. Fresh login, provider verification/challenges and complete session creation remain blocked as described above. No phase-3 iOS device results or performance improvement are fabricated. Follow [the device checklist](SWIFTUI_NATIVE_DEVICE_TEST.md).

## Delivered candidate identities

Implementation revision: `607f5954670ff7e98d8e5873928c3a14524f0f40`. Proof: `0f59f958f85511f00e97d888d0e20e1cbb3de2d018f9dafeac30c2dbdd37a382`. Both flavors were built from a clean checkout using the VM compiler above and packaged on Ubuntu. The [artifact and validation receipt](SWIFTUI_NATIVE_FOUNDATION_ARTIFACTS.json) records exact source/input/output identities, preserved checkpoint comparisons, compiler findings and pending device gates. The final 25 host tests and six Apple-compiled ABI checks passed; both macOS model test executables passed. No iOS device acceptance is inferred.

| Flavor | Bytes | IPA SHA256 |
| --- | --- | --- |
| Baseline | 196475822 | `e6e6a317be5f352fc2a0bbccd3dc4433e34faf2c1515cb9876fed20bccdf1b2d` |
| Native | 196479929 | `b9f5c836e728f82e109ed1c71679f3b3ab6de408cd86d6fd1d6c8f204b45ff9b` |

Files are in `build/native-swiftui/`. Original UIKit IPAs and earlier development/device records remain intact. A later documentation-receipt commit does not alter these compiled source/proof identities.

## Later device evidence for a donor-native login route

[The logout/login device review](SWIFTUI_NATIVE_DEVICE_REVIEW_2.md) now demonstrates
one first-party Twitch login route usable in native mode: account state clears
on logout, then the native GraphQL adapter retrieves account/follows after the
tester logs in through Twitch's own replacement interface, with zero guarded
RN/Hermes/worklet entries. This supplies compatibility evidence for that observed
donor-native route, independently of the RN hosted-portal findings above.
The tester identifies the successful method as Twitch username/password and
reports that SwiftUI returns after a full restart; the additional restart report
is pending. A SwiftUI-controlled presentation/completion handoff remains open.
Other providers and verification/recovery challenges remain untested. The original compiled
foundation, historical build findings and original limitations remain scoped to
their recorded candidate.

The subsequent [report-5 restart validation](SWIFTUI_NATIVE_DEVICE_REVIEW_2.md#restart-validation-report-5)
now confirms a distinct native launch returning to the SwiftUI root, successful
account/followed-channel restoration with 50 results, all instrumented images
armed and all 25 probe counts zero. This resolves the previously pending restart
evidence for the tested username/password flow. Controlled login presentation
and return to SwiftUI in the same process remain implementation work.
