# Twitch 31.6.2 startup splash activation

Read-only donor investigation, 2026-10-17, from Streamside revision `9e38256`
on `fix/rn-composer-diagnostics`. No runtime hooks, flag overrides, production
changes or replacement IPA were introduced. Original donors remain unchanged.

## Finding

The native executable ships `Twitch.SecondSplashView`, gated by the Eppo
experiment `ios-ultralight-second-splash` and RN eligibility. The native
experimentation service loads persisted configuration, falls back to a bundled
production snapshot, and refreshes from the network. This shipped feature can
therefore change activation without replacing the executable or Hermes bundle.

This supports an explanation for an animation appearing on a later launch;
it does not establish the assignment on the reporting device. No device
container, saved configuration, assignment history or matching launch capture
was available. No causal connection to missing chat rows or small black input
text has been established.

## Exact inputs

Twitch 31.6.2, bundle build `262872150334984303`, from the previously verified
decrypted donor. All hashes below are SHA-256.

| Input | Bytes | Hash |
| --- | --- | --- |
| Original IPA | 197,132,394 | `8cf72803d0e0b1aeb7c062af2d0cbac1e20f78e9f3c73fc590ac5ae9d1d29186` |
| Main executable | 108,159,824 | `bcec3102c572afb82f9eed213517d0a6532dc15e8e2de222428058c6599e50da` |
| `index.ios.bundle` | 28,682,408 | `20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458` |
| Bundled `eppo-config.json` | 284,500 | `614cbdb1782957b3db0f380a04bfe57261d46100a2fae9d3206e07026ade217d` |

Configuration path:
`TwitchDependencies_EppoExperimentation.bundle/eppo-config.json`.
Environment Production, format SERVER, `createdAt=2026-10-14T20:22:59.865Z`,
342 flags. The 31.6 snapshot has 335 flags,
`createdAt=2026-10-09T17:24:17.752Z`, hash
`f1412a16a286296b032408793ffd9b3c7dbc312f417fb9b93191545a67dfabcc`.

## Native activation path

Addresses are unslid virtual addresses in this exact donor, for inspection only.
Descriptions of stripped Swift routines identify inspected roles, not recovered
source declarations.

| Address | Verified role/control flow |
| --- | --- |
| `0x1033c2b90` | Initializes an `ExperimentBucket<String>` for `ios-ultralight-second-splash`, default string `false`, using the experimentation dependency. |
| `0x1033c2c00` | Returns false on iPad. Reads the bucket and compares case-insensitively with `true`; other values return false. A match proceeds to RN eligibility at `0x1033ced68`. |
| `0x1033ced68` | Checks device/user eligibility, a persisted staff override and the Boolean `ios-ultralight` experiment, default false. The override initializer names `TWUltralightStaffOverrideEnabledKey` / `UltralightStaffOverride`; this is not a general user splash preference. |
| `0x1033c43e0` | Requires its caller's Boolean permission, no existing second-splash instance, and a true splash gate. Creates `SecondSplashView` with host bounds, adds it as a subview and retains it in process state. Called from launch/root construction at `0x1030adf7c`. The additional caller Boolean's precise meaning was not established. |
| `0x1033c2cec`, `0x1033c2e50`, `0x1033c3140` | Build the native view, gradient and shape layers. The animation uses Core Animation; it does not require a downloaded animation or JS splash component. |
| `0x1033c4518` onward | Checks Reduce Motion; when false, starts gradient movement and animations keyed `blink` and `look`. Schedules a main-queue work item at now + 1.9 seconds. This fallback deadline is not a measured device display duration. |

The ordinary `SplashScreenViewController` separately loads the packaged
`launch_screen` storyboard (`0x1023988f4`). It should not be conflated with the
experimental second splash. Lottie and cosmic chat assets also exist in the
package; their presence alone does not identify this splash implementation.

## Experiment provider, storage and refresh

The flag wrapper initializer/accessor are `0x104d0a394` / `0x104d0a4dc`.
Its String witness at `0x105d49018` points to `0x104d0bde4`, which delegates
through the injected experimentation provider. Live provider construction at
`0x103341a7c` creates native `EppoExperimentation` (`0x105043388`) and publishes
witness table `0x105d6d8f0`. The String entry resolves to `0x105045788` /
`0x1050457a8`. The splash key is thus connected to the Eppo provider, rather
than classified as remote merely from its name.

Verified provider behavior:

- Initialization (`0x10504a3cc`) constructs a shared-session requester using
  `https://assets.twitch.tv/eppo/api` and resource name `eppo-config.json`,
  registers for app-active notifications and attempts refresh.
- `loadConfigurationForLaunch(named:)` (`0x10504006c`) first reads and decodes
  configuration in Documents. Its failure path reads the packaged resource
  using `URLForResource:withExtension:`. Configuration survives app launches.
- `applicationDidBecomeActive` (`0x105046df8`) invokes the refresh scheduler
  (`0x105044af0`). It checks active app state, an in-flight guard, and elapsed
  monotonic time. The interval comparison is 900 seconds, with a separate
  initial-state bypass. This does not imply background polling or guaranteed
  successful refresh every 15 minutes.
- The asynchronous `refreshFromNetwork()` path (`0x105046eb8` through
  `0x105047134`) obtains requester results, merges configuration through
  `0x105040c9c`, updates state and posts the experiments-refresh notification.
  It JSON-encodes and writes configuration to Documents
  (`0x105047414`–`0x1050474e0`), with separate failure-reporting paths.
- Assignment inputs include app version, release track, device/user context
  and other attributes. Presence of a flag or `enabled=true` alone does not
  prove an assigned variation. Overrides are additional inputs.

The presentation check reads the available provider; it does not synchronously
fetch a flag. A later refresh can persist rules for a subsequent launch.
Per-evaluation memoization and activation timing were not measured on device.

## Bundled rule comparison with 31.6

The parsed rules for `ios-ultralight-second-splash`, `ios-ultralight` and
`ios-ultralight-skyline` match between the two snapshots. Native splash and
experiment code is covered by the prior executable-text comparison; its sole
main-text difference was the unrelated Crashlytics import-slot change.

The splash flag has String variations `false` / `true`, entity ID 144 and
10,000 shards. Its first allocation contains an `app_version` condition with
operator `LTE`, value `31.2.0`, then a true split covering the full shard range.
The fallback allocation selects false. This is not a universal enablement:
the allocation rule must match before the split applies. The native evaluator
was not executed with the device's attributes, overrides or cached rules.

There are 17 added/changed flag records across the snapshots. For example,
`rn-skyline-banner-ads` is absent in the 31.6 resource and present with a true
allocation in 31.6.2. This establishes a bundled configuration difference,
not that a banner was shown, that this donor consumes that flag in a relevant
path, or that it caused a layout defect. Executable equivalence does not
establish feature-activation equivalence.

## Hermes and separate update machinery

The exact HBC matches 31.6 byte-for-byte. Its string table contains no
`ios-ultralight-second-splash` key. Inspected functions
`getSplashDismissedTime` (8252), `setSplashDismissedTime` (8260),
`createHostSplashDismissed` (8263), its stub (8264), and `readSplashAnchor`
(27150) expose/validate dismissal timestamps through `TwitchRNSplashDismissed`
and timing context. They do not implement native second-splash activation.

Hermes also has Eppo infrastructure: `createEppoFlags` (8764),
`parseEppoConfig` (8770), `createEppoClient` (8771), and `loadEppoConfig`
(8772; generator 42576). The loader issues GET requests, checks response
success, parses text and returns null on failure. `resolveClient` (27757)
supports a lazy bundled client; `setClient` (27761) changes the source to
network and notifies subscribers. `getActiveConfigInfo` (27764) exposes
source/environment and configuration creation time. This verifies RN config
infrastructure, not a particular chat flag changing on the reporting device.

`HotUpdater.framework` also includes downloaded-bundle storage, stable/staging
metadata, bundle URL selection, verification and recovery. Its presence does
not establish an OTA download, the app's effective update policy or the HBC
actually used on device. An OTA replacement is unnecessary to explain
activation of the shipped native splash.

## Validation limits and next evidence

Evidence is static inspection of original HBC, ARM64 instructions, Objective-C
metadata, Swift witness dispatch, resources and parsed configuration. Native
UIKit/Eppo code was not executed on Linux; no live configuration endpoint was
queried. Private disassembly and complete donor configuration remain outside
the repository.

The original 31.6.2 IPA hash was rechecked after inspection. Direct byte
comparisons against the original 31.6 main executable also confirmed equality
over the splash region `[0x1033c2b90,0x1033c4a58)`, experiment wrapper region
`[0x104d0a394,0x104d0c250)` and Eppo configuration/provider region
`[0x10503fb6c,0x10504b820)`. Documentation validation passed.

The missing evidence is the affected install's effective configuration and
assignment at the symptom, plus its actual loaded bundle identity. Examine
existing saved configuration and source/creation-time metadata before adding
instrumentation. No flag was forced or disabled. Remote activation is not an
established cause of either intermittent bug.

Related: [hotfix comparison](TWITCH_31_6_HOTFIX_COMPARISON.md),
[composer keyboard trial](RN_COMPOSER_KEYBOARD_TRIAL.md), and
[composer diagnostics](RN_COMPOSER_DIAGNOSTICS.md).
