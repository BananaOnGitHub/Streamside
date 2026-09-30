# TwitchAdBlock-VAFT-iOS

A native iOS port of the **VAFT** strategy from
[pixeltris/TwitchAdSolutions](https://github.com/pixeltris/TwitchAdSolutions).
It supports both sideloaded decrypted copies of Twitch and jailbroken devices.

The sideload and jailbreak builds come from the same checked-in source.
Version 2.3.1 is prepared, not published: it removes the donor loader identity
and makes the 16 KiB Mach-O layout a checked build-to-package contract.

## Status

- Published sideload IPA: **2.3.0**; jailbreak packages: **2.3.0**
- Prepared source: **2.3.1** (Streamside loader and enforced packaging checks)
- Upstream strategy: **VAFT solution 24**
- Tested app version: **Twitch 30.4.2, arm64**
  - Emotes were device-confirmed on an iPhone 16 Pro running iOS 18.2 with dev.8. The corrected loader trial launches; newly compiled 2.3.1 still needs its own device test.
- Previously tested installation paths: ESign and LiveContainer/ZSign

Other Twitch versions may work, but Twitch can change its GraphQL, HLS, or
Amazon IVS behavior without notice.

## What it does

- Intercepts Twitch playback-token and HLS requests without private Twitch
  symbols.
- Tries VAFT's `embed`, `popout`, and `autoplay` player types when an ad-bearing
  playlist is detected.
- Matches alternate renditions by resolution and frame rate.
- Falls back to suppressing stitched ad segments when clean alternates are not
  available.
- Maintains isolated state for simultaneous streams, including Twitch mobile's
  PiP player and muted profile previews.
- Adds an Ad Block settings page with opt-in, sanitized diagnostics.

### Third-party emotes (2.3.0)

The shared source now includes optional 7TV, BTTV, and FFZ global and channel
emotes for chat messages. Open **Profile → Settings → Ad Block** to
enable them, then relaunch Twitch. They are off by default. Turning them off
and relaunching skips the emote hooks and provider requests altogether.

**Clear Emote Cache** is on the Ad Block page. It discards this module's
in-memory emote definitions and image-ID mappings; the next incoming chat
message refetches the current channel. It does not clear Twitch's unrelated
image cache. **Reload Emotes** is intended to appear in the stream's Chat
Settings sheet and refresh global and current channel definitions.

The module retains at most six recently active channel registries, up to 4,000
names each, and 2,500 global names. Inactive rooms expire after 20 minutes.
Provider JSON responses are accepted up to 8 MiB, including large 7TV sets.
Evicted image IDs have a bounded 45-minute grace period to allow existing chat
cells to redraw. It maintains no separate image files or decoded image cache.

Incoming static and animated emotes, the scrolling Reload Emotes row, provider
tap details, proportional image widths, and emotes in your own sent messages
were all device-confirmed on Twitch 30.4.2. The detail sheet has a preview,
provider/scope, available creator credit, Copy name, Copy image URL, and Open in
browser. Diagnostics record delivery, sizing, image-layer, and tap activity
without retaining chat text or image URLs.

The sideload build uses `Streamside.framework/Streamside` with the required
`@rpath/Streamside.framework/Streamside` dependency. Its binary is this project's
native C dylib; initialization does not depend on a donor runtime. Jailbreak
packages retain `TwitchAdBlock.dylib` and the package ID for upgrades.

## Diagnostics

Open **Profile → Settings (cog) → Ad Block**. The diagnostics page provides:

- A persistent logging toggle.
- A live session summary and sanitized event log.
- One-tap report copying.
- Log clearing.

Diagnostics distinguish intercepted and missed HLS requests, master and variant
playlists, unmapped variants, known ad markers, access-token failures, VAFT
candidate results, clean swaps, and segment suppression. Channel names and
URLs are replaced by temporary process-local labels in the log. Route history
records active and retired matches, generations, and ages for unmapped variants.
The report also lists emote hook installation, WebSocket frame stages, provider
fetch outcomes, image response categories, and chat-menu presentation counts. These
aggregate counters appear even when event logging is off. They do not contain
chat text or room IDs.
Logging starts off; URL paths, request headers, access tokens, and manifest
contents are not written to the diagnostic log. On first load, this version
deletes the older path-bearing `diagnostics.log`. The new log is capped at
512 KiB and rotates automatically. Labels reset after Twitch restarts, or
sooner if the bounded label table fills.

For a playback regression, enable logging, reproduce the failure, then copy the
diagnostic report from the same page.

## Install from a release

Published standard releases contain the IPA only; sign it with your sideloading
tool. Version 2.3.1 has not been published. To prepare the current source locally,
build the framework as described below and patch a decrypted IPA.

Requirements:

- A decrypted Twitch IPA
- Python 3.10 or newer
- A sideloading/signing tool

After `make verify`, run:

```bash
python3 tools/patch_ipa.py Twitch.ipa \
  --framework build/Streamside.framework \
  --output Twitch-VAFT.ipa
```

The resulting IPA is unsigned. Sign `Twitch-VAFT.ipa` with your normal
sideloading tool before installing it.

The patcher:

- Refuses encrypted executables.
- Refuses a missing build fingerprint or a framework changed since validation.
- Validates 16 KiB segment ranges, exact loader/signing identity, signature
  placement and space, linkedit bounds, and every CodeDirectory page hash.
- Removes old donor dylib/framework load commands and embedded components.
- Adds exactly one required `@rpath/Streamside.framework/Streamside` command
  using existing Mach-O header padding (never a weak load).
- Reads back the finished IPA and compares its framework byte-for-byte with
  the verified build, then atomically installs the output filename.
- Preserves unrelated entries and verifies the SHA-256 of `Assets.car`.

`build/Streamside.framework.macho.json` is the required build fingerprint.
Keep it alongside the framework when moving it to another machine; packaging
never regenerates a missing fingerprint or silently normalizes its input.
For a separate unsigned final-package check:

```bash
python3 tools/verify_ipa.py Twitch-VAFT.ipa --framework build/Streamside.framework
```

## Install on a jailbroken device

Separate `-jb` prereleases include two standalone packages:

- `iphoneos-arm` for traditional rootful jailbreaks.
- `iphoneos-arm64` for rootless jailbreaks using the `/var/jb` layout.

Install the package matching the jailbreak, then restart Twitch. The filter is
scoped to the `tv.twitch` bundle and does not patch the app executable. It can
therefore be used with the newest Twitch version supported by the device's iOS
version. The package conflicts with level3tjg's TwitchAdBlock because both
projects intercept the same playback stack.

## Build from source

Install [Zig 0.14.0](https://ziglang.org/download/0.14.0/) and run:

```bash
make verify
make test
```

To use a Zig binary outside `PATH`:

```bash
ZIG=/path/to/zig make verify
```

The build produces both identities:

- `build/TwitchAdBlock.dylib` for rootful/rootless jailbreak packages.
- `build/Streamside.framework` for sideload IPA patching.
- Adjacent `.macho.json` fingerprints required by the packagers.

`make deb` prepares jailbreak packages locally and checks their data archive
bytes. `make ipa INPUT_IPA=/path/to/Twitch.ipa OUTPUT_IPA=/path/to/output.ipa`
builds, tests, and prepares an unsigned IPA. Neither command publishes anything.
`make release` is a local developer-bundle command, not GitHub publication.
ZIPs and checksum files are internal build artifacts, not release attachments.
Standard public releases are IPA-only; `-jb` prereleases are DEB-only and retain
the existing exact jailbreak warning. Publication requires separate approval.

## Troubleshooting

### The signer says it cannot sign the dylib

Use the verified `Streamside.framework` build for sideloaded IPAs. Its Mach-O
layout is normalized to the 16 KiB segment boundaries required by the tested
iOS signing paths. The jailbreak dylib retains a 64 KiB replacement-signature
reservation. The framework wrapper is retained; switching to a bare sideload
dylib is a separate, untested migration.

### Packaging refuses a hash or layout mismatch

Do not bypass the check or regenerate the fingerprint over a replacement
binary. Rebuild from the intended source with `make verify`, and package those
exact outputs. Matching source labels or filenames do not establish binary
equivalence. Tests recreate the segment-size regression and corrupt finished
archives to ensure these paths fail closed.

### The app launches logged out but crashes after login

Verify that the input IPA contains the complete `Assets.car`. Twitch force-loads
signed-in navigation assets; a truncated asset catalog can survive the login
screen and then crash during scene creation. The included patcher refuses an IPA
with no asset catalog and verifies its CRC after repackaging.

### PiP and profile previews interfere with one another

Upgrade to 2.0.3 or newer. Older native builds used one global VAFT context and
could substitute one player's clean playlist into another player.

Playback reports should include the Twitch and iOS versions, installation
method, failure type, and the copied diagnostic report. Remove anything you do
not want to share before posting it.

See [Architecture](docs/ARCHITECTURE.md), [Version history](docs/HISTORY.md),
[Contributing](CONTRIBUTING.md), and [Upstream provenance](UPSTREAM.md) for more
detail.

## License and attribution

The native port is Apache-2.0 licensed.

This project is not affiliated with Twitch Interactive, Inc., Amazon.com, Inc.,
pixeltris, level3tjg, or the Tweach project. Twitch is a trademark of its
respective owner.
