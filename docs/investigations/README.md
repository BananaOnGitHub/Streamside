# Active investigations

This directory holds records made during active work: investigations,
implementation trials, per-build findings, failures, and testing evidence.
Reusable maintainer guidance belongs in [development guides](../development/),
not here.

## 3.1.0 trials

- [Secure investigation updates v2 plan](SECURE_INVESTIGATION_UPDATES_V2_PLAN.md): required future GitHub-backed configuration updates, independent TUF/Ed25519 authorization, trust/cache/activation boundaries and finite implementation gates.

- [Diagnostic v1 hardening acceptance](DIAGNOSTIC_V1_HARDENING_ACCEPTANCE.md): F1–F4 implementation, focused/integration evidence, bounded resource accounting and pending F5/F6 device acceptance.

- [Diagnostic infrastructure completion audit](DIAGNOSTIC_INFRASTRUCTURE_COMPLETION_AUDIT.md): original-brief conformance, implementation/host/device evidence, closure blockers, and the finite F1–F6 completion plan.

- [Modular diagnostics implementation](MODULAR_DIAGNOSTICS_IMPLEMENTATION.md): checkpoint evidence, strict registry/coordinator, runtime admission, and remaining verification.

- [Local diagnostic runtime baseline](LOCAL_DIAGNOSTIC_RUNTIME_BASELINE.md): WSL checkout recovery audit, verified build/test baseline, artifact identities, and missing implementation inputs.

- [Diagnostic categories](DIAGNOSTIC_CATEGORIES.md): launch-applied presets, verbosity, category collection/retention/export, and branch integration.

- [App-icon trial](APP_ICON_TRIAL.md): flat Streamside icon packaging and automatic Liquid Glass appearance observations, build 1.
- [RN composer emote holds](RN_COMPOSER_HOLDS.md): provider attachment holds, native menu fallback, host checks, and device observations, build 2.
- [RN composer cursor requests](RN_COMPOSER_CURSOR.md): build-3 queued-selection guard and build-6 follow-up for late native requests on 31.6.
- [Native emoticon proportions](NATIVE_EMOTICON_PROPORTIONS.md): image-aspect sizing and cold-load layout refresh for classic Twitch emoticons, build 4.
- [Twitch 31.6 compatibility](TWITCH_31_6_COMPATIBILITY.md): build-4 donor inspection, build-5 Hermes port, native ABI comparison, packaging, and pending 31.6 device acceptance.

At feature freeze, reconcile the completed implementation with its owning
[feature documents](../features/). Preserve closed investigation evidence in
[History](../HISTORY.md) or the [archive](../archive/README.md), retaining its
original scope, outcomes, and artifact identities. Follow
[Documentation maintenance](../development/DOCUMENTATION.md) when moving records
and updating navigation.

- [Provider WebP animation trial](WEBP_ANIMATION_TRIAL.md) — build 14 passed RN checks; build 15 restores legacy animation and addresses taps/picker focus; build 16 fast-emote speeds confirmed in legacy; build 17 restores the native compact transition after extended-library selection.

- [Twitch 31.6 hotfix comparison](TWITCH_31_6_HOTFIX_COMPARISON.md): read-only 31.6.1/31.6.2 donor identities, RN chat/reward behavior, patch admission and native/WebP/playback boundaries.
- [Twitch 31.6.2 candidate](TWITCH_31_6_2_CANDIDATE.md): build 18 uses the unchanged exact-body integration; host/package checks and unsigned IPA identity, pending device validation.
