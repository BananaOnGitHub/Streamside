# Modular diagnostics implementation

Implementation branch: `feat/modular-diagnostic-runtime`, based on
`0a3cf9603f8885d6c2d8433dded227698b047f20` from `dev/3.1.0`.
The historical chat and composer diagnostic branches remain unchanged.
The initial target is exact Twitch 31.6.2 build `262872150334984303`, Hermes 98.
This is active implementation evidence, not device acceptance.

## Checkpoint A: coordinator and immutable registry

The native [core](../../src/TASInvestigation.c) supplies fixed version-1
descriptors for current chat snapshots, chat lifecycle, and reward observation.
Its asynchronous command coordinator keeps pending commands separate from
acknowledged Armed state, rejects stale generations/sequences, invalidates
failed/timed-out commands, and does not expire an acknowledged armed session.
No timers, bridge calls or instrumentation are installed by this core.
Missing runtime admission remains Unsupported. No UI or live adapter exists
at this checkpoint; the core alone cannot activate an investigation.

The allocation-free native JSON reader bounds input to 16 KiB, 256 tokens,
eight nesting levels and 256 UTF-8 bytes per string. It validates UTF-8 and
surrogate pairs, rejects decoded duplicate/unknown keys, integer overflow,
fractional/exponent spellings, incompatible versions/profiles, new event
families and resource expansion. Failed parse clears the output. Remote
configuration cannot introduce executable code, hook locations, selectors,
property paths or transport endpoints. General diagnostic presets are separate.

The [bundled manifest](../../diagnostics/investigations/rn-chat-gaps/1.json)
selects event-driven observation in the first prototype, separate 256/64 event
rings, two current lists, 128 snapshot entries, a 2-second snapshot deadline,
bounded work/rate/identity budgets, and return to Armed after capture.
These are compiled ceilings and manifest choices, not measured device results.
Observation and retention are implemented in later checkpoints.

The exact manifest bytes and SHA-256 pin are generated into a checked-in header.
The host must supply the system cryptographic primitive. An invalid optional
cache is rejected in favor of the separately verified bundle. Only identical
compiled bytes can be accepted from a cache; mutable signed updates and actual
network/disk-cache transport remain unimplemented. The registry index and schema
are authoring artifacts; native validation is the runtime admission authority.

Validation: 12 focused native tests passed, including every manifest truncation,
wrong native/Hermes identities, missing capability readiness, escaped duplicate
keys, narrowed budgets, integrity fallback, late activation, 100 repeated
arm/capture/stop cycles and stale acknowledgments. Ordinary native artifacts
passed verification; the complete host suite ran 205 tests: 201 passed and four
Apple/donor-runtime cases skipped before the new Hermes toolchain was used.
These results do not establish live RN command delivery or device overhead.

The local baseline record is committed as `962aef7`. Local commits use the
explicit agent identity `Codex <codex@localhost>` because a personal Git author
identity is not configured. No global Git settings or remote refs are changed.

## Next validation boundary

The exact pinned Hermes compiler and existing runner have been built locally.
The original donor bundle and React framework are extracted once under the
workspace donor directory. The native-to-JS seam, dormant list attachment,
original callback preservation and real donor accessors still require admission
and executable validation before claiming a working runtime.
