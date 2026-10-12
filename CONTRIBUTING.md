# Contributing

Bug reports and focused pull requests are welcome. Start with [Architecture](docs/ARCHITECTURE.md), then the guide for the subsystem you want to change.

## Report a problem

Include the Twitch app/build, iOS version, device, Streamside version/build, installation method, and clear reproduction steps. Say what happened and what you expected.

For playback, distinguish preroll, midroll, PiP, profile preview, and account sign-in state. For emotes, distinguish incoming/sent messages, composer, suggestions, library, details, RN/legacy, and static/animated/wide cases.

Copy the in-app diagnostic report after reproduction. Logging is opt-in; aggregate counters are still available with logging off. Reports from the same launch are easier to compare than unrelated cumulative sessions.

Crop screenshots and redact private chat. Do not include tokens, signing certificates, provisioning profiles, client-integrity values, or raw authenticated requests. See [Security](SECURITY.md) and [Diagnostics](docs/features/DIAGNOSTICS.md).

## Development workflow

1. Work on a focused development branch based on current `main`.
2. Preserve unrelated work and keep behavior changes separate from diagnostic-only experiments where practical.
3. Read current callers/state owners, not only a historical trial.
4. Add a regression for the actual production helper/adapter boundary.
5. Run the relevant gates and record pass/fail/skip status accurately.
6. Record development findings during active work; reconcile affected guides and the changelog with completed work at feature freeze. Correct inaccurate security or compatibility information immediately. See [Documentation maintenance](docs/development/DOCUMENTATION.md).

Archived branches preserve research; they are not active implementation branches. `archive/compat/twitch-31.5` records the completed compatibility line, and `archive/diagnostic/` contains independent probe histories.

## Required checks

```sh
make verify
make test
make deb
```

Native builds treat warnings as errors. Stream-routing changes must preserve `TASStreamContext` ownership/generations. Image changes must preserve request-variant identity, stop/completion rules, cache correctness, and bounded admission.

On macOS:

```sh
make test-foundation-cache
```

RN library changes and donor ports also require `make test-rn-virtualization` with the five explicit runtime/donor variables described in [Building](docs/BUILDING.md). A skipped optional unittest is not a passing mandatory gate.

Public CI runs Linux build/package/host tests and macOS Foundation cache integration. It does not run the private-donor Hermes gate or device checks. [Testing](docs/development/TESTING.md) defines each evidence boundary.

## Native/runtime changes

Validate complete Objective-C encodings and exact class/field spans before installing an adapter. Do not assume a Swift weak existential is an ObjC weak pointer or fabricate Swift model values from guessed storage.

Plain C blocks require explicit object lifetime ownership. Audit creation failure, cancellation, stale generations, completion, and teardown, not only the successful callback.

Preserve Twitch's native message/draft/catalog authority. Unknown layouts should retain native behavior rather than using a best-effort offset.

## Diagnostics and documentation

Keep probes bounded, scoped, privacy-safe, and compiled out of ordinary builds. Record what they observe and what remains unknown. Avoid using a render attempt, cache object, or load callback as proof of physical display.

Run `make docs-check` for documentation edits, linked-file moves, and current version metadata changes. The separate Documentation CI gate checks local references and metadata, including archived Markdown, without generating or rewriting docs. [Testing](docs/development/TESTING.md#documentation-integrity) defines its scope.

The README owns installation. Architecture owns subsystem relationships. Feature guides own algorithms/lifecycle. History/archive own failed trials and superseding corrections. Do not copy the same implementation explanation into every layer.

## Upstream and packaging changes

Update the VAFT source, pin/version/hash, [Upstream](docs/UPSTREAM.md), and required notices together. Review native-port differences explicitly.

Do not bypass binary fingerprints or normalize a different binary during packaging. [Packaging](docs/development/PACKAGING.md) covers artifact preparation and binary contracts; [Testing](docs/development/TESTING.md) defines the required validation and device evidence.
