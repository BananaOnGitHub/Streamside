# TwitchAdBlock VAFT iOS 2.2.1

**Sideload IPA for Twitch 30.4.2 (arm64).** Sign the IPA with your normal
sideloading tool before installing it.

This update adds opt-in playback diagnostics with temporary channel and
playlist labels and route history. Logging remains off until you enable it.
Labels stay consistent while Twitch is running and reset after Twitch restarts.
The app now explains that behavior in the Ad Block settings page and report.

The Ad Block button appears in Profile → Settings. It no longer appears on
Chat Identity or other settings pages. The R7 candidate was confirmed on an
iPhone to restore the button; the 2.2.1 IPA has the same executable code, with
only its build label and signature hashes changed.

Asset: `Twitch_30.4.2_TAS-VAFT_2.2.1.ipa`

SHA-256: `d564eaa9c705103b110709f6e631d2fd362d58f688423422ff122cc85ff0b1a4`

This is an **IPA-only release**. The newer diagnostics source was not retained
in the repository. The separate source-built 2.2.1-jb prerelease has the
Settings button fix but does not include these R5 diagnostic changes.
The staging script in `tools/stage_r5_production.py` documents the exact R5
input IPA and applies the small 2.2.1 UI and wording patch to its framework.
The button guard recognizes the English `Settings` title.
