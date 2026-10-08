# Streamside

A native iOS port of the **VAFT** strategy from
[pixeltris/TwitchAdSolutions](https://github.com/pixeltris/TwitchAdSolutions).
It supports both sideloaded decrypted copies of Twitch and jailbroken devices.

The sideload and jailbreak builds come from the same checked-in source.
Version **3.0.0** is in preparation. The installed sideload app is named
**Twitch Streamside**. This update adds a third-party emote composer and keyboard
library while retaining the enforced 16 KiB Mach-O build-to-package contract.
Publication is on hold for device testing and the forthcoming logo.

## Status

- Published sideload IPA: **2.3.0**; jailbreak packages: **2.3.0**
- Prepared source: **3.0.0** (compatibility bundle build `3.0.0.66`)
- Upstream strategy: **VAFT solution 24**
- Target app: **Twitch 31.5, arm64**, with the active React Native chat.
  - Builds 51–54 established the receive and presentation boundaries on the
    separate diagnostic branch. Build 55 is the first incoming-only synthetic-ID
    rendering experiment. Device reports B/C confirm observed correct static and
    animated images, with animation continuing after scrolling. Build 56's
    proportional incoming width is device-confirmed for the user's tested cases.
    Build 59 reached local-preview export discovery but hid sent messages before
    any native preview call. Build 60 corrects its outgoing call-frame overlap
    and adds exception fallback to original emission. The user confirms sent
    messages and emotes now render correctly. Build 61 adds channel-scoped
    provider preview maps to the active native text input. Its device trial
    produces a placeholder without an image. Build 62 covers the native input's
    URL-based completion transport, which bypassed the request redirects;
    images are device-confirmed but appear square and static. Build 63 adds
    provider-only native attachment widths and independent GIF preview clocks.
    Width is device-confirmed; GIFs play after deleting and retyping, but miss
    first-download startup. Build 64 tracks pending inputs before decoder
    creation so the existing download completion can start the original
    attachment. The user confirms that correction works. Diagnostic build 65
    confirms provider taps reach the RN emote sheet but never its query-backed
    content. Build 66 adds a provider RN card within the existing bottom sheet,
    preserving Twitch's card for native IDs. The new popup awaits device
    validation; see [the trial notes](docs/RN_PROVIDER_INFO_TRIAL.md).
  - Build 50's adapter targets legacy chat present in the donor binary, not the
    active RN interface. That baseline is preserved in
    `archive/twitch-31.5-build50-legacy-chat`.
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
- Adds a Streamside settings page with opt-in, sanitized diagnostics.

### Third-party emotes

The shared source now includes optional 7TV, BTTV, and FFZ global and channel
emotes for chat messages. Open **Profile → Settings → Streamside** to
enable them, then relaunch Twitch. They are off by default. Turning them off
and relaunching skips the emote hooks and provider requests altogether.

**Clear Emote Cache** is on the Streamside page. It discards this module's
in-memory emote definitions and image-ID mappings; the next incoming chat
message refetches the current channel. It does not clear Twitch's unrelated
image cache. **Reload Emotes** is intended to appear in the stream's Chat
Settings sheet and refresh global and current channel definitions.

The module retains at most six recently active channel registries, up to 4,000
names each, and 2,500 global names. Inactive rooms expire after 20 minutes.
Provider JSON responses are accepted up to 8 MiB, including large 7TV sets.
Evicted image IDs have a bounded 45-minute grace period to allow existing chat
cells to redraw. It maintains no separate image files. The composer keeps a bounded, in-memory
thumbnail cache (96 entries, 16 MiB cost limit), with at most eight concurrent
image requests. It does not clear Twitch’s own image cache.

The confirmed RN IRC delegate reuses the matcher to append synthetic IDs to
incoming `emotes=` metadata. The image redirect resolves synthetic Twitch CDN
requests to provider assets. Build 55 device observations confirmed rendering
and continued animation after scrolling. Build 56 adds an exact-bundle-gated,
in-memory EmotePart style patch: the image and inline wrapper get the same
proportional width before Fabric measures them. The donor bundle on disk and
native emote styles stay unchanged. Build 59 adds provider-only ranges to
LibraryTmiClient's completed own-message display line, preserving its native
range objects, body and identity. Builds 57/58 recorded zero local callbacks;
their TmiClient preview seam belongs to a separate client. Build 59 uses the
LibraryTmiClient own event and the existing NativeModules loader. Local device
rendering is device-confirmed after build 60's call-frame correction. It reuses
the image/width route. Catalog, picker and tap-detail remain deferred. Build 63
adds animation only to native text-box provider attachments. See the
[incoming rendering trial](docs/RN_INCOMING_SYNTHETIC_TRIAL.md) and
[width experiment and device test](docs/RN_INCOMING_WIDTH_TRIAL.md) and
[local sent-message trial](docs/RN_LOCAL_ECHO_TRIAL.md).
The [native text-box trial](docs/RN_COMPOSER_PREVIEW_TRIAL.md) covers build 63's
proportional sizing and bounded GIF playback; non-GIF images retain native
decoding and still-image fallback.
The [build-50 report](docs/TWITCH_31_5_PRESENTATION_TRIAL.md) describes legacy chat
only; its TextKit/layer sizing does not establish RN/Fabric proportional widths.
Historical validation of the
Reload Emotes row, provider tap details, proportional image widths and sent
emotes is recorded separately. The detail sheet has a preview,
provider/scope, available creator credit, Copy name, Copy image URL, and Open in
browser. Diagnostics record delivery, sizing, image-layer, and tap activity
without retaining chat text or image URLs.

The sideload build uses `Streamside.framework/Streamside` with the required
`@rpath/Streamside.framework/Streamside` dependency. Its binary is this project's
native C dylib; initialization does not depend on a donor runtime. Jailbreak
packages use `Streamside.dylib`; the existing package ID is retained for upgrades.

### Composer and picker (3.0.0 candidate)

- A compact horizontal suggestion strip appears above the chat box. Choose
  **Automatic**, **Colon (:name)**, or **Off** in Streamside settings. Automatic
  completion starts after two characters; colon completion opens on `:`.
- Tap a suggestion to replace the current prefix with the emote name and a space.
  Recognized third-party names become proportional image previews in the editor;
  Twitch receives the original names when editing or sending. Native Twitch
  attachments remain intact. Composer previews use a still image; GIF thumbnails
  animate when Twitch's `FLAnimatedImageView` is available.
- Open Twitch's smiley keyboard and select the additional **Third-party emotes**
  footer button. Its provider selector has **All / 7TV / BTTV / FFZ**, followed
  by **Channel / Global**. Changing the provider resets the scope to Channel.
- The native **Recent** tab includes a provider-emote row above Twitch's own
  entries. Up to 40 recent names persist locally and are resolved against the
  current channel; unavailable names are omitted. Twitch's native history is
  preserved.
- The integration resolves the channel from the input view, not the last
  background-chat frame. It checks native method encodings and the inspected
  identity layout; unsupported bridges report missing hooks in diagnostics.

The logo is pending. The current icon and `Assets.car` are preserved. The future
logo must support UIKit's dynamic appearance/background and tint behavior; that
requirement is for the logo.

## Diagnostics

Open **Profile → Settings (cog) → Streamside**. The diagnostics page provides:

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
tool. Version 3.0.0 has not been published. To prepare the current source locally,
build the framework as described below and patch a decrypted IPA.

Requirements:

- A decrypted Twitch IPA
- Python 3.10 or newer
- A sideloading/signing tool

After `make verify`, run:

```bash
python3 tools/patch_ipa.py Twitch.ipa \
  --framework build/Streamside.framework \
  --output Twitch-Streamside.ipa
```

The resulting IPA is unsigned. Sign `Twitch-Streamside.ipa` with your normal
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
python3 tools/verify_ipa.py Twitch-Streamside.ipa --framework build/Streamside.framework
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
ZIG=/path/to/zig make verify test
```

The build produces both identities:

- `build/Streamside.dylib` for rootful/rootless jailbreak packages.
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
