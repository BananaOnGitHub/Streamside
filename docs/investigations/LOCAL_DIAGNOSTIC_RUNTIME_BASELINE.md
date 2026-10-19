# Local diagnostic runtime baseline — 2026-10-19

## Workspace and source

The persistent checkout is `/home/bananas/Agent-Stuff/streamside`, on the
WSL2 Linux ext4 filesystem. The local `dev/3.1.0` branch tracks
`origin/dev/3.1.0` at `0a3cf9603f8885d6c2d8433dded227698b047f20`.
The checkout was initially clean on `main` at
`2f81a409c143644e3e2e11f016a3de970e49ef7b`.

An upstream heads query confirmed these cached references were current:

| Reference | Commit |
| --- | --- |
| `main` | `2f81a409c143644e3e2e11f016a3de970e49ef7b` |
| `dev/3.1.0` | `0a3cf9603f8885d6c2d8433dded227698b047f20` |
| `fix/rn-chat-gaps` | `e26a4e2f166872a970f35d81e8bc0c41236f326d` |
| `fix/rn-composer-diagnostics` | `d58b1323951fcfe0adcf34962125bada0341ccca` |

No independent clone or worktree was created. An unused local
`feat/modular-diagnostic-runtime` reference also points to the same development
baseline; implementation work belongs on `dev/3.1.0`.
The historical branches and their records remain unchanged.

## Recovery findings

The initial worktree inventory contained only this checkout. There were no
stashes, local source modifications, or unreachable objects reported by
`git fsck --no-reflogs --unreachable`. The reflogs contained only the local clone
at `main`; they did not contain a later modular-runtime checkpoint.

The available branch trees and history did not reveal a modular diagnostic
runtime, capability registry, or new flight-recorder implementation.
The specialized prior observer remains available on `origin/fix/rn-chat-gaps`:
`src/rn/ChatTrace.js`, `src/TASChatTrace.c`, its bridge/graft headers, tests,
validation tools, and `docs/investigations/RN_CHAT_ROW_GAPS.md`.
Those are earlier diagnostic experiments, not recovered implementation of the
new modular runtime. No branches, objects, or historical findings were discarded.

## Local build and tests

The initial environment supplied Git, Python 3.14.4, GCC 15.2.0 and Make.
Zig, a matching Hermes compiler/runner/source checkout, CMake, Ninja and Apple
build tools were absent from PATH. The bundled Node runtime was available at
`/home/bananas/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node`.

Zig 0.14.0 was installed under `build/toolchains/zig-0.14.0/` in this checkout.
Its official Linux archive was checked against the existing CI SHA-256 pin:
`473ec26806133cf4d1918caf1a410f8403a13d979726a9045b421b685031a982`.
The toolchain, caches and generated artifacts remain in ignored `build/`.

An initial focused diagnostics run passed six cases and failed its transport
case because Zig was missing. No source change was made to bypass that failure.
After installing Zig, `make verify test` passed at the source revision above:

- Both ordinary native artifacts passed WebP symbol and Mach-O artifact checks.
- The suite ran 193 tests: 189 passed, four skipped, zero failures.
- Skips were real Apple Foundation, real Apple ImageIO, compiled donor/Hermes
  execution, and the exact-donor settings registration check.
- The 29 documentation-validator tests passed. Repository documentation
  validation checked 76 Markdown files and 716 explicit references with no errors
  before this record was added.

The log is `build/local-baseline-2026-10-19.log`, SHA-256
`27de08f003be2fab252b7899c2cc52508f8c57f64865d766e3b5f80143aba126`.
Success messages emitted by gate-record fixtures do not establish that the
skipped real-donor/Hermes execution ran.

## Baseline artifacts

These artifacts contain the existing build-18 implementation, with no new
modular diagnostics code:

| Artifact | SHA-256 |
| --- | --- |
| `build/Streamside.dylib` | `21130bff1452338766c715f5f05474db9abdecf2d106f51233ad754f390d3707` |
| `build/Streamside.framework/Streamside` | `ae9b15de1e161f8d62463e450a82f5c9897b7342a00ddaa4696a391b4f286086` |

Matching receipts are `build/Streamside.dylib.macho.json` and
`build/Streamside.framework.macho.json`. No IPA was found or produced locally.
The [earlier candidate record](TWITCH_31_6_2_CANDIDATE.md) preserves historical
package identities; those identities do not mean that its package exists here.

## Outstanding inputs and verification

`MODULAR_DIAGNOSTIC_RUNTIME_PROPOSAL.md` and the original functional brief
`investigation implementation(1)(1).md` were not found in the inspected local
files, available branch trees or recorded Git paths. Their contents have not
been verified. Architecture conformance cannot be established without the
proposal; no replacement architecture was invented during this baseline audit.

No decrypted Twitch donor or original Hermes bundle was found in the inspected
local directories. The initial target is Twitch 31.6.2 build
`262872150334984303`, with original Hermes-98 SHA-256
`20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458`.
The exact identities are preserved in the
[donor inventory](TWITCH_31_6_HOTFIX_INVENTORY.json).

The required Hermes source revision remains
`40b4c8d4e22ed2b9af46aba81aec3ca8aa5e169c`, as specified in
[Building](../BUILDING.md#required-compiled-rn-validation).
The compiler, runner and donor are needed before claiming bootstrap, live
native-to-JS command delivery, read-only LegendList inspection or graft
validation. Existing JS-to-native fixture coverage does not prove the reverse
command channel under Twitch's actual RN architecture.

No modular implementation checkpoint, live activation, device performance,
UI acceptance or new IPA readiness is established by this audit. Native source,
functional Twitch behavior, build labels and public feature documentation remain
unchanged. Continue with implementation after recovering the design inputs;
retain the separate donor/Hermes, Apple-only and device acceptance boundaries.


## Input recovery follow-up — 2026-10-19

Subsequent retrieval recovered the complete original implementation brief from
an attachment in the source history. A persistent byte-preserving copy is now
`build/recovered-inputs/investigation implementation(1)(1).md`. It requires
event-driven observation in the first prototype and supersedes the architecture
proposal's snapshot-first recommendation and short armed lease. Work remains
on `dev/3.1.0`.

The original architecture proposal was located in its source history at
`docs/investigations/MODULAR_DIAGNOSTIC_RUNTIME_PROPOSAL.md`. It was an uncommitted
639-line investigation document. The history reader exposes its original
49,570-character addition but truncates each included output to 20,000
characters. Only that prefix and the subsequent small corrections have been
recovered locally. They are explicitly named
`build/recovered-inputs/MODULAR_DIAGNOSTIC_RUNTIME_PROPOSAL.partial.md` and
`build/recovered-inputs/MODULAR_DIAGNOSTIC_RUNTIME_PROPOSAL.later-corrections.patch`.
They are not a reconstructed complete proposal. Recovery provenance records
the original artifact location. Complete artifact retrieval remains unavailable
through the available authenticated access; the partial file must not be treated
as the complete architecture reference.

The downloaded donor is now present at
`/home/bananas/Agent-Stuff/tv.twitch-31.6.2.ipa`, 197,132,394 bytes. Direct hashing
matched SHA-256
`8cf72803d0e0b1aeb7c062af2d0cbac1e20f78e9f3c73fc590ac5ae9d1d29186`.
The archive identifies `tv.twitch`, version `31.6.2`, build
`262872150334984303`. Its original `Payload/Twitch.app/index.ios.bundle` is
28,682,408 bytes and matches SHA-256
`20743bcfa65117fd5683e0010d954aae1349010d375da85796a6a1de76787458`.
These checks establish the recorded input identity, not new graft validation,
packaging or device acceptance. The IPA has not been copied or modified.

`build/recovered-inputs/recovery-provenance.json` records the exact source
identifiers, truncation limit, recovered-file hashes and donor identities.
The initial missing-input findings above remain a record of the first audit;
this follow-up resolves the original brief and donor inputs, while the complete
proposal and local Hermes toolchain remain outstanding. Runtime code is unchanged.


## Workspace organization follow-up — 2026-10-19

The workspace root remains `/home/bananas/Agent-Stuff/streamside`. Its Git
checkout is now `/home/bananas/Agent-Stuff/streamside/repo`. The checkout was
moved intact, including `.git`, staged changes, toolchain, caches and baseline
artifacts. Pre/post relocation checks confirmed the same HEAD, branch, status,
staged diff and unstaged diff. No source or Git history was rewritten.

Original donor packages are in `../donors/` relative to the repository.
The verified Twitch 31.6.2 IPA and its download metadata moved there without
copying or changing the package. Reference documents are in `../references/`;
the recovery excerpts and provenance moved from `build/recovered-inputs/` to
`../references/recovery/`, outside build cleanup.

The complete architecture proposal is now available as
`../references/MODULAR_DIAGNOSTIC_RUNTIME_PROPOSAL.md`: 50,166 bytes, 644 lines,
SHA-256 `36779fced095c425bd886a597dd7a9b3d149d2a6cfb8da6cead06a888464a580`.
Its opening matches the recovered prefix, it includes all three later
corrections, and its JSON example parses. Both implementation briefs are also
in `../references/`. The later brief requires event observation in the first
prototype and long-session arming; it supersedes the proposal's snapshot-first
recommendation and 60-second armed lease.

The earlier paths and missing-input statements above describe the initial
baseline and recovery stages. Current input locations and hashes are recorded
outside the repository in `../references/recovery/current-inputs.json`;
the movement audit is `workspace-relocation-2026-10-19.json` in that directory.
The complete design inputs and exact donor are available. The local pinned
Hermes compiler/runner and remaining implementation/device validation are still
outstanding. Future repository commands run from the `repo/` checkout.
