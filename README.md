<p align="center">
  <img src="docs/assets/streamsidelogo.png" alt="Streamside logo" width="160">
</p>

# Streamside

**More emotes and VAFT-based ad blocking for Twitch on iOS.**

Streamside brings 7TV, BetterTTV, and FrankerFaceZ into the Twitch app you already use, with VAFT-based ad blocking and a few extra comforts for chatting.

Find your favorite emotes, preview them while you type, and see animated and wide emotes in chat. Everything fits into Twitch's own chat and emote keyboard, so you can keep watching and chatting where you're used to.

## Features

- **Ad blocking** — VAFT-based filtering for Twitch streams, with support for the main player, Picture in Picture, and channel previews.
- **7TV, BTTV, and FFZ** — See third-party emotes in chat and in ordinary messages you send.
- **Animated and wide emotes** — Keep their animation and proper proportions.
- **Emote suggestions** — Find Twitch and third-party emotes together as you type, with Automatic, Colon, and Off modes.
- **An expanded emote picker** — Browse by provider, switch between channel and global emotes, and revisit recently used ones. Names appear below each thumbnail.
- **Composer previews** — See emotes before sending, including supported animated GIFs. Backspace removes a whole emote at once.
- **Emote details** — Open a preview, see creator credit when available, copy an emote's name or link, and visit its provider page.
- **Built into Twitch** — Use Twitch's familiar chat and keyboard. Refresh the emote list from Chat Settings when you need to.

**3.0.0 is being prepared for release.** These features describe the upcoming version for Twitch 31.5. The latest published IPA is 2.3.0 for Twitch 30.4.2; it does not include the new React Native composer and library. Check the release notes before downloading.

## Compatibility

| Distribution | Twitch target | Installation | Status |
| --- | --- | --- | --- |
| Published 2.3.0 IPA | 30.4.2, arm64 | Sign the released IPA | Published; see its release notes and compatibility details |
| Upcoming 3.0.0 | 31.5, arm64 | Sideloaded patched IPA | In preparation; not yet published |
| Separate `-jb` prereleases | Version listed in the release | Rootful or rootless DEB | Build/package checks; not confirmed on a jailbroken device |

Twitch 31.5 requires iOS 16.4 or later. Streamside supports both of its chat interfaces: React Native and legacy UIKit. Device and signing compatibility also matter; meeting the minimum iOS version is only part of the picture. Earlier ESign and LiveContainer/ZSign results apply to the 30.4.2 builds they were tested with.

See [Compatibility](docs/COMPATIBILITY.md) for the complete evidence and limitations.

## Installation

Start with a [compatible release](https://github.com/BananaOnGitHub/Streamside/releases), then choose the installation method below.

### Sideload a release

1. Open [Releases](https://github.com/BananaOnGitHub/Streamside/releases) and choose the standard IPA release matching the Twitch version you intend to use.
2. Download the attached IPA. GitHub's automatically generated source archives are not installable apps.
3. Sign and install it with your sideloading tool. Released IPAs are unsigned; certificate, provisioning, and container requirements belong to the chosen installation tool.
4. Open **Twitch Streamside** for the prepared 3.0.0 build. Older releases may use the previous **Twitch VAFT** display name.
5. Open **Profile → Settings → Streamside**. Enable third-party emotes, then fully quit and reopen Twitch. Emotes are off by default.

To build the upcoming 3.0.0 version yourself, follow [Building](docs/BUILDING.md). You'll need a compatible decrypted Twitch IPA for a source build; installing a published release does not require one.

### Install a jailbreak package

Use the separate `-jb` release and choose the package matching your jailbreak:

- `iphoneos-arm`: traditional rootful layout.
- `iphoneos-arm64`: rootless layout under `/var/jb`.

Install the DEB with your package manager and restart Twitch. Injection is limited to the `tv.twitch` app. The package conflicts with level3tjg's TwitchAdBlock because both modify the playback stack.

Jailbreak packages have passed build and packaging checks, but have not been tested on a jailbroken device. Do not install both playback tweaks together.

### Update or remove

For a sideloaded app, use the same installation tool to install a compatible newer IPA. Check that tool's backup and update guidance first: deleting the app can remove its settings and recent emotes. If an update changes Twitch versions, check [Compatibility](docs/COMPATIBILITY.md) again.

For a jailbreak installation, upgrade or uninstall `dev.tas.twitchadblock` through the package manager, then restart Twitch. The package identifier is retained even though the project is now called Streamside.

## Using emotes

In **Automatic** mode, start typing an emote name to see suggestions. In **Colon** mode, begin with `:`. Tap a suggestion to insert the emote. Choose **Off** if you prefer browsing the picker; emotes still work in chat and the library.

Open Twitch's emote keyboard and choose **Third-party emotes** to browse the library. Use the provider tabs and **Channel / Global** switch to narrow it down, then scroll sideways through the five-row grid. Recently used emotes stay in place while the menu is open and update when you reopen it.

Missing a newly added emote? Try **Reload Emotes** in the stream's Chat Settings. **Clear Emote Cache** on the Streamside settings page resets Streamside's saved definitions and image mappings; it does not clear all downloaded images.

iOS keyboard predictions stay as text until you accept them. If an emote keeps showing as its name, its catalog may still be loading, or the installed Twitch version may be incompatible. [Troubleshooting](docs/TROUBLESHOOTING.md) has a few things to check.

## Troubleshooting and support

Something not working? Start with [Troubleshooting](docs/TROUBLESHOOTING.md). If you need to [report an issue](https://github.com/BananaOnGitHub/Streamside/issues), include your Twitch and iOS versions, installation method, and steps to reproduce it.

For playback issues, say whether it was a preroll, midroll, Picture in Picture, or channel preview. Enable diagnostic logging under **Profile → Settings → Streamside**, reproduce the problem, and copy the report from that session.

For emote issues, mention where they happen: chat, the message box, suggestions, or the library. A screenshot helps; crop unrelated chat and private information.

[Troubleshooting](docs/TROUBLESHOOTING.md) · [Report an issue](https://github.com/BananaOnGitHub/Streamside/issues) · [Contributing](CONTRIBUTING.md)

Never post account tokens, signing certificates, provisioning profiles, or raw authenticated requests. [Security guidance](SECURITY.md) explains what to leave out.

## Learn more

[Release changes](CHANGELOG.md) · [Documentation index](docs/README.md) · [Architecture](docs/ARCHITECTURE.md) · [Emote deep dives](docs/features/third-party-emotes/README.md) · [Project history](docs/HISTORY.md)

## License and attribution

Streamside's native implementation is [Apache-2.0 licensed](LICENSE). VAFT and the emote references are credited in [Third-party notices](docs/THIRD_PARTY_NOTICES.md).

Streamside is not affiliated with Twitch or Amazon. Twitch is a trademark of its respective owner.
