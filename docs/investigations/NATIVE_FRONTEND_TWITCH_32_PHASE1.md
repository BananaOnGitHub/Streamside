# Native frontend feasibility: Twitch 32.0, phase 1

Investigation date: 2026-11-10. Branch: `feat/native-frontend`.
Scope: original supplied donor inspection and development-state recovery.
No interface, startup hook, credential export, authenticated request, or replacement
IPA was created. Findings below distinguish inspected control flow from behavior
that still needs an iOS device.

## Decision

Proceed to a small backend-and-runtime isolation proof before implementing the
new interface. Twitch 32.0 has a native account/session authority, a native
GraphQL request pipeline, and native playback-token/player services. The
inspected native request path does not call Hermes.

A native screen alone does **not** establish reduced runtime overhead. The donor
explicitly starts RN through a `TwitchRNWarmup` root view, gives it a 1×1-point
frame, and releases the view. Its startup branch must be excluded before
claiming isolation. Zero Hermes runtime creations and a measurable resource
reduction remain device acceptance requirements.

| Question | Established from this donor | Remaining proof |
| --- | --- | --- |
| Lifecycle | `TWAppDelegate`, `SceneDelegate`, native root container/router, lazy RN factory, root-view demand and startup warmup are identified. | Full launch ordering on device, including deferred work and every re-entry route. |
| Authentication | `StandardAccountManager` owns native authentication state, Keychain restoration, credential propagation, invalidation and user refresh. | Account restoration/login/logout while RN is excluded; expiry/invalid credentials. An OAuth refresh-token exchange was not established. |
| Swift backend access | Native Apollo/URLSession consumes native HTTP authentication; native playback-token queries exist; selected framework load closures contain no RN/Hermes dependencies. | An app-owned Swift adapter with validated ABI and successful authenticated queries/playback while runtime counters remain zero. |
| Runtime isolation | Factory creation and actual runtime allocation are distinct; a specific startup warmup would defeat a visible-screen-only replacement. | Suppress all launch/surface/prewarm routes, prove no runtime creation, then measure overhead. Removing linked libraries is a later, separate milestone. |

## Development base and recovery

The working checkout is `/home/bananas/Agent-Stuff/streamside/repo`.
`feat/native-frontend` was created from
`f5cacb0e45fb0617b2f44c536cd25f9129763951`, the clean local
`feat/modular-diagnostic-runtime` tip. This includes diagnostic v1 hardening at
`d9317c52fac8916e1d0887bec1ba4cef5194d9c5` and its acceptance/provenance notes.
It is 47 commits ahead of public `origin/main`
(`2f81a409c143644e3e2e11f016a3de970e49ef7b`). The inherited development build
is still 3.1.0 build 25; this investigation does not create a native-front-end
build or admit Twitch 32.0 into the existing 31.6 Hermes patch chain.

Remote references were refreshed. Refs, reflogs and `git fsck --full
--no-reflogs --unreachable` were examined. There were no unreachable commits,
only six intermediate blobs belonging to the diagnostic source/baseline notes:

- `f8e52d09d8a9b49c8c096805a6363d17e58800bc`: earlier `TASInvestigationHost.c`.
- `7b89a46bd9aa4bfee941100744ee8e29f7540fb0`: earlier `TASEmotes.c`, without the later source-readiness reporting.
- `a84888644ddba64de6b0eca10f16380f011a3f65`: earlier modular implementation notes, including a subsequently corrected test count.
- `0fa7f95b156a6b2284a6d9bc38ab3c2f685b5da8`, `adae12baeea643557e9c5d14fe0c8140ab90f3a5`, `d2bbf19e54aaa4c4cd6bd7c5d65f7b510bc3ce5e`: intermediate local baseline notes.

These were compared with the committed descendants; they do not supply a later
recoverable development tree. Existing side branches remain preserved:
`origin/fix/rn-composer-diagnostics` at `d58b132` and
`origin/fix/rn-chat-gaps` at `e26a4e2`. Their divergent RN experiments are not
silently merged into this branch. In particular, `d58b132` contains the earlier
31.6.2 splash/Eppo investigation. Its addresses are not reused for 32.0.

The recovery is bounded to this checkout, its object database, refreshed remote
refs and the workspace recovery records; it does not claim to recover unavailable
source from another machine. The prior branch, donors and historical receipts
remain intact.

## Input identity and reproduction

Donor: `donors/tv.twitch-32.0.ipa`, 201,278,706 bytes, SHA-256
`076d8cced98bfce0baeaf4cc6e71adf0eedd8110f4430db501a1e39225839129`.
Bundle `tv.twitch`, version `32.0`, build `263110145453907615`, minimum OS
`16.4`. The scene manifest selects `Twitch.SceneDelegate`, allows one scene,
and supplies no main storyboard. `launch_screen` is the launch storyboard.

| Input | Bytes | SHA-256 |
| --- | --- | --- |
| `Twitch` | 106,381,504 | `f256c2a8576f4bafb26d4bd8f3c36470c0a6fc779e06fd1e254bbefa059875f1` |
| `main.jsbundle` | 29,678,860 | `1866099398b36a4fc98717dca5715547d6f16785bfa3dc8f74605fe98d1755d8` |
| `TwitchKit` | 6,254,432 | `f9cf2a880924bfcef7b46a7f64887fb835c28f5aa7e1593c6d5fa31bd1711401` |
| `React` | 12,338,576 | `74a3b3cde26076fd5fb9b327c7e15928443a514a4f86b27ecb376b7cc33d76f5` |
| `hermesvm` | 5,213,408 | `fce4c67d0e4acdc65edfbe5c029cd5b90c17f9a0249d686df753e5db598e3a33` |

The [inventory](TWITCH_32_NATIVE_FRONTEND_INVENTORY.json) records all 72 inspected
Mach-O images, UUIDs, encryption commands, dependencies, selected Objective-C
methods/encodings, field names, and 27 checked ARM64 call relationships. All eight
required evidence images have `cryptid=0`. The Hermes bundle is version 98 with
a valid SHA-1 footer. Field names are ownership evidence, not admission of
runtime field offsets or Swift value layouts.

Reproduce from the repository root, using Python's standard library:

```sh
python3 tools/inspect_native_frontend.py \
  /home/bananas/Agent-Stuff/streamside/donors/tv.twitch-32.0.ipa \
  --output /tmp/twitch-32-native-inventory.json
cmp docs/investigations/TWITCH_32_NATIVE_FRONTEND_INVENTORY.json /tmp/twitch-32-native-inventory.json
```

The [inspector](../../tools/inspect_native_frontend.py) refuses an unrecorded IPA,
changed required images, unsupported chained pointers, missing selected classes,
or changed call relationships. It reads the archive without unpacking, modifying,
or executing donor code. Full private disassembly remains outside the repository.
Addresses below are **unslid virtual addresses for analysis**, never hook-ready
live addresses. Framework addresses are relative to their own image, not Twitch.

## 1. Application lifecycle and navigation

| Image/address | Inspected responsibility |
| --- | --- |
| Twitch `0x1030add6c` / `0x1030aeaec` | Objective-C `TWAppDelegate` will/did-finish-launching entries; delegate to Swift workers `0x1030af08c` / `0x1030af348`. |
| Twitch `0x1034b7acc` | `prepareLiveDependencies`, dispatching through the native dependency setup. Preserve service initialization independently of frontend selection. |
| Twitch `0x102625e5c` → `0x1026267c4` | `configureGraphQL`; resolves native `TKGraphQL`, sets its metrics callback and prepares client integrity. |
| Twitch `0x103d07860` / `0x103d078c0` | `loadInitialAccountData` / `logoutUserWithUserInitiated:` dispatch through the native account-manager witness table. |
| Twitch `0x1030b14b8` → `0x1030b4fbc` | `SceneDelegate.scene:willConnectToSession:options:`. Casts to `UIWindowScene`, constructs the app window with `initWithWindowScene:`, sets its appearance/identifier, calls `makeKeyAndVisible`, and retains the window. |
| Twitch `0x1039adb28` | Router-side root installation: updates an existing `RootViewController.childViewController`, or creates the wrapper, performs containment and installs it with `setRootViewController:`. |
| Twitch `0x1001787c8` / `0x100178834` | Native root-child setter and containment work. `RootViewController` also forwards status-bar/orientation/home-indicator responsibilities. |
| Twitch `0x1033acb44` / `0x1033acce0` | Lazy singleton allocation and initialization of `TwitchRNHost`; singleton storage is `0x106097aa8`, with once token `0x105eb3f98`. |
| Twitch `0x1033bf864` | `factoryIfNeeded()`: creates `RCTReactNativeFactory` with `TwitchRNFactoryDelegate`, installs the dependency provider and related native integrations, and caches the factory. |
| Twitch `0x1033ac4c0` | RN factory delegate `bundleURL`; reads `TwitchRNPreparedRuntimeSource` through a separate lazy source-preparation service. |

`AppRouter` is a native object with attached routing state and account/GraphQL/
HTTP dependencies. Its account-notification handlers include user availability,
credential changes and updates. `TwitchRNHostNavigation` is an RN-facing native
navigation module, with theatre, profile, VOD, clip and category routes. It is
not the backend authority.

`TwitchRNHost` retains `feedSurface`, `profileSurface`, presented theatre/browse/
recap controllers, prewarming state, PiP/cast state, and account/GraphQL/router
dependencies. Replacing only the root child leaves these independent entry paths
available. Scene connection also handles notifications, URLs and restored launch
destinations; they must be routed into the chosen frontend before invoking RN.

## 2. Authentication ownership and refresh semantics

`TwitchIdentity.framework` defines `AccountManager`,
`AuthenticatedUserProviding`, `AuthenticatedUser` and native user-change
publishers. The concrete `Twitch.StandardAccountManager` lives in the main
executable. Its metadata includes authentication state, a serialized action
queue, current-user request cancellation, Keychain, HTTP, GraphQL and user-default
dependencies, plus authentication-failure subscriptions. It exposes no selected
Objective-C instance methods; its Swift protocol ABI is a real integration
boundary, not something `objc_msgSend` can manufacture.

The inspected native operations are:

| Twitch address | Operation identified by instructions and embedded source/function metadata |
| --- | --- |
| `0x100754c08` | `logIn(withAccessToken:userInitiated:userJustSignedUp:)` |
| `0x1007556dc` | `logout(userInitiated:)` |
| `0x100755ca0` | `refresh()`: reads a saved access token, attempts native login, handles missing credentials, and schedules user information refresh. |
| `0x1007566c8` | `refreshUserInformation(for:)` |
| `0x10075ad08` | `authenticationStateDidChange(from:to:)` |
| `0x10075b384` | `userCredentialsDidChange(from:to:)`: constructs `HTTPAccessTokenAuth`, observes failed authorization, assigns `PMHTTP.HTTPManager.defaultAuth`, and clears native Apollo cache state. |
| `0x10075c788` | `authenticatedUserDidChange(from:to:)`: clears user-specific state and publishes native identity notifications. |
| `0x10075e8ec` | `handleAuthenticationFailure(from:)` |
| `0x10075eb38` | `revokeAccessToken(_:)` |
| `0x10075f694` / `0x1007605a4` | `persistUserInformation()` / `deserializeUserInformationFromKeychain(for:)` |

In TwitchKit, `HTTPAccessTokenAuth.headers` at `0x2e3b7c` constructs
`Authorization: OAuth <access token>`. Unauthorized handling (`0x2e4324` →
`0x2e4790` → callback `0x2e4a00`) posts the native failed-authorization
notification and calls completion with false. This is not an observed automatic
OAuth refresh-grant retry.

The HBC separately contains `AuthProvider` (function 9055) and an `AuthSession`
implementation (30427) with a token, persistence callbacks and listeners. The
native request path does not establish the synchronization contract of every
RN login flow. Session restoration and account changes must be tested with RN/Hermes
excluded rather than assuming that contract is already satisfied.

Keep three meanings separate: account restoration/user refresh, account-token
renewal, and short-lived playback-token refresh. Only the first and native
playback-token request/cache machinery were established here. No account OAuth
refresh-token owner, expiry timer or refresh-grant endpoint has been established.
Firebase installation and Amazon login token classes are not evidence for the
Twitch account's refresh lifecycle. The native failure path must be preserved,
and actual expiration/re-authentication tested before replacing authentication.

## 3. Backend access without Hermes

The concrete native authenticated GraphQL path is:

1. `StandardAccountManager` installs `HTTPAccessTokenAuth` into the native HTTP manager.
2. TwitchKit `AuthorizationRequestInterceptor` witness `0x25d0ec` calls implementation `0x25cf04`.
3. That implementation reads shared `PMHTTP.HTTP.defaultAuth`, checks `HTTPAccessTokenAuth`, obtains its headers, merges them into the request and continues the native Apollo chain.
4. `TKGraphQL` construction (`0x2cdf4c` → `0x2ce60c`) builds an ephemeral URLSession client, native Apollo store, interceptor provider, request-chain transport and Apollo client for `https://gql.twitch.tv/gql`.
5. The native interceptor provider (`0x26568c`) includes networking, parsing, caching, authorization and client-integrity challenge machinery. `TwitchHeadersInterceptor` (`0x26689c`) also consumes session/device/common environment headers.

Thus authenticated native requests are not merely JS fetches forwarded to
NSURLSession. There is an existing native consumer of native authentication.
The request sequence inspected above has no Hermes dispatch. This establishes
native capability; it does not prove a new Swift adapter has already exercised it.

For playback, the native live-stream requester code around `0x1025e077c` resolves
`TKGraphQL`, constructs `PlaybackAccessTokenParams` and `StreamAccessTokenQuery`
(`0x1025e0854`), then calls native `TWApolloClient.fetchAsPromise`
(`0x1025e0958`) and decodes a `LiveStreamPlaybackAccessToken` fragment.
Clip/VOD access-token requesters and `StandardMediaPlaybackAccessTokenRequester`
/ `StandardMediaPlaybackSourceRequester` also exist in native code. Their
`forceRefresh` and cache/expiry logic concerns media tokens/sources, not proof
of Twitch account-token renewal.

`IVSMediaPlaybackSourceRequester` contains native `IVSPlayer` source preparation.
The player itself has Objective-C `preload:completionHandler:`, `loadSource:`,
`load:`, `play`, `pause`, delegate and quality APIs in `AmazonIVSPlayer.framework`.
A player view does not by itself obtain account-scoped playback entitlement.

The packaged dependency closures rooted at TwitchIdentity, TwitchKit,
TwitchApollo, TwitchGraphQLAPI, PMHTTP and AmazonIVSPlayer contain none of React,
Hermes, ReactCodegen, ReactNativeDependencies, worklets or reanimated. This is
load-command evidence, not a complete runtime call-graph proof. Concrete account,
router and playback services also reside in the RN-linked main executable.

### Swift integration boundary

Exported Swift APIs include `TKGraphQL.currentUser()`, query/fetch methods,
Apollo wrappers and native model types; Objective-C exposes `TKGraphQL.sharedInstance`
and selected helpers. The core account manager and many playback operations are
pure Swift, including generic values, protocol witnesses, promises and async calls.
An exported mangled symbol or a class name is not a safe C function signature.

Use an owned service facade with explicit account-change observation, cancellation
and main-thread ownership. Its first implementation must validate actual donor
ABI and live service instances, or use a validated Objective-C transport boundary
while preserving the complete native request policy. Do not copy a token into an
independent permanent client, bypass the integrity/challenge chain, cast Swift
structs to guessed layouts, or route requests back through JS to call the result
"native". Persisted queries, generated models and client integrity are part of
the integration work, not just an endpoint and an authorization header.

## 4. Runtime isolation and overhead

The startup continuation at `0x1030adc40` calls RN eligibility at `0x1030adccc`
(`0x1033e5a80`, Ultralight availability). On its true branch it resolves the
`TwitchRNHost` singleton, invokes warmup at `0x1030adcec`, and performs additional
host/account preparation at `0x1030adcf0`. This path is independent of presenting
a replacement screen.

Warmup implementation `0x1033c0174`:

1. Checks/sets the native host's `didStartPrewarm` state.
2. Calls `factoryIfNeeded()`.
3. Records `recordReactHostStart`, gets the root-view factory and requests module `TwitchRNWarmup` using `viewWithModuleName:initialProperties:`.
4. Sets the returned view's frame to `(0, 0, 1, 1)` and releases it.

Releasing that view does not undo the host/runtime initialization requested by
its creation. The exact module name is reconstructed from native immediate
constants by the inspector. The HBC also contains a `Warmup` component; its mere
presence is not the proof of startup—the native call sequence is.

In React, root-view creation at `0x341ec8` initializes a React host and requests a
surface. `RCTHost.start` (`0x2b2ec4`) constructs `RCTInstance`. The default factory
delegate's `createJSRuntimeFactory` (`0x33f6f8`) branches to
`jsrt_create_hermes_factory`; `RCTHermesInstance.createJSRuntime` (`0x2b2534`)
calls `HermesInstance.createJSRuntime` (`0x2b0228`), which calls imported
`facebook::hermes::makeHermesRuntime` at `0x2b0784`.
`TwitchRNExpoHostBootstrap` also implements `hostDidStart:` and
`host:didInitializeRuntime:`. These are useful observation boundaries.

The factory is lazy: the host initializer starts with no factory, and
`factoryIfNeeded` checks its cache. This provides a candidate cut point. It does
not establish that suppressing just one warmup function will exclude all other
surfaces, bundle preparation, preloads, notifications or deep-link entry routes.
A blanket runtime-constructor stub that breaks callers is not an acceptable
isolation strategy.

There are three separate milestones:

- **Screen substitution:** a native controller renders, but the rest of Twitch can still start RN. No runtime-overhead claim follows.
- **Runtime exclusion:** native service bootstrap and routing work while no RN host, RN bundle evaluation or Hermes VM is created, including after deferred startup and lifecycle events.
- **Loaded-image reduction:** remove RN/Hermes and dependent frameworks from the dependency graph where feasible. The current Twitch executable directly links them, so they remain loadable at process start even when no VM is created. Removing those load commands alone would leave imported symbols/classes unresolved.

A standalone native executable cannot recover the complete account implementation
by linking TwitchKit alone: `StandardAccountManager` and other concrete services
are compiled into Twitch. Reaching the loaded-image milestone therefore requires
a separately validated service/bootstrap boundary or coordinated removal of RN
imports and initialization, beyond a root-controller replacement.

Other runtime creators must be observed as well: the worklets binary imports
`makeHermesRuntime`, so counting only `RCTInstance` is insufficient. Successful
runtime exclusion may reduce JS heap/CPU/startup work while still retaining native
framework mappings and initialization. Do not report a memory or CPU reduction
until it has been measured.

## Device acceptance before interface implementation

Use separate baseline and isolation candidates from the same donor, signing
configuration, device, account and settings. No candidate for these checks has
been built in phase 1.

| Gate | Required evidence |
| --- | --- |
| Native launch ownership | An early frontend mode chooses the native root and routes notifications/URLs/restoration before any RN surface demand. Preserve native dependency, identity, network and lifecycle setup. Audit deferred launch tasks and source preparation. |
| Native backend proof | Restore a valid session; read current identity; execute an authenticated followed-content query; obtain live/VOD playback access and play through the native player. Verify logout/login/account switching, cancellation, unauthorized results and client-integrity handling. No credential values in reports. |
| No RN/Hermes | Instrument from process start: RN factory/host start, instance initialization, surface requests, bundle load/evaluation, Hermes runtime creation entry points and worklet runtime creation. Confirm hooks are installed before their first possible call. Zero counts must hold through a bounded launch-idle observation period, backend calls, playback, foreground/background, account change, deep links and stream switching. |
| Observation controls | The baseline must trigger the same counters and show actual stacks. Also inspect runtime instances/JS threads; a missing hook, missing callback or unavailable counter is a failed/inconclusive measurement, never a zero. Record the effective loaded bundle identity if RN runs. |
| Resource reduction | Repeat comparable cold launches and idle/playback runs; record launch time, physical footprint/JS heap, CPU, threads, wakeups and energy with sampling methodology. Report variation and distinguish linked-image residency from VM allocations. |
| Compatibility | Existing native network/ad-block hooks, emote services, login/session behavior, player errors, background audio, PiP, orientation and accessibility remain explicit regression surfaces. A successful build or generic host tests do not establish donor/device support. |

The immediate next implementation should be this small native service/runtime
proof, with a diagnostic result surface only if needed. Broad SwiftUI/UIKit
screen development waits until the backend and zero-runtime gates are satisfied.
If native-only login or request services require JS in a tested route, record the
actual dependency and revise the bootstrap boundary before expanding the frontend.

## Validation record

- Exact donor identity, app metadata, 72 Mach-O images, selected Objective-C metadata, dependency closures and 27 call relationships reproduced by the inspector.
- Inventory regeneration is deterministic; unrecognized-IPA refusal is checked.
- The configured inherited host suite ran 220 tests: 218 passed, two explicitly skipped (Apple Foundation/Xcode and Apple ImageIO/Xcode). This includes the pinned **31.6** donor/Hermes checks and does not validate 32.0 compatibility.
- The first unconfigured invocation failed with 52 failures, three setup errors and 22 skips because the required Zig/Node/private-input environment was absent. Existing toolchains were located and configured before the successful rerun; no tests or runtime source were changed to obtain a pass.
- Documentation integrity passed. Exact validation commands and log identities are preserved in the [validation record](NATIVE_FRONTEND_PHASE1_VALIDATION.json).
- Apple runtime execution, a Swift ABI bridge, authenticated network requests, actual playback and device performance remain untested. No native-frontend IPA or compatibility claim is produced.

This record follows [documentation ownership and timing](../development/DOCUMENTATION.md).
Public feature/release documentation remains unchanged during this experiment.
