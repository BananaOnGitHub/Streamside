# TwitchAdBlock VAFT iOS 2.2.1

**Sideload IPA for Twitch 30.4.2 (arm64).** Sign the IPA with your normal
sideloading tool before installing it.

The app display name and bundle name shown on the device are **Twitch VAFT**.

This replacement is built from the source in this repository. The IPA embeds
the same R5 diagnostics implementation used by the rootful and rootless
jailbreak packages: opt-in process-local channel and resource labels, route
registration and retirement history, and the main Profile → Settings button
guard. Logging starts off. The older diagnostic log containing request paths
is removed at initialization.

The earlier binary-staged 2.2.1 IPA was confirmed on an iPhone. This new
source-built replacement passed build and package checks, but **has not been
tested on a device**. It is a prerelease pending device confirmation. The
button guard currently recognizes the English `Settings` title.

Asset: `Twitch_30.4.2_TAS-VAFT_2.2.1.ipa`

SHA-256: `680749f6dfe9c0a28eecbdc4aca6a6a764ab62533e8401e6629f46f50a13dd75`
