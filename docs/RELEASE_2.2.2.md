# TwitchAdBlock VAFT iOS 2.2.2

**Sideload IPA for Twitch 30.4.2 (arm64).** Sign the IPA with your normal
sideloading tool before installing it.

R5's opt-in diagnostic privacy labels and route history are now in the Git
source. This IPA uses the same source-built implementation as the separate
rootful and rootless jailbreak packages. Logging starts off. Channel names and
URLs are replaced by temporary labels in the log; the older log containing URL
paths is removed at initialization. Unmapped variants report active and
retired route counts, age, generation, and retirement reason.

The Ad Block button remains scoped to Profile → Settings. This reconstructed
build passed local build and package checks but has **not** been tested on an
iPhone. The previously tested 2.2.1 IPA was a separately staged binary, so
2.2.2 is a prerelease pending device confirmation.

Asset: `Twitch_30.4.2_TAS-VAFT_2.2.2.ipa`

SHA-256: `db7e47eecafa0edf284905c39ecea8a620ec53efc682d717cddaff6aae7178de`
