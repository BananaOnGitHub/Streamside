# Active investigations

This directory holds records made during active work: investigations,
implementation trials, per-build findings, failures, and testing evidence.
Reusable maintainer guidance belongs in [development guides](../development/),
not here.

## 3.1.0 trials

- [App-icon trial](APP_ICON_TRIAL.md): flat Streamside icon packaging and automatic Liquid Glass appearance observations, build 1.
- [RN composer emote holds](RN_COMPOSER_HOLDS.md): provider attachment holds, native menu fallback, host checks, and device observations, build 2.
- [RN composer cursor requests](RN_COMPOSER_CURSOR.md): stale queued/late selection requests during continued typing, build 3.
- [Native emoticon proportions](NATIVE_EMOTICON_PROPORTIONS.md): image-aspect sizing and cold-load layout refresh for classic Twitch emoticons, build 4.
- [Twitch 31.6 compatibility](TWITCH_31_6_COMPATIBILITY.md): build-4 donor inspection, build-5 Hermes port, native ABI comparison, packaging, and pending 31.6 device acceptance.

At feature freeze, reconcile the completed implementation with its owning
[feature documents](../features/). Preserve closed investigation evidence in
[History](../HISTORY.md) or the [archive](../archive/README.md), retaining its
original scope, outcomes, and artifact identities. Follow
[Documentation maintenance](../development/DOCUMENTATION.md) when moving records
and updating navigation.
