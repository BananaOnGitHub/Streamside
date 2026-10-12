# Documentation

Start at the level that answers your question. Each guide links to the deeper implementation and historical evidence behind it.

## Using Streamside

- [README and installation](../README.md#installation): features, setup, updates, and removal.
- [Compatibility](COMPATIBILITY.md): Twitch/iOS targets, installation evidence, both chat architectures, and limitations.
- [Troubleshooting](TROUBLESHOOTING.md): practical checks and useful reports.
- [Release changes](../CHANGELOG.md): public-release summaries.

## Understanding Streamside

- [Architecture](ARCHITECTURE.md): subsystem relationships, ownership, platform integration, and failure handling.
- [Adblock](features/ADBLOCK.md): VAFT request interception and per-stream playback state.
- [Third-party emotes](features/third-party-emotes/README.md): the feature map and substantial technical deep dives.
- [Diagnostics](features/DIAGNOSTICS.md): counters, logs, privacy, probes, and evidence limits.
- [Upstream](UPSTREAM.md) and [Third-party notices](THIRD_PARTY_NOTICES.md): provenance, maintenance, and attribution.

## Developing Streamside

- [Building](BUILDING.md): ordinary builds, donor tooling, and diagnostic variants.
- [Contributing](../CONTRIBUTING.md): workflow and issue-reporting requirements.
- [Documentation maintenance](development/DOCUMENTATION.md): ownership, update timing, historical preservation, and mechanical validation.
- [Testing](development/TESTING.md): host, Foundation, Hermes, packaging, and device checks.
- [Twitch internals](development/TWITCH_INTERNALS.md): runtime/ABI admission and donor-porting methodology.
- [Packaging](development/PACKAGING.md): binary fingerprints, IPA/DEB contracts, and developer bundles.

## Project history

- [History](HISTORY.md): release/build chronology, failures, corrections, and validation.
- [Research archive](archive/README.md): an indexed record of investigations and experiments.

The current-system guides describe the implementation at `7754dd9`, released version 3.0.0 / internal bundle 3.0.0.92. Archive records retain their original build scope; a historical “pending” statement does not describe the current feature.
