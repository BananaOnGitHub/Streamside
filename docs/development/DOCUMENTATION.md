# Documentation maintenance

Streamside's documentation describes the maintained implementation and preserves the evidence behind it. Each document has a defined purpose, so readers can find a complete explanation without reconciling several competing versions.

## Document ownership

| Document | Owns |
| --- | --- |
| [README](../../README.md) | Features, installation, setup, updates, and removal. |
| [Changelog](../../CHANGELOG.md) | Changes in published releases. A clearly marked unreleased entry may collect completed changes for the next release. |
| [Architecture](../ARCHITECTURE.md) | System design, subsystem relationships, state ownership, and integration boundaries. |
| [Feature documents](../features/) | Current implementation details, algorithms, lifecycle, fallback behavior, and feature-specific limitations. The [third-party emote guides](../features/third-party-emotes/README.md) divide that subsystem into its individual features. |
| [Compatibility](../COMPATIBILITY.md) | Supported Twitch versions and configurations, validation scope, and known compatibility limits. |
| [Troubleshooting](../TROUBLESHOOTING.md) | Practical diagnosis, recovery, and useful bug reports. |
| [Development guides](../README.md#developing-streamside) | Building, testing, packaging, and investigation methods. |
| [History](../HISTORY.md) and [archive](../archive/README.md) | Development chronology, experiments, failures, superseded approaches, and supporting technical evidence. |
| [Documentation index](../README.md) | Navigation between the current guides and historical records. |

Put each substantial explanation in its owning document and link to it from other layers. The README can summarize a feature without duplicating its implementation guide. Historical records provide evidence for a current explanation; they do not define current behavior.

## When to update

During active development, prioritize implementation, testing, and recording findings. Keep useful evidence in development notes, investigation records, or commits: what changed, why, what was tested, what failed, and what remains unresolved. Include source revisions, build labels, and artifact identities when they are needed to interpret the result.

Do not continually rewrite public-facing guides around experiments or unfinished behavior. At feature freeze, review the completed implementation and update all affected documentation before publication. Finalize the release's changelog entry against the changes since the previous published version.

Correct inaccurate security or compatibility information immediately, even during active development. If support or safety is uncertain, narrow the claim and state the known limit while further investigation continues.

## Preserve development evidence

Never silently erase failed experiments, superseded approaches, or unique technical findings. When replacing an explanation, carry still-relevant information into its current owner and preserve the remaining evidence in History or the archive.

Historical records should retain their original scope and outcome. Add a clearly separated correction or supersession note when later evidence changes the conclusion. Identify the relevant build, Twitch donor, source revision, successor document, and validation limits where available.

Keep recorded artifact hashes attached to the artifacts they originally described. A replacement asset gets its own identity and explanation. Do not rewrite an earlier result as though the replacement or corrected approach had always existed.

When moving records, update the archive index and affected links. Preserve distinct branch closure records and make their source revisions traceable.

## Writing standards

Write in a natural maintainer voice, with direct descriptions of behavior, decisions, and evidence. Keep references to prompts, conversations, and drafting instructions out of repository documentation.

Separate current behavior from proposals and historical observations. Explain limitations where they affect use or maintenance. Prefer source and test links over repeated explanations.

Compatibility and validation claims must have supporting evidence. Distinguish host tests, donor inspection, package verification, CI, and device testing. Record failures and skips accurately; a skipped check is not a pass. Successful packaging does not establish device compatibility, and clean playback alone does not establish ad suppression.

Use exact version and build identities when the distinction matters. Do not infer a Twitch package's supported iOS floor from Streamside's framework metadata, or extend one tested configuration to other devices, signers, or jailbreak installations without evidence.

## Review at feature freeze

Compare affected documents with the final source, tests, candidate artifacts, and supported Twitch versions. Check that:

- Feature descriptions match the retained implementation, including fallback behavior and known limits.
- Test and validation claims match actual results and identify their scope.
- Version labels, artifact identities, installation instructions, and compatibility information agree.
- The changelog describes changes since the previous published release and uses the correct publication status.
- Development findings have been incorporated or preserved with traceable references.
- Links, source paths, archive navigation, attribution, and documentation included in packages remain correct.

Resolve contradictions before publication. Document unresolved limits explicitly rather than treating missing evidence as successful validation.

## Updating this guide

When the documentation structure changes, update this policy in the same change. Revise the ownership table, links, and timing or review guidance affected by the new structure. Update the documentation index and other references alongside it.

For a split or merged guide, assign each subject a clear owner and preserve unique content before removing the old location. Explain the change in the commit so the new organization remains traceable. Keep this guide aligned with the maintained structure without turning it into a record of every past layout.
